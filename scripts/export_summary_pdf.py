#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_PDF_ENGINES = {"xelatex", "pdflatex"}
DEFAULT_OUTPUT_DIR = "output/pdf"
COMMON_EXECUTABLE_DIRS = [
    Path("/Library/TeX/texbin"),
]

MSG_MISSING_MARKDOWN = "Summary Markdown not found."
MSG_EXISTING_PDF = "Output PDF already exists. Use --force to overwrite."
MSG_MISSING_PANDOC = "Missing dependency: pandoc. Install Pandoc before exporting PDF."
MSG_MISSING_ENGINE = "Missing PDF engine: {engine}. Install it before exporting PDF."
MSG_PANDOC_FAILED = "Pandoc failed to generate the PDF."
MSG_EMPTY_PDF = "Generated PDF is missing or empty."
MSG_NO_CODEX = "This script only converts Markdown to PDF and does not invoke Codex CLI."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a final summary Markdown file to PDF with Pandoc.")
    parser.add_argument("summary", help="Path to summary.md or transcript basename.")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory where the PDF will be written. Default: {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing PDF.")
    parser.add_argument(
        "--pdf-engine",
        default="xelatex",
        choices=sorted(ALLOWED_PDF_ENGINES),
        help="Pandoc PDF engine. Default: xelatex.",
    )
    parser.add_argument("--title", help="Optional PDF title metadata.")
    parser.add_argument("--toc", action="store_true", help="Generate a table of contents.")
    parser.add_argument("--verbose", action="store_true", help="Print Pandoc command and diagnostics to stderr.")
    parser.add_argument("--json", action="store_true", help="Print a technical JSON report to stdout.")
    parser.add_argument("--output-name", help="Custom PDF file name.")
    parser.add_argument("--open", action="store_true", help="Open the PDF after generation with macOS open.")
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


def resolve_existing_path(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def strip_summary_suffix(name: str) -> str:
    if name.endswith("_summary.md"):
        return name[: -len("_summary.md")]
    if name.endswith(".md"):
        return name[:-3]
    return name


def basename_from_summary_path(path: Path) -> str:
    if path.name == "summary.md" and path.parent.name:
        return path.parent.name
    return strip_summary_suffix(path.name)


def summary_candidates(root: Path, basename: str) -> list[Path]:
    return [
        root / "output" / "markdown" / f"{basename}_summary.md",
        root / "output" / "analysis" / basename / "summary.md",
        root / "output" / "final" / basename / "summary.md",
        root / "output" / basename / "summary.md",
    ]


def resolve_summary_input(value: str, root: Path) -> tuple[Path, str, str]:
    looks_like_path = value.endswith(".md") or "/" in value
    if looks_like_path:
        path = resolve_existing_path(value, root)
        return path, basename_from_summary_path(path), "path"

    for candidate in summary_candidates(root, value):
        if candidate.exists():
            return candidate, value, "basename"
    return summary_candidates(root, value)[0], value, "basename"


def safe_output_name(name: str) -> str:
    name = name.strip()
    name = name.replace("/", "-").replace("\\", "-")
    name = re.sub(r"[\x00-\x1f]", "", name)
    return name or "summary.pdf"


def output_pdf_path(output_dir: Path, basename: str, output_name: str | None) -> Path:
    if output_name:
        name = safe_output_name(output_name)
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf"
        return output_dir / name
    return output_dir / f"{basename}_summary.pdf"


def extract_markdown_title(path: Path) -> str | None:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                return title or None
    except OSError:
        return None
    return None


def executable_for_command(command: str) -> str | None:
    found = shutil.which(command)
    if found:
        return found
    for directory in COMMON_EXECUTABLE_DIRS:
        candidate = directory / command
        if candidate.exists() and candidate.is_file():
            return candidate.as_posix()
    return None


def command_available(command: str) -> bool:
    executable = executable_for_command(command)
    if executable is None:
        return False
    completed = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
    return completed.returncode == 0


def dependency_status(pdf_engine: str) -> dict[str, bool]:
    return {
        "pandoc": command_available("pandoc"),
        pdf_engine: command_available(pdf_engine),
    }


def build_pandoc_command(
    *,
    source_markdown: Path,
    output_pdf: Path,
    pdf_engine: str,
    title: str,
    toc: bool,
) -> list[str]:
    command = [
        "pandoc",
        source_markdown.as_posix(),
        "-o",
        output_pdf.as_posix(),
        "--standalone",
        "--from",
        "markdown",
        f"--pdf-engine={pdf_engine}",
        "--metadata",
        f"title={title}",
    ]
    if toc:
        command.append("--toc")
    return command


def run_pandoc(command: list[str], verbose: bool) -> subprocess.CompletedProcess[str]:
    if verbose:
        print("Running: " + " ".join(command), file=sys.stderr)
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if verbose and completed.stdout:
        print(completed.stdout, file=sys.stderr, end="" if completed.stdout.endswith("\n") else "\n")
    if verbose and completed.stderr:
        print(completed.stderr, file=sys.stderr, end="" if completed.stderr.endswith("\n") else "\n")
    return completed


def page_count_with_pdfinfo(path: Path) -> int | None:
    if shutil.which("pdfinfo") is None:
        return None
    completed = subprocess.run(["pdfinfo", path.as_posix()], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return None
    for line in completed.stdout.splitlines():
        if line.startswith("Pages:"):
            _, value = line.split(":", 1)
            try:
                return int(value.strip())
            except ValueError:
                return None
    return None


def page_count_with_pypdf(path: Path) -> int | None:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return None
    try:
        return len(PdfReader(path.as_posix()).pages)
    except Exception:
        return None


def pdf_page_count(path: Path) -> int | None:
    return page_count_with_pdfinfo(path) or page_count_with_pypdf(path)


def base_report(
    *,
    source_markdown: Path,
    output_pdf: Path,
    output_dir: Path,
    pdf_engine: str,
    root: Path,
    created: bool,
    overwritten: bool,
) -> dict[str, Any]:
    return {
        "source_markdown": rel(source_markdown, root),
        "output_pdf": rel(output_pdf, root),
        "output_dir": rel(output_dir, root),
        "pdf_engine": pdf_engine,
        "pandoc_available": False,
        "pdf_engine_available": False,
        "created": created,
        "overwritten": overwritten,
        "file_size_bytes": None,
        "page_count": None,
        "validation": {
            "pdf_exists": False,
            "pdf_non_empty": False,
            "page_count_gt_zero": None,
        },
        "created_at": now_iso(),
        "message": None,
        "notes": [MSG_NO_CODEX],
    }


def validate_pdf(path: Path) -> tuple[int | None, dict[str, bool | None], int | None]:
    exists = path.exists()
    size = path.stat().st_size if exists else None
    non_empty = bool(size and size > 0)
    page_count = pdf_page_count(path) if non_empty else None
    return (
        page_count,
        {
            "pdf_exists": exists,
            "pdf_non_empty": non_empty,
            "page_count_gt_zero": (page_count > 0) if page_count is not None else None,
        },
        size,
    )


def export_summary_pdf(
    *,
    summary_input: str,
    output_dir_value: str,
    pdf_engine: str = "xelatex",
    force: bool = False,
    title: str | None = None,
    toc: bool = False,
    output_name: str | None = None,
    open_pdf: bool = False,
    verbose: bool = False,
    root: Path | None = None,
) -> tuple[dict[str, Any], int]:
    root = root or project_root()
    source_markdown, basename, _ = resolve_summary_input(summary_input, root)
    output_dir = resolve_existing_path(output_dir_value, root)
    output_pdf = output_pdf_path(output_dir, basename, output_name)
    overwritten = output_pdf.exists() and force
    report = base_report(
        source_markdown=source_markdown,
        output_pdf=output_pdf,
        output_dir=output_dir,
        pdf_engine=pdf_engine,
        root=root,
        created=False,
        overwritten=overwritten,
    )

    if not source_markdown.exists():
        report["message"] = MSG_MISSING_MARKDOWN
        return report, 1

    if output_pdf.exists() and not force:
        report["message"] = MSG_EXISTING_PDF
        page_count, validation, size = validate_pdf(output_pdf)
        report["page_count"] = page_count
        report["validation"] = validation
        report["file_size_bytes"] = size
        return report, 1

    status = dependency_status(pdf_engine)
    report["pandoc_available"] = status["pandoc"]
    report["pdf_engine_available"] = status[pdf_engine]
    if not status["pandoc"]:
        report["message"] = MSG_MISSING_PANDOC
        return report, 1
    if not status[pdf_engine]:
        report["message"] = MSG_MISSING_ENGINE.format(engine=pdf_engine)
        return report, 1

    output_dir.mkdir(parents=True, exist_ok=True)
    if output_pdf.exists() and force:
        output_pdf.unlink()

    pdf_title = title or extract_markdown_title(source_markdown) or basename
    resolved_pdf_engine = executable_for_command(pdf_engine) or pdf_engine
    command = build_pandoc_command(
        source_markdown=source_markdown,
        output_pdf=output_pdf,
        pdf_engine=resolved_pdf_engine,
        title=pdf_title,
        toc=toc,
    )
    report["pandoc_command"] = command

    completed = run_pandoc(command, verbose=verbose)
    if completed.returncode != 0:
        report["message"] = MSG_PANDOC_FAILED
        report["returncode"] = completed.returncode
        report["stderr"] = completed.stderr
        return report, 1

    page_count, validation, size = validate_pdf(output_pdf)
    report["page_count"] = page_count
    report["validation"] = validation
    report["file_size_bytes"] = size
    if not validation["pdf_exists"] or not validation["pdf_non_empty"]:
        report["message"] = MSG_EMPTY_PDF
        return report, 1

    report["created"] = True
    report["message"] = "PDF exported successfully."

    if open_pdf:
        subprocess.run(["open", output_pdf.as_posix()], check=False)

    return report, 0


def main() -> int:
    args = parse_args()
    report, code = export_summary_pdf(
        summary_input=args.summary,
        output_dir_value=args.output_dir,
        pdf_engine=args.pdf_engine,
        force=args.force,
        title=args.title,
        toc=args.toc,
        output_name=args.output_name,
        open_pdf=args.open,
        verbose=args.verbose,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif code == 0:
        print(report["output_pdf"])
    else:
        print(report["message"], file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
