# Repository Inventory

This inventory records the tracked files reviewed for the documentation pass.
Line counts come from the current worktree with local caches, virtual
environments, and temporary project outputs excluded.

Total tracked lines at the time of this pass: `60435`.

## Root And Project Metadata

| File | Lines | Documentation role |
| --- | ---: | --- |
| `.gitignore` | 43 | Local ignore rules. |
| `.python-version` | 1 | Python version pin. |
| `CLAUDE.md` | 177 | Project agent instructions and context. |
| `CODEOWNERS` | 1 | Repository ownership. |
| `CONTRIBUTING.md` | 38 | Contributor guidance. |
| `LICENSE` | 21 | MIT license. |
| `README.md` | 118 | Short product overview and docs entry point. |
| `package.json` | 35 | npm launcher package metadata. |
| `pyproject.toml` | 83 | Python package, dependency, build, test, and lint metadata. |
| `uv.lock` | 2849 | Locked Python dependency graph. |

## GitHub Metadata

| File | Lines | Documentation role |
| --- | ---: | --- |
| `.github/assets/traccia-logo.svg` | 28 | Repository logo used in the README. |
| `.github/dependabot.yml` | 11 | Dependency update configuration. |
| `.github/workflows/ci.yml` | 92 | CI workflow. |
| `.github/workflows/release.yml` | 117 | Release workflow. |
| `.github/workflows/security.yml` | 43 | Security workflow. |

## User And Maintainer Docs

| File | Lines | Documentation role |
| --- | ---: | --- |
| `docs/index.md` | 48 | Documentation table of contents. |
| `docs/quickstart.md` | 122 | First project tutorial. |
| `docs/cli-reference.md` | 95 | CLI command reference. |
| `docs/project-layout.md` | 72 | Project artifact layout reference. |
| `docs/configuration.md` | 193 | Config schema guide. |
| `docs/ingestion.md` | 153 | Ingestion, staging, scoring, and resume guide. |
| `docs/exports.md` | 131 | Export, curation, and publish guide. |
| `docs/architecture.md` | 94 | System architecture explanation. |
| `docs/codebase-map.md` | 132 | Maintainer codebase map. |
| `docs/repository-inventory.md` | this file | Tracked file and line-count audit. |
| `docs/development.md` | 114 | Maintainer development guide. |

## Design Records And Deep References

| File | Lines | Documentation role |
| --- | ---: | --- |
| `docs/architecture-notes.md` | 68 | Implementation notes and risk areas. |
| `docs/decisions.md` | 277 | Product and architecture decision history. |
| `docs/finished-run-viewer-decisions.md` | 435 | Viewer design and public export decision history. |
| `docs/ingest-architecture.md` | 358 | Detailed ingest and scoring architecture record. |
| `docs/plan.md` | 348 | Original phased implementation plan. |
| `docs/references.md` | 105 | Related project references and anti-references. |
| `docs/spec.md` | 933 | Full product specification. |

## Python Package

| File | Lines | Documentation role |
| --- | ---: | --- |
| `src/traccia/__init__.py` | 5 | Package version surface. |
| `src/traccia/__main__.py` | 4 | `python -m traccia` entrypoint. |
| `src/traccia/bootstrap.py` | 414 | Project scaffold, prompts, initial artifacts, and SQLite schema. |
| `src/traccia/cli.py` | 930 | Typer CLI command surface. |
| `src/traccia/config.py` | 163 | Config schema and YAML load/write helpers. |
| `src/traccia/curation.py` | 595 | Viewer curation and public graph redaction. |
| `src/traccia/document_normalizer.py` | 296 | PDF/DOCX normalization provider chain. |
| `src/traccia/extraction.py` | 204 | Evidence extraction contracts. |
| `src/traccia/family_normalizer.py` | 1187 | Source-family normalization. |
| `src/traccia/fixtures.py` | 44 | Test fixture helpers. |
| `src/traccia/google_takeout.py` | 193 | Google Takeout relevance policy. |
| `src/traccia/llm.py` | 1342 | Backend abstraction, structured calls, retries, and leases. |
| `src/traccia/models.py` | 317 | Strict domain models and enums. |
| `src/traccia/parsers.py` | 1630 | Parser registry, spans, attachments, and chunking. |
| `src/traccia/pipeline.py` | 4368 | End-to-end discovery, ingest, scoring, resume, and graph sync. |
| `src/traccia/pipeline_support.py` | 163 | Support scoring and skill-state helpers. |
| `src/traccia/rendering.py` | 1069 | Graph, markdown, profile, Obsidian, and debug rendering. |
| `src/traccia/source_detection.py` | 291 | Source type and family detection. |
| `src/traccia/storage.py` | 851 | SQLite persistence, queries, review, overrides, and caches. |
| `src/traccia/taxonomy.py` | 119 | Built-in taxonomy seeds and aliases. |
| `src/traccia/utils.py` | 45 | IDs, slugs, timestamps, hashes, and text helpers. |
| `src/traccia/viewer.py` | 924 | Static viewer export, admin export, and publish assembly. |
| `src/traccia/viewer_assets.py` | 10555 | Embedded viewer HTML, CSS, JavaScript, and SFX assets. |

