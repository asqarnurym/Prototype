from types import SimpleNamespace

from pipeline import summary


def test_generate_summary_uses_description_config_fields(monkeypatch):
    """Summary generation should use the active description config keys."""
    scenes = [
        {"time": 0.0, "description": "Title slide introduces the lesson."},
        {"time": 12.0, "description": "The presenter compares two interface layouts."},
        {"time": 25.0, "description": "A checklist summarizes the accessibility settings."},
    ]
    calls = {}

    class FakeModels:
        def generate_content(self, *, model, contents):
            calls["model"] = model
            calls["contents"] = contents
            return SimpleNamespace(
                text='{"summary_points": ["Lesson overview"], "chapters": [{"time": 0.0, "title": "Intro"}]}'
            )

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(summary, "_client", None)
    monkeypatch.setattr(summary.settings, "google_cloud_project", "prototype-487106")
    monkeypatch.setattr(summary.settings, "google_cloud_location", "global")
    monkeypatch.setattr(summary.settings, "description_model", "gemini-2.5-flash")
    monkeypatch.setattr(summary, "_get_gemini_client", lambda: FakeClient())

    result = summary.generate_summary(scenes=scenes, job_id="job-1", language="en")

    assert "Lesson overview" in result["summary_points"]
    assert len(result["summary_points"]) >= 3
    assert result["chapters"] == [{"time": 0.0, "title": "Intro"}]
    assert calls["model"] == "gemini-2.5-flash"
    assert "Title slide introduces the lesson." in calls["contents"][0]
    assert "5-8 bullet points" in calls["contents"][0]


def test_generate_summary_fallback_uses_scene_content(monkeypatch):
    """Fallback summaries should stay useful when the external model is unavailable."""
    scenes = [
        {"time": 0.0, "description": "Course title and learning goals appear on screen."},
        {
            "time": 42.0,
            "description": "The instructor demonstrates keyboard shortcuts in the editor.",
        },
        {"time": 84.0, "description": "A comparison table summarizes the accessibility settings."},
    ]

    monkeypatch.setattr(summary, "_client", None)
    monkeypatch.setattr(summary.settings, "google_cloud_project", "")

    result = summary.generate_summary(scenes=scenes, job_id="job-2", language="en")

    assert len(result["summary_points"]) >= 3
    assert any("learning goals" in point.lower() for point in result["summary_points"])
    assert any("keyboard shortcuts" in point.lower() for point in result["summary_points"])
    assert not any(
        "external summarization model" in point.lower() for point in result["summary_points"]
    )
    assert len(result["chapters"]) >= 2
