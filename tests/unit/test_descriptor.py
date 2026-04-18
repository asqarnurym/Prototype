from PIL import Image

from pipeline.visual import descriptor


def test_description_prompt_requests_specific_natural_audio_description():
    prompt = descriptor._build_description_prompt(language="en")

    assert "natural to hear out loud" in prompt
    assert "Avoid vague filler" in prompt
    assert "most important visual change first" in prompt


def test_description_prompt_respects_language_instruction():
    prompt = descriptor._build_description_prompt(language="ru")

    assert "Отвечай на русском языке." in prompt


def test_description_generation_uses_explicit_generation_config(tmp_path, monkeypatch):
    image_path = tmp_path / "frame.png"
    Image.new("RGB", (10, 10), color="black").save(image_path)
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)

            class Response:
                text = "Concrete scene description."

            return Response()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(descriptor, "_client", None)
    monkeypatch.setattr(descriptor, "_get_description_client", lambda: FakeClient())

    result = descriptor._describe_with_model(str(image_path), "en")

    assert result == "Concrete scene description."
    assert captured["config"]["temperature"] == 0.2
    assert captured["config"]["top_p"] == 0.8
    assert captured["config"]["max_output_tokens"] >= 200
