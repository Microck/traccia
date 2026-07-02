# Quickstart

This guide creates a local Traccia project, ingests a small folder, and shows
the first useful outputs.

## Requirements

- Python 3.12.
- `uv` for the recommended local workflow.
- An OpenAI-compatible model endpoint for live extraction, unless you switch the
  generated config to the fake backend for tests.

Install dependencies from the repository:

```bash
uv sync
```

Install the CLI on `PATH` from the checkout:

```bash
uv tool install -e .
```

You can also run every command as `uv run traccia ...` from the repository.

## Create A Project

```bash
traccia init my-traccia
traccia doctor my-traccia
```

`init` creates the project layout, default config, prompts, empty graph files,
and SQLite catalog. `doctor` checks that the scaffold exists and reports
optional local capabilities such as document normalization, OCR, media tools,
and backend authentication.

## Configure The Backend

Open `my-traccia/config/config.yaml`. The default backend is OpenAI-compatible:

```yaml
backend:
  provider: openai_compatible
  model: gpt-5-chat-latest
  api_key_env: OPENAI_API_KEY
  base_url: https://api.openai.com/v1
```

Set the required API key in your shell:

```bash
export OPENAI_API_KEY=...
```

For deterministic local tests, use:

```yaml
backend:
  provider: fake
```

## Preview A Folder

Before spending model quota, inspect what Traccia will treat as materials:

```bash
traccia discover-dir /path/to/archive --project-root my-traccia
```

For machine-readable output:

```bash
traccia discover-dir /path/to/archive --project-root my-traccia --format json
```

## Ingest Files

Run a full directory ingest:

```bash
traccia ingest-dir /path/to/archive --project-root my-traccia
```

The default flow discovers materials, imports raw files, parses spans, extracts
evidence, scores the graph, and renders projections.

For one file:

```bash
traccia ingest /path/to/file.md --project-root my-traccia
```

## Inspect The Result

```bash
traccia stats --project-root my-traccia
traccia tree --project-root my-traccia
traccia explain python --project-root my-traccia
traccia review --project-root my-traccia
```

Useful files:

- `graph/graph.json` for the machine graph.
- `tree/index.md` for the tree overview.
- `tree/nodes/` for one markdown page per skill.
- `profile/skill.md` for the profile projection.
- `state/catalog.sqlite` for canonical derived state.

## Export

```bash
traccia export obsidian --project-root my-traccia
traccia export viewer --project-root my-traccia
traccia export admin --project-root my-traccia
traccia export publish --project-root my-traccia
```

The publish step reads curation from `exports/viewer/curation.json` and writes a
separate redacted public bundle under `exports/viewer-public/`.
