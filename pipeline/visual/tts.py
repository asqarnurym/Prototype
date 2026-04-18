"""On-demand text-to-speech helpers for scene descriptions.

Data flow:
- input: description text plus a target language code;
- output: a dict with ``audio_path`` and ``duration_sec``;
- caller: ``api/server.py`` uses these helpers for scene playback requests.

Google TTS is preferred when credentials are configured; otherwise the module
falls back to edge-tts.
"""

import asyncio
import logging
import subprocess
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)


async def synthesize_speech_async(
    text: str,
    output_path: str,
    language: str = "en",
) -> dict:
    """Asynchronous TTS entry point used by the FastAPI layer.

    edge-tts can be awaited directly, while the synchronous Google client is
    delegated to an executor.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    runtime = settings.tts_runtime_info()

    logger.info(
        "TTS request [provider=%s language=%s auth=%s service_account=%s output=%s]",
        runtime["provider"],
        language,
        runtime["auth_mode"],
        runtime["service_account_email"],
        output_path,
    )

    if settings.tts_provider == "google":
        # Google TTS is synchronous, so run it in an executor.
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _tts_google, text, output_path, language)
    else:
        result = await _tts_edge_async(text, output_path, language)

    return result


def _tts_google(text: str, output_path: str, language: str) -> dict:
    """Synthesize speech through Google Cloud Text-to-Speech."""
    runtime = settings.tts_runtime_info()
    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechClient()

        voice_name = settings.tts_voices.get(language, settings.tts_voices["en"])["google"]
        language_code = voice_name.split("-")[0] + "-" + voice_name.split("-")[1]

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.95,  # Slightly slower speech improves accessibility.
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        with open(output_path, "wb") as f:
            f.write(response.audio_content)

        duration = _get_audio_duration(output_path)

        logger.info(
            "Google TTS succeeded [language=%s auth=%s service_account=%s output=%s duration=%.2fs]",
            language,
            runtime["auth_mode"],
            runtime["service_account_email"],
            output_path,
            duration,
        )
        return {"audio_path": output_path, "duration_sec": duration}

    except ImportError:
        logger.warning("google-cloud-texttospeech is not installed. Falling back to edge-tts.")
        return _tts_edge_sync(text, output_path, language)
    except Exception as e:
        logger.warning(
            "Google TTS failed [auth=%s service_account=%s language=%s output=%s]: %s. Falling back to edge-tts.",
            runtime["auth_mode"],
            runtime["service_account_email"],
            language,
            output_path,
            e,
        )
        return _tts_edge_sync(text, output_path, language)


def _tts_edge_sync(text: str, output_path: str, language: str) -> dict:
    """Synchronous edge-tts fallback for threaded or non-async callers."""
    try:
        import edge_tts

        voice = settings.tts_voices.get(language, settings.tts_voices["en"])["edge"]

        async def _synthesize():
            communicate = edge_tts.Communicate(text, voice, rate="-5%")
            await communicate.save(output_path)

        # Detect whether a loop is already running in this thread.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # When a loop is already running, create a fresh loop in a worker thread.
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _synthesize())
                future.result()
        else:
            # No running loop: execute normally.
            asyncio.run(_synthesize())

        duration = _get_audio_duration(output_path)

        logger.info(
            "Edge TTS succeeded [language=%s output=%s duration=%.2fs]",
            language,
            output_path,
            duration,
        )
        return {"audio_path": output_path, "duration_sec": duration}

    except ImportError as exc:
        logger.error("edge-tts is not installed. Install it with: pip install edge-tts")
        raise RuntimeError("No TTS provider is available") from exc
    except Exception as e:
        logger.error(f"Edge TTS failed: {e}")
        raise


async def _tts_edge_async(text: str, output_path: str, language: str) -> dict:
    """Native async edge-tts helper for FastAPI request handlers."""
    try:
        import edge_tts

        voice = settings.tts_voices.get(language, settings.tts_voices["en"])["edge"]
        communicate = edge_tts.Communicate(text, voice, rate="-5%")
        await communicate.save(output_path)

        duration = _get_audio_duration(output_path)

        logger.info(
            "Edge TTS async succeeded [language=%s output=%s duration=%.2fs]",
            language,
            output_path,
            duration,
        )
        return {"audio_path": output_path, "duration_sec": duration}

    except ImportError as exc:
        logger.error("edge-tts is not installed. Install it with: pip install edge-tts")
        raise RuntimeError("No TTS provider is available") from exc
    except Exception as e:
        logger.error(f"Edge TTS failed: {e}")
        raise


def _get_audio_duration(audio_path: str) -> float:
    """Measure audio duration with ffprobe when it is available."""
    try:
        cmd = [
            settings.ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return round(duration, 3)

    except (subprocess.CalledProcessError, ValueError, FileNotFoundError) as e:
        logger.warning(f"ffprobe could not determine duration: {e}. Falling back to estimation.")
        # Rough estimate based on MP3 size at approximately 128 kbps.
        try:
            file_size = Path(audio_path).stat().st_size
            estimated = file_size / 16000  # ~16 kB/s for 128 kbps MP3 audio.
        except OSError:
            estimated = 5.0  # Last-resort fallback.
        return max(estimated, 1.0)
