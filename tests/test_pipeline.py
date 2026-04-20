from __future__ import annotations

import json
import os
import shutil
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from traccia.cli import app
from traccia.config import load_config, write_config
from traccia.llm import FakeLLMBackend
from traccia.models import EvidenceItem, EvidenceType, ParsedSpan, ReliabilityTier, SignalClass
from traccia.parsers import parse_document
from traccia.pipeline import Pipeline, _chunk_document
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


def test_ingest_dir_records_archive_family_and_member_in_manifest(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)

    corpus_root = tmp_path / "archive-corpus"
    corpus_root.mkdir()
    archive_path = corpus_root / "twitter-export.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "data/account.js",
            'window.YTD.account.part0 = [{"account": {"username": "alice"}}];\n',
        )

    result = runner.invoke(app, ["ingest-dir", str(corpus_root), "--project-root", str(tmp_path)])
    assert result.exit_code == 0, result.stdout

    manifest = latest_manifest(tmp_path)
    assert len(manifest["materials"]) == 1
    entry = manifest["materials"][0]
    assert entry["status"] == "processed"
    assert entry["source_family"] == "twitter_archive"
    assert entry["archive_member"] == "data/account.js"

    storage = Pipeline(tmp_path).storage
    sources = storage.list_sources()
    assert len(sources) == 1
    metadata = json.loads(sources[0]["metadata_json"])
    assert metadata["source_family"] == "twitter_archive"
    assert metadata["archive_member"] == "data/account.js"
    assert metadata["source_family_subproduct"] == "account"
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
            for index in range(18)
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
