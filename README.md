<div align="center">
  <img src=".github/assets/traccia-logo.svg" alt="traccia logo" width="220">
  <h1>traccia</h1>
</div>

<p align="center">build a local skill graph from your own archive. keep the evidence, keep the timestamps, keep the raw files untouched.</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-000000?style=flat-square" alt="python badge">
  <img src="https://img.shields.io/badge/interface-typer-000000?style=flat-square" alt="typer badge">
  <img src="https://img.shields.io/badge/backend-openai--compatible-000000?style=flat-square" alt="backend badge">
  <img src="https://img.shields.io/badge/mode-local--first-000000?style=flat-square" alt="local first badge">
  <img src="https://img.shields.io/badge/license-MIT-000000?style=flat-square" alt="mit license badge">
</p>

---

`traccia` ingests notes, code, docs, AI chats, and platform exports one file at a time, extracts grounded evidence, and turns that into a videogame-style skill tree with explainable levels, freshness, acquisition timing, and graph exports.

this is not a resume parser and not a generic personal wiki. the primary artifact is the skill graph.

## why

most personal knowledge tools keep the files but lose the skill story.

most resume tools flatten the story into a pitch and throw away the evidence.

`traccia` sits in the middle:

- keep raw sources immutable
- infer skills from evidence instead of vibes
- separate weak signals from real demonstrated work
- show when a skill first appeared, when it was learned, and when it was first strongly demonstrated
- let the graph decay, strengthen, or stay historical as the archive changes
- export to markdown, json, a local viewer, and an obsidian-friendly vault

## quickstart

requires python 3.12+ and `uv`.

```bash
uv sync

# initialize a traccia project
uv run traccia init my-traccia

# ingest a corpus into that project
uv run traccia ingest-dir /path/to/corpus --project-root my-traccia

# inspect the result
uv run traccia tree --project-root my-traccia
uv run traccia explain python --project-root my-traccia
uv run traccia review --project-root my-traccia

# export projections
uv run traccia export obsidian --project-root my-traccia
uv run traccia viewer --project-root my-traccia
```

for local deterministic testing, switch the generated config to:

```yaml
backend:
  provider: fake
```

for a live model, the default path is an openai-style `/v1/chat/completions` backend:

```yaml
backend:
  provider: openai_compatible
  model: gpt-4o-2024-08-06
  api_key_env: OPENAI_API_KEY
  base_url: https://api.openai.com/v1
  api_style: chat_completions
  structured_output_mode: json_schema
```

this is openai-style, not openai-only. any provider with a compatible endpoint can be used by changing `base_url`, `model`, and `api_key_env`.

## what it ships right now

- immutable source intake into `raw/imported/`
- file-by-file parsing with span tracking
- broad source classification across authored content, produced artifacts, platform activity, social/community traces, and AI dialogue
- evidence extraction with signal classes such as `artifact_backed_work`, `problem_solving_trace`, `self_presentation`, and `ambient_interest`
- canonical skill nodes plus review queue for uncertain creation
- person-specific skill state with:
  - level
  - confidence
  - freshness
  - historical peak
  - first seen
  - first learned
  - first strong evidence
  - estimated acquisition time and basis
  - core-self centrality
- rendered markdown node pages and profile exports
- `graph.json`, `tree.json`, ascii tree output, and a local static viewer
- obsidian vault export with real note generation instead of a raw folder dump

## input surface

`traccia` is built for mixed personal archives, not just project repos.

current supported file types:

- markdown
- plain text
- python, js, ts, tsx, rust, go, sql
- json
- csv
- pdf
- docx

current structured normalization includes:

- AI conversation json exports
- reddit json exports
- google activity json exports

the intended archive boundary is wider than that. the system is meant to grow toward reddit, google takeout, twitter/x, social profiles, issue trackers, and broader activity exports without treating every signal as equal proof of skill.

## output surface

after ingest, `traccia` renders:

- `tree/index.md`
- `tree/nodes/*.md`
- `tree/log.md`
- `graph/graph.json`
- `graph/tree.json`
- `profile/skill.md`
- `viewer/index.html`
- `exports/obsidian/`

each skill node is meant to answer:

- where it fits in the graph
- what evidence supports it
- how deep the demonstrated competence is
- how current it is
- when it first showed up
- when it seems to have been learned or acquired
- how central it is to the broader archive

## scoring stance

`traccia` explicitly separates:

- **current mastery**: how deep the demonstrated competence is right now
- **core-self centrality**: how recurrent or foundational the skill is across the archive

that matters because platform exports create a lot of weak signals.

searches, follows, bios, bookmarks, and lightweight AI chats can support interest or context. they should not inflate mastery on their own.

## command surface

main commands:

- `traccia init`
- `traccia doctor`
- `traccia ingest`
- `traccia ingest-dir`
- `traccia rebuild`
- `traccia tree`
- `traccia explain`
- `traccia evidence`
- `traccia review`
- `traccia lock`
- `traccia hide`
- `traccia stats`
- `traccia export graph`
- `traccia export profile`
- `traccia export skill-md`
- `traccia export obsidian`

## repo map

- `SPEC.md` - product and architecture spec
- `PLAN.md` - implementation plan and phase boundaries
- `decisions.md` - decisions and research conclusions
- `REFERENCES.md` - inspirations and anti-references
- `src/traccia/` - implementation
- `tests/` - fixtures and regression coverage

## verification

current repo verification is green with:

```bash
uv run pytest -q
```

the live external backend path was not verified against a real provider in this workspace state unless you supply credentials and point the config at one.
