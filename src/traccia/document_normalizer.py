from __future__ import annotations

import importlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from pypdf import PdfReader

from traccia.config import TracciaConfig
from traccia.models import SourceType

DOCUMENT_SOURCE_TYPES = {SourceType.PDF, SourceType.DOCX}
AUTO_PDF_DOCUMENT_PROVIDERS = ("marker", "docling", "markitdown", "native")
AUTO_DOCX_DOCUMENT_PROVIDERS = ("docling", "markitdown", "native")
AUTO_OCR_PROVIDER = "auto"
NO_OCR_PROVIDER = "none"


@dataclass(slots=True)
class DocumentNormalizationResult:
    text: str
    parser: str
    metadata: dict[str, Any]


def normalize_document(
    path: Path,
    *,
    source_type: SourceType,
    config: TracciaConfig | None = None,
) -> DocumentNormalizationResult:
    if source_type not in DOCUMENT_SOURCE_TYPES:
        raise ValueError(f"Unsupported document source type: {source_type}")

    provider = config.document_normalization.provider if config else "auto"
    ocr_provider = config.document_normalization.ocr_provider if config else AUTO_OCR_PROVIDER
    provider_sequence = _provider_sequence(source_type=source_type, provider=provider)
    failures: list[str] = []

    for candidate_provider in provider_sequence:
        try:
            if candidate_provider == "marker":
                return _normalize_document_marker(
                    path=path,
                    source_type=source_type,
                    ocr_provider=ocr_provider,
                )
            if candidate_provider == "docling":
                return _normalize_document_docling(
                    path=path,
                    source_type=source_type,
                    ocr_provider=ocr_provider,
                )
            if candidate_provider == "markitdown":
                return _normalize_document_markitdown(path=path)
            if candidate_provider == "native":
                return _normalize_document_native(path=path, source_type=source_type)
        except RuntimeError as exc:
            failures.append(f"{candidate_provider}: {exc}")
            if provider != "auto":
                raise

    joined_failures = "; ".join(failures) if failures else "no providers attempted"
    raise RuntimeError(f"Document normalization failed: {joined_failures}")


def _provider_sequence(*, source_type: SourceType, provider: str) -> tuple[str, ...]:
    if provider == "auto":
        if source_type == SourceType.PDF:
            return AUTO_PDF_DOCUMENT_PROVIDERS
        return AUTO_DOCX_DOCUMENT_PROVIDERS
    supported_providers = {"marker", "docling", "markitdown", "native"}
    if provider in supported_providers:
        return (provider,)
    raise ValueError(f"Unsupported document_normalization.provider: {provider}")


def _normalize_document_marker(
    *,
    path: Path,
    source_type: SourceType,
    ocr_provider: str,
) -> DocumentNormalizationResult:
    if source_type != SourceType.PDF:
        raise RuntimeError("marker is currently wired only for PDFs in traccia.")

    command = [
        "marker_single",
        str(path),
        "--output_format",
        "markdown",
    ]
    if ocr_provider != NO_OCR_PROVIDER:
        command.append("--force_ocr")

    try:
        with tempfile.TemporaryDirectory(prefix="traccia-marker-") as output_dir:
            command.extend(["--output_dir", output_dir])
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
                raise RuntimeError(f"marker_single failed: {stderr}")

            markdown_path = _find_marker_markdown(Path(output_dir), source_path=path)
            text = markdown_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(
            "marker is not installed. Install the optional `marker` dependency to use the "
            "preferred PDF markdown path."
        ) from exc

    resolved_ocr_provider = "marker-force-ocr" if ocr_provider != NO_OCR_PROVIDER else NO_OCR_PROVIDER
    return DocumentNormalizationResult(
        text=text,
        parser="marker",
        metadata={
            "document_normalizer": "marker",
            "document_normalization_mode": "markdown",
            "document_ocr_provider": resolved_ocr_provider,
            "document_ocr_requested": ocr_provider != NO_OCR_PROVIDER,
            "document_ocr_used": ocr_provider != NO_OCR_PROVIDER,
        },
    )


def _find_marker_markdown(output_dir: Path, *, source_path: Path) -> Path:
    markdown_paths = sorted(output_dir.rglob("*.md"))
    if not markdown_paths:
        raise RuntimeError("marker completed without producing a markdown artifact.")

    exact_matches = [path for path in markdown_paths if path.stem == source_path.stem]
    if exact_matches:
        return exact_matches[0]
    if len(markdown_paths) == 1:
        return markdown_paths[0]
    raise RuntimeError("marker produced multiple markdown artifacts and none matched the source stem.")


