"""Preserve text from supplied PDFs and DOCX files with the native AnyMD CLI."""
from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import date
from pathlib import Path

from ..base import CollectionAdapter
from ..models import CollectionOutput, DraftSource, ResearchRequest

_PAGE_MARKER = re.compile(r"^<!-- page ([1-9][0-9]*) -->[ \t]*$", re.MULTILINE)


def _pdf_pages(markdown: str) -> list[tuple[str, str]]:
    parts = _PAGE_MARKER.split(markdown)
    if len(parts) == 1 or parts[0].strip():
        raise ValueError("AnyMD output has text without a PDF page marker")

    pages = []
    previous = 0
    for label, text in zip(parts[1::2], parts[2::2]):
        number = int(label)
        if number <= previous:
            raise ValueError("AnyMD PDF page markers are out of order")
        previous = number
        if text.strip():
            pages.append((f"page {number}", text.strip()))
    return pages


class AnyMDAdapter(CollectionAdapter):
    name = "anymd"

    def __init__(self, executable: str = "anymd") -> None:
        self.executable = executable

    def collect(self, request: ResearchRequest) -> CollectionOutput:
        output = CollectionOutput()
        documents = request.params.get("documents", [])
        if not documents:
            output.retrieval_failures.append({"error": "supply at least one document path"})
            return output

        for document in documents[:request.limit]:
            try:
                path = Path(document).resolve(strict=True)
                if (path.drive.startswith("\\\\") or path.suffix.lower() not in {".pdf", ".docx"}
                        or not path.is_file()):
                    raise ValueError("expected a local PDF or DOCX file")
                with path.open("rb") as original:
                    digest = hashlib.sha256()
                    for chunk in iter(lambda: original.read(1024 * 1024), b""):
                        digest.update(chunk)
            except (OSError, ValueError) as exc:
                output.retrieval_failures.append({"file_ref": str(document), "error": str(exc)})
                continue

            try:
                sections = self._convert(path)
            except OSError as exc:
                output.retrieval_failures.append({"file_ref": str(path), "error": str(exc)})
                continue
            except (ValueError, subprocess.SubprocessError) as exc:
                output.extraction_failures.append({"file_ref": str(path), "error": str(exc)})
                continue

            original_hash = digest.hexdigest()
            for locator, excerpt in sections:
                output.sources.append(DraftSource(
                    source_ref=f"anymd:{original_hash}:{locator.replace(' ', ':')}",
                    origin="file_upload", file_ref=str(path), locator=locator,
                    excerpt=excerpt, retrieved_on=date.today(),
                ))
        return output

    def _convert(self, path: Path) -> list[tuple[str, str]]:
        is_pdf = path.suffix.lower() == ".pdf"
        command = [self.executable, "--no-ocr", "--images", "none"]
        if not is_pdf:
            command.extend(["--revisions", "accept"])
        result = subprocess.run(
            [*command, "--", str(path)], stdin=subprocess.DEVNULL,
            capture_output=True, timeout=60, encoding="utf-8", check=True,
        )
        markdown = result.stdout.strip()
        sections = _pdf_pages(markdown) if is_pdf and markdown else []
        if not is_pdf and markdown:
            sections = [("document", markdown)]
        if not sections:
            raise ValueError("AnyMD found no document text")
        return sections
