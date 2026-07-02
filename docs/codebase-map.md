# Codebase Map

This map covers the tracked repository files that define Traccia's behavior,
packaging, tests, and documentation. Generated caches, local virtual
environments, and temporary project outputs are not product surface. For the
tracked repository surface and audit commands, see
[Repository inventory](repository-inventory.md).

## Root Files

| File | Purpose |
| --- | --- |
| `README.md` | Short product overview, install paths, and documentation entry points. |
| `pyproject.toml` | Python package metadata, dependencies, optional extras, console script, pytest, and Ruff config. |
| `uv.lock` | Locked Python dependency graph for the `uv` workflow. |
| `package.json` | npm package metadata for the thin `@microck/traccia` launcher. |
| `AGENTS.md` | Harness-agnostic coding-agent instructions for this repository. |
| `.env.example` | Blank local environment variable template. |
| `CHANGELOG.md` | User-facing release notes. |
| `LICENSE` | MIT license. |
| `SECURITY.md` | Vulnerability reporting policy. |
| `SUPPORT.md` | Support and reproduction guidance. |
| `CODE_OF_CONDUCT.md` | Collaboration expectations. |
| `CONTRIBUTING.md` | Contributor workflow notes. |
| `CODEOWNERS` | Repository ownership. |
| `CLAUDE.md` | Claude-specific agent guidance for the project context. |
| `.python-version` | Local Python version pin. |
| `.gitignore` | Local ignore rules. |

## Python Package

| File | Responsibility |
| --- | --- |
| `src/traccia/__init__.py` | Package version surface. |
| `src/traccia/__main__.py` | `python -m traccia` entrypoint. |
| `src/traccia/bootstrap.py` | Project scaffolding, default prompts, initial files, and SQLite schema. |
| `src/traccia/cli.py` | Typer CLI commands and command-level orchestration. |
| `src/traccia/config.py` | Pydantic configuration models and YAML load/write helpers. |
| `src/traccia/curation.py` | Viewer curation and public publish redaction logic. |
| `src/traccia/document_normalizer.py` | PDF/DOCX markdown normalization provider chain. |
| `src/traccia/extraction.py` | Evidence extraction contracts and extractor integration. |
| `src/traccia/family_normalizer.py` | Source-family-specific normalization for exported data shapes. |
| `src/traccia/fixtures.py` | Fixture helpers for tests and golden data. |
| `src/traccia/google_takeout.py` | Deterministic Google Takeout relevance and product policy. |
| `src/traccia/llm.py` | Backend abstraction, structured calls, retries, leases, and healthchecks. |
| `src/traccia/models.py` | Strict Pydantic domain models and enums. |
| `src/traccia/parsers.py` | Parser registry, source parsing, spans, attachments, and chunking. |
| `src/traccia/pipeline.py` | End-to-end pipeline orchestration for ingest, discovery, scoring, resume, and graph sync. |
| `src/traccia/pipeline_support.py` | Support scoring, strong-action detection, node creation, review, and state scoring helpers. |
| `src/traccia/rendering.py` | Graph JSON, tree markdown, profile, Obsidian, and debug report rendering. |
| `src/traccia/source_detection.py` | Source family and source type detection. |
| `src/traccia/storage.py` | SQLite persistence, schema checks, queries, merge, review, overrides, and caches. |
| `src/traccia/taxonomy.py` | Built-in seed taxonomy and skill aliases. |
| `src/traccia/utils.py` | Shared IDs, slugs, timestamps, hashes, and small text helpers. |
| `src/traccia/viewer.py` | Static viewer, admin viewer, and publish export assembly. |
| `src/traccia/viewer_assets.py` | Embedded HTML/CSS/JS assets for the static viewer. |

## Assets

| Path | Purpose |
| --- | --- |
| `src/traccia/assets/favicon.svg` | Viewer/package favicon. |
| `src/traccia/assets/fonts/README.md` | Notes for bundled font assets. |
| `src/traccia/assets/fonts/*.ttf` | Bundled display, UI, label, and mono font files. |
| `.github/assets/traccia-logo.svg` | README and repository logo. |
| `.github/assets/traccia-loop-squircle.gif` | README viewer animation. |

## npm Launcher

