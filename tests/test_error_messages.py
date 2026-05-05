from __future__ import annotations

from pathlib import Path

import pytest

from traccia.document_normalizer import _find_marker_markdown, _normalize_document_marker
from traccia.models import SourceType
from traccia.parsers import _parse_ai_conversation_export, detect_source_type


def test_detect_source_type_lists_supported_suffixes(tmp_path: Path) -> None:
    binary = tmp_path / "archive.bin"
    binary.write_bytes(b"\x00\x01\x02")

    with pytest.raises(ValueError, match="Supported suffixes:"):
        detect_source_type(binary)


def test_ai_conversation_error_names_source_id() -> None:
    with pytest.raises(ValueError, match="conversation.json"):
        _parse_ai_conversation_export(payload=[], source_id="conversation.json")


def test_marker_non_pdf_error_suggests_docx_alternatives(tmp_path: Path) -> None:
    docx_path = tmp_path / "sample.docx"
    docx_path.write_bytes(b"not-a-real-docx")

    with pytest.raises(RuntimeError, match="Use docling, markitdown, or native"):
        _normalize_document_marker(
            path=docx_path,
            source_type=SourceType.DOCX,
            ocr_provider="none",
        )


def test_marker_empty_output_error_names_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "marker-output"
    output_dir.mkdir()

    with pytest.raises(RuntimeError, match=str(output_dir)):
        _find_marker_markdown(output_dir, source_path=tmp_path / "source.pdf")


def test_marker_multiple_output_error_lists_artifacts(tmp_path: Path) -> None:
    (tmp_path / "one.md").write_text("one", encoding="utf-8")
    (tmp_path / "two.md").write_text("two", encoding="utf-8")

    with pytest.raises(RuntimeError, match="one.md, two.md"):
        _find_marker_markdown(tmp_path, source_path=tmp_path / "source.pdf")
