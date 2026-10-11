#!/usr/bin/env python3
"""Validate template packs and build release ZIPs/checksums."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import sys
import unicodedata
import urllib.parse
import zipfile
from pathlib import Path, PurePosixPath

HTML_MARKUP = re.compile(r"</?[A-Za-z][^>]*>|<!--|<!\[CDATA\[|<!DOCTYPE", re.IGNORECASE)
DANGEROUS_SCHEME = re.compile(r"(?:javascript|vbscript|data|file):", re.IGNORECASE)
IGNORED_FILE = ".gitkeep"
SUPPORTED_DATA_FORMATS = {".csv", ".json"}


def fail(message: str) -> None:
    raise ValueError(message)


def validate_text(path: Path, text: str, *, allow_empty: bool = False) -> None:
    if not allow_empty and not text.strip():
        fail(f"{path}: file is empty.")
    if HTML_MARKUP.search(text):
        fail(f"{path}: raw HTML is not allowed in templates.")

    normalized = html.unescape(urllib.parse.unquote(text))
    normalized = "".join(
        character
        for character in normalized
        if not character.isspace() and not unicodedata.category(character).startswith("C")
    )
    if DANGEROUS_SCHEME.search(normalized):
        fail(f"{path}: dangerous URL scheme found.")


def validate_markdown(path: Path) -> None:
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        fail(f"{path}: Markdown must be valid UTF-8: {error}")
    validate_text(path, text)


def validate_data_file(path: Path) -> None:
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        fail(f"{path}: {path.suffix[1:].upper()} file must be valid UTF-8: {error}")
    validate_text(path, text)

    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text, parse_constant=lambda value: fail(f"{path}: invalid JSON value {value}."))
        except json.JSONDecodeError as error:
            fail(f"{path}: invalid JSON: {error}")

        def validate_json_strings(value: object) -> None:
            if isinstance(value, str):
                validate_text(path, value, allow_empty=True)
            elif isinstance(value, dict):
                for key, item in value.items():
                    validate_text(path, key, allow_empty=True)
                    validate_json_strings(item)
            elif isinstance(value, list):
                for item in value:
                    validate_json_strings(item)

        validate_json_strings(data)
    else:
        try:
            for row in csv.reader(io.StringIO(text, newline=""), strict=True):
                for cell in row:
                    if cell:
                        validate_text(path, cell, allow_empty=True)
        except csv.Error as error:
            fail(f"{path}: invalid CSV: {error}")


def validate_template(template_dir: Path) -> list[Path]:
    if template_dir.is_symlink():
        fail(f"{template_dir}: template directories cannot be symlinks.")

    files: list[Path] = []
    for path in sorted(template_dir.rglob("*")):
        relative_path = path.relative_to(template_dir)
        hidden_parts = [part for part in relative_path.parts if part.startswith(".")]
        if hidden_parts and not (
            relative_path.name == IGNORED_FILE and len(hidden_parts) == 1
        ):
            fail(f"{path}: hidden files and directories are not allowed.")
        if path.is_symlink():
            fail(f"{path}: symlinks are not allowed in templates.")
        if path.is_dir():
            continue
        if not path.is_file():
            fail(f"{path}: only regular files are allowed in templates.")
        if path.name == IGNORED_FILE:
            if path.stat().st_size != 0:
                fail(f"{path}: {IGNORED_FILE} placeholders must be empty.")
            files.append(path)
            continue
        suffix = path.suffix.lower()
        if suffix == ".md":
            validate_markdown(path)
        elif suffix in SUPPORTED_DATA_FORMATS:
            validate_data_file(path)
        else:
            fail(
                f"{path}: only Markdown, CSV, JSON, and {IGNORED_FILE} "
                "files are allowed."
            )

        files.append(path)

    if template_dir.name != "blank" and not any(path.name != IGNORED_FILE for path in files):
        fail(f"{template_dir}: no template files found.")
    return files


def validate_archive(archive_path: Path, files: list[Path], template_dir: Path) -> None:
    expected_names = {
        PurePosixPath(path.relative_to(template_dir).as_posix()).as_posix()
        for path in files
    }
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            fail(f"{archive_path}: duplicate paths found in ZIP archive.")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                fail(f"{archive_path}: unsafe path found in ZIP archive: {name}")
        if set(names) != expected_names:
            fail(f"{archive_path}: archived files do not match validated template files.")
        bad_file = archive.testzip()
        if bad_file is not None:
            fail(f"{archive_path}: ZIP integrity check failed for {bad_file}.")


def package_templates(root: Path, output_dir: Path) -> None:
    root = root.resolve()
    output_dir = output_dir.resolve()
    if not root.is_dir():
        fail(f"{root}: repository root is not a directory.")

    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        fail(f"{output_dir}: output directory must be empty.")

    template_dirs = sorted(
        path
        for path in root.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and path.resolve() != output_dir
    )
    if not template_dirs:
        fail(f"{root}: no template directories found.")

    checksums: list[str] = []
    for template_dir in template_dirs:
        files = validate_template(template_dir)
        if template_dir.name == "blank":
            print("Validated blank template: no downloadable archive")
            continue

        archive_path = output_dir / f"{template_dir.name}.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(template_dir).as_posix())
        validate_archive(archive_path, files, template_dir)
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        checksums.append(f"{digest}  {archive_path.name}")
        file_counts = {
            suffix: sum(path.suffix.lower() == suffix for path in files)
            for suffix in (".md", ".csv", ".json")
        }
        summary = ", ".join(
            f"{count} {suffix[1:].upper() if suffix != '.md' else 'Markdown'}"
            for suffix, count in file_counts.items()
            if count
        )
        print(f"Validated {template_dir.name}: {summary} file(s)")

    (output_dir / "checksums.txt").write_text(
        "\n".join(checksums) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root containing the template directories",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist"),
        help="empty directory where ZIP files and checksums.txt are written",
    )
    arguments = parser.parse_args()

    try:
        package_templates(arguments.root, arguments.output_dir)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"Template validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
