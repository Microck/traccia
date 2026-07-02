# Project Layout

A Traccia project is a folder created by `traccia init`. Raw inputs, parsed
spans, evidence, graph state, rendered markdown, and exports live in separate
directories.

## Top-Level Directories

| Path | Owner | Meaning |
| --- | --- | --- |
| `config/` | User and CLI | Project configuration. |
| `config/prompts/` | Maintainer and CLI | Prompt contracts for extraction, canonicalization, scoring, and rendering. |
| `raw/inbox/` | User | Optional drop zone for source files. |
| `raw/imported/` | Pipeline | Imported source files or links. Raw content is not rewritten by the LLM. |
| `parsed/` | Pipeline | Parsed source documents and spans. |
| `evidence/` | Pipeline | Per-source evidence extraction artifacts. |
| `graph/` | Renderer | Machine-readable graph projections. |
| `tree/` | Renderer | Markdown skill tree pages. |
| `profile/` | Renderer | Profile projection derived from graph state. |
| `state/` | Pipeline and storage | SQLite catalog, manifests, progress, review queue, and run telemetry. |
| `exports/` | Export commands | Obsidian vault, debug report, viewer bundles, and publish outputs. |

## Canonical State

`state/catalog.sqlite` is the canonical derived state. The graph JSON, markdown
tree, profile, Obsidian export, and static viewers are render outputs.

Important SQLite tables are initialized by `src/traccia/bootstrap.py` and
managed by `src/traccia/storage.py`:

| Table | Meaning |
| --- | --- |
| `sources` | Imported source records, metadata, source family, status, and fingerprints. |
| `source_spans` | Parsed offsets for source-local evidence boundaries. |
| `evidence_items` | Evidence extracted from one source or source chunk. |
| `skills` | Canonical skill nodes. |
| `skill_aliases` | Lookup aliases for canonical skills. |
| `skill_edges` | Parent, related, prerequisite, and other graph edges. |
| `person_skill_states` | Level, confidence, freshness, centrality, and manual state for each skill. |
| `review_queue` | Items requiring human accept/reject. |
| `manual_overrides` | Locks, hides, aliases, and other explicit user decisions. |
| `pipeline_runs` | Scoring and pipeline run summaries. |

## Rendered Outputs

| File | Meaning |
| --- | --- |
| `graph/graph.json` | Full graph projection for machine use and viewer export. |
| `graph/tree.json` | Tree-shaped projection for terminal and markdown rendering. |
| `tree/index.md` | Top-level markdown skill tree. |
| `tree/log.md` | Ingest log. |
| `tree/nodes/<skill-id>.md` | One markdown page per skill. |
| `profile/skill.md` | Profile summary from accepted graph state. |
| `profile/strengths.md` | Strengths projection derived from graph state. |
| `profile/gaps.md` | Gaps projection derived from graph state. |
| `profile/artifacts.md` | Artifact summary derived from graph state. |
| `exports/debug/report.json` | Debug export with counts and pipeline diagnostics. |
| `exports/debug/report.md` | Markdown version of the debug report. |

## Progress And Recovery Files

| File | Meaning |
| --- | --- |
| `state/progress.json` | Current directory/material ingest progress. |
| `state/manifests/<ingest-id>.json` | Per-run discovery and material outcomes. |
| `state/review_queue.jsonl` | File projection of pending review items. |
| `state/graph-score-progress.json` | Current graph scoring progress. |
| `state/graph-score-runs.jsonl` | Append-only graph scoring telemetry. |

Crashes should not erase imported sources or accepted evidence. Re-run the same
ingest command to resume from stored source, parsed, evidence, and progress
state.
