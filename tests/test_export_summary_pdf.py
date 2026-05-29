from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "export_summary_pdf",
    ROOT / "scripts" / "export_summary_pdf.py",
)
export_summary_pdf = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["export_summary_pdf"] = export_summary_pdf
SPEC.loader.exec_module(export_summary_pdf)


class ExportSummaryPdfTests(unittest.TestCase):
    def write_summary(self, root: Path, basename: str = "demo", body: str = "# Demo\n\nTesto.") -> Path:
        path = root / "output" / "markdown" / f"{basename}_summary.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def run_cli(self, root: Path, args: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = ["export_summary_pdf.py", *args]
        with patch.object(export_summary_pdf, "project_root", lambda: root), patch.object(
            export_summary_pdf.sys, "argv", argv
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            code = export_summary_pdf.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_missing_markdown_fails_without_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report, code = export_summary_pdf.export_summary_pdf(
                summary_input="missing",
                output_dir_value="output/pdf",
                root=root,
            )

            self.assertEqual(code, 1)
            self.assertEqual(report["message"], export_summary_pdf.MSG_MISSING_MARKDOWN)
            self.assertFalse((root / "output" / "pdf").exists())

    def test_existing_pdf_without_force_does_not_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_summary(root)
            pdf = root / "output" / "pdf" / "demo_summary.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"existing")

            report, code = export_summary_pdf.export_summary_pdf(
                summary_input="demo",
                output_dir_value="output/pdf",
                root=root,
            )

            self.assertEqual(code, 1)
            self.assertEqual(report["message"], export_summary_pdf.MSG_EXISTING_PDF)
            self.assertEqual(pdf.read_bytes(), b"existing")

    def test_existing_pdf_with_force_proceeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_summary(root)
            pdf = root / "output" / "pdf" / "demo_summary.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"existing")

            def fake_run(command: list[str], verbose: bool) -> subprocess.CompletedProcess[str]:
                pdf.write_bytes(b"%PDF-1.7\nfake\n")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(export_summary_pdf, "dependency_status", return_value={"pandoc": True, "xelatex": True}), patch.object(
                export_summary_pdf, "run_pandoc", side_effect=fake_run
            ), patch.object(export_summary_pdf, "pdf_page_count", return_value=1):
                report, code = export_summary_pdf.export_summary_pdf(
                    summary_input="demo",
                    output_dir_value="output/pdf",
                    force=True,
                    root=root,
                )

            self.assertEqual(code, 0)
            self.assertTrue(report["created"])
            self.assertTrue(report["overwritten"])
            self.assertEqual(pdf.read_bytes(), b"%PDF-1.7\nfake\n")

    def test_output_dir_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_summary(root)
            output_dir = root / "custom" / "pdf"

            def fake_run(command: list[str], verbose: bool) -> subprocess.CompletedProcess[str]:
                Path(command[3]).write_bytes(b"%PDF-1.7\nfake\n")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(export_summary_pdf, "dependency_status", return_value={"pandoc": True, "xelatex": True}), patch.object(
                export_summary_pdf, "run_pandoc", side_effect=fake_run
            ), patch.object(export_summary_pdf, "pdf_page_count", return_value=1):
                report, code = export_summary_pdf.export_summary_pdf(
                    summary_input="demo",
                    output_dir_value=output_dir.as_posix(),
                    root=root,
                )

            self.assertEqual(code, 0)
            self.assertTrue(output_dir.exists())
            self.assertTrue((output_dir / "demo_summary.pdf").exists())
            self.assertEqual(report["output_dir"], "custom/pdf")

    def test_pandoc_command_construction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_summary(root)
            output = root / "output" / "pdf" / "demo_summary.pdf"

            command = export_summary_pdf.build_pandoc_command(
                source_markdown=source,
                output_pdf=output,
                pdf_engine="xelatex",
                title="Titolo",
                toc=True,
            )

            self.assertEqual(command[0], "pandoc")
            self.assertIn(source.as_posix(), command)
            self.assertIn(output.as_posix(), command)
            self.assertIn("--pdf-engine=xelatex", command)
            self.assertIn("--standalone", command)
            self.assertIn("--metadata", command)
            self.assertIn("title=Titolo", command)
            self.assertIn("--toc", command)

    def test_json_output_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_summary(root)

            def fake_run(command: list[str], verbose: bool) -> subprocess.CompletedProcess[str]:
                Path(command[3]).write_bytes(b"%PDF-1.7\nfake\n")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(export_summary_pdf, "dependency_status", return_value={"pandoc": True, "xelatex": True}), patch.object(
                export_summary_pdf, "run_pandoc", side_effect=fake_run
            ), patch.object(export_summary_pdf, "pdf_page_count", return_value=1):
                code, stdout, _ = self.run_cli(root, ["demo", "--output-dir", "output/pdf", "--json"])

            self.assertEqual(code, 0)
            report = json.loads(stdout)
            for field in {
                "source_markdown",
                "output_pdf",
                "output_dir",
                "pdf_engine",
                "created",
                "validation",
                "created_at",
            }:
                self.assertIn(field, report)
            self.assertTrue(report["created"])

    def test_source_markdown_is_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_summary(root, body="# Demo\n\nContenuto originale.")
            before = source.read_text(encoding="utf-8")

            def fake_run(command: list[str], verbose: bool) -> subprocess.CompletedProcess[str]:
                Path(command[3]).write_bytes(b"%PDF-1.7\nfake\n")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(export_summary_pdf, "dependency_status", return_value={"pandoc": True, "xelatex": True}), patch.object(
                export_summary_pdf, "run_pandoc", side_effect=fake_run
            ), patch.object(export_summary_pdf, "pdf_page_count", return_value=1):
                report, code = export_summary_pdf.export_summary_pdf(
                    summary_input="demo",
                    output_dir_value="output/pdf",
                    root=root,
                )

            self.assertEqual(code, 0)
            self.assertTrue(report["created"])
            self.assertEqual(source.read_text(encoding="utf-8"), before)

    def test_does_not_create_agent_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_summary(root)

            def fake_run(command: list[str], verbose: bool) -> subprocess.CompletedProcess[str]:
                Path(command[3]).write_bytes(b"%PDF-1.7\nfake\n")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(export_summary_pdf, "dependency_status", return_value={"pandoc": True, "xelatex": True}), patch.object(
                export_summary_pdf, "run_pandoc", side_effect=fake_run
            ), patch.object(export_summary_pdf, "pdf_page_count", return_value=1):
                report, code = export_summary_pdf.export_summary_pdf(
                    summary_input="demo",
                    output_dir_value="output/pdf",
                    root=root,
                )

            self.assertEqual(code, 0)
            self.assertTrue(report["created"])
            self.assertFalse((root / "output" / "json" / "demo_classification.json").exists())
            self.assertFalse((root / "output" / "json" / "demo_analysis.json").exists())
            self.assertFalse((root / "output" / "prompts" / "demo_generated_prompt.md").exists())

    def test_path_summary_uses_parent_as_basename_for_summary_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output" / "analysis" / "demo-path" / "summary.md"
            source.parent.mkdir(parents=True)
            source.write_text("# Demo path\n\nTesto.", encoding="utf-8")

            resolved, basename, input_type = export_summary_pdf.resolve_summary_input(source.as_posix(), root)

            self.assertEqual(resolved, source)
            self.assertEqual(basename, "demo-path")
            self.assertEqual(input_type, "path")

    def test_detailed_notes_path_uses_detailed_notes_pdf_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output" / "markdown" / "demo_detailed_notes.md"
            source.parent.mkdir(parents=True)
            source.write_text("# Demo notes\n\nTesto.", encoding="utf-8")
            expected_pdf = root / "output" / "pdf" / "demo_detailed_notes.pdf"

            def fake_run(command: list[str], verbose: bool) -> subprocess.CompletedProcess[str]:
                Path(command[3]).write_bytes(b"%PDF-1.7\nfake\n")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch.object(export_summary_pdf, "dependency_status", return_value={"pandoc": True, "xelatex": True}), patch.object(
                export_summary_pdf, "run_pandoc", side_effect=fake_run
            ), patch.object(export_summary_pdf, "pdf_page_count", return_value=1):
                report, code = export_summary_pdf.export_summary_pdf(
                    summary_input=source.as_posix(),
                    output_dir_value="output/pdf",
                    root=root,
                )

            self.assertEqual(code, 0)
            self.assertTrue(expected_pdf.exists())
            self.assertEqual(report["output_pdf"], "output/pdf/demo_detailed_notes.pdf")

    def test_basename_prefers_detailed_notes_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = self.write_summary(root, basename="demo", body="# Legacy summary\n\nVecchio.")
            detailed = root / "output" / "markdown" / "demo_detailed_notes.md"
            detailed.write_text("# Detailed notes\n\nNuovo.", encoding="utf-8")

            resolved, basename, input_type = export_summary_pdf.resolve_summary_input("demo", root)

            self.assertEqual(resolved, detailed)
            self.assertEqual(basename, "demo")
            self.assertEqual(input_type, "basename")
            self.assertTrue(summary.exists())

    @unittest.skipUnless(
        export_summary_pdf.command_available("pandoc") and export_summary_pdf.command_available("xelatex"),
        "pandoc/xelatex not available",
    )
    def test_real_pandoc_integration_if_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "summary_test.md"
            source.write_text(
                "# Riassunto di test\n\n"
                "## Sintesi\n\n"
                "Questo e' un PDF generato da Markdown con Pandoc.\n\n"
                "## Punti principali\n\n"
                "* Primo punto\n* Secondo punto\n* Terzo punto\n",
                encoding="utf-8",
            )

            report, code = export_summary_pdf.export_summary_pdf(
                summary_input=source.as_posix(),
                output_dir_value=(root / "pdf").as_posix(),
                force=True,
                root=root,
            )

            self.assertEqual(code, 0)
            self.assertTrue((root / report["output_pdf"]).exists())
            self.assertGreater(report["file_size_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
