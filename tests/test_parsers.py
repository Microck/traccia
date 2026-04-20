from __future__ import annotations

import json
import types
from pathlib import Path

import pytest
from docx import Document as DocxDocument

import traccia.document_normalizer as document_normalizer
from traccia.config import TracciaConfig
from traccia.models import SourceCategory, SourceFamily, SourceType
from traccia.parsers import ingestable_file, parse_document


def test_parse_ai_conversation_export_builds_chat_spans_with_stable_line_numbers(
    tmp_path: Path,
) -> None:
    export_path = tmp_path / "assistant-conversation.json"
    export_path.write_text(
        json.dumps(
            {
                "title": "Test Conversation",
                "messages": [
                    {
                        "role": "user",
                        "content": "First prompt",
                        "created_at": "2026-04-19T20:00:00Z",
                    },
                    {
                        "role": "assistant",
                        "content": "Second answer\nwith continuation",
                        "created_at": "2026-04-19T20:01:00Z",
                    },
                ],
            }
        )
    )

    parsed = parse_document(
        export_path,
        project_relative_path=Path("assistant-conversation.json"),
    )

    assert parsed.source.source_type == SourceType.CHAT
    assert parsed.source.source_category == SourceCategory.AI_DIALOGUE
    assert parsed.source.parser == "ai-conversation-json"
    assert len(parsed.spans) == 2
    assert parsed.spans[0].line_start == 1
    assert parsed.spans[0].line_end == 1
    assert parsed.spans[1].line_start == 3
    assert parsed.spans[1].line_end == 4
    assert parsed.text == (
        "User: First prompt\n\n"
        "Assistant: Second answer\nwith continuation"
    )


def test_parse_instagram_export_html_uses_family_normalizer(tmp_path: Path) -> None:
    export_path = tmp_path / "message_1.html"
    export_path.write_text(
        """
        <html>
          <head><style>body { color: red; }</style></head>
          <body>
            <div class="thread">
              <h1>h</h1>
              <div>no way you know them?</div>
              <a href="https://www.instagram.com/stories/example">story link</a>
              <div>may. 13, 2024 9:16 pm</div>
            </div>
          </body>
        </html>
        """
    )

    parsed = parse_document(
        export_path,
        project_relative_path=Path(
            "Instagram/export/your_instagram_activity/messages/inbox/h_123/message_1.html"
        ),
        source_family=SourceFamily.INSTAGRAM_EXPORT,
        source_family_subproduct="messages",
    )

    assert parsed.source.parser == "instagram_export-html"
    assert parsed.source.metadata["family_normalizer"] == "html-export"
    assert parsed.source.metadata["family_normalizer_record_count"] >= 1
    assert "body { color: red; }" not in parsed.text
    assert "no way you know them?" in parsed.text
    assert "https://www.instagram.com/stories/example" in parsed.text


def test_parse_twitter_archive_js_uses_family_normalizer(tmp_path: Path) -> None:
    export_path = tmp_path / "account.js"
    export_path.write_text(
        """
        window.YTD.account.part0 = [
          {
            "account": {
              "username": "JustMicrock",
              "email": "gkievfx@gmail.com",
              "createdAt": "2019-12-02T14:21:19.009Z"
            }
          }
        ];
        """
    )

    parsed = parse_document(
        export_path,
        project_relative_path=Path("Twitter/archive/data/account.js"),
        source_family=SourceFamily.TWITTER_ARCHIVE,
        source_family_subproduct="account",
    )

    assert parsed.source.parser == "twitter-ytd-json"
    assert parsed.source.metadata["family_normalizer"] == "twitter-ytd-js"
    assert parsed.source.metadata["family_normalizer_kind"] == "account"
    assert "username: JustMicrock" in parsed.text
    assert "email: gkievfx@gmail.com" in parsed.text


def test_parse_reddit_export_csv_uses_family_normalizer(tmp_path: Path) -> None:
    export_path = tmp_path / "comments.csv"
    export_path.write_text(
        "subreddit,body,created_utc\nLocalLLaMA,benchmarked OCR tools,1715577360\n"
    )

    parsed = parse_document(
        export_path,
        project_relative_path=Path("Reddit/reddit-export/comments.csv"),
        source_family=SourceFamily.REDDIT_EXPORT,
        source_family_subproduct="comments",
    )

    assert parsed.source.parser == "reddit-csv"
    assert parsed.source.metadata["family_normalizer"] == "reddit-csv"
    assert parsed.source.metadata["family_normalizer_record_count"] == 1
    assert "subreddit: LocalLLaMA" in parsed.text
    assert "benchmarked OCR tools" in parsed.text


