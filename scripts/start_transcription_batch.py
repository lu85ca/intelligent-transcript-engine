#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LOG = "output/transcription/transcribe_remaining.log"
DEFAULT_PID = "output/transcription/transcribe_remaining.pid"
MSG_NO_CODEX = "This launcher starts deterministic MLX transcription only and does not invoke Codex CLI."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start MLX Whisper batch transcription in the background.")
    parser.add_argument("--log", default=DEFAULT_LOG, help=f"Log file path. Default: {DEFAULT_LOG}.")
    parser.add_argument("--pid-file", default=DEFAULT_PID, help=f"PID file path. Default: {DEFAULT_PID}.")
    parser.add_argument("--force", action="store_true", help="Pass --force to transcribe_audio_mlx.py.")
    parser.add_argument("--json", action="store_true", help="Print a JSON report.")
    parser.add_argument("--dry-run", action="store_true", help="Show pending audio files without starting transcription.")
    return parser.parse_args()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_path(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid(pid_file: Path) -> int | None:
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def pending_audio(root: Path, force: bool) -> list[Path]:
    audio_dir = root / "input" / "audio"
    raw_dir = root / "input" / "transcripts" / "raw"
    if not audio_dir.exists():
        return []
    pending: list[Path] = []
    for audio in sorted(audio_dir.glob("*.wav"), key=lambda item: item.name.lower()):
        raw = raw_dir / f"{audio.stem}_raw.md"
        if force or not raw.exists():
            pending.append(audio)
    return pending


def build_command(root: Path, force: bool) -> list[str]:
    command = [sys.executable, (root / "scripts" / "transcribe_audio_mlx.py").as_posix()]
    if force:
        command.append("--force")
    return command


def status_commands(pid: int, log_path: Path, root: Path) -> dict[str, str]:
    return {
        "check_process": f"ps -p {pid} -o pid,etime,pcpu,pmem,command",
        "watch_log": f"tail -n 40 {rel(log_path, root)}",
        "check_completed_raw": (
            "python3 - <<'PY'\n"
            "from pathlib import Path\n"
            "for audio in sorted(Path('input/audio').glob('*.wav')):\n"
            "    raw = Path('input/transcripts/raw') / f'{audio.stem}_raw.md'\n"
            "    print(('DONE' if raw.exists() else 'TODO'), '|', audio.name)\n"
            "PY"
        ),
    }


def start_batch(args: argparse.Namespace, root: Path) -> tuple[dict[str, Any], int]:
    log_path = resolve_path(args.log, root)
    pid_file = resolve_path(args.pid_file, root)
    running_pid = read_pid(pid_file)
    pending = pending_audio(root, args.force)

    report: dict[str, Any] = {
        "status": None,
        "pid": None,
        "pid_file": rel(pid_file, root),
        "log_file": rel(log_path, root),
        "force": args.force,
        "pending_count": len(pending),
        "pending_audio": [rel(path, root) for path in pending],
        "command": command_for_report(build_command(root, args.force), root),
        "created_at": now_iso(),
        "notes": [MSG_NO_CODEX],
    }

    if running_pid and process_is_running(running_pid):
        report.update(
            {
                "status": "already_running",
                "pid": running_pid,
                "commands_to_check": status_commands(running_pid, log_path, root),
                "next_message_to_codex": (
                    "La trascrizione batch e' terminata. Prosegui con review, normalizzazione, "
                    "selezione transcript, generazione detailed_notes/classification/analysis e PDF "
                    "per i nuovi video completati."
                ),
            }
        )
        return report, 0

    if args.dry_run:
        report["status"] = "dry_run"
        return report, 0

    if not pending:
        report["status"] = "nothing_to_transcribe"
        return report, 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("ab", buffering=0)
    process = subprocess.Popen(
        build_command(root, args.force),
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log_handle.close()
    pid_file.write_text(f"{process.pid}\n", encoding="utf-8")

    report.update(
        {
            "status": "started",
            "pid": process.pid,
            "commands_to_check": status_commands(process.pid, log_path, root),
            "next_message_to_codex": (
                "La trascrizione batch e' terminata. Prosegui con review, normalizzazione, "
                "selezione transcript, generazione detailed_notes/classification/analysis e PDF "
                "per i nuovi video completati."
            ),
        }
    )
    return report, 0


def command_for_report(command: list[str], root: Path) -> list[str]:
    return [rel(Path(item), root) if item.startswith("/") else item for item in command]


def print_human(report: dict[str, Any]) -> None:
    status = report["status"]
    print(f"status: {status}")
    if report.get("pid"):
        print(f"pid: {report['pid']}")
    print(f"log: {report['log_file']}")
    print(f"pending_count: {report['pending_count']}")
    if report.get("pending_audio"):
        print("pending_audio:")
        for audio in report["pending_audio"]:
            print(f"- {audio}")
    commands = report.get("commands_to_check") or {}
    if commands:
        print("\nComandi per verificare:")
        print(commands["check_process"])
        print(commands["watch_log"])
        print(commands["check_completed_raw"])
    if report.get("next_message_to_codex"):
        print("\nMessaggio successivo da inviare a Codex:")
        print(report["next_message_to_codex"])


def main() -> int:
    args = parse_args()
    root = project_root()
    report, code = start_batch(args, root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
