# Development Guide

This page is for maintainers working on the Traccia repository.

## Setup

```bash
uv sync
```

Run the CLI from the checkout:

```bash
uv run traccia --help
```

Install the editable console script:

```bash
uv tool install -e .
```

## Tests And Lint

Run tests:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check src tests
```

The configured test path is `tests/`. Ruff targets Python 3.12 and uses a
100-column line length.

## Package Metadata

The Python package is defined in `pyproject.toml`:

- Package name: `traccia`.
- Console script: `traccia = "traccia.cli:app"`.
- Python range: `>=3.12,<3.14`.
- Build backend: Hatchling.
- Runtime dependencies: Pydantic, PyYAML, Typer, pypdf, python-docx, openpyxl,
  and lxml.

Optional extras:

| Extra | Adds |
| --- | --- |
| `docling` | Docling document conversion. |
| `marker` | Marker PDF conversion. |
| `markitdown` | MarkItDown conversion. |
| `document-markdown` | Full local document normalization stack. |

## npm Wrapper

The npm package is `@microck/traccia`. It does not contain a JavaScript
implementation of Traccia. It launches the Python CLI through `uvx`:

```bash
npx @microck/traccia doctor .
```

Maintainer mode runs the local checkout:

```bash
TRACCIA_USE_LOCAL_REPO=1 node npm/bin/traccia.js doctor .
```

To test a different Python package spec:

```bash
TRACCIA_UVX_SPEC='traccia[document-markdown]' npx @microck/traccia doctor .
```

## High-Risk Areas

| Area | Why it needs careful tests |
| --- | --- |
| `pipeline.py` | Orchestrates discovery, extraction, resume, scoring, deletion sync, and rendering. |
| `storage.py` | Owns SQLite persistence and additive schema checks. |
| `llm.py` | Owns backend calls, retries, structured output, and LLM request leases. |
| `parsers.py` | Encodes messy file and attachment parsing rules. |
| `family_normalizer.py` | Normalizes provider export formats. |
| `rendering.py` | Turns canonical graph state into user-facing projections. |
| `viewer.py` and `viewer_assets.py` | Own static viewer export, curation, performance, and public redaction contracts. |

Prefer behavior tests over implementation-only tests. If a change affects public
CLI behavior, generated artifacts, config schema, persistence format, or export
redaction, update the corresponding docs and tests in the same patch.

## Release Surface

The source distribution includes:

- `.env.example`
- `.github/assets`
- `.github/ISSUE_TEMPLATE`
- `.github/pull_request_template.md`
- `AGENTS.md`
- `CHANGELOG.md`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `README.md`
- `docs`
- `npm`
- `package.json`
- `pyproject.toml`
- `src`
- `tests`

The build excludes local caches, virtual environments, `dist`, scripts, and
temporary project outputs.