## Assets

| File | Lines | Documentation role |
| --- | ---: | --- |
| `src/traccia/assets/favicon.svg` | 14 | Viewer and package favicon. |
| `src/traccia/assets/fonts/README.md` | 10 | Font asset notes. |
| `src/traccia/assets/fonts/traccia-display-bold.ttf` | 1355 | Bundled display font. |
| `src/traccia/assets/fonts/traccia-display-medium.ttf` | 1298 | Bundled display font. |
| `src/traccia/assets/fonts/traccia-display-regular.ttf` | 875 | Bundled display font. |
| `src/traccia/assets/fonts/traccia-label-bold.ttf` | 1172 | Bundled label font. |
| `src/traccia/assets/fonts/traccia-label-medium.ttf` | 897 | Bundled label font. |
| `src/traccia/assets/fonts/traccia-label-regular.ttf` | 2341 | Bundled label font. |
| `src/traccia/assets/fonts/traccia-mono-bold.ttf` | 1354 | Bundled mono font. |
| `src/traccia/assets/fonts/traccia-mono-medium.ttf` | 1209 | Bundled mono font. |
| `src/traccia/assets/fonts/traccia-mono-regular.ttf` | 1012 | Bundled mono font. |
| `src/traccia/assets/fonts/traccia-ui-bold.ttf` | 1190 | Bundled UI font. |
| `src/traccia/assets/fonts/traccia-ui-medium.ttf` | 1517 | Bundled UI font. |
| `src/traccia/assets/fonts/traccia-ui-regular.ttf` | 1413 | Bundled UI font. |

## npm And Scripts

| File | Lines | Documentation role |
| --- | ---: | --- |
| `npm/bin/traccia.js` | 56 | Node launcher that delegates to `uvx` or local `uv run`. |
| `scripts/check-viewer-performance.mjs` | 1250 | Maintainer browser performance check for viewer exports. |

## Test Fixtures

| File | Lines | Documentation role |
| --- | ---: | --- |
| `tests/fixtures/corpus/app.py` | 10 | Small code fixture. |
| `tests/fixtures/corpus/notes.md` | 5 | Small notes fixture. |
| `tests/fixtures/corpus/project-readme.md` | 4 | Small README fixture. |
| `tests/fixtures/corpus/tasks.csv` | 2 | Small CSV fixture. |
| `tests/fixtures/golden/evidence-item.json` | 21 | Evidence model golden fixture. |
| `tests/fixtures/golden/manifest.json` | 8 | Manifest golden fixture. |
| `tests/fixtures/golden/person-skill-state.json` | 25 | Skill-state golden fixture. |
| `tests/fixtures/golden/project/config.yaml` | 29 | Golden project config. |
| `tests/fixtures/golden/sample-source.md` | 3 | Golden source fixture. |
| `tests/fixtures/golden/skill-node.json` | 15 | Skill-node golden fixture. |
| `tests/fixtures/golden/source-document.json` | 17 | Source-document golden fixture. |

## Tests

| File | Lines | Documentation role |
| --- | ---: | --- |
| `tests/test_config.py` | 75 | Config defaults and validation contracts. |
| `tests/test_error_messages.py` | 50 | User-facing error message contracts. |
| `tests/test_extraction.py` | 167 | Evidence extraction and attribution contracts. |
| `tests/test_fixtures.py` | 12 | Fixture loading contract. |
| `tests/test_init.py` | 910 | Project scaffold and doctor contracts. |
| `tests/test_llm.py` | 945 | Backend, structured output, retry, and lease contracts. |
| `tests/test_models.py` | 32 | Domain model validation contracts. |
| `tests/test_npm_wrapper.py` | 109 | npm launcher contracts. |
| `tests/test_parsers.py` | 1060 | Parser, attachment, and normalization contracts. |
| `tests/test_pipeline.py` | 3506 | Ingest, scoring, staging, deletion, resume, and export contracts. |
| `tests/test_signal_handling.py` | 286 | Interruption and signal handling contracts. |
| `tests/test_source_detection.py` | 98 | Source type and family detection contracts. |
| `tests/test_storage.py` | 58 | SQLite storage contracts. |
| `tests/test_utils.py` | 29 | Utility helper contracts. |
| `tests/test_viewer.py` | 3659 | Viewer, admin curation, publish, accessibility, performance, and redaction contracts. |
