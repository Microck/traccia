from __future__ import annotations

import gzip
import json
import os
import shutil
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from traccia.cli import app
from traccia.config import default_config, load_config, write_config
from traccia.llm import BackendError, CanonicalSkillDecision, FakeLLMBackend, ScorePayload
from traccia.models import (
    EvidenceItem,
    EvidenceType,
    IngestManifestEntry,
    IngestMaterialStatus,
    IngestRunState,
    ParsedSpan,
    ReliabilityTier,
    SignalClass,
    SourceFamily,
)
from traccia.parsers import parse_document
from traccia.pipeline import (
    Pipeline,
    _build_person_skill_state,
    _chunk_document,
    _time_reference_to_datetime,
)
from traccia.rendering import _sanitize_export_text
from traccia.utils import source_id_for_relative_path


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


def latest_manifest(project_root: Path) -> dict[str, object]:
    manifest_paths = sorted(
        (project_root / "state" / "manifests").glob("*.json"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    assert manifest_paths
    return json.loads(manifest_paths[-1].read_text())


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
    python_node = next(node for node in graph["nodes"] if node["name"] == "Python")
    assert python_node["provenance"]
    python_provenance = python_node["provenance"][0]
    assert python_provenance["evidenceId"].startswith("ev_")
    assert python_provenance["sourceId"].startswith("src_")
    assert python_provenance["source"]["filename"]
    assert "relativeImportPath" not in python_provenance["source"]

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
    assert (tmp_path / "exports" / "debug" / "report.json").exists()
    assert (tmp_path / "exports" / "debug" / "report.md").exists()
    assert "ingest-dir" in (tmp_path / "tree" / "log.md").read_text()
    assert "review_redis" in (tmp_path / "state" / "review_queue.jsonl").read_text()

    debug_report = json.loads((tmp_path / "exports" / "debug" / "report.json").read_text())
    assert debug_report["counts"]["sources"] == 4
    assert debug_report["counts"]["evidence_items"] >= 4
    assert "by_type" in debug_report["sources"]
    assert "top_skills" in debug_report["skills"]


def test_time_reference_to_datetime_accepts_reduced_precision_dates() -> None:
    month_precision = _time_reference_to_datetime("2024-07")
    year_precision = _time_reference_to_datetime("2024")
    unknown_day = _time_reference_to_datetime("2025-03-XX")

    assert month_precision == datetime(2024, 7, 1, tzinfo=UTC)
    assert year_precision == datetime(2024, 1, 1, tzinfo=UTC)
    assert unknown_day == datetime(2025, 3, 1, tzinfo=UTC)


def test_build_person_skill_state_clamps_backend_scores_to_unit_interval() -> None:
    evidence = EvidenceItem(
        evidence_id="ev_score_clamp",
        source_id="src_score_clamp",
        span_start=0,
        span_end=12,
        quote="I built it.",
        evidence_type=EvidenceType.IMPLEMENTED,
        signal_class=SignalClass.ARTIFACT_BACKED_WORK,
        skill_candidates=["Python"],
        artifact_candidates=["tool"],
        time_reference="2026-04-01",
        reliability=ReliabilityTier.TIER_B,
        extractor_version="test",
        confidence=0.9,
    )
    score_payload = ScorePayload(
        level=9,
        confidence=1.5,
        recency_score=2.0,
        breadth_score=-0.2,
        depth_score=2.0,
        artifact_score=1.2,
        teaching_score=-1.0,
        freshness="active",
        status="active",
        manual_note=None,
        rationale="Out-of-range values should be normalized at the LLM boundary.",
    )

    state = _build_person_skill_state(
        skill_id="skill.python",
        evidence_items=[evidence],
        score_payload=score_payload,
        previous_row=None,
        locked=False,
    )

    assert state.level == 5
    assert state.confidence == 1.0
    assert state.breadth_score == 0.0
    assert state.depth_score == 1.0
    assert state.artifact_score == 1.0
    assert state.teaching_score == 0.0


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


def test_ingest_dir_blocks_when_large_previous_root_suddenly_appears_empty(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "large-corpus"
    corpus_root.mkdir()
    for index in range(30):
        (corpus_root / f"note-{index}.md").write_text(
            f"I built and debugged Python automation workflow #{index}.\n"
        )

    first_run = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert first_run.exit_code == 0, first_run.stdout

    for path in corpus_root.iterdir():
        path.unlink()

    second_run = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert second_run.exit_code != 0

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "blocked"
    assert "appears empty" in progress["blocked_reason"]

    run_state_paths = list((tmp_path / "state" / "ingest-runs").glob("*.json"))
    assert run_state_paths
    run_state = json.loads(run_state_paths[0].read_text())
    assert run_state["total_materials"] == 30


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
    secret = "API_KEY=redacted-test-credential"
    secret_file.write_text(f"# built parser with {secret}\n")

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    sanitized = _sanitize_export_text(secret, redact_source_paths=True)
    assert sanitized == "API_KEY=[REDACTED]"

    node_page = (tmp_path / "tree" / "nodes" / "skill.python.md").read_text()
    assert secret not in node_page
    assert "Core-self centrality" in node_page
    assert "First strong evidence" in node_page


def test_graph_provenance_includes_source_paths_when_export_redaction_is_disabled(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    config = load_config(tmp_path / "config" / "config.yaml")
    config.privacy.redact_source_paths_in_exports = False
    write_config(tmp_path / "config" / "config.yaml", config)

    corpus_root = tmp_path / "source-path-corpus"
    corpus_root.mkdir()
    source_file = corpus_root / "python-work.md"
    source_file.write_text("I built a Python parser and debugged the graph export.\n")

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    graph = json.loads((tmp_path / "graph" / "graph.json").read_text())
    python_node = next(node for node in graph["nodes"] if node["name"] == "Python")
    provenance = python_node["provenance"][0]
    assert provenance["source"]["filename"] == "python-work.md"
    assert provenance["source"]["relativeImportPath"] == "source-path-corpus/python-work.md"
    assert provenance["source"]["uri"].endswith("/source-path-corpus/python-work.md")


def test_ingest_dir_accepts_text_like_unknown_extension(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "mixed-corpus"
    corpus_root.mkdir()
    export_file = corpus_root / "activity.export"
    export_file.write_text("I built a Python parser and debugged the ingest pipeline.\n")

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "imported=1" in result.stdout
    assert "processed=1" in result.stdout

    storage = Pipeline(tmp_path).storage
    sources = storage.list_sources()
    assert len(sources) == 1
    assert sources[0]["title"] == "Activity"
    assert "activity.export" in json.loads(sources[0]["metadata_json"])["filename"]
    imported_path = tmp_path / "raw" / "imported" / "mixed-corpus" / "activity.export"
    assert imported_path.is_symlink()
    assert imported_path.resolve() == export_file.resolve()


def test_ingest_dir_accepts_gzipped_jsonl_agent_logs(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "agent-log-corpus"
    corpus_root.mkdir()
    log_path = corpus_root / "session.jsonl.gz"
    with gzip.open(log_path, "wt", encoding="utf-8") as handle:
        handle.write('{"role":"user","content":"I built a Python parser."}\n')
        handle.write('{"role":"assistant","content":"I debugged the storage layer."}\n')

    source_id, processed = Pipeline(tmp_path).ingest_file(log_path, root=corpus_root)

    assert processed is True
    source = Pipeline(tmp_path).storage.fetch_source(source_id)
    assert source["source_type"] == "text"
    parsed = json.loads((tmp_path / "parsed" / f"{source_id}.json").read_text())
    assert "I built a Python parser" in parsed["text"]


def test_discovery_prunes_expanded_opencode_session_directories(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "archive-data"
    expanded_session_dir = corpus_root / "agent-logs" / "opencode" / "ses_parent.jsonl"
    expanded_session_dir.mkdir(parents=True)
    (expanded_session_dir / "ses_child.jsonl").write_text(
        '{"role":"user","content":"I built a duplicate parser trace."}\n'
    )
    compressed_session_path = corpus_root / "agent-logs" / "opencode" / "ses_parent.jsonl.gz"
    with gzip.open(compressed_session_path, "wt", encoding="utf-8") as handle:
        handle.write('{"role":"user","content":"I built the canonical parser trace."}\n')

    summary = Pipeline(tmp_path).discover_directory(corpus_root)

    assert summary.total_materials == 1
    assert summary.direct_files == 1


def test_resume_cache_filters_expanded_opencode_session_paths(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "archive-data"
    corpus_root.mkdir()
    cached_state = IngestRunState(
        root_uri=corpus_root.resolve().as_uri(),
        updated_at=datetime.now(tz=UTC),
        total_materials=2,
        materials=[
            IngestManifestEntry(
                relative_import_path="archive-data/agent-logs/opencode/ses_parent.jsonl/ses_child.jsonl",
                source_path=(corpus_root / "agent-logs" / "opencode" / "ses_parent.jsonl" / "ses_child.jsonl")
                .resolve()
                .as_posix(),
                source_family=SourceFamily.GENERIC,
                detection_reason="cached generic path",
                status=IngestMaterialStatus.DISCOVERED,
            ),
            IngestManifestEntry(
                relative_import_path="archive-data/agent-logs/opencode/ses_parent.jsonl.gz",
                source_path=(corpus_root / "agent-logs" / "opencode" / "ses_parent.jsonl.gz")
                .resolve()
                .as_posix(),
                source_family=SourceFamily.GENERIC,
                detection_reason="cached generic path",
                status=IngestMaterialStatus.DISCOVERED,
            ),
        ],
    )

    cached_materials = Pipeline(tmp_path)._resume_cached_materials(cached_state)

    assert cached_materials is not None
    assert [material.relative_import_path.as_posix() for material in cached_materials] == [
        "archive-data/agent-logs/opencode/ses_parent.jsonl.gz"
    ]


def test_ingest_dir_expands_zip_exports(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "zip-corpus"
    corpus_root.mkdir()
    archive_path = corpus_root / "reddit-export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "reddit/posts.md",
            "I built a Python ingestion tool and reviewed the SQLite schema.\n",
        )

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "imported=1" in result.stdout
    assert "processed=1" in result.stdout

    expanded_file = (
        tmp_path
        / "raw"
        / "imported"
        / "zip-corpus"
        / "reddit-export"
        / "reddit"
        / "posts.md"
    )
    assert expanded_file.exists()

    storage = Pipeline(tmp_path).storage
    sources = storage.list_sources()
    assert len(sources) == 1
    assert sources[0]["uri"] == expanded_file.resolve().as_uri()
    assert expanded_file.is_symlink() is False


def test_discover_dir_reports_nested_material_counts(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "discover-corpus"
    (corpus_root / "Google").mkdir(parents=True)
    (corpus_root / "Twitter").mkdir(parents=True)
    (corpus_root / "Google" / "activity.json").write_text('{"messages":[]}\n')
    (corpus_root / "Twitter" / "tweet-1.js").write_text("console.log('one')\n")
    archive_path = corpus_root / "reddit-export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("comments.csv", "id,body\n1,hello\n")
        archive.writestr("posts.csv", "id,title\n1,post\n")

    result = runner.invoke(
        app,
        ["discover-dir", str(corpus_root), "--project-root", str(tmp_path), "--format", "json"],
    )
    assert result.exit_code == 0, result.stdout

    payload = json.loads(result.stdout)
    assert payload["materials"] == 4
    assert payload["direct_files"] == 2
    assert payload["archive_members"] == 2
    assert payload["by_root"]["Google"] == 1
    assert payload["by_root"]["Twitter"] == 1
    assert payload["by_root"]["reddit-export"] == 2
    assert payload["by_family"]["google_takeout"] == 1
    assert payload["by_family"]["twitter_archive"] == 1
    assert payload["by_family"]["reddit_export"] == 2
    assert payload["by_family_subproduct"]["reddit_export:comments"] == 1
    assert payload["by_family_subproduct"]["reddit_export:posts"] == 1


def test_discover_dir_does_not_require_backend_auth(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    config = load_config(tmp_path / "config" / "config.yaml")
    config.backend.provider = "openai_compatible"
    config.backend.api_key_env = "MISSING_DISCOVER_KEY"
    write_config(tmp_path / "config" / "config.yaml", config)

    corpus_root = tmp_path / "discover-auth-corpus"
    (corpus_root / "Google").mkdir(parents=True)
    (corpus_root / "Google" / "localizacion.txt").write_text("drive pointers\n")

    result = runner.invoke(
        app,
        ["discover-dir", str(corpus_root), "--project-root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["by_family"]["google_takeout"] == 1


def test_discover_dir_excludes_twitter_archive_support_assets(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "twitter-discover-corpus"
    (corpus_root / "Twitter" / "twitter-export" / "assets" / "js").mkdir(parents=True)
    (corpus_root / "Twitter" / "twitter-export" / "data").mkdir(parents=True)
    (corpus_root / "Twitter" / "twitter-export" / "assets" / "js" / "runtime.js").write_text(
        "console.log('bundle');\n"
    )
    (corpus_root / "Twitter" / "twitter-export" / "data" / "shop-module.js").write_text(
        "window.YTD.shop_module.part0 = [ ];\n"
    )
    (corpus_root / "Twitter" / "twitter-export" / "data" / "tweet.js").write_text(
        'window.YTD.tweet.part0 = [{"tweet": {"full_text": "I built a parser."}}];\n'
    )

    result = runner.invoke(
        app,
        ["discover-dir", str(corpus_root), "--project-root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["materials"] == 1
    assert payload["by_family"]["twitter_archive"] == 1
    assert payload["by_family_subproduct"]["twitter_archive:tweets"] == 1


def test_discover_dir_excludes_instagram_low_signal_metadata_exports(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "instagram-discover-corpus"
    export_root = corpus_root / "Instagram" / "instagram-export"
    (export_root / "security_and_login_information" / "login_and_profile_creation").mkdir(
        parents=True
    )
    (export_root / "your_instagram_activity" / "likes").mkdir(parents=True)
    (
        export_root
        / "security_and_login_information"
        / "login_and_profile_creation"
        / "login_activity.html"
    ).write_text("<html><body>Login metadata</body></html>\n")
    (export_root / "start_here.html").write_text("<html><body>Index</body></html>\n")
    (export_root / "your_instagram_activity" / "likes" / "posts_liked_1.html").write_text(
        "<html><body>I liked machining posts and metalworking reels.</body></html>\n"
    )

    result = runner.invoke(
        app,
        ["discover-dir", str(corpus_root), "--project-root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["materials"] == 1
    assert payload["by_family"]["instagram_export"] == 1
    assert payload["by_family_subproduct"]["instagram_export:your-instagram-activity"] == 1


def test_discover_dir_excludes_placeholder_no_data_exports(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "no-data-discover-corpus"
    (corpus_root / "Instagram" / "instagram-export" / "connections" / "contacts").mkdir(parents=True)
    (corpus_root / "notes").mkdir(parents=True)
    (
        corpus_root / "Instagram" / "instagram-export" / "connections" / "contacts" / "no-data.txt"
    ).write_text("No data\n")
    (corpus_root / "notes" / "builder.txt").write_text(
        "I learned CAD and machining by building keyboard parts.\n"
    )

    result = runner.invoke(
        app,
        ["discover-dir", str(corpus_root), "--project-root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["materials"] == 1
    assert payload["by_family"]["generic"] == 1


def test_ingest_dir_writes_processed_then_skipped_manifests(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "takeout-corpus"
    takeout_file = corpus_root / "Takeout" / "My Activity" / "Chrome" / "MyActivity.html"
    takeout_file.parent.mkdir(parents=True)
    takeout_file.write_text(
        "<html><body>I built a Python parser and debugged the ingest pipeline.</body></html>\n"
    )

    first_run = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert first_run.exit_code == 0, first_run.stdout

    first_manifest = latest_manifest(tmp_path)
    assert first_manifest["root_uri"] == corpus_root.resolve().as_uri()
    assert len(first_manifest["materials"]) == 1
    first_entry = first_manifest["materials"][0]
    assert first_entry["status"] == "processed"
    assert first_entry["source_family"] == "google_takeout"
    assert first_entry["archive_member"] is None

    second_run = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert second_run.exit_code == 0, second_run.stdout

    second_manifest = latest_manifest(tmp_path)
    second_entry = second_manifest["materials"][0]
    assert second_entry["status"] == "skipped"
    assert second_entry["source_family"] == "google_takeout"

    storage = Pipeline(tmp_path).storage
    sources = storage.list_sources()
    assert len(sources) == 1
    metadata = json.loads(sources[0]["metadata_json"])
    assert metadata["source_family"] == "google_takeout"
    assert "Google Takeout" in metadata["source_family_reason"]
    assert metadata["source_family_subproduct"] == "my-activity"
    assert metadata["family_normalizer"] == "html-export"
    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "completed"
    assert progress["materials"]["discovered"] == 1
    assert progress["materials"]["by_family_subproduct"]["google_takeout:my-activity"] == 1


def test_discover_dir_excludes_zero_value_export_metadata(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "archive-data"
    twitter_root = corpus_root / "Twitter" / "twitter-export" / "data"
    reddit_root = corpus_root / "Reddit" / "export"
    instagram_root = corpus_root / "Instagram" / "instagram-export" / "your_instagram_activity"

    twitter_root.mkdir(parents=True)
    reddit_root.mkdir(parents=True)
    (instagram_root / "monetization").mkdir(parents=True)
    (instagram_root / "messages" / "inbox" / "project_chat").mkdir(parents=True)

    (twitter_root / "ad-engagements.js").write_text("window.YTD.ad_engagements.part0 = []\n")
    (twitter_root / "tweet-headers.js").write_text("window.YTD.tweet_headers.part0 = []\n")
    (twitter_root / "tweets.js").write_text(
        "window.YTD.tweets.part0 = [{ tweet: { full_text: 'I designed a keyboard PCB.' } }]\n"
    )
    (reddit_root / "ip_logs.csv").write_text("date,ip\n2026-01-01,127.0.0.1\n")
    (reddit_root / "comments.csv").write_text("id,body\n1,I debugged a parser\n")
    (instagram_root / "monetization" / "eligibility.html").write_text(
        "<html><body>Eligible</body></html>\n"
    )
    (instagram_root / "messages" / "inbox" / "project_chat" / "message_1.html").write_text(
        "<html><body>I lubed switches and tuned stabilizers.</body></html>\n"
    )

    result = runner.invoke(
        app,
        ["discover-dir", str(corpus_root), "--project-root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["materials"] == 3
    assert payload["by_family"]["twitter_archive"] == 1
    assert payload["by_family"]["reddit_export"] == 1
    assert payload["by_family"]["instagram_export"] == 1


def test_discover_dir_excludes_low_signal_google_takeout_metadata_and_drive_archives(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "takeout-corpus"
    takeout_root = corpus_root / "Takeout"
    (takeout_root / "Actividad de registro de accesos").mkdir(parents=True)
    (takeout_root / "Correo" / "Configuración de usuario").mkdir(parents=True)
    (takeout_root / "Chrome").mkdir(parents=True)
    (takeout_root / "Drive").mkdir(parents=True)
    (takeout_root / "Drive" / ".cache").mkdir(parents=True)
    (takeout_root / "Drive" / "Python-3.9.7").mkdir(parents=True)
    (takeout_root / "YouTube y YouTube Music" / "comentarios").mkdir(parents=True)

    (takeout_root / "weakpass_4a-004.txt").write_text("password1\npassword2\n")
    (takeout_root / "Actividad de registro de accesos" / "Actividades.csv").write_text(
        "service,last_access\nChrome,2026-01-01\n"
    )
    (
        takeout_root
        / "Correo"
        / "Configuración de usuario"
        / "Direcciones bloqueadas.json"
    ).write_text("[]\n")
    (takeout_root / "Chrome" / "Configuración.json").write_text("{}\n")
    (takeout_root / "Chrome" / "Historial.json").write_text(
        '[{"title":"Python parser docs","url":"https://example.com"}]\n'
    )
    (takeout_root / "Drive" / "project-notes.txt").write_text(
        "I built a keyboard firmware flashing checklist.\n"
    )
    with zipfile.ZipFile(takeout_root / "Drive" / "Yuzu.zip", "w") as archive:
        archive.writestr("notes.txt", "This should not be expanded from a Drive archive.\n")
    (takeout_root / "Drive" / ".cache" / "pip-response.txt").write_text(
        "This cache file should not be traversed.\n"
    )
    (takeout_root / "Drive" / ".bash_logout").write_text("This dotfile should not be sniffed.\n")
    (takeout_root / "Drive" / "Python-3.9.7" / "Makefile").write_text(
        "This vendored runtime source should not be traversed.\n"
    )
    (takeout_root / "Drive" / "placements.json.bak").write_text(
        "This duplicate backup file should not be sniffed.\n"
    )
    (
        takeout_root
        / "YouTube y YouTube Music"
        / "comentarios"
        / "comentarios.csv"
    ).write_text("timestamp,comment\n2026-01-01,I debugged OBS encoding settings\n")

    result = runner.invoke(
        app,
        ["discover-dir", str(corpus_root), "--project-root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["materials"] == 3
    assert payload["by_family"] == {"google_takeout": 3}
    assert payload["by_family_subproduct"]["google_takeout:chrome"] == 1
    assert payload["by_family_subproduct"]["google_takeout:drive"] == 1
    assert payload["by_family_subproduct"]["google_takeout:youtube-and-youtube-music"] == 1


def test_discover_dir_excludes_low_signal_discord_metadata_but_keeps_messages(
    tmp_path: Path,
) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "archive-data"
    discord_root = corpus_root / "Discord" / "package"
    (discord_root / "Account").mkdir(parents=True)
    (discord_root / "Messages" / "c123").mkdir(parents=True)
    (discord_root / "Servers" / "s123").mkdir(parents=True)

    (discord_root / "Account" / "user.json").write_text(
        json.dumps({"connections": [{"type": "github", "name": "Microck"}]})
    )
    (discord_root / "Messages" / "index.json").write_text('{"c123":"project"}\n')
    (discord_root / "Messages" / "c123" / "channel.json").write_text(
        '{"id":"c123","name":"project"}\n'
    )
    (discord_root / "Activity" / "reporting").mkdir(parents=True)
    (discord_root / "Activity" / "tns").mkdir(parents=True)
    (discord_root / "Activity" / "reporting" / "events-2026-00000-of-00001.json").write_text(
        json.dumps([{"event_type": "metadata-only activity report"}])
    )
    (discord_root / "Activity" / "tns" / "events-2026-00000-of-00001.json").write_text(
        json.dumps([{"event_type": "metadata-only trust and safety telemetry"}])
    )
    (discord_root / "Messages" / "c123" / "messages.json").write_text(
        json.dumps(
            [
                {
                    "ID": "1",
                    "Timestamp": "2026-01-01 00:00:00",
                    "Contents": "I debugged a Discord bot parser.",
                }
            ]
        )
    )
    (discord_root / "Servers" / "index.json").write_text('{"s123":"server"}\n')
    (discord_root / "Servers" / "s123" / "audit-log.json").write_text("[]\n")

    result = runner.invoke(
        app,
        ["discover-dir", str(corpus_root), "--project-root", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["materials"] == 1
    assert payload["by_family"] == {"discord_data_package": 1}
    assert payload["by_family_subproduct"] == {"discord_data_package:messages": 1}


def test_export_debug_report_command_writes_report_artifacts(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    ingest_corpus(runner, tmp_path)

    result = runner.invoke(app, ["export", "debug-report", "--project-root", str(tmp_path)])

    assert result.exit_code == 0, result.stdout
    output_path = Path(result.stdout.strip())
    assert output_path == tmp_path / "exports" / "debug" / "report.json"
    assert output_path.exists()
    assert (tmp_path / "exports" / "debug" / "report.md").exists()


def test_ingest_dir_records_archive_family_and_member_in_manifest(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "archive-corpus"
    corpus_root.mkdir()
    archive_path = corpus_root / "twitter-export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "data/tweet.js",
            'window.YTD.tweet.part0 = [{"tweet": {"full_text": "I learned Python by building parsers."}}];\n',
        )

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    manifest = latest_manifest(tmp_path)
    assert len(manifest["materials"]) == 1
    entry = manifest["materials"][0]
    assert entry["status"] == "processed"
    assert entry["source_family"] == "twitter_archive"
    assert entry["archive_member"] == "data/tweet.js"

    storage = Pipeline(tmp_path).storage
    sources = storage.list_sources()
    assert len(sources) == 1
    metadata = json.loads(sources[0]["metadata_json"])
    assert metadata["source_family"] == "twitter_archive"
    assert metadata["archive_member"] == "data/tweet.js"
    assert metadata["source_family_subproduct"] == "tweets"
    assert metadata["family_normalizer"] == "twitter-ytd-js"


def test_ingest_dir_records_instagram_and_facebook_families_from_provider_roots(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "social-corpus"
    (corpus_root / "Instagram" / "messages").mkdir(parents=True)
    (corpus_root / "Facebook" / "your_facebook_activity").mkdir(parents=True)
    instagram_file = corpus_root / "Instagram" / "messages" / "thread_1.json"
    facebook_file = corpus_root / "Facebook" / "your_facebook_activity" / "posts.json"
    instagram_file.write_text('{"messages":[]}\n')
    facebook_file.write_text('{"posts":[]}\n')

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    storage = Pipeline(tmp_path).storage
    sources = {
        json.loads(row["metadata_json"])["filename"]: json.loads(row["metadata_json"])
        for row in storage.list_sources()
    }

    assert sources["thread_1.json"]["source_family"] == "instagram_export"
    assert sources["thread_1.json"]["source_family_subproduct"] == "messages"
    assert sources["posts.json"]["source_family"] == "facebook_export"
    assert sources["posts.json"]["source_family_subproduct"] == "your-facebook-activity"


class ChunkRecordingBackend:
    def __init__(self) -> None:
        self.call_count = 0
        self.delegate = FakeLLMBackend()

    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        del prompt
        self.call_count += 1
        span = document.spans[0]
        return [
            EvidenceItem(
                evidence_id="duplicate",
                source_id=document.source.source_id,
                span_start=span.span_start,
                span_end=span.span_end,
                quote=span.text,
                evidence_type=EvidenceType.IMPLEMENTED,
                signal_class=SignalClass.ARTIFACT_BACKED_WORK,
                skill_candidates=["Python"],
                artifact_candidates=["text export"],
                time_reference=document.source.ingested_at.isoformat(),
                reliability=ReliabilityTier.TIER_B,
                extractor_version="chunk-test",
                confidence=0.9,
            )
        ]

    def canonicalize(self, *, prompt: str, request):
        return self.delegate.canonicalize(prompt=prompt, request=request)

    def score_skill(self, *, prompt: str, request):
        return self.delegate.score_skill(prompt=prompt, request=request)


class FailOnceBackend:
    def __init__(self) -> None:
        self.failed = False
        self.delegate = FakeLLMBackend()

    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        del prompt
        if not self.failed:
            self.failed = True
            raise RuntimeError("transient failure")
        span = document.spans[0]
        return [
            EvidenceItem(
                evidence_id="resume-test",
                source_id=document.source.source_id,
                span_start=span.span_start,
                span_end=span.span_end,
                quote=span.text,
                evidence_type=EvidenceType.IMPLEMENTED,
                signal_class=SignalClass.ARTIFACT_BACKED_WORK,
                skill_candidates=["Python"],
                artifact_candidates=["resume test"],
                time_reference=document.source.ingested_at.isoformat(),
                reliability=ReliabilityTier.TIER_B,
                extractor_version="resume-test",
                confidence=0.9,
            )
        ]

    def canonicalize(self, *, prompt: str, request):
        return self.delegate.canonicalize(prompt=prompt, request=request)

    def score_skill(self, *, prompt: str, request):
        return self.delegate.score_skill(prompt=prompt, request=request)


class FailOnNthChunkBackend:
    def __init__(self, *, fail_on_call: int) -> None:
        self.fail_on_call = fail_on_call
        self.call_count = 0
        self.seen_quotes: list[str] = []
        self.delegate = FakeLLMBackend()

    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        del prompt
        self.call_count += 1
        span = document.spans[0]
        self.seen_quotes.append(span.text)
        if self.call_count == self.fail_on_call:
            raise RuntimeError("quota exhausted")
        return [
            EvidenceItem(
                evidence_id=f"checkpoint-{self.call_count}",
                source_id=document.source.source_id,
                span_start=span.span_start,
                span_end=span.span_end,
                quote=span.text,
                evidence_type=EvidenceType.IMPLEMENTED,
                signal_class=SignalClass.ARTIFACT_BACKED_WORK,
                skill_candidates=["Python"],
                artifact_candidates=["checkpoint"],
                time_reference=document.source.ingested_at.isoformat(),
                reliability=ReliabilityTier.TIER_B,
                extractor_version="checkpoint-test",
                confidence=0.9,
            )
        ]

    def canonicalize(self, *, prompt: str, request):
        return self.delegate.canonicalize(prompt=prompt, request=request)

    def score_skill(self, *, prompt: str, request):
        return self.delegate.score_skill(prompt=prompt, request=request)


class StopOnQuotaBackend:
    def __init__(self, *, fail_on_call: int) -> None:
        self.fail_on_call = fail_on_call
        self.call_count = 0
        self.delegate = FakeLLMBackend()

    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        del prompt
        self.call_count += 1
        if self.call_count == self.fail_on_call:
            raise BackendError("LLM backend request failed (429): quota exhausted")
        span = document.spans[0]
        return [
            EvidenceItem(
                evidence_id=f"quota-stop-{self.call_count}",
                source_id=document.source.source_id,
                span_start=span.span_start,
                span_end=span.span_end,
                quote=span.text,
                evidence_type=EvidenceType.IMPLEMENTED,
                signal_class=SignalClass.ARTIFACT_BACKED_WORK,
                skill_candidates=["Python"],
                artifact_candidates=["quota stop"],
                time_reference=document.source.ingested_at.isoformat(),
                reliability=ReliabilityTier.TIER_B,
                extractor_version="quota-stop-test",
                confidence=0.9,
            )
        ]

    def canonicalize(self, *, prompt: str, request):
        return self.delegate.canonicalize(prompt=prompt, request=request)

    def score_skill(self, *, prompt: str, request):
        return self.delegate.score_skill(prompt=prompt, request=request)


class StopOnModelCooldownBackend(StopOnQuotaBackend):
    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        self.call_count += 1
        if self.call_count == self.fail_on_call:
            raise BackendError(
                'LLM backend request failed (429): {"error":{"code":"model_cooldown",'
                '"message":"All credentials for model star-gemini-3-flash are cooling down",'
                '"reset_seconds":1743,"reset_time":"29m3s"}}'
            )
        return self.delegate.extract_evidence(prompt=prompt, document=document)


class StopOnRateLimitBackend(StopOnQuotaBackend):
    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        self.call_count += 1
        if self.call_count == self.fail_on_call:
            raise BackendError(
                'LLM backend request failed (429): {"error":{"code":"1302",'
                '"message":"Rate limit reached for requests"}}'
            )
        return self.delegate.extract_evidence(prompt=prompt, document=document)


class StopOnStructuredValidationBackend(StopOnQuotaBackend):
    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        self.call_count += 1
        if self.call_count == self.fail_on_call:
            raise BackendError(
                "Structured response validation failed after 3 attempt(s): "
                "Invalid JSON: expected `,` or `}` at line 1 column 192"
            )
        return self.delegate.extract_evidence(prompt=prompt, document=document)


class StopOnGraphCooldownBackend(FakeLLMBackend):
    def score_skill(self, *, prompt: str, request):
        del prompt, request
        raise BackendError(
            'LLM backend request failed (429): {"error":{"code":"model_cooldown",'
            '"message":"All credentials for model star-gemini-3-flash are cooling down",'
            '"reset_seconds":812,"reset_time":"13m31s"}}'
        )


class StopOnMaterialThenGraphCooldownBackend(StopOnModelCooldownBackend):
    def score_skill(self, *, prompt: str, request):
        del prompt, request
        raise BackendError(
            'LLM backend request failed (429): {"error":{"code":"model_cooldown",'
            '"message":"All credentials for model star-gemini-3-flash are cooling down",'
            '"reset_seconds":1743,"reset_time":"29m3s"}}'
        )


class CountingGraphBackend:
    def __init__(self) -> None:
        self.delegate = FakeLLMBackend()
        self.canonicalize_calls = 0
        self.score_calls = 0

    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        return self.delegate.extract_evidence(prompt=prompt, document=document)

    def canonicalize(self, *, prompt: str, request):
        self.canonicalize_calls += 1
        return self.delegate.canonicalize(prompt=prompt, request=request)

    def score_skill(self, *, prompt: str, request):
        self.score_calls += 1
        return self.delegate.score_skill(prompt=prompt, request=request)


class ProgressiveGraphBackend:
    def __init__(self) -> None:
        self.delegate = FakeLLMBackend()

    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        del prompt
        span = document.spans[0]
        return [
            EvidenceItem(
                evidence_id=f"{document.source.source_id}-python",
                source_id=document.source.source_id,
                span_start=span.span_start,
                span_end=span.span_end,
                quote=span.text,
                evidence_type=EvidenceType.IMPLEMENTED,
                signal_class=SignalClass.ARTIFACT_BACKED_WORK,
                skill_candidates=["Python"],
                artifact_candidates=[],
                time_reference=document.source.ingested_at.isoformat(),
                reliability=ReliabilityTier.TIER_B,
                extractor_version="progressive-graph-test",
                confidence=0.92,
            ),
            EvidenceItem(
                evidence_id=f"{document.source.source_id}-sqlite",
                source_id=document.source.source_id,
                span_start=span.span_start,
                span_end=span.span_end,
                quote=span.text,
                evidence_type=EvidenceType.DESIGNED,
                signal_class=SignalClass.ARTIFACT_BACKED_WORK,
                skill_candidates=["SQLite"],
                artifact_candidates=[],
                time_reference=document.source.ingested_at.isoformat(),
                reliability=ReliabilityTier.TIER_B,
                extractor_version="progressive-graph-test",
                confidence=0.88,
            ),
        ]

    def canonicalize(self, *, prompt: str, request):
        del prompt
        return CanonicalSkillDecision(
            candidate_name=request.candidate_name,
            action="create",
            canonical_name=request.candidate_name,
            skill_id=None,
            reason="Strong evidence for direct creation.",
        )

    def score_skill(self, *, prompt: str, request):
        del prompt
        return ScorePayload(
            level=3,
            confidence=0.87,
            recency_score=0.91,
            breadth_score=0.6,
            depth_score=0.7,
            artifact_score=0.8,
            teaching_score=0.0,
            freshness="active",
            status="active",
            manual_note=None,
            rationale=f"Scored from {len(request.evidence_items)} evidence item(s).",
        )


class DomainReuseBackend:
    def __init__(self) -> None:
        self.delegate = FakeLLMBackend()

    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        del prompt
        span = document.spans[0]
        return [
            EvidenceItem(
                evidence_id="domain-reuse",
                source_id=document.source.source_id,
                span_start=span.span_start,
                span_end=span.span_end,
                quote=span.text,
                evidence_type=EvidenceType.DESIGNED,
                signal_class=SignalClass.ARTIFACT_BACKED_WORK,
                skill_candidates=["data analysis"],
                artifact_candidates=[],
                time_reference=document.source.ingested_at.isoformat(),
                reliability=ReliabilityTier.TIER_B,
                extractor_version="domain-reuse-test",
                confidence=0.9,
            )
        ]

    def canonicalize(self, *, prompt: str, request):
        del prompt
        return CanonicalSkillDecision(
            candidate_name=request.candidate_name,
            action="use_existing",
            canonical_name="Data",
            skill_id="domain.data",
            reason="This evidence fits the existing Data domain node.",
        )

    def score_skill(self, *, prompt: str, request):
        return self.delegate.score_skill(prompt=prompt, request=request)


class ProgressRecordingPipeline(Pipeline):
    def __init__(self, project_root: Path) -> None:
        super().__init__(project_root)
        self.progress_statuses: list[str] = []
        self.progress_payloads: list[dict[str, object]] = []

    def _write_progress(self, **kwargs):
        self.progress_statuses.append(str(kwargs["status"]))
        self.progress_payloads.append(dict(kwargs))
        return super()._write_progress(**kwargs)


class CheckpointRecordingPipeline(Pipeline):
    def __init__(self, project_root: Path) -> None:
        super().__init__(project_root)
        self.graph_checkpoint_calls = 0

    def _refresh_live_graph_checkpoint(
        self,
        *,
        root: Path,
        manifest_entries,
        completed: int,
        total_materials: int,
        graph_progress_callback=None,
    ) -> None:
        del root, manifest_entries, completed, total_materials, graph_progress_callback
        self.graph_checkpoint_calls += 1


class ForbiddenExtractionBackend:
    def extract_evidence(self, *, prompt: str, document) -> list[EvidenceItem]:
        del prompt, document
        raise AssertionError("LLM extraction should have been skipped")


def test_ingest_file_chunks_large_documents_and_normalizes_evidence_ids(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "large-corpus"
    corpus_root.mkdir()
    large_file = corpus_root / "notes.txt"
    large_file.write_text(
        "\n\n".join(
            f"I built a Python ingestion component number {index} and debugged its parser."
            for index in range(150)
        )
        + "\n"
    )

    pipeline = Pipeline(tmp_path)
    backend = ChunkRecordingBackend()
    pipeline.backend = backend

    source_id, processed = pipeline.ingest_file(large_file, root=corpus_root)
    assert processed is True
    assert backend.call_count > 1

    evidence_items = pipeline.storage.list_source_evidence(source_id)
    assert len(evidence_items) == backend.call_count
    assert len({item.evidence_id for item in evidence_items}) == len(evidence_items)


def test_ingest_file_can_resume_after_partial_failure(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "resume-corpus"
    corpus_root.mkdir()
    source_path = corpus_root / "notes.txt"
    source_path.write_text("I built a Python ingest pipeline and debugged the parser.\n")

    pipeline = Pipeline(tmp_path)
    flaky_backend = FailOnceBackend()
    pipeline.backend = flaky_backend

    try:
        pipeline.ingest_file(source_path, root=corpus_root)
    except RuntimeError as exc:
        assert "transient failure" in str(exc)
    else:
        raise AssertionError("expected first ingest to fail")

    source_id = source_id_for_relative_path(Path("resume-corpus") / "notes.txt")
    assert (tmp_path / "parsed" / f"{source_id}.json").exists()
    assert not (tmp_path / "evidence" / f"{source_id}.json").exists()

    resumed_pipeline = Pipeline(tmp_path)
    resumed_pipeline.backend = flaky_backend
    resumed_source_id, processed = resumed_pipeline.ingest_file(source_path, root=corpus_root)

    assert resumed_source_id == source_id
    assert processed is True
    assert (tmp_path / "evidence" / f"{source_id}.json").exists()
    assert len(resumed_pipeline.storage.list_source_evidence(source_id)) == 1


def test_ingest_file_resumes_from_completed_chunk_checkpoints(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "checkpoint-corpus"
    corpus_root.mkdir()
    source_path = corpus_root / "notes.txt"
    source_path.write_text(
        "\n\n".join(
            f"I built Python ingestion chunk {index} and debugged parser section {index}."
            for index in range(140)
        )
        + "\n"
    )

    parsed_document = parse_document(
        source_path,
        project_relative_path=Path("checkpoint-corpus") / "notes.txt",
        config=load_config(tmp_path / "config" / "config.yaml"),
    )
    chunks = _chunk_document(parsed_document)
    assert len(chunks) > 2
    first_chunk_quote = chunks[0].spans[0].text
    second_chunk_quote = chunks[1].spans[0].text

    pipeline = Pipeline(tmp_path)
    flaky_backend = FailOnNthChunkBackend(fail_on_call=2)
    pipeline.backend = flaky_backend

    try:
        pipeline.ingest_file(source_path, root=corpus_root)
    except RuntimeError as exc:
        assert "quota exhausted" in str(exc)
    else:
        raise AssertionError("expected checkpointing ingest to fail")

    source_id = source_id_for_relative_path(Path("checkpoint-corpus") / "notes.txt")
    checkpoints = pipeline.storage.list_extraction_checkpoints(source_id)
    assert len(checkpoints) == 1
    assert flaky_backend.seen_quotes[:2] == [first_chunk_quote, second_chunk_quote]

    resumed_pipeline = Pipeline(tmp_path)
    resumed_backend = FailOnNthChunkBackend(fail_on_call=999)
    resumed_pipeline.backend = resumed_backend
    resumed_source_id, processed = resumed_pipeline.ingest_file(source_path, root=corpus_root)

    assert resumed_source_id == source_id
    assert processed is True
    assert resumed_backend.seen_quotes[0] == second_chunk_quote
    assert first_chunk_quote not in resumed_backend.seen_quotes
    assert resumed_pipeline.storage.list_extraction_checkpoints(source_id) == []
    assert len(resumed_pipeline.storage.list_source_evidence(source_id)) == len(chunks)


def test_ingest_dir_continues_after_material_failure(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "partial-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")
    (corpus_root / "two.txt").write_text("I debugged the SQLite migration.\n")

    pipeline = Pipeline(tmp_path)
    flaky_backend = FailOnceBackend()
    pipeline.backend = flaky_backend

    result = pipeline.ingest_directory(corpus_root)

    assert result.failed == 1
    assert result.processed == 1
    assert len(pipeline.storage.list_sources()) == 2
    assert len(pipeline.storage.list_evidence()) == 1

    resumed_pipeline = Pipeline(tmp_path)
    resumed_pipeline.backend = flaky_backend
    resumed_result = resumed_pipeline.ingest_directory(corpus_root)

    assert resumed_result.failed == 0
    assert resumed_result.processed >= 1
    assert len(resumed_pipeline.storage.list_evidence()) >= 2

def test_ingest_dir_fast_resumes_completed_materials_after_quota_stop(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "resume-dir-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")
    (corpus_root / "two.txt").write_text("I shipped a Python migration.\n")
    (corpus_root / "three.txt").write_text("I documented the parser release flow.\n")

    first_pipeline = Pipeline(tmp_path)
    first_backend = StopOnQuotaBackend(fail_on_call=2)
    first_pipeline.backend = first_backend

    try:
        first_pipeline.ingest_directory(corpus_root)
    except RuntimeError as exc:
        assert "quota exhausted" in str(exc)
    else:
        raise AssertionError("expected first ingest to stop on quota")

    second_pipeline = Pipeline(tmp_path)
    second_backend = FailOnNthChunkBackend(fail_on_call=999)
    second_pipeline.backend = second_backend

    resumed_result = second_pipeline.ingest_directory(corpus_root)

    assert resumed_result.failed == 0
    assert resumed_result.processed == 2
    assert resumed_result.skipped == 1
    assert second_backend.call_count == 2

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "completed"
    assert progress["resume"]["completed_before_run"] == 1
    assert progress["progress"]["completed"] == 3


def test_ingest_dir_marks_progress_as_discovering_before_processing(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "discovering-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")

    pipeline = ProgressRecordingPipeline(tmp_path)
    pipeline.backend = FakeLLMBackend()

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 1
    assert pipeline.progress_statuses[0] == "discovering"
    assert "running" in pipeline.progress_statuses
    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "completed"
    assert "blocked_reason" not in progress


def test_ingest_file_skips_low_signal_instagram_metadata_exports(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "instagram-corpus"
    export_path = (
        corpus_root
        / "Instagram"
        / "instagram-export"
        / "personal_information"
        / "device_information"
        / "devices.html"
    )
    export_path.parent.mkdir(parents=True)
    export_path.write_text(
        """
        <html>
          <body>
            <div>Camera Model</div>
            <div>Phone device metadata</div>
          </body>
        </html>
        """
    )

    pipeline = Pipeline(tmp_path)
    pipeline.backend = ForbiddenExtractionBackend()

    source_id, processed = pipeline.ingest_file(export_path, root=corpus_root)

    assert processed is True
    assert pipeline.storage.list_source_evidence(source_id) == []
    evidence_payload = json.loads((tmp_path / "evidence" / f"{source_id}.json").read_text())
    assert evidence_payload == []


def test_ingest_file_skips_instagram_export_index_pages(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "instagram-index-corpus"
    export_path = corpus_root / "Instagram" / "instagram-export" / "start_here.html"
    export_path.parent.mkdir(parents=True)
    export_path.write_text(
        """
        <html>
          <body>
            <h1>Instagram export</h1>
            <p>Use these links to browse your download.</p>
            <a href="connections/followers_and_following/followers_1.html">Followers</a>
          </body>
        </html>
        """
    )

    pipeline = Pipeline(tmp_path)
    pipeline.backend = ForbiddenExtractionBackend()

    source_id, processed = pipeline.ingest_file(export_path, root=corpus_root)

    assert processed is True
    assert pipeline.storage.list_source_evidence(source_id) == []
    evidence_payload = json.loads((tmp_path / "evidence" / f"{source_id}.json").read_text())
    assert evidence_payload == []


def test_ingest_file_skips_instagram_security_login_metadata_exports(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "instagram-security-corpus"
    export_path = (
        corpus_root
        / "Instagram"
        / "instagram-export"
        / "security_and_login_information"
        / "login_and_profile_creation"
        / "login_activity.html"
    )
    export_path.parent.mkdir(parents=True)
    export_path.write_text(
        """
        <html>
          <body>
            <h1>Login activity</h1>
            <div>IP Address</div>
            <div>90.163.156.171</div>
            <div>Date and Time</div>
            <div>Feb 02, 2026 8:30 pm</div>
          </body>
        </html>
        """
    )

    pipeline = Pipeline(tmp_path)
    pipeline.backend = ForbiddenExtractionBackend()

    source_id, processed = pipeline.ingest_file(export_path, root=corpus_root)

    assert processed is True
    assert pipeline.storage.list_source_evidence(source_id) == []
    evidence_payload = json.loads((tmp_path / "evidence" / f"{source_id}.json").read_text())
    assert evidence_payload == []


def test_ingest_file_skips_twitter_archive_support_assets(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "twitter-asset-corpus"
    asset_path = corpus_root / "Twitter" / "twitter-export" / "assets" / "images" / "defaultAvatar.svg"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_text(
        """
        <svg width="45" height="45" xmlns="http://www.w3.org/2000/svg">
          <path d="M0 0h10v10H0z" />
        </svg>
        """
    )

    pipeline = Pipeline(tmp_path)
    pipeline.backend = ForbiddenExtractionBackend()

    source_id, processed = pipeline.ingest_file(asset_path, root=corpus_root)

    assert processed is True
    assert pipeline.storage.list_source_evidence(source_id) == []
    evidence_payload = json.loads((tmp_path / "evidence" / f"{source_id}.json").read_text())
    assert evidence_payload == []


def test_ingest_file_skips_empty_twitter_ytd_modules(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "twitter-ytd-corpus"
    module_path = corpus_root / "Twitter" / "twitter-export" / "data" / "shop-module.js"
    module_path.parent.mkdir(parents=True)
    module_path.write_text("window.YTD.shop_module.part0 = [ ];\n")

    pipeline = Pipeline(tmp_path)
    pipeline.backend = ForbiddenExtractionBackend()

    source_id, processed = pipeline.ingest_file(module_path, root=corpus_root)

    assert processed is True
    assert pipeline.storage.list_source_evidence(source_id) == []
    evidence_payload = json.loads((tmp_path / "evidence" / f"{source_id}.json").read_text())
    assert evidence_payload == []


def test_ingest_file_skips_empty_documents(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "empty-corpus"
    source_path = corpus_root / "blank.txt"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("\n\n\t \n")

    pipeline = Pipeline(tmp_path)
    pipeline.backend = ForbiddenExtractionBackend()

    source_id, processed = pipeline.ingest_file(source_path, root=corpus_root)

    assert processed is True
    assert pipeline.storage.list_source_evidence(source_id) == []
    evidence_payload = json.loads((tmp_path / "evidence" / f"{source_id}.json").read_text())
    assert evidence_payload == []


def test_parse_document_discovers_linked_html_image_attachment(tmp_path: Path) -> None:
    html_path = tmp_path / "post.html"
    image_path = tmp_path / "preview.jpg"
    image_path.write_bytes(b"jpeg-bytes")
    html_path.write_text(
        """
        <html>
          <body>
            <p>Post text</p>
            <img src="preview.jpg" alt="preview image" />
          </body>
        </html>
        """.strip()
    )

    config = default_config()
    config.multimodal.enable_local_image_ocr = False

    parsed = parse_document(
        html_path,
        project_relative_path=Path("post.html"),
        config=config,
        source_family=SourceFamily.INSTAGRAM_EXPORT,
    )

    assert len(parsed.attachments) == 1
    attachment = parsed.attachments[0]
    assert attachment.kind.value == "image"
    assert attachment.reference == "preview.jpg"
    assert attachment.label == "preview image"
    assert attachment.resolved_path == image_path.resolve().as_posix()


def test_parse_document_discovers_twitter_archive_media_attachment(tmp_path: Path) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    image_path = media_dir / "tweet-photo.jpg"
    image_path.write_bytes(b"jpeg-bytes")

    archive_js = tmp_path / "tweet.js"
    archive_js.write_text(
        'window.YTD.tweets.part0 = [{"tweet":{"full_text":"Built analytics dashboard","media_url_https":"media/tweet-photo.jpg"}}];\n'
    )

    config = default_config()
    config.multimodal.enable_local_image_ocr = False

    parsed = parse_document(
        archive_js,
        project_relative_path=Path("tweet.js"),
        config=config,
        source_family=SourceFamily.TWITTER_ARCHIVE,
        source_family_subproduct="tweets",
    )

    assert len(parsed.attachments) == 1
    attachment = parsed.attachments[0]
    assert attachment.kind.value == "image"
    assert attachment.reference == "media/tweet-photo.jpg"
    assert attachment.resolved_path == image_path.resolve().as_posix()


def test_chunk_document_splits_oversized_single_span(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "oversized-corpus"
    corpus_root.mkdir()
    source_path = corpus_root / "oversized.txt"
    source_path.write_text("A" * 14050 + "\n")

    parsed_document = parse_document(
        source_path,
        project_relative_path=Path("oversized-corpus") / "oversized.txt",
        source_family=SourceFamily.GENERIC,
    )

    assert len(parsed_document.spans) == 1
    chunks = _chunk_document(parsed_document)

    assert len(chunks) > 1
    assert all(len(span.text) <= 4000 for chunk in chunks for span in chunk.spans)
    assert all(sum(len(span.text) for span in chunk.spans) <= 12000 for chunk in chunks)


def test_chunk_document_does_not_over_split_dense_structured_exports(tmp_path: Path) -> None:
    payload = {
        f"setting_{index:03d}": {
            "enabled": index % 2 == 0,
            "label": f"short preference value {index}",
        }
        for index in range(120)
    }
    source_path = tmp_path / "settings.json"
    source_path.write_text(json.dumps(payload, indent=2) + "\n")

    parsed_document = parse_document(
        source_path,
        project_relative_path=Path("settings.json"),
        source_family=SourceFamily.GENERIC,
    )

    assert len(parsed_document.spans) > 100
    chunks = _chunk_document(parsed_document)

    assert len(chunks) <= 10
    assert all(sum(len(span.text) for span in chunk.spans) <= 12000 for chunk in chunks)


def test_ingest_dir_writes_chunk_progress_heartbeats_for_large_materials(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "heartbeat-corpus"
    corpus_root.mkdir()
    large_file = corpus_root / "notes.txt"
    large_file.write_text(
        "\n\n".join(
            f"I built a Python ingestion component number {index} and debugged its parser."
            for index in range(150)
        )
        + "\n"
    )

    pipeline = ProgressRecordingPipeline(tmp_path)
    pipeline.backend = ChunkRecordingBackend()

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 1
    chunk_progress_updates = [
        payload
        for payload in pipeline.progress_payloads
        if payload.get("current_chunk_total") is not None
    ]
    assert chunk_progress_updates
    assert any(int(payload["current_chunk_total"]) > 1 for payload in chunk_progress_updates)


def test_ingest_dir_writes_graph_phase_progress_heartbeats(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "graph-heartbeat-corpus"
    corpus_root.mkdir()
    (corpus_root / "notes.txt").write_text("I built a Python ingestion component and debugged its parser.\n")

    pipeline = ProgressRecordingPipeline(tmp_path)
    pipeline.backend = ChunkRecordingBackend()

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 1
    phases = [payload.get("phase") for payload in pipeline.progress_payloads]
    assert "graph_checkpoint" in phases
    assert "graph_sync" in phases


def test_ingest_dir_writes_graph_candidate_progress_heartbeats(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "graph-candidate-heartbeat-corpus"
    corpus_root.mkdir()
    (corpus_root / "notes.md").write_text("I built a Python data tool and designed its SQLite storage.\n")

    pipeline = ProgressRecordingPipeline(tmp_path)
    pipeline.backend = ProgressiveGraphBackend()

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 1
    graph_progress_updates = [
        payload
        for payload in pipeline.progress_payloads
        if isinstance(payload.get("graph_progress"), dict)
    ]
    assert graph_progress_updates
    graph_events = [payload["graph_progress"]["event"] for payload in graph_progress_updates]
    assert "candidate-start" in graph_events
    assert "skill-score-start" in graph_events
    assert "skill-score-finished" in graph_events
    assert all(payload.get("phase") in {"graph_checkpoint", "graph_sync"} for payload in graph_progress_updates)


def test_ingest_dir_reuses_incomplete_discovery_cache_on_resume(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "resume-cache-corpus"
    corpus_root.mkdir()
    source_path = corpus_root / "notes.md"
    source_path.write_text("I built a Python parser and debugged the import flow.\n")
    relative_import_path = Path("resume-cache-corpus") / "notes.md"

    pipeline = Pipeline(tmp_path)
    pipeline._write_ingest_run_state(
        root=corpus_root,
        total_materials=1,
        entries=[
            IngestManifestEntry(
                relative_import_path=relative_import_path.as_posix(),
                source_path=source_path.resolve().as_posix(),
                archive_member=None,
                source_family=SourceFamily.GENERIC,
                source_family_subproduct=None,
                detection_reason="test cached discovery",
                status=IngestMaterialStatus.DISCOVERED,
            )
        ],
    )

    class NoDiscoveryPipeline(Pipeline):
        def _discover_materials(self, root, *, on_progress=None):
            del root, on_progress
            raise AssertionError("resume should use cached discovery materials")

    resumed = NoDiscoveryPipeline(tmp_path)
    resumed.backend = FakeLLMBackend()

    result = resumed.ingest_directory(corpus_root)

    assert result.processed == 1
    assert "ingest-discovery-cache-reused" in (tmp_path / "tree" / "log.md").read_text()


def test_recompute_graph_reuses_cached_candidate_decisions(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "graph-cache-corpus"
    corpus_root.mkdir()
    (corpus_root / "report.md").write_text(
        "I built a Python reporting dashboard, designed the SQLite schema, and reviewed the analytics.\n"
    )

    pipeline = Pipeline(tmp_path)
    backend = CountingGraphBackend()
    pipeline.backend = backend

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 1
    assert backend.canonicalize_calls > 0
    assert backend.score_calls > 0

    first_canonicalize_calls = backend.canonicalize_calls
    first_score_calls = backend.score_calls

    pipeline.recompute_graph()

    assert backend.canonicalize_calls == first_canonicalize_calls
    assert backend.score_calls == first_score_calls


def test_recompute_graph_emits_progressive_checkpoints(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "progressive-graph-corpus"
    corpus_root.mkdir()
    (corpus_root / "notes.md").write_text("I built a Python data tool and designed its SQLite storage.\n")

    pipeline = Pipeline(tmp_path)
    pipeline.backend = ProgressiveGraphBackend()

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 1

    checkpoint_calls: list[str] = []
    pipeline.recompute_graph(checkpoint_callback=lambda: checkpoint_calls.append("checkpoint"))

    assert len(checkpoint_calls) >= 2


def test_recompute_graph_reuses_existing_domain_skill_id(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "domain-reuse-corpus"
    corpus_root.mkdir()
    (corpus_root / "notes.md").write_text("I designed several data analysis workflows.\n")

    pipeline = Pipeline(tmp_path)
    pipeline.backend = DomainReuseBackend()

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 1

    skill_rows = {
        row["skill_id"]: row
        for row in pipeline.storage.list_skill_rows()
    }
    assert "domain.data" in skill_rows
    assert skill_rows["domain.data"]["level"] is not None
    assert "skill:data" not in skill_rows


def test_ingest_dir_refreshes_live_graph_before_completion(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "checkpoint-corpus"
    corpus_root.mkdir()
    (corpus_root / "notes.md").write_text("I built a Python parser and debugged the release flow.\n")

    pipeline = CheckpointRecordingPipeline(tmp_path)
    pipeline.backend = FakeLLMBackend()

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 1
    assert pipeline.graph_checkpoint_calls >= 1


def test_ingest_dir_batches_live_graph_refreshes_for_large_runs(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    config = load_config(tmp_path / "config" / "config.yaml")
    config.graph_refresh.live_checkpoint_material_interval = 3
    config.graph_refresh.live_checkpoint_min_interval_seconds = 0.0
    config.graph_refresh.small_run_live_checkpoint_material_limit = 0
    write_config(tmp_path / "config" / "config.yaml", config)

    corpus_root = tmp_path / "batched-checkpoint-corpus"
    corpus_root.mkdir()
    for index in range(4):
        (corpus_root / f"notes-{index}.md").write_text(
            f"I built Python parser component {index} and debugged its SQLite storage.\n"
        )

    pipeline = CheckpointRecordingPipeline(tmp_path)
    pipeline.backend = FakeLLMBackend()

    result = pipeline.ingest_directory(corpus_root)

    assert result.processed == 4
    assert pipeline.graph_checkpoint_calls == 1


def test_ingest_dir_stops_when_backend_quota_is_exhausted(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "quota-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")
    (corpus_root / "two.txt").write_text("I shipped a Python ingestion pipeline.\n")
    (corpus_root / "three.txt").write_text("I documented the Python graph layout.\n")

    pipeline = Pipeline(tmp_path)
    backend = StopOnQuotaBackend(fail_on_call=2)
    pipeline.backend = backend

    try:
        pipeline.ingest_directory(corpus_root)
    except RuntimeError as exc:
        assert "Ingest stopped because the LLM backend is unavailable" in str(exc)
        assert "quota exhausted" in str(exc)
    else:
        raise AssertionError("expected ingest to stop on quota exhaustion")

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "blocked"
    assert "quota exhausted" in progress["blocked_reason"].lower()
    assert progress["counts"]["processed"] == 1
    assert progress["counts"]["failed"] == 1
    assert progress["progress"]["completed"] == 2
    assert progress["progress"]["total"] == 3
    assert backend.call_count == 2
    assert len(pipeline.storage.list_sources()) == 2


def test_ingest_dir_stops_when_backend_model_is_cooling_down(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "cooldown-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")
    (corpus_root / "two.txt").write_text("I shipped a Python ingestion pipeline.\n")
    (corpus_root / "three.txt").write_text("I documented the Python graph layout.\n")

    pipeline = Pipeline(tmp_path)
    backend = StopOnModelCooldownBackend(fail_on_call=2)
    pipeline.backend = backend

    try:
        pipeline.ingest_directory(corpus_root)
    except RuntimeError as exc:
        assert "Ingest stopped because the LLM backend is unavailable" in str(exc)
        assert "model_cooldown" in str(exc)
        assert "reset_seconds" in str(exc)
    else:
        raise AssertionError("expected ingest to stop on model cooldown")

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "blocked"
    assert "model_cooldown" in progress["blocked_reason"]
    assert progress["counts"]["processed"] == 1
    assert progress["counts"]["failed"] == 1
    assert progress["progress"]["completed"] == 2
    assert progress["progress"]["total"] == 3
    assert backend.call_count == 2


def test_ingest_dir_stops_when_backend_rate_limit_is_reached(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "rate-limit-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")
    (corpus_root / "two.txt").write_text("I shipped a Python ingestion pipeline.\n")
    (corpus_root / "three.txt").write_text("I documented the Python graph layout.\n")

    pipeline = Pipeline(tmp_path)
    backend = StopOnRateLimitBackend(fail_on_call=2)
    pipeline.backend = backend

    try:
        pipeline.ingest_directory(corpus_root)
    except RuntimeError as exc:
        assert "Ingest stopped because the LLM backend is unavailable" in str(exc)
        assert "Rate limit reached for requests" in str(exc)
    else:
        raise AssertionError("expected ingest to stop on request rate limit")

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "blocked"
    assert "Rate limit reached for requests" in progress["blocked_reason"]
    assert progress["counts"]["processed"] == 1
    assert progress["counts"]["failed"] == 1
    assert progress["progress"]["completed"] == 2
    assert progress["progress"]["total"] == 3
    assert backend.call_count == 2


def test_ingest_dir_stops_when_source_material_is_unavailable(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "missing-source-corpus"
    corpus_root.mkdir()
    missing_source = corpus_root / "missing.txt"
    pipeline = Pipeline(tmp_path)
    pipeline._write_ingest_run_state(
        root=corpus_root,
        total_materials=1,
        entries=[
            IngestManifestEntry(
                relative_import_path=Path("missing-source-corpus/missing.txt").as_posix(),
                source_path=missing_source.as_posix(),
                archive_member=None,
                source_family=SourceFamily.GENERIC,
                source_family_subproduct=None,
                detection_reason="cached test material",
                status=IngestMaterialStatus.DISCOVERED,
            )
        ],
    )

    try:
        pipeline.ingest_directory(corpus_root)
    except RuntimeError as exc:
        assert "source input is unavailable" in str(exc)
        assert "Source material is unavailable" in str(exc)
    else:
        raise AssertionError("expected ingest to stop on unavailable source material")

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "blocked"
    assert "Source material is unavailable" in progress["blocked_reason"]
    assert progress["counts"]["failed"] == 1


def test_ingest_dir_stops_when_backend_returns_invalid_structured_json(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "structured-json-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")
    (corpus_root / "two.txt").write_text("I shipped a Python ingestion pipeline.\n")
    (corpus_root / "three.txt").write_text("I documented the Python graph layout.\n")

    pipeline = Pipeline(tmp_path)
    backend = StopOnStructuredValidationBackend(fail_on_call=2)
    pipeline.backend = backend

    try:
        pipeline.ingest_directory(corpus_root)
    except RuntimeError as exc:
        assert "Ingest stopped because the LLM backend is unavailable" in str(exc)
        assert "Structured response validation failed" in str(exc)
    else:
        raise AssertionError("expected ingest to stop on malformed structured backend output")

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "blocked"
    assert "Structured response validation failed" in progress["blocked_reason"]
    assert progress["counts"]["processed"] == 1
    assert progress["counts"]["failed"] == 1
    assert progress["progress"]["completed"] == 2
    assert progress["progress"]["total"] == 3
    assert backend.call_count == 2


def test_ingest_dir_writes_blocked_progress_before_retrying_graph_on_material_cooldown(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "material-graph-cooldown-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")
    (corpus_root / "two.txt").write_text("I shipped a Python ingestion pipeline.\n")

    pipeline = Pipeline(tmp_path)
    backend = StopOnMaterialThenGraphCooldownBackend(fail_on_call=2)
    pipeline.backend = backend

    try:
        pipeline.ingest_directory(corpus_root)
    except RuntimeError as exc:
        assert "Ingest stopped because the LLM backend is unavailable" in str(exc)
        assert "model_cooldown" in str(exc)
    else:
        raise AssertionError("expected material cooldown to stop ingest")

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "blocked"
    assert "model_cooldown" in progress["blocked_reason"]
    assert progress["counts"]["processed"] == 1
    assert progress["counts"]["failed"] == 1


def test_ingest_dir_marks_progress_blocked_when_graph_sync_model_is_cooling_down(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "graph-cooldown-corpus"
    corpus_root.mkdir()
    (corpus_root / "one.txt").write_text("I built a Python parser.\n")

    pipeline = Pipeline(tmp_path)
    pipeline.backend = StopOnGraphCooldownBackend()

    try:
        pipeline.ingest_directory(corpus_root)
    except RuntimeError as exc:
        assert "during graph sync" in str(exc)
        assert "model_cooldown" in str(exc)
    else:
        raise AssertionError("expected graph sync cooldown to stop ingest")

    progress = json.loads((tmp_path / "state" / "progress.json").read_text())
    assert progress["status"] == "blocked"
    assert "model_cooldown" in progress["blocked_reason"]
    assert progress["counts"]["processed"] == 1
    assert progress["counts"]["failed"] == 0
    assert progress["progress"]["completed"] == 1
    assert progress["progress"]["total"] == 1


def test_replace_source_spans_deduplicates_duplicate_span_ids(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    pipeline = Pipeline(tmp_path)
    pipeline.storage.replace_source_spans(
        "src_duplicate",
        [
            ParsedSpan(
                span_id="span_duplicate",
                source_id="src_duplicate",
                segment_kind="line",
                heading=None,
                text="first",
                span_start=0,
                span_end=5,
                line_start=1,
                line_end=1,
            ),
            ParsedSpan(
                span_id="span_duplicate",
                source_id="src_duplicate",
                segment_kind="line",
                heading=None,
                text="second",
                span_start=6,
                span_end=12,
                line_start=2,
                line_end=2,
            ),
        ],
    )

    with pipeline.storage.connect() as connection:
        rows = connection.execute(
            "select span_id from source_spans where source_id = ? order by span_start",
            ("src_duplicate",),
        ).fetchall()

    assert len(rows) == 2
    assert rows[0]["span_id"] == "span_duplicate"
    assert rows[1]["span_id"].startswith("span_duplicate::")
