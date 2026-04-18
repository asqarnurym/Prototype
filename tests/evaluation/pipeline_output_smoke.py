"""
pipeline_output_smoke.py — Manual end-to-end pipeline smoke check.

This script exercises the real ASR/model stack and is intentionally kept
out of default pytest discovery.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()


def _load_runtime_deps():
    from core.config import settings
    from main import process_video

    return settings, process_video


settings, process_video = _load_runtime_deps()


class PipelineOutputSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create a tiny dummy video for testing pipeline artifacts."""
        cls.test_dir = Path(tempfile.mkdtemp())
        cls.dummy_video = cls.test_dir / "dummy.mp4"

        cmd = [
            settings.ffmpeg_path,
            "-y",
            "-v",
            "quiet",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=640x480:d=1",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono:d=1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(cls.dummy_video),
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg failed to generate dummy video. Ensure ffmpeg is installed. {e}"
            ) from e

    @classmethod
    def tearDownClass(cls):
        """Clean up dummy video and its output directory."""
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_pipeline_on_demand_no_visual(self):
        """
        Verify that processing a dummy video with enable_visual=False
        generates the expected JSON and VTT artifacts.
        """
        out_dir = self.test_dir / "output_no_visual"

        result = process_video(
            video_path=str(self.dummy_video),
            language="en",
            enable_visual=False,
            output_dir=str(out_dir),
        )

        self.assertEqual(result["status"], "completed")

        self.assertIn("subtitles", result["artifacts"])
        self.assertIn("timeline", result["artifacts"])

        vtt_path = Path(result["artifacts"]["subtitles"])
        json_path = Path(result["artifacts"]["timeline"])

        self.assertTrue(vtt_path.exists())
        self.assertTrue(json_path.exists())
        self.assertTrue((out_dir / "job_meta.json").exists())

        self.assertNotIn("scene_index", result["artifacts"])


if __name__ == "__main__":
    unittest.main()
