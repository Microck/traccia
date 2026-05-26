from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

import typer

from traccia.bootstrap import DIRECTORIES, FILES, JSON_FILES, RepoInitializer
from traccia.config import load_config
from traccia.llm import BackendError, backend_from_config, backend_summary
from traccia.pipeline import GRAPH_SCORE_MODE_FULL, GRAPH_SCORE_MODE_INCREMENTAL, Pipeline
from traccia.rendering import (
    ascii_tree,
    export_debug_report,
    export_obsidian,
    mermaid_tree,
    render_project,
)
from traccia.storage import Storage
from traccia.viewer import export_admin_viewer, export_viewer, publish_public_bundle

app = typer.Typer(help="Local-first reflective skill graph compiler.")
alias_app = typer.Typer(help="Manage canonical aliases.")
export_app = typer.Typer(help="Export graph projections.")
app.add_typer(alias_app, name="alias")
app.add_typer(export_app, name="export")


def _project_config_path(project_root: Path) -> Path:
    return project_root / "config" / "config.yaml"


def _storage(project_root: Path) -> Storage:
    return Storage(project_root.resolve())


def _pipeline(project_root: Path) -> Pipeline:
    return Pipeline(project_root.resolve())


def _graph_score_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {GRAPH_SCORE_MODE_INCREMENTAL, GRAPH_SCORE_MODE_FULL}:
        raise typer.BadParameter("expected 'incremental' or 'full'")
    return normalized


def _ingest_score_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {GRAPH_SCORE_MODE_INCREMENTAL, GRAPH_SCORE_MODE_FULL, "none"}:
        raise typer.BadParameter("expected 'incremental', 'full', or 'none'")
    return normalized


def _skill_markdown_path(project_root: Path, skill_id: str) -> Path:
    return project_root / "tree" / "nodes" / f"{skill_id}.md"


def _package_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _command_available(command: str) -> bool:
    return shutil.which(command) is not None


_REMOTE_TRANSCRIPTION_API_KEY_ENVS = (
    "GROQ_API_KEY",
    "ASSEMBLYAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_GENERATIVE_AI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENAI_API_KEY",
    "FAL_KEY",
)

_LOCAL_WHISPER_CPP_COMMANDS = (
    "whisper-cli",
    "whisper-cpp",
)

_DEFAULT_WHISPER_CPP_MODEL_PATH = (
    Path.home() / ".summarize" / "cache" / "whisper-cpp" / "models" / "ggml-base.bin"
)