def test_ingestable_file_skips_known_binary_media_extensions(tmp_path: Path) -> None:
    image_path = tmp_path / "photo.webp"
    image_path.write_bytes(b"RIFFxxxxWEBPVP8 " + (b"\x00" * 32))

    assert ingestable_file(image_path) is False


def test_parse_docx_uses_native_document_normalizer_when_requested(tmp_path: Path) -> None:
    document_path = tmp_path / "notes.docx"
    document = DocxDocument()
    document.add_paragraph("I built a parser.")
    document.save(document_path)
    config = TracciaConfig.model_validate(
        {
            "document_normalization": {
                "provider": "native",
            }
        }
    )

    parsed = parse_document(
        document_path,
        project_relative_path=Path("notes.docx"),
        config=config,
    )

    assert parsed.source.source_type == SourceType.DOCX
    assert parsed.source.parser == "python-docx"
    assert parsed.source.metadata["document_normalizer"] == "native"
    assert parsed.source.metadata["document_ocr_used"] is False
    assert "I built a parser." in parsed.text


def test_parse_docx_auto_prefers_docling_when_available(tmp_path: Path, monkeypatch) -> None:
    document_path = tmp_path / "notes.docx"
    document_path.write_bytes(b"fake-docx")
    captured: dict[str, object] = {}

    class FakeDocumentConverter:
        def __init__(self, *args, **kwargs) -> None:
            captured["args"] = args
            captured["kwargs"] = kwargs

        def convert(self, source: Path):
            captured["source"] = source
            return types.SimpleNamespace(
                document=types.SimpleNamespace(
                    export_to_markdown=lambda: "# Notes\n\nI built a parser."
                )
            )

    def fake_import_module(name: str):
        if name == "docling.document_converter":
            return types.SimpleNamespace(DocumentConverter=FakeDocumentConverter)
        if name == "docling.datamodel.base_models":
            return types.SimpleNamespace(InputFormat=types.SimpleNamespace(PDF="pdf"))
        if name == "docling.datamodel.pipeline_options":
            return types.SimpleNamespace(PdfPipelineOptions=lambda: None)
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(document_normalizer.importlib, "import_module", fake_import_module)

    parsed = parse_document(
        document_path,
        project_relative_path=Path("notes.docx"),
    )

    assert parsed.source.parser == "docling"
    assert parsed.source.metadata["document_normalizer"] == "docling"
    assert parsed.source.metadata["document_normalization_mode"] == "markdown"
    assert parsed.source.metadata["document_ocr_provider"] == "none"
    assert captured["source"] == document_path
    assert parsed.text.startswith("# Notes")


