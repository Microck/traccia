from __future__ import annotations

import json
import os
from pathlib import Path

import typer

from traccia.bootstrap import DIRECTORIES, FILES, JSON_FILES, RepoInitializer
from traccia.config import load_config
from traccia.llm import BackendError, backend_from_config, backend_summary
from traccia.pipeline import Pipeline
from traccia.rendering import ascii_tree, export_obsidian, mermaid_tree, render_project
from traccia.storage import Storage

app = typer.Typer(help="Local-first reflective skill graph compiler.")
alias_app = typer.Typer(help="Manage canonical aliases.")
export_app = typer.Typer(help="Export graph projections.")
app.add_typer(alias_app, name="alias")
app.add_typer(export_app, name="export")


_PROJECT_ROOT_HELP = "Initialized traccia repository."


def _project_config_path(project_root: Path) -> Path:
    return project_root / "config" / "config.yaml"


def _storage(project_root: Path) -> Storage:
    return Storage(project_root.resolve())


def _pipeline(project_root: Path) -> Pipeline:
    return Pipeline(project_root.resolve())


def _skill_markdown_path(project_root: Path, skill_id: str) -> Path:
    return project_root / "tree" / "nodes" / f"{skill_id}.md"


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

    missing_paths.extend(
        d for d in DIRECTORIES if not (project_root / d).exists()
    )
    missing_paths.extend(
        p
        for p in (*FILES.keys(), *JSON_FILES.keys(), "state/catalog.sqlite")
        if not (project_root / p).exists()
    )

    if missing_paths:
        for missing_path in missing_paths:
            typer.echo(f"missing: {missing_path}")
        raise typer.Exit(code=1)

    config = load_config(_project_config_path(project_root))
    typer.echo(f"backend: {backend_summary(config)}")

    backend_key = os.getenv(config.backend.api_key_env)
    if config.backend.provider == "fake":
        typer.echo("backend auth: not required for fake provider")
    elif backend_key:
        typer.echo(f"backend auth: found env var {config.backend.api_key_env}")
    else:
        typer.echo(
            "backend auth: missing env var "
            f"{config.backend.api_key_env} for provider {config.backend.provider}"
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
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    imported_path = _pipeline(project_root).add_file(path.resolve())
    typer.echo(f"added: {imported_path}")


@app.command("add-dir")
def add_dir(
    path: Path,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    count = _pipeline(project_root).add_directory(path.resolve())
    typer.echo(f"added={count}")


@app.command()
def reingest(
    source_id: str,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    processed = _pipeline(project_root).reingest(source_id)
    typer.echo(f"reingest source_id={source_id} processed={int(processed)}")


@app.command()
def watch(
    path: Path,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
    interval_seconds: int = typer.Option(2, "--interval-seconds", help="Polling interval in seconds."),
) -> None:
    _pipeline(project_root).watch(path.resolve(), interval_seconds=interval_seconds)


@app.command()
def ingest(
    path: Path,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    _, processed = _pipeline(project_root).ingest_file(path.resolve(), root=path.parent.resolve())
    _pipeline(project_root).recompute_graph()
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(f"processed={int(processed)} skipped={int(not processed)}")


@app.command("ingest-dir")
def ingest_dir(
    path: Path,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    result = _pipeline(project_root).ingest_directory(path.resolve())
    typer.echo(
        f"imported={result.imported} "
        f"processed={result.processed} "
        f"skipped={result.skipped} "
        f"deleted={result.deleted}"
    )


@app.command()
def rebuild(
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    result = _pipeline(project_root).rebuild()
    typer.echo(f"rebuilt={result.processed}")


@app.command()
def render(
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(f"rendered={project_root.resolve()}")


@app.command()
def tree(
    format: str = typer.Option("ascii", "--format", help="ascii or mermaid"),
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    if format == "mermaid":
        typer.echo(mermaid_tree(project_root.resolve()))
        return
    typer.echo(ascii_tree(project_root.resolve()))


@app.command()
def node(
    skill_id: str,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    typer.echo(_skill_markdown_path(project_root.resolve(), skill_id).read_text())


@app.command()
def explain(
    skill_or_alias: str,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    row = _storage(project_root).find_skill_by_lookup(skill_or_alias)
    if not row:
        raise typer.Exit(code=1)
    typer.echo(_skill_markdown_path(project_root.resolve(), row["skill_id"]).read_text())


@app.command()
def why(
    skill_id: str,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    explain(skill_id, project_root)


@app.command()
def evidence(
    skill_id: str,
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    row = _storage(project_root).find_skill_by_lookup(skill_id)
    if not row:
        raise typer.Exit(code=1)
    evidence_items = _storage(project_root).list_evidence()
    for item in evidence_items:
        if row["name"] in item.skill_candidates:
            typer.echo(f"{item.evidence_id}: {item.evidence_type.value} - {item.quote}")


@app.command()
def viewer(
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    typer.echo((project_root.resolve() / "viewer" / "index.html").as_uri())


@app.command()
def review(
    accept: str | None = typer.Option(None, "--accept", help="Accept a review item."),
    reject: str | None = typer.Option(None, "--reject", help="Reject a review item."),
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
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
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
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
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
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
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
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
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(project_root.resolve() / "graph" / "graph.json")


@export_app.command("profile")
def export_profile(
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(project_root.resolve() / "profile" / "skill.md")


@export_app.command("skill-md")
def export_skill_md(
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(project_root.resolve() / "tree" / "nodes")


@export_app.command("obsidian")
def export_obsidian_command(
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    render_project(project_root.resolve(), storage=_storage(project_root))
    typer.echo(export_obsidian(project_root.resolve()))


@app.command()
def stats(
    project_root: Path = typer.Option(Path("."), "--project-root", help=_PROJECT_ROOT_HELP),
) -> None:
    storage = _storage(project_root)
    typer.echo(f"sources: {len(storage.list_sources())}")
    typer.echo(f"skills: {len(storage.list_skill_rows())}")
    typer.echo(f"evidence: {len(storage.list_evidence())}")
    typer.echo(f"review: {len(storage.list_review_items())}")
