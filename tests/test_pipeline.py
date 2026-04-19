from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from traccia.cli import app
from traccia.config import load_config, write_config


def initialize_repo(runner: CliRunner, project_root: Path) -> None:
    result = runner.invoke(app, ["init", str(project_root)])
    assert result.exit_code == 0, result.stdout
    config = load_config(project_root / "config" / "config.yaml")
    config.backend.provider = "fake"
    write_config(project_root / "config" / "config.yaml", config)


def ingest_corpus(runner: CliRunner, project_root: Path) -> str:
    corpus_root = Path("tests/fixtures/corpus").resolve()
    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(project_root)])
    assert result.exit_code == 0, result.stdout
    return result.stdout


def copy_fixture_corpus(destination: Path) -> Path:
    shutil.copytree(Path("tests/fixtures/corpus").resolve(), destination, dirs_exist_ok=True)
    return destination


def set_mtime(path: Path, timestamp: datetime) -> None:
    epoch_seconds = timestamp.timestamp()
    path.touch()
    os.utime(path, (epoch_seconds, epoch_seconds))


def test_ingest_dir_builds_graph_and_artifacts(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    output = ingest_corpus(runner, tmp_path)

    assert "processed=4" in output

    graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    node_names = {node["name"] for node in graph["nodes"]}
    assert "Python" in node_names
    assert "SQLite" in node_names
    assert "Rust" in node_names

    tree_result = runner.invoke(app, ["tree", "--project-root", str(tmp_path)])
    assert tree_result.exit_code == 0, tree_result.stdout
    assert "Programming" in tree_result.stdout
    assert "Python" in tree_result.stdout

    explain_result = runner.invoke(app, ["explain", "python", "--project-root", str(tmp_path)])
    assert explain_result.exit_code == 0, explain_result.stdout
    assert "Level rationale" in explain_result.stdout
    assert "implemented" in explain_result.stdout.lower()

    review_result = runner.invoke(app, ["review", "--project-root", str(tmp_path)])
    assert review_result.exit_code == 0, review_result.stdout
    assert "redis" in review_result.stdout.lower()

    assert (tmp_path / "parsed").is_dir()
    assert any((tmp_path / "parsed").iterdir())
    assert any((tmp_path / "evidence").iterdir())
    assert (tmp_path / "tree" / "nodes" / "skill.python.md").exists()
    assert (tmp_path / "profile" / "skill.md").exists()
    assert (tmp_path / "viewer" / "index.html").exists()
    assert "ingest-dir" in (tmp_path / "tree" / "log.md").read_text()
    assert "review_redis" in (tmp_path / "state" / "review_queue.jsonl").read_text()


def test_reingest_skips_unchanged_files(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    ingest_corpus(runner, tmp_path)
    second_run = ingest_corpus(runner, tmp_path)

    assert "processed=0" in second_run
    assert "skipped=4" in second_run
    assert "deleted=0" in second_run

    stats_result = runner.invoke(app, ["stats", "--project-root", str(tmp_path)])
    assert stats_result.exit_code == 0, stats_result.stdout
    assert "sources: 4" in stats_result.stdout


def test_review_accept_and_alias_add_update_query_surface(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    review_result = runner.invoke(app, ["review", "--project-root", str(tmp_path)])
    assert review_result.exit_code == 0, review_result.stdout

    first_line = next(
        line for line in review_result.stdout.splitlines() if line.startswith("item_id=")
    )
    item_id = first_line.split("=", maxsplit=1)[1].strip()

    accept_result = runner.invoke(
        app, ["review", "--accept", item_id, "--project-root", str(tmp_path)]
    )
    assert accept_result.exit_code == 0, accept_result.stdout

    alias_result = runner.invoke(
        app, ["alias", "add", "skill.python", "py", "--project-root", str(tmp_path)]
    )
    assert alias_result.exit_code == 0, alias_result.stdout

    explain_result = runner.invoke(app, ["explain", "py", "--project-root", str(tmp_path)])
    assert explain_result.exit_code == 0, explain_result.stdout
    assert "# Python" in explain_result.stdout

    export_result = runner.invoke(app, ["export", "obsidian", "--project-root", str(tmp_path)])
    assert export_result.exit_code == 0, export_result.stdout
    obsidian_root = tmp_path / "exports" / "obsidian"
    assert (obsidian_root / "Home.md").exists()
    assert (obsidian_root / "Skills" / "python.md").exists()
    assert (obsidian_root / "Domains" / "programming.md").exists()
    assert (obsidian_root / "Evidence").is_dir()
    assert "[[Domains/programming|Programming]]" in (obsidian_root / "Skills" / "python.md").read_text()

    tree_result = runner.invoke(app, ["tree", "--project-root", str(tmp_path)])
    assert "Redis" in tree_result.stdout


def test_ingest_dir_retracts_deleted_sources_and_pending_reviews(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    corpus_root = copy_fixture_corpus(tmp_path / "corpus")

    first_run = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert first_run.exit_code == 0, first_run.stdout
    assert "deleted=0" in first_run.stdout

    (corpus_root / "notes.md").unlink()
    second_run = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert second_run.exit_code == 0, second_run.stdout
    assert "deleted=1" in second_run.stdout

    graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    node_names = {node["name"] for node in graph["nodes"]}
    assert "Rust" not in node_names
    assert "review_redis" not in (tmp_path / "state" / "review_queue.jsonl").read_text()


def test_old_evidence_marks_skill_historical(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "historical-corpus"
    corpus_root.mkdir()
    python_file = corpus_root / "python.md"
    python_file.write_text("I built a Python migration tool and debugged the release pipeline.\n")
    set_mtime(python_file, datetime.now(tz=UTC) - timedelta(days=420))

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    python_node = next(node for node in graph["nodes"] if node["name"] == "Python")
    assert python_node["freshness"] == "historical"
    assert python_node["historicalPeakLevel"] >= python_node["level"]
    assert python_node["firstSeenAt"] is not None
    assert python_node["acquiredAt"] == python_node["firstStrongEvidenceAt"]
    assert python_node["acquisitionBasis"] == "strong_evidence"
    assert python_node["coreSelfCentrality"] >= 0


def test_historical_peak_survives_weaker_reingest(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "peak-corpus"
    corpus_root.mkdir()
    python_file = corpus_root / "python.md"
    python_file.write_text("I built a Python CLI, debugged the parser, and implemented the release tooling.\n")

    first_run = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert first_run.exit_code == 0, first_run.stdout

    initial_graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    initial_python = next(node for node in initial_graph["nodes"] if node["name"] == "Python")

    python_file.write_text("I studied Python packaging patterns.\n")
    second_run = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert second_run.exit_code == 0, second_run.stdout

    weakened_graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    weakened_python = next(node for node in weakened_graph["nodes"] if node["name"] == "Python")
    assert weakened_python["level"] <= initial_python["level"]
    assert weakened_python["historicalPeakLevel"] == initial_python["level"]
    assert weakened_python["historicalPeakAt"] is not None
    assert weakened_python["firstStrongEvidenceAt"] is not None


def test_studied_skill_sets_first_learned_and_acquired_timestamp(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "study-corpus"
    corpus_root.mkdir()
    python_file = corpus_root / "python-study.md"
    python_file.write_text("I studied Python packaging patterns and researched release workflows.\n")
    set_mtime(python_file, datetime.now(tz=UTC) - timedelta(days=14))

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    python_node = next(node for node in graph["nodes"] if node["name"] == "Python")
    assert python_node["firstLearnedAt"] is not None
    assert python_node["acquiredAt"] == python_node["firstLearnedAt"]
    assert python_node["acquisitionBasis"] == "learning_evidence"


def test_rendering_redacts_secret_like_values_when_raw_export_is_enabled(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    config = load_config(tmp_path / "config" / "config.yaml")
    config.privacy.allow_raw_excerpt_export = True
    write_config(tmp_path / "config" / "config.yaml", config)

    corpus_root = tmp_path / "secret-corpus"
    corpus_root.mkdir()
    secret_file = corpus_root / "leak.py"
    secret = "OPENAI_API_KEY=sk-live-1234567890abcdefghijklmnopqrstuv"
    secret_file.write_text(f"{secret}\nprint('built parser')\n")

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    node_page = (tmp_path / "tree" / "nodes" / "skill.python.md").read_text()
    assert "[REDACTED]" in node_page
    assert secret not in node_page
    assert "Core-self centrality" in node_page
    assert "First strong evidence" in node_page