| File | Purpose |
| --- | --- |
| `npm/bin/traccia.js` | Node launcher that runs `uvx --from traccia traccia ...`; maintainer mode uses `TRACCIA_USE_LOCAL_REPO=1` to run `uv run traccia ...` from a checkout. |

Environment variables:

| Variable | Meaning |
| --- | --- |
| `TRACCIA_UVX_SPEC` | Override the `uvx --from` package spec, for example `traccia[document-markdown]`. |
| `TRACCIA_USE_LOCAL_REPO=1` | Run the local checkout with `uv run traccia ...` instead of `uvx`. |
| `TRACCIA_LLM_LEASE_PATH` | Override the cross-process LLM request lease path. |
| `TRACCIA_VIEWER_FONT_DIR` | Override the viewer font asset directory. |
| `OPENAI_API_KEY` | Default OpenAI-compatible backend credential. |
| `CLIPROXYAPI_KEY` | Common OpenAI-compatible backend credential for CLIProxyAPI configs. |
| `SUMMARIZE_WHISPER_CPP_BINARY` | Optional local transcription binary override. |
| `SUMMARIZE_WHISPER_CPP_MODEL_PATH` | Optional local transcription model override. |

## Scripts

| File | Purpose |
| --- | --- |
| `scripts/check-viewer-performance.mjs` | Browser-side performance check for exported viewer assets. |

Scripts are tracked for maintainer use but are not shipped in the Python sdist
according to `pyproject.toml`.

## Tests

| File | Covers |
| --- | --- |
| `tests/test_config.py` | Config defaults and validation. |
| `tests/test_error_messages.py` | User-facing error message behavior. |
| `tests/test_extraction.py` | Evidence extraction and validation. |
| `tests/test_fixtures.py` | Fixture loading. |
| `tests/test_init.py` | Project initialization, scaffold files, and doctor behavior. |
| `tests/test_llm.py` | Backend behavior, structured outputs, retries, and leases. |
| `tests/test_models.py` | Pydantic domain model contracts. |
| `tests/test_npm_wrapper.py` | npm launcher behavior and failure messages. |
| `tests/test_parsers.py` | Parser registry, source parsing, attachments, and normalization. |
| `tests/test_pipeline.py` | End-to-end ingest, scoring, review, staging, deletion, and resume behavior. |
| `tests/test_signal_handling.py` | Signal handling and interruption behavior. |
| `tests/test_source_detection.py` | Source family/type detection. |
| `tests/test_storage.py` | SQLite persistence behavior. |
| `tests/test_utils.py` | Shared utility helpers. |
| `tests/test_viewer.py` | Viewer, admin curation, public publish, and redaction contracts. |

Fixtures live under `tests/fixtures/` and include a small corpus plus golden JSON
contracts for sources, evidence, skills, manifests, and config.

## GitHub Workflows

| File | Purpose |
| --- | --- |
| `.github/workflows/ci.yml` | CI checks for the Python package and tests. |
| `.github/workflows/release.yml` | Release packaging workflow. |
| `.github/workflows/security.yml` | Security-oriented workflow checks. |
| `.github/dependabot.yml` | Dependency update configuration. |
| `.github/pull_request_template.md` | Pull request checklist. |
| `.github/ISSUE_TEMPLATE/*.yml` | Bug and feature request forms. |

## Documentation Files

| File | Purpose |
| --- | --- |
| `docs/index.md` | Documentation table of contents. |
| `docs/quickstart.md` | First successful local project flow. |
| `docs/cli-reference.md` | Command reference. |
| `docs/project-layout.md` | Project directories and artifacts. |
| `docs/configuration.md` | Config schema guide. |
| `docs/ingestion.md` | Ingest, staging, scoring, source families, and resume. |
| `docs/exports.md` | Markdown, Obsidian, viewer, admin, and publish exports. |
| `docs/architecture.md` | System model and boundaries. |
| `docs/development.md` | Maintainer workflow. |
| `docs/spec.md` | Detailed product specification. |
| `docs/architecture-notes.md` | Implementation-level notes. |
| `docs/ingest-architecture.md` | Detailed ingest architecture. |
| `docs/finished-run-viewer-decisions.md` | Viewer design decisions. |
| `docs/plan.md` | Original phased build plan. |
| `docs/decisions.md` | Planning and product decisions. |
| `docs/references.md` | External references and anti-references. |