def _normalize_document_docling(
    *,
    path: Path,
    source_type: SourceType,
    ocr_provider: str,
) -> DocumentNormalizationResult:
    try:
        converter_module = importlib.import_module("docling.document_converter")
        base_models_module = importlib.import_module("docling.datamodel.base_models")
        pipeline_options_module = importlib.import_module("docling.datamodel.pipeline_options")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "docling is not installed. Install the optional `docling` dependency to use "
            "the preferred local markdown normalization path."
        ) from exc

    document_converter = converter_module.DocumentConverter
    document = None
    resolved_ocr_provider = NO_OCR_PROVIDER

    if source_type == SourceType.PDF:
        pdf_pipeline_options = pipeline_options_module.PdfPipelineOptions()
        requested_ocr = ocr_provider != NO_OCR_PROVIDER
        pdf_pipeline_options.do_ocr = requested_ocr
        if requested_ocr:
            pdf_pipeline_options.ocr_options = _docling_ocr_options(
                pipeline_options_module=pipeline_options_module,
                ocr_provider=ocr_provider,
            )
            resolved_ocr_provider = _resolved_docling_ocr_provider(ocr_provider)

        converter = document_converter(
            format_options={
                base_models_module.InputFormat.PDF: converter_module.PdfFormatOption(
                    pipeline_options=pdf_pipeline_options,
                )
            }
        )
        document = converter.convert(path).document
    else:
        converter = document_converter()
        document = converter.convert(path).document

    text = document.export_to_markdown()
    return DocumentNormalizationResult(
        text=text,
        parser="docling",
        metadata={
            "document_normalizer": "docling",
            "document_normalization_mode": "markdown",
            "document_ocr_provider": resolved_ocr_provider,
            "document_ocr_requested": ocr_provider != NO_OCR_PROVIDER,
            "document_ocr_used": resolved_ocr_provider != NO_OCR_PROVIDER,
        },
    )


def _docling_ocr_options(*, pipeline_options_module: Any, ocr_provider: str) -> Any:
    provider_map = {
        AUTO_OCR_PROVIDER: "OcrAutoOptions",
        "tesseract": "TesseractOcrOptions",
        "tesseract_cli": "TesseractCliOcrOptions",
        "easyocr": "EasyOcrOptions",
        "rapidocr": "RapidOcrOptions",
    }
    option_class_name = provider_map.get(ocr_provider)
    if option_class_name is None:
        raise ValueError(f"Unsupported document_normalization.ocr_provider: {ocr_provider}")

    option_class = getattr(pipeline_options_module, option_class_name, None)
    if option_class is None:
        raise RuntimeError(
            f"Docling OCR backend {ocr_provider} is unavailable in the installed docling build."
        )
    return option_class()


def _resolved_docling_ocr_provider(ocr_provider: str) -> str:
    if ocr_provider == AUTO_OCR_PROVIDER:
        return "docling-auto"
    return f"docling-{ocr_provider}"


def _normalize_document_markitdown(*, path: Path) -> DocumentNormalizationResult:
    try:
        markitdown_module = importlib.import_module("markitdown")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "markitdown is not installed. Install the optional `markitdown` dependency to use "
            "markdown-preserving fallback normalization."
        ) from exc

    converter = markitdown_module.MarkItDown(enable_plugins=False)
    result = converter.convert(path)
    text = getattr(result, "text_content", None)
    if not isinstance(text, str):
        raise RuntimeError("markitdown conversion did not return a text_content string.")

    return DocumentNormalizationResult(
        text=text,
        parser="markitdown",
        metadata={
            "document_normalizer": "markitdown",
            "document_normalization_mode": "markdown",
            "document_ocr_provider": NO_OCR_PROVIDER,
            "document_ocr_requested": False,
            "document_ocr_used": False,
        },
    )


def _normalize_document_native(path: Path, *, source_type: SourceType) -> DocumentNormalizationResult:
    return DocumentNormalizationResult(
        text=_native_document_text(path=path, source_type=source_type),
        parser=_native_parser_name(source_type),
        metadata={
            "document_normalizer": "native",
            "document_normalization_mode": "plain_text",
            "document_ocr_provider": NO_OCR_PROVIDER,
            "document_ocr_requested": False,
            "document_ocr_used": False,
        },
    )


def _native_document_text(path: Path, *, source_type: SourceType) -> str:
    if source_type == SourceType.PDF:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if source_type == SourceType.DOCX:
        document = DocxDocument(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError(f"Unsupported document source type: {source_type}")


def _native_parser_name(source_type: SourceType) -> str:
    return {
        SourceType.PDF: "pypdf",
        SourceType.DOCX: "python-docx",
    }[source_type]
