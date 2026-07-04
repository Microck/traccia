<div align="center">
  <img src=".github/assets/traccia-logo.svg" alt="traccia logo" width="220">
  <h1>traccia</h1>
</div>

<p align="center">
  <img src="https://img.shields.io/npm/v/@microck/traccia?style=flat-square&color=000000" alt="npm version badge">
  <img src="https://img.shields.io/npm/dt/@microck/traccia?style=flat-square&color=000000" alt="npm total downloads badge">
  <img src="https://img.shields.io/badge/python-3.12%2B-000000?style=flat-square" alt="python badge">
  <img src="https://img.shields.io/badge/license-MIT-000000?style=flat-square" alt="mit license badge">
</p>

<p align="center">
  <img width="800" height="auto" alt="traccia exported skill map animation" src=".github/assets/traccia-loop-squircle.gif" />
</p>

`traccia` is a tool that turns your personal archive into a self-explaining skill
graph. it takes as input notes, code, docs, ai chat transcripts, export files from
other platforms, or just your half-structured personal history and leaves these
source files untouched. out of them it extracts timestamped fragments of evidence,
which it renders as a graph tracing how each skill has been acquired, how deeply
explored it is, how recent any progress is, and how central it is to your ongoing
work as seen in your archive.

it is built for working with mixed archives, not for single authoritative sources
such as a single git repo. at its best, it can pull from a broad mix of inputs such
as repo history, google activity, social profiles and ai conversation logs. it
avoids the trap of pretending all signals are equally valid but keeps all weak
signals weak, strong evidence strong, and leaves the trail visible so you can
question anything later.

## quick start

install with npm:

```bash
npm install -g @microck/traccia
```

the npm wrapper requires `uvx` on `PATH`.

or install the Python CLI from a checkout:

```bash
uv sync
uv tool install -e .
```

then create a project and ingest a folder:

```bash
traccia init my-traccia
traccia doctor my-traccia
traccia ingest-dir /path/to/archive --project-root my-traccia
traccia tree --project-root my-traccia
traccia explain python --project-root my-traccia
```

export the results:

```bash
traccia export obsidian --project-root my-traccia
traccia export viewer --project-root my-traccia
traccia export admin --project-root my-traccia
traccia export publish --project-root my-traccia
```

## what it produces

| output | purpose |
| --- | --- |
| `graph/graph.json` | Machine-readable skill graph. |
| `tree/index.md` | Markdown overview of the graph. |
| `tree/nodes/*.md` | One markdown page per skill. |
| `profile/skill.md` | A profile summary derived from accepted graph state. |
| `exports/obsidian/` | Obsidian-friendly vault export. |
| `exports/viewer/` | Public read-only skill map viewer. |
| `exports/viewer-admin/` | Admin curation viewer. |
| `exports/viewer-public/` | Redacted public bundle generated from curation. |

## install paths

the canonical implementation is the Python package. the npm package is a thin
launcher for Node-first environments.

| path | command | notes |
| --- | --- | --- |
| repo-local | `uv sync` then `uv run traccia ...` | best while developing. |
| editable CLI | `uv tool install -e .` | installs `traccia` on `PATH`. |
| pip editable | `pip install -e .` | same console script through pip. |
| npm one-off | `npx @microck/traccia doctor .` | requires `uvx` on `PATH`. |
| npm global | `npm install -g @microck/traccia` | installs the npm launcher. |

optional document parsing extras are available when you need heavier local PDF
or DOCX normalization:

```bash
uv sync --extra docling
uv sync --extra marker
uv sync --extra document-markdown
```

## documentation

start here:

- [Documentation index](docs/index.md)
- [Quickstart](docs/quickstart.md)
- [CLI reference](docs/cli-reference.md)
- [Project layout](docs/project-layout.md)
- [Ingestion guide](docs/ingestion.md)
- [Configuration reference](docs/configuration.md)
- [Exports and publishing](docs/exports.md)
- [Architecture overview](docs/architecture.md)
- [Codebase map](docs/codebase-map.md)
- [Repository inventory](docs/repository-inventory.md)
- [Development guide](docs/development.md)

design records and deeper planning notes remain in `docs/` for maintainers.

## core guarantees

- Source files in `raw/` are not rewritten by the LLM.
- First-pass extraction is scoped to one source or source chunk.
- Evidence is stored before graph scoring.
- SQLite is the canonical derived state.
- Markdown, JSON, profile files, and viewers are projections.
- Public publishing physically removes hidden/private graph data from the public
  bundle.

## license

MIT
