from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from traccia.cli import app
from traccia.config import load_config, write_config
from traccia.parsers import parse_document
from traccia.storage import Storage


def initialize_repo(runner: CliRunner, project_root: Path) -> None:
    result = runner.invoke(app, ["init", str(project_root)])
    assert result.exit_code == 0, result.stdout
    config = load_config(project_root / "config" / "config.yaml")
    config.backend.provider = "fake"
    write_config(project_root / "config" / "config.yaml", config)


def test_parse_document_classifies_broad_export_categories(tmp_path: Path) -> None:
    profile_path = tmp_path / "twitter-profile.md"
    profile_path.write_text("Python engineer and Rust hobbyist.\n")

    history_path = tmp_path / "google-search-history.json"
    history_path.write_text(json.dumps({"query": "cnc machining tolerancing"}))

    ai_path = tmp_path / "claude-conversation.md"
    ai_path.write_text("User: I debugged a Python parser today.\nAssistant: Good.\n")

    profile_doc = parse_document(profile_path, project_relative_path=Path("exports/twitter-profile.md"))
    history_doc = parse_document(history_path, project_relative_path=Path("exports/google-search-history.json"))
    ai_doc = parse_document(ai_path, project_relative_path=Path("exports/claude-conversation.md"))

    assert profile_doc.source.source_category.value == "social_or_community_trace"
    assert history_doc.source.source_category.value == "platform_export_activity"
    assert ai_doc.source.source_category.value == "ai_dialogue"


def test_parse_document_normalizes_chat_json_exports(tmp_path: Path) -> None:
    chat_export = tmp_path / "chatgpt-export.json"
    chat_export.write_text(
        json.dumps(
            {
                "title": "Parser Debugging Session",
                "messages": [
                    {
                        "role": "user",
                        "content": "I debugged a Python parser and reviewed the release checklist.",
                        "created_at": "2025-03-02T10:15:00Z",
                    },
                    {
                        "role": "assistant",
                        "content": "The parser fix and review flow both point to Python work.",
                        "created_at": "2025-03-02T10:16:00Z",
                    },
                ],
            }
        )
    )

    document = parse_document(
        chat_export,
        project_relative_path=Path("exports/chatgpt-export.json"),
    )

    assert document.source.source_type.value == "chat"
    assert document.source.source_category.value == "ai_dialogue"
    assert document.source.parser == "ai-conversation-json"
    assert document.source.metadata["structured_export_kind"] == "ai_conversation"
    assert len(document.spans) == 2
    assert document.spans[0].heading == "user"
    assert "User: I debugged a Python parser" in document.text


def test_parse_document_normalizes_reddit_json_exports(tmp_path: Path) -> None:
    reddit_export = tmp_path / "reddit-export.json"
    reddit_export.write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "subreddit": "learnpython",
                        "title": "Built a SQLite migration helper",
                        "selftext": "I debugged the parser and shipped the tool this weekend.",
                        "created_utc": 1740916800,
                    }
                ],
                "comments": [
                    {
                        "subreddit": "metalworking",
                        "body": "I built a Python CNC toolpath visualizer for the workshop.",
                        "created_utc": 1741003200,
                    }
                ],
            }
        )
    )

    document = parse_document(
        reddit_export,
        project_relative_path=Path("exports/reddit-export.json"),
    )

    assert document.source.source_category.value == "social_or_community_trace"
    assert document.source.parser == "reddit-export-json"
    assert document.source.metadata["structured_export_kind"] == "reddit_activity"
    assert len(document.spans) == 2
    assert "r/learnpython" in document.text
    assert "toolpath visualizer" in document.text


def test_parse_document_normalizes_google_activity_json_exports(tmp_path: Path) -> None:
    google_export = tmp_path / "google-activity.json"
    google_export.write_text(
        json.dumps(
            [
                {
                    "header": "Search",
                    "title": "Searched for CNC machining tolerances",
                    "titleUrl": "https://www.google.com/search?q=cnc+machining+tolerances",
                    "time": "2025-03-04T09:30:00Z",
                },
                {
                    "header": "YouTube",
                    "title": "Watched Python packaging tutorial",
                    "titleUrl": "https://www.youtube.com/watch?v=example",
                    "time": "2025-03-05T08:00:00Z",
                },
            ]
        )
    )

    document = parse_document(
        google_export,
        project_relative_path=Path("exports/google-activity.json"),
    )

    assert document.source.source_category.value == "platform_export_activity"
    assert document.source.parser == "google-activity-json"
    assert document.source.metadata["structured_export_kind"] == "google_activity"
    assert len(document.spans) == 2
    assert "CNC machining tolerances" in document.text
    assert "youtube.com" in document.text.lower()


def test_self_presentation_profile_does_not_auto_create_skill(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "profile-corpus"
    corpus_root.mkdir()
    profile = corpus_root / "reddit-profile.md"
    profile.write_text("Python engineer. Rust enthusiast. Builder. Problem solver.\n")

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    node_names = {node["name"] for node in graph["nodes"]}
    assert "Python" not in node_names

    review_queue = (tmp_path / "state" / "review_queue.jsonl").read_text()
    assert "python" in review_queue.lower()

    evidence_items = Storage(tmp_path).list_evidence()
    assert evidence_items[0].signal_class.value == "self_presentation"


def test_ai_problem_solving_trace_is_distinct_from_artifact_backed_work(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "ai-corpus"
    corpus_root.mkdir()
    conversation = corpus_root / "claude-conversation.md"
    conversation.write_text(
        "User: I debugged a Python parser and reviewed the release checklist with the assistant.\n"
    )

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    evidence_items = Storage(tmp_path).list_evidence()
    assert evidence_items[0].signal_class.value == "problem_solving_trace"

    graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    python_node = next(node for node in graph["nodes"] if node["name"] == "Python")
    assert python_node["level"] <= 2
    assert python_node["confidence"] < 0.9


def test_chat_json_export_ingests_as_ai_problem_solving_trace(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "chat-json-corpus"
    corpus_root.mkdir()
    conversation = corpus_root / "chatgpt-export.json"
    conversation.write_text(
        json.dumps(
            {
                "title": "Python Parser Work",
                "messages": [
                    {
                        "role": "user",
                        "content": "I debugged a Python parser and reviewed the migration checklist.",
                        "created_at": "2025-03-02T10:15:00Z",
                    },
                    {
                        "role": "assistant",
                        "content": "That suggests practical Python maintenance work.",
                        "created_at": "2025-03-02T10:16:00Z",
                    },
                ],
            }
        )
    )

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    evidence_items = Storage(tmp_path).list_evidence()
    assert evidence_items[0].signal_class.value == "problem_solving_trace"

    graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    python_node = next(node for node in graph["nodes"] if node["name"] == "Python")
    assert python_node["level"] <= 2
