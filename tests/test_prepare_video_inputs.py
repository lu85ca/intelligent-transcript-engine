from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PrepareVideoInputsTests(unittest.TestCase):
    def test_long_video_path_with_spaces_is_not_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            script = scripts_dir / "prepare_video_inputs.sh"
            shutil.copy2(ROOT / "scripts" / "prepare_video_inputs.sh", script)
            script.chmod(0o755)

            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_ffmpeg = fake_bin / "ffmpeg"
            fake_ffmpeg.write_text(
                "#!/usr/bin/env bash\n"
                "out=\"${@: -1}\"\n"
                "mkdir -p \"$(dirname \"$out\")\"\n"
                "printf 'fake wav' > \"$out\"\n",
                encoding="utf-8",
            )
            fake_ffmpeg.chmod(0o755)

            video_name = "2026-05-22 17-02-34 - ROUND TABLE AI - Registrata io - Non ci capisco nulla.mkv"
            video = root / "input" / "videos" / video_name
            video.parent.mkdir(parents=True)
            video.write_text("fake video", encoding="utf-8")

            env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"}
            completed = subprocess.run(
                [script.as_posix()],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(
                (root / "output" / "preprocessing" / f"{video.stem}_preprocessing.json").read_text(
                    encoding="utf-8"
                )
            )
            command = report["command"]
            self.assertEqual(report["status"], "ok")
            self.assertEqual(command[command.index("-i") + 1], video.resolve().as_posix())
            self.assertTrue((root / "input" / "audio" / f"{video.stem}.wav").exists())


if __name__ == "__main__":
    unittest.main()
