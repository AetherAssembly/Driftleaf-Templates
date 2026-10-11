import tempfile
import unittest
import zipfile
from pathlib import Path

from validate_templates import package_templates, validate_template


class TemplateValidationTests(unittest.TestCase):
    def test_accepts_markdown_and_intentional_date_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "journal"
            entry = template / "Journal" / "{{date}}.md"
            entry.parent.mkdir(parents=True)
            entry.write_text("# Journal\n\nNotes for today.\n", encoding="utf-8")

            self.assertEqual(validate_template(template), [entry])

    def test_rejects_raw_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "general"
            template.mkdir()
            (template / "note.md").write_text("<script>alert(1)</script>", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "raw HTML"):
                validate_template(template)

    def test_rejects_obfuscated_dangerous_scheme(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "general"
            template.mkdir()
            (template / "note.md").write_text(
                "[open](java%73cript:alert(1))",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "dangerous URL scheme"):
                validate_template(template)

    def test_rejects_unsupported_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "general"
            template.mkdir()
            (template / "note.md").write_text("# Notes\n", encoding="utf-8")
            (template / "payload.js").write_text("alert(1)", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "only Markdown, CSV, JSON"):
                validate_template(template)

    def test_accepts_and_packages_csv_and_json_databases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "database-template"
            template.mkdir()
            (template / "README.md").write_text("# Database template\n", encoding="utf-8")
            (template / "records.csv").write_text(
                'id,name,note\n1,Ada,"Uses a comma, safely"\n',
                encoding="utf-8",
            )
            (template / "database.json").write_text(
                '{"records": [{"id": 1, "name": "Ada", "note": ""}]}',
                encoding="utf-8",
            )
            output = root / "dist"

            package_templates(root, output)

            with zipfile.ZipFile(output / "database-template.zip") as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"README.md", "records.csv", "database.json"},
                )

    def test_accepts_data_only_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "database"
            template.mkdir()
            (template / "records.json").write_text('{"records": []}', encoding="utf-8")

            self.assertEqual(validate_template(template), [template / "records.json"])

    def test_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "database"
            template.mkdir()
            (template / "records.json").write_text('{"records": }', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                validate_template(template)

    def test_rejects_invalid_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "database"
            template.mkdir()
            (template / "records.csv").write_text('"unterminated field', encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid CSV"):
                validate_template(template)

    def test_rejects_dangerous_scheme_in_json_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "database"
            template.mkdir()
            (template / "records.json").write_text(
                '{"url": "javascript:alert(1)"}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "dangerous URL scheme"):
                validate_template(template)

    def test_rejects_nonempty_gitkeep_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "general"
            template.mkdir()
            (template / "note.md").write_text("# Notes\n", encoding="utf-8")
            (template / ".gitkeep").write_text("payload", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "placeholders must be empty"):
                validate_template(template)

    def test_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "general"
            template.mkdir()
            target = template / "note.md"
            target.write_text("# Notes\n", encoding="utf-8")
            (template / "linked.md").symlink_to(target)

            with self.assertRaisesRegex(ValueError, "symlinks"):
                validate_template(template)

    def test_packages_archives_and_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blank = root / "blank"
            blank.mkdir()
            (blank / ".gitkeep").write_text("", encoding="utf-8")
            template = root / "general"
            template.mkdir()
            (template / "note.md").write_text("# Notes\n", encoding="utf-8")
            projects = template / "Projects"
            projects.mkdir()
            (projects / "Project Notes.md").write_text("# Project Notes\n", encoding="utf-8")
            output = root / "dist"

            package_templates(root, output)

            self.assertTrue((output / "general.zip").is_file())
            self.assertFalse((output / "blank.zip").exists())
            self.assertEqual(
                sorted(path.name for path in output.glob("*.zip")),
                ["general.zip"],
            )
            with zipfile.ZipFile(output / "general.zip") as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"note.md", "Projects/Project Notes.md"},
                )
            self.assertIn("  general.zip\n", (output / "checksums.txt").read_text())


if __name__ == "__main__":
    unittest.main()