def test_parse_pdf_auto_prefers_marker_when_available(tmp_path: Path, monkeypatch) -> None:
    document_path = tmp_path / "paper.pdf"
    document_path.write_bytes(b"%PDF-1.4 fake")
    captured: dict[str, object] = {}

    def fake_run(command, *, check, capture_output, text):
        del check, capture_output, text
        captured["command"] = command
        output_dir = Path(command[command.index("--output_dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "paper").mkdir(exist_ok=True)
        (output_dir / "paper" / "paper.md").write_text("# Parsed\n\nMarker output")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(document_normalizer.subprocess, "run", fake_run)

    parsed = parse_document(
        document_path,
        project_relative_path=Path("paper.pdf"),
    )

    assert parsed.source.parser == "marker"
    assert parsed.source.metadata["document_normalizer"] == "marker"
    assert parsed.source.metadata["document_ocr_provider"] == "marker-force-ocr"
    assert "--force_ocr" in captured["command"]
    assert "Marker output" in parsed.text


def test_parse_docx_auto_falls_back_to_markitdown_when_docling_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    document_path = tmp_path / "notes.docx"
    document_path.write_bytes(b"fake-docx")
    captured: dict[str, object] = {}

    def fake_import_module(name: str):
        if name == "docling.document_converter":
            raise ModuleNotFoundError(name)
        if name == "markitdown":
            class FakeMarkItDown:
                def __init__(self, *, enable_plugins: bool = False, **kwargs) -> None:
                    captured["enable_plugins"] = enable_plugins
                    captured["kwargs"] = kwargs

                def convert(self, source: Path):
                    captured["source"] = source
                    return types.SimpleNamespace(text_content="# Notes\n\nFallback parser.")

            return types.SimpleNamespace(MarkItDown=FakeMarkItDown)
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(document_normalizer.importlib, "import_module", fake_import_module)

    parsed = parse_document(
        document_path,
        project_relative_path=Path("notes.docx"),
    )

    assert parsed.source.parser == "markitdown"
    assert parsed.source.metadata["document_normalizer"] == "markitdown"
    assert parsed.source.metadata["document_ocr_provider"] == "none"
    assert captured["enable_plugins"] is False
    assert captured["source"] == document_path


def test_parse_pdf_auto_falls_back_to_docling_when_marker_missing(tmp_path: Path, monkeypatch) -> None:
    document_path = tmp_path / "scan.pdf"
    document_path.write_bytes(b"%PDF-1.4 fake")
    captured: dict[str, object] = {}

    def fake_run(command, *, check, capture_output, text):
        del command, check, capture_output, text
        raise FileNotFoundError("marker_single")

    class FakePdfPipelineOptions:
        def __init__(self) -> None:
            self.do_ocr = False
            self.ocr_options = None

    class FakeOcrAutoOptions:
        pass

    class FakeDocumentConverter:
        def __init__(self, *, format_options=None) -> None:
            captured["format_options"] = format_options

        def convert(self, source: Path):
            captured["source"] = source
            return types.SimpleNamespace(
                document=types.SimpleNamespace(export_to_markdown=lambda: "Docling fallback")
            )

    class FakePdfFormatOption:
        def __init__(self, *, pipeline_options) -> None:
            captured["pipeline_options"] = pipeline_options

    def fake_import_module(name: str):
        if name == "docling.document_converter":
            return types.SimpleNamespace(
                DocumentConverter=FakeDocumentConverter,
                PdfFormatOption=FakePdfFormatOption,
            )
        if name == "docling.datamodel.base_models":
            return types.SimpleNamespace(InputFormat=types.SimpleNamespace(PDF="pdf"))
        if name == "docling.datamodel.pipeline_options":
            return types.SimpleNamespace(
                PdfPipelineOptions=FakePdfPipelineOptions,
                OcrAutoOptions=FakeOcrAutoOptions,
            )
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(document_normalizer.subprocess, "run", fake_run)
    monkeypatch.setattr(document_normalizer.importlib, "import_module", fake_import_module)

    parsed = parse_document(
        document_path,
        project_relative_path=Path("scan.pdf"),
    )

    assert parsed.source.parser == "docling"
    assert parsed.source.metadata["document_normalizer"] == "docling"
    assert parsed.source.metadata["document_ocr_provider"] == "docling-auto"
    assert parsed.text == "Docling fallback"


def test_parse_docx_markitdown_missing_dependency_raises_clear_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    document_path = tmp_path / "notes.docx"
    document_path.write_bytes(b"fake-docx")

    def fake_import_module(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(document_normalizer.importlib, "import_module", fake_import_module)
    config = TracciaConfig.model_validate(
        {
            "document_normalization": {
                "provider": "markitdown",
            },
        }
    )

    with pytest.raises(RuntimeError, match="markitdown is not installed"):
        parse_document(
            document_path,
            project_relative_path=Path("notes.docx"),
            config=config,
        )


def test_parse_pdf_docling_uses_local_ocr_backend(
    tmp_path: Path,
    monkeypatch,
) -> None:
    document_path = tmp_path / "scan.pdf"
    document_path.write_bytes(b"%PDF-1.4 fake")
    captured: dict[str, object] = {}

    class FakePdfPipelineOptions:
        def __init__(self) -> None:
            self.do_ocr = False
            self.ocr_options = None

    class FakeRapidOcrOptions:
        def __init__(self) -> None:
            captured["ocr_options_class"] = "RapidOcrOptions"

    class FakeDocumentConverter:
        def __init__(self, *, format_options=None) -> None:
            captured["format_options"] = format_options

        def convert(self, source: Path):
            captured["source"] = source
            return types.SimpleNamespace(
                document=types.SimpleNamespace(
                    export_to_markdown=lambda: "Recovered local OCR markdown"
                )
            )

    class FakePdfFormatOption:
        def __init__(self, *, pipeline_options) -> None:
            captured["pipeline_options"] = pipeline_options

    def fake_import_module(name: str):
        if name == "docling.document_converter":
            return types.SimpleNamespace(
                DocumentConverter=FakeDocumentConverter,
                PdfFormatOption=FakePdfFormatOption,
            )
        if name == "docling.datamodel.base_models":
            return types.SimpleNamespace(InputFormat=types.SimpleNamespace(PDF="pdf"))
        if name == "docling.datamodel.pipeline_options":
            return types.SimpleNamespace(
                PdfPipelineOptions=FakePdfPipelineOptions,
                RapidOcrOptions=FakeRapidOcrOptions,
            )
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(document_normalizer.importlib, "import_module", fake_import_module)
    config = TracciaConfig.model_validate(
        {
            "document_normalization": {
                "provider": "docling",
                "ocr_provider": "rapidocr",
            },
        }
    )

    parsed = parse_document(
        document_path,
        project_relative_path=Path("scan.pdf"),
        config=config,
    )

    assert parsed.source.source_type == SourceType.PDF
    assert parsed.source.parser == "docling"
    assert parsed.source.metadata["document_normalizer"] == "docling"
    assert parsed.source.metadata["document_ocr_provider"] == "docling-rapidocr"
    assert parsed.source.metadata["document_ocr_requested"] is True
    assert parsed.source.metadata["document_ocr_used"] is True
    assert captured["ocr_options_class"] == "RapidOcrOptions"
    assert captured["pipeline_options"].do_ocr is True
    assert isinstance(captured["pipeline_options"].ocr_options, FakeRapidOcrOptions)
    assert captured["source"] == document_path


def test_parse_pdf_marker_can_be_disabled_explicitly(tmp_path: Path, monkeypatch) -> None:
    document_path = tmp_path / "paper.pdf"
    document_path.write_bytes(b"%PDF-1.4 fake")
    captured: dict[str, object] = {}

    class FakePdfPipelineOptions:
        def __init__(self) -> None:
            self.do_ocr = False
            self.ocr_options = None

    class FakeDocumentConverter:
        def __init__(self, *, format_options=None) -> None:
            captured["format_options"] = format_options

        def convert(self, source: Path):
            captured["source"] = source
            return types.SimpleNamespace(
                document=types.SimpleNamespace(export_to_markdown=lambda: "Docling only")
            )

    class FakePdfFormatOption:
        def __init__(self, *, pipeline_options) -> None:
            captured["pipeline_options"] = pipeline_options

    def fake_import_module(name: str):
        if name == "docling.document_converter":
            return types.SimpleNamespace(
                DocumentConverter=FakeDocumentConverter,
                PdfFormatOption=FakePdfFormatOption,
            )
        if name == "docling.datamodel.base_models":
            return types.SimpleNamespace(InputFormat=types.SimpleNamespace(PDF="pdf"))
        if name == "docling.datamodel.pipeline_options":
            return types.SimpleNamespace(
                PdfPipelineOptions=FakePdfPipelineOptions,
                OcrAutoOptions=lambda: object(),
            )
        raise ModuleNotFoundError(name)

    def forbidden_run(command, *, check, capture_output, text):
        raise AssertionError(f"marker should not run: {command}")

    monkeypatch.setattr(document_normalizer.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(document_normalizer.subprocess, "run", forbidden_run)
    config = TracciaConfig.model_validate(
        {
            "document_normalization": {
                "provider": "docling",
                "ocr_provider": "none",
            },
        }
    )

    parsed = parse_document(
        document_path,
        project_relative_path=Path("paper.pdf"),
        config=config,
    )

    assert parsed.source.parser == "docling"
    assert parsed.source.metadata["document_ocr_provider"] == "none"
    assert parsed.text == "Docling only"