def _env_available(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def _path_env_available(name: str) -> bool:
    value = os.environ.get(name, "").strip()
    return bool(value and Path(value).expanduser().exists())


def _summarize_whisper_cpp_binary_available() -> bool:
    binary_override = os.environ.get("SUMMARIZE_WHISPER_CPP_BINARY", "").strip()
    if binary_override:
        return _command_available(binary_override)
    return any(_command_available(command) for command in _LOCAL_WHISPER_CPP_COMMANDS)


def _summarize_whisper_cpp_model_path() -> Path:
    model_override = os.environ.get("SUMMARIZE_WHISPER_CPP_MODEL_PATH", "").strip()
    if model_override:
        return Path(model_override).expanduser()
    return _DEFAULT_WHISPER_CPP_MODEL_PATH


def _summarize_whisper_cpp_model_available() -> bool:
    return _summarize_whisper_cpp_model_path().exists()


def _remote_transcription_fallback_available() -> tuple[bool, bool, bool, bool]:
    api_key_available = any(_env_available(name) for name in _REMOTE_TRANSCRIPTION_API_KEY_ENVS)
    local_whisper_cpp_binary_available = _summarize_whisper_cpp_binary_available()
    local_whisper_cpp_model_available = _summarize_whisper_cpp_model_available()
    local_whisper_cpp_available = (
        local_whisper_cpp_binary_available and local_whisper_cpp_model_available
    )
    return (
        api_key_available,
        local_whisper_cpp_available,
        local_whisper_cpp_binary_available,
        local_whisper_cpp_model_available,
    )


def _remote_media_capability_line(config) -> str:
    enabled = config.multimodal.enable_remote_media_enrichment
    command = config.multimodal.remote_media_enrichment_command
    summarize_available = _command_available(command)
    ffmpeg_available = _command_available("ffmpeg")
    yt_dlp_available = _command_available("yt-dlp") or _path_env_available("YT_DLP_PATH")
    tesseract_available = _command_available("tesseract")
    (
        api_key_available,
        local_whisper_cpp_available,
        local_whisper_cpp_binary_available,
        local_whisper_cpp_model_available,
    ) = _remote_transcription_fallback_available()

    required_ready = summarize_available
    if config.multimodal.enable_remote_media_slides:
        required_ready = required_ready and ffmpeg_available and yt_dlp_available
    if config.multimodal.enable_remote_media_slides_ocr:
        required_ready = required_ready and tesseract_available
    transcription_fallback_ready = api_key_available or local_whisper_cpp_available

    if not enabled:
        status = "disabled"
    elif required_ready and transcription_fallback_ready:
        status = "ready"
    else:
        status = "degraded"

    return (
        "remote media enrichment "
        f"(multimodal.enable_remote_media_enrichment={str(enabled).lower()}, "
        f"command={command}, "
        f"video_mode={config.multimodal.remote_media_enrichment_video_mode}, "
        f"slides={str(config.multimodal.enable_remote_media_slides).lower()}, "
        f"slides_ocr={str(config.multimodal.enable_remote_media_slides_ocr).lower()}): "
        f"status={status} "
        f"summarize={'yes' if summarize_available else 'no'} "
        f"ffmpeg={'yes' if ffmpeg_available else 'no'} "
        f"yt-dlp={'yes' if yt_dlp_available else 'no'} "
        f"tesseract={'yes' if tesseract_available else 'no'} "
        "transcription_fallback="
        f"api_key:{'yes' if api_key_available else 'no'} "
        f"local_whisper_cpp:{'yes' if local_whisper_cpp_available else 'no'} "
        f"whisper_cpp_binary:{'yes' if local_whisper_cpp_binary_available else 'no'} "
        f"whisper_cpp_model:{'yes' if local_whisper_cpp_model_available else 'no'} "
        f"whisper_cpp_model_path={_summarize_whisper_cpp_model_path().as_posix()}"
    )


def _optional_capability_lines(config) -> list[str]:
    lines: list[str] = []
    lines.append(
        "document normalization: "
        f"docling={'yes' if _package_available('docling') else 'no'} "
        f"markitdown={'yes' if _package_available('markitdown') else 'no'} "
        f"marker_single={'yes' if _command_available('marker_single') else 'no'}"
    )
    lines.append(
        "image OCR "
        f"(multimodal.enable_local_image_ocr={str(config.multimodal.enable_local_image_ocr).lower()}): "
        f"tesseract={'yes' if _command_available('tesseract') else 'no'}"
    )
    lines.append(
        "media transcription "
        f"(multimodal.enable_local_media_transcription={str(config.multimodal.enable_local_media_transcription).lower()}, "
        f"provider={config.multimodal.audio_transcription_provider}): "
        f"ffmpeg={'yes' if _command_available('ffmpeg') else 'no'} "
        f"ffprobe={'yes' if _command_available('ffprobe') else 'no'} "
        f"whisper={'yes' if _command_available('whisper') else 'no'}"
    )
    lines.append(_remote_media_capability_line(config))
    return lines


@app.command()
def init(
    path: Path = typer.Argument(Path("."), help="Directory to initialize."),
    force: bool = typer.Option(False, "--force", help="Overwrite scaffold-managed files."),
) -> None:
    """Create the repository layout, config, prompts, and empty state."""

    RepoInitializer(project_root=path.resolve(), force=force).initialize()
    typer.echo(f"Initialized traccia repository at {path.resolve()}")


@app.command()
def lint(path: Path = typer.Argument(Path("."), help="Project root to validate.")) -> None:
    """Validate the repo config against the schema."""

    config = load_config(_project_config_path(path.resolve()))
    typer.echo(
        "Config valid: "
        f"project={config.project_name} "
        f"extractor_version={config.pipeline.extractor_version}"
    )


@app.command()
def doctor(
    path: Path = typer.Argument(Path("."), help="Project root to inspect."),
    check_backend: bool = typer.Option(
        False,
        "--check-backend",
        help="Run an authenticated backend healthcheck after verifying the scaffold.",
    ),
) -> None:
    """Check that the scaffolded layout exists."""

    project_root = path.resolve()
    missing_paths: list[str] = []

    if not _project_config_path(project_root).exists():
        missing_paths.append("config/config.yaml")

    for directory in DIRECTORIES:
        if not (project_root / directory).exists():
            missing_paths.append(directory)

    for relative_path in (*FILES.keys(), *JSON_FILES.keys(), "state/catalog.sqlite"):
        if not (project_root / relative_path).exists():
            missing_paths.append(relative_path)

    if missing_paths:
        for missing_path in missing_paths:
            typer.echo(f"missing: {missing_path}")
        raise typer.Exit(code=1)

    config = load_config(_project_config_path(project_root))
    typer.echo(f"backend: {backend_summary(config)}")
    for line in _optional_capability_lines(config):
        typer.echo(line)

    backend_key = os.getenv(config.backend.api_key_env)
    if config.backend.provider == "fake":
        typer.echo("backend auth: not required for fake provider")
    elif backend_key:
        typer.echo(f"backend auth: found env var {config.backend.api_key_env}")
    else:
        typer.echo(
            f"backend auth: missing env var {config.backend.api_key_env} for provider {config.backend.provider}"
        )
        if check_backend:
            raise typer.Exit(code=1)

    if check_backend:
        try:
            typer.echo(f"backend health: {backend_from_config(config).healthcheck()}")
        except BackendError as exc:
            typer.echo(f"backend health: failed - {exc}")
            raise typer.Exit(code=1) from exc

    typer.echo("Phase 0 scaffold looks healthy.")


@app.command()
def add(
    path: Path,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    imported_path = _pipeline(project_root).add_file(path.resolve())
    typer.echo(f"added: {imported_path}")


@app.command("add-dir")
def add_dir(
    path: Path,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    count = _pipeline(project_root).add_directory(path.resolve())
    typer.echo(f"added={count}")


@app.command()
def reingest(
    source_id: str,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    processed = _pipeline(project_root).reingest(source_id)
    typer.echo(f"reingest source_id={source_id} processed={int(processed)}")


@app.command()
def watch(
    path: Path,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
    interval_seconds: int = typer.Option(
        2, "--interval-seconds", help="Polling interval in seconds."
    ),
) -> None:
    _pipeline(project_root).watch(path.resolve(), interval_seconds=interval_seconds)


@app.command()
def ingest(
    path: Path,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
    score_mode: str = typer.Option(
        GRAPH_SCORE_MODE_INCREMENTAL,
        "--score-mode",
        help="Graph scoring mode after ingest: incremental, full, or none.",
    ),
) -> None:
    resolved_score_mode = _ingest_score_mode(score_mode)
    _, processed = _pipeline(project_root).ingest_file(path.resolve(), root=path.parent.resolve())
    if resolved_score_mode != "none":
        _pipeline(project_root).recompute_graph(score_mode=resolved_score_mode)
        render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(f"processed={int(processed)} skipped={int(not processed)}")


@app.command("ingest-dir")
def ingest_dir(
    path: Path,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
    import_prefix: Path | None = typer.Option(
        None,
        "--import-prefix",
        help="Stable relative identity prefix for source IDs and raw/imported paths.",
    ),
    sync_graph: bool = typer.Option(
        True,
        "--sync-graph/--no-sync-graph",
        help="Recompute and render graph projections after extraction.",
    ),
    sync_deletions: bool = typer.Option(
        True,
        "--sync-deletions/--no-sync-deletions",
        help="Mark previously tracked sources missing from this import scope as deleted.",
    ),
    parallel_extractions: int | None = typer.Option(
        None,
        "--parallel-extractions",
        min=1,
        max=16,
        help="Number of concurrent evidence extraction workers. Defaults to config ingest.parallel_extractions.",
    ),
    score_mode: str = typer.Option(
        GRAPH_SCORE_MODE_INCREMENTAL,
        "--score-mode",
        help="Graph scoring mode after extraction: incremental, full, or none.",
    ),
) -> None:
    resolved_score_mode = _ingest_score_mode(score_mode)
    effective_sync_graph = sync_graph and resolved_score_mode != "none"
    result = _pipeline(project_root).ingest_directory(
        path.resolve(),
        import_prefix=import_prefix,
        sync_graph=effective_sync_graph,
        sync_deletions=sync_deletions,
        parallel_extractions=parallel_extractions,
        score_mode=resolved_score_mode
        if resolved_score_mode != "none"
        else GRAPH_SCORE_MODE_INCREMENTAL,
    )
    typer.echo(
        f"discovered={result.discovered} imported={result.imported} prepared={result.prepared} "
        f"processed={result.processed} skipped={result.skipped} "
        f"delayed={result.delayed} failed={result.failed} deleted={result.deleted} "
        f"graph_sync={str(effective_sync_graph).lower()} "
        f"score_mode={resolved_score_mode} deletion_sync={str(sync_deletions).lower()}"
    )


@app.command("stage-dir")
def stage_dir(
    path: Path,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
    import_prefix: Path | None = typer.Option(
        None,
        "--import-prefix",
        help="Stable relative identity prefix for source IDs and raw/imported paths.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-prepare materials even when their parsed artifacts are current.",
    ),
) -> None:
    """Prepare materials without LLM extraction or graph recompute.

    This is safe to run beside an already-active scoring process because it only
    discovers, imports, parses, and checkpoints material state. Evidence
    extraction and graph scoring are deferred to a normal ingest/scoring run.
    """

    result = _pipeline(project_root).ingest_directory(
        path.resolve(),
        force=force,
        extract=False,
        sync_graph=False,
        sync_deletions=False,
        import_prefix=import_prefix,
    )
    typer.echo(
        f"discovered={result.discovered} imported={result.imported} prepared={result.prepared} "
        f"processed={result.processed} skipped={result.skipped} delayed={result.delayed} "
        f"failed={result.failed} deleted={result.deleted} extraction=deferred "
        "graph_sync=deferred deletion_sync=deferred"
    )


@app.command("merge-project")
def merge_project(
    source_project_root: Path,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Target initialized traccia repository."
    ),
    rebuild: bool = typer.Option(
        True,
        "--rebuild/--no-rebuild",
        help="Recompute and render the target graph after importing evidence.",
    ),
    copy_artifacts: bool = typer.Option(
        True,
        "--copy-artifacts/--no-copy-artifacts",
        help="Copy missing parsed/evidence artifacts for resume consistency.",
    ),
) -> None:
    """Merge source/evidence records from another Traccia project into this one."""

    target_root = project_root.resolve()
    source_root = source_project_root.resolve()
    source_db_path = source_root / "state" / "catalog.sqlite"
    if not source_db_path.exists():
        typer.echo(f"missing source catalog: {source_db_path}")
        raise typer.Exit(code=1)
    if source_db_path == target_root / "state" / "catalog.sqlite":
        typer.echo("source and target projects are the same")
        raise typer.Exit(code=1)

    counts = _storage(target_root).merge_imported_records_from(source_db_path)
    artifact_counts = {"parsed": 0, "evidence": 0}
    if copy_artifacts:
        artifact_counts = _copy_missing_merge_artifacts(source_root=source_root, target_root=target_root)

    if rebuild:
        _pipeline(target_root).recompute_graph()
        render_project(target_root, storage=_storage(target_root))

    typer.echo(
        " ".join(
            [
                f"sources={counts['sources']}",
                f"source_spans={counts['source_spans']}",
                f"evidence_items={counts['evidence_items']}",
                f"parsed_artifacts={artifact_counts['parsed']}",
                f"evidence_artifacts={artifact_counts['evidence']}",
                f"rebuilt={str(rebuild).lower()}",
            ]
        )
    )


def _copy_missing_merge_artifacts(*, source_root: Path, target_root: Path) -> dict[str, int]:
    counts = {"parsed": 0, "evidence": 0}
    for directory_name in ("parsed", "evidence"):
        source_directory = source_root / directory_name
        target_directory = target_root / directory_name
        if not source_directory.exists():
            continue
        target_directory.mkdir(parents=True, exist_ok=True)
        for source_path in source_directory.glob("*.json"):
            target_path = target_directory / source_path.name
            if target_path.exists():
                continue
            shutil.copy2(source_path, target_path)
            counts[directory_name] += 1
    return counts


@app.command("discover-dir")
def discover_dir(
    path: Path,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
    import_prefix: Path | None = typer.Option(
        None,
        "--import-prefix",
        help="Stable relative identity prefix to use while previewing source IDs.",
    ),
    format: str = typer.Option("text", "--format", help="text or json"),
) -> None:
    summary = _pipeline(project_root).discover_directory(
        path.resolve(),
        import_prefix=import_prefix,
    )
    payload = {
        "root_uri": path.resolve().as_uri(),
        "materials": summary.total_materials,
        "direct_files": summary.direct_files,
        "archive_members": summary.archive_members,
        "by_root": summary.by_root,
        "by_family": summary.by_family,
        "by_family_subproduct": summary.by_family_subproduct,
    }
    if format == "json":
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(
        f"materials={summary.total_materials} direct_files={summary.direct_files} "
        f"archive_members={summary.archive_members}"
    )
    typer.echo("by_root:")
    for name, count in sorted(summary.by_root.items()):
        typer.echo(f"- {name}: {count}")
    typer.echo("by_family:")
    for name, count in sorted(summary.by_family.items()):
        typer.echo(f"- {name}: {count}")
    typer.echo("by_family_subproduct:")
    for name, count in sorted(summary.by_family_subproduct.items()):
        typer.echo(f"- {name}: {count}")


@app.command()
def rebuild(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    result = _pipeline(project_root).rebuild()
    typer.echo(f"rebuilt={result.processed}")


@app.command()
def score(
    mode: str = typer.Option(
        GRAPH_SCORE_MODE_INCREMENTAL,
        "--mode",
        help="Graph scoring mode: incremental reuses unchanged work; full ignores score caches.",
    ),
    parallel_scores: int | None = typer.Option(
        None,
        "--parallel-scores",
        min=1,
        max=16,
        help="Number of concurrent skill scoring workers. Defaults to config graph_scoring.parallel_scores.",
    ),
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    resolved_mode = _graph_score_mode(mode)
    _pipeline(project_root).recompute_graph(
        score_mode=resolved_mode,
        parallel_scores=parallel_scores,
    )
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(
        f"scored={resolved_mode} parallel_scores={parallel_scores or 'config'} "
        f"rendered={project_root.resolve()}"
    )


@app.command()
def render(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(f"rendered={project_root.resolve()}")


@app.command()
def tree(
    format: str = typer.Option("ascii", "--format", help="ascii or mermaid"),
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    if format == "mermaid":
        typer.echo(mermaid_tree(project_root.resolve()))
        return
    typer.echo(ascii_tree(project_root.resolve()))


@app.command()
def node(
    skill_id: str,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    typer.echo(_skill_markdown_path(project_root.resolve(), skill_id).read_text())


@app.command()
def explain(
    skill_or_alias: str,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    row = _storage(project_root).find_skill_by_lookup(skill_or_alias)
    if not row:
        raise typer.Exit(code=1)
    typer.echo(_skill_markdown_path(project_root.resolve(), row["skill_id"]).read_text())


@app.command()
def why(
    skill_id: str,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    explain(skill_id, project_root)


@app.command()
def evidence(
    skill_id: str,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    row = _storage(project_root).find_skill_by_lookup(skill_id)
    if not row:
        raise typer.Exit(code=1)
    evidence_items = _storage(project_root).list_evidence()
    for item in evidence_items:
        if row["name"] in item.skill_candidates:
            typer.echo(f"{item.evidence_id}: {item.evidence_type.value} - {item.quote}")


@app.command()
def review(
    accept: str | None = typer.Option(None, "--accept", help="Accept a review item."),
    reject: str | None = typer.Option(None, "--reject", help="Reject a review item."),
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    storage = _storage(project_root)
    if accept:
        item = storage.get_review_item(accept)
        if not item:
            raise typer.Exit(code=1)
        proposed = json.loads(item["proposed_change_json"])
        storage.set_review_status(accept, "accepted")
        if proposed.get("type") == "create_skill":
            storage.add_manual_override(
                target_type="skill",
                target_id=proposed["name"],
                action="create_skill",
                payload={"name": proposed["name"]},
            )
            _pipeline(project_root).recompute_graph()
            render_project(project_root.resolve(), storage=storage)
        storage.sync_review_queue_file()
        typer.echo(f"accepted={accept}")
        return
    if reject:
        storage.set_review_status(reject, "rejected")
        storage.sync_review_queue_file()
        typer.echo(f"rejected={reject}")
        return

    review_items = storage.list_review_items()
    if not review_items:
        typer.echo("No pending review items.")
        return
    for item in review_items:
        typer.echo(f"item_id={item['item_id']}")
        typer.echo(f"reason={item['reason']}")
        typer.echo(f"proposal={item['proposed_change_json']}")
        typer.echo(f"evidence_ids={item['evidence_ids_json']}")
        typer.echo("")


@app.command()
def lock(
    skill_id: str,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    storage = _storage(project_root)
    row = storage.find_skill_by_lookup(skill_id)
    if not row:
        raise typer.Exit(code=1)
    storage.add_manual_override(
        target_type="skill",
        target_id=row["skill_id"],
        action="lock",
        payload={"locked": True},
    )
    _pipeline(project_root).recompute_graph()
    render_project(project_root.resolve(), storage=storage)
    typer.echo(f"locked={row['skill_id']}")


@app.command()
def hide(
    skill_id: str,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    storage = _storage(project_root)
    row = storage.find_skill_by_lookup(skill_id)
    if not row:
        raise typer.Exit(code=1)
    storage.add_manual_override(
        target_type="skill",
        target_id=row["skill_id"],
        action="hide",
        payload={"hidden": True},
    )
    _pipeline(project_root).recompute_graph()
    render_project(project_root.resolve(), storage=storage)
    typer.echo(f"hidden={row['skill_id']}")


@alias_app.command("add")
def alias_add(
    skill_id: str,
    alias: str,
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    storage = _storage(project_root)
    row = storage.find_skill_by_lookup(skill_id)
    if not row:
        raise typer.Exit(code=1)
    storage.add_manual_override(
        target_type="skill",
        target_id=row["skill_id"],
        action="alias_add",
        payload={"alias": alias},
    )
    _pipeline(project_root).recompute_graph()
    render_project(project_root.resolve(), storage=storage)
    typer.echo(f"alias-added={alias}")


@export_app.command("graph")
def export_graph(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(project_root.resolve() / "graph" / "graph.json")


@export_app.command("profile")
def export_profile(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(project_root.resolve() / "profile" / "skill.md")


@export_app.command("skill-md")
def export_skill_md(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(project_root.resolve() / "tree" / "nodes")


@export_app.command("obsidian")
def export_obsidian_command(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(export_obsidian(project_root.resolve()))


@export_app.command("debug-report")
def export_debug_report_command(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(export_debug_report(project_root.resolve()))


@export_app.command("viewer")
def export_viewer_command(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
    no_sound: bool = typer.Option(
        False,
        "--no-sound",
        help="Disable SFX in the exported public viewer by default.",
    ),
) -> None:
    """Generate the read-only public finished-run skill map viewer.

    Produces a static export folder at ``exports/viewer/`` containing a
    public-safe graph contract, HTML, CSS, JS, and a procedural SFX engine.
    The viewer is desktop-first but responsive, with pan/zoom, search,
    filters, minimap, legend, node drawer, and hash deep links.
    """
    render_project(project_root.resolve(), storage=_storage(project_root))
    export_path = export_viewer(project_root.resolve(), enable_sound=not no_sound)
    typer.echo(export_path)


@export_app.command("admin")
def export_admin_command(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
    no_sound: bool = typer.Option(
        False,
        "--no-sound",
        help="Disable SFX in the exported admin viewer by default.",
    ),
) -> None:
    """Generate the admin curation viewer for the finished-run skill map.

    Produces a static export folder at ``exports/viewer-admin/`` containing
    the full internal graph (admin-visible, includes hidden/disputed/review/
    low-confidence nodes), curation.json, and the admin viewer assets. The
    admin can hide/mute, restore, feature/pin, collapse/expand domains, add
    public label/note overrides, and save curation.json.

    When running locally, the save action writes directly to the export
    folder. Otherwise it triggers a browser download of curation.json.
    """
    render_project(project_root.resolve(), storage=_storage(project_root))
    export_path = export_admin_viewer(project_root.resolve(), enable_sound=not no_sound)
    typer.echo(export_path)


@export_app.command("publish")
def export_publish_command(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
    no_sound: bool = typer.Option(
        False,
        "--no-sound",
        help="Disable SFX in the published public viewer by default.",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        help="Output directory name under exports/ (default: viewer-public).",
    ),
) -> None:
    """Generate the redacted public bundle from graph.json + curation.json.

    Reads the full internal graph and admin-authored curation.json (from
    ``exports/viewer/curation.json``), applies all redaction rules, and
    writes a separate public bundle with its own viewer assets.

    The public bundle physically excludes hidden nodes, hidden edges,
    private/redacted provenance, raw source paths, raw excerpts, sensitive
    evidence IDs, disputed/review nodes (unless approved), and
    low-confidence nodes (unless approved).
    """
    render_project(project_root.resolve(), storage=_storage(project_root))
    publish_path = publish_public_bundle(
        project_root.resolve(),
        enable_sound=not no_sound,
        output_dir=output_dir,
    )
    typer.echo(publish_path)


@app.command()
def stats(
    project_root: Path = typer.Option(
        Path("."), "--project-root", help="Initialized traccia repository."
    ),
) -> None:
    storage = _storage(project_root)
    typer.echo(f"sources: {len(storage.list_sources())}")
    typer.echo(f"skills: {len(storage.list_skill_rows())}")
    typer.echo(f"evidence: {len(storage.list_evidence())}")
    typer.echo(f"review: {len(storage.list_review_items())}")
