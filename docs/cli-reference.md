# CLI Reference

The console script is `traccia`. In a source checkout you can also run
`uv run traccia`.

Most commands accept `--project-root`. If omitted, the current directory is the
project root.

## Project Commands

| Command | Purpose |
| --- | --- |
| `traccia init [PATH]` | Create a project scaffold, config, prompts, empty graph files, and SQLite catalog. |
| `traccia lint [PATH]` | Validate `config/config.yaml` against the config schema. |
| `traccia doctor [PATH]` | Check scaffold files, backend settings, optional parsers, OCR, media tools, and auth. |
| `traccia doctor [PATH] --check-backend` | Also run an authenticated backend healthcheck. |
| `traccia stats --project-root PATH` | Print source, skill, evidence, and review counts. |

## Intake Commands

| Command | Purpose |
| --- | --- |
| `traccia add FILE --project-root PATH` | Import a file into `raw/imported/` without running the full evidence pipeline. |
| `traccia add-dir DIR --project-root PATH` | Import a directory into `raw/imported/` without the full evidence pipeline. |
| `traccia ingest FILE --project-root PATH` | Parse, extract evidence, score, and render one file. |
| `traccia ingest-dir DIR --project-root PATH` | Discover and process a directory or archive tree. |
| `traccia stage-dir DIR --project-root PATH` | Discover, import, and parse materials without LLM extraction or graph sync. |
| `traccia discover-dir DIR --project-root PATH` | Preview material counts and source-family detection. |
| `traccia reingest SOURCE_ID --project-root PATH` | Reprocess one tracked source. |
| `traccia watch DIR --project-root PATH` | Poll a directory for new files and ingest changes. |
| `traccia merge-project SOURCE_PROJECT --project-root TARGET` | Merge source and evidence records from another Traccia project. |

Common `ingest-dir` options:

| Option | Meaning |
| --- | --- |
| `--import-prefix PATH` | Preserve stable source IDs when ingesting a subfolder from a larger archive. |
| `--no-sync-graph` | Extract evidence without recomputing rendered graph projections. |
| `--no-sync-deletions` | Do not mark previously tracked files in the import scope as deleted. |
| `--parallel-extractions N` | Run multiple material-level extraction workers inside one ingest process. |
| `--score-mode incremental` | Reuse unchanged graph scoring work. This is the default. |
| `--score-mode full` | Recompute canonicalization and scoring from stored evidence. |
| `--score-mode none` | Store sources and evidence only; run `traccia score` later. |

## Scoring And Rendering

| Command | Purpose |
| --- | --- |
| `traccia score --project-root PATH` | Recompute graph scoring and render projections. |
| `traccia score --mode full --project-root PATH` | Ignore score caches and recompute graph decisions. |
| `traccia score --parallel-scores N --project-root PATH` | Run bounded parallel skill scoring. |
| `traccia rebuild --project-root PATH` | Rebuild derived outputs through the pipeline. |
| `traccia render --project-root PATH` | Render markdown, JSON, profile, and debug outputs from stored graph state. |

## Reading The Graph

| Command | Purpose |
| --- | --- |
| `traccia tree --project-root PATH` | Print an ASCII tree. |
| `traccia tree --format mermaid --project-root PATH` | Print a Mermaid graph. |
| `traccia node SKILL_ID --project-root PATH` | Print one generated node page. |
| `traccia explain SKILL_OR_ALIAS --project-root PATH` | Print the node page found by skill ID, name, or alias. |
| `traccia why SKILL_ID --project-root PATH` | Alias for `explain`. |
| `traccia evidence SKILL_ID --project-root PATH` | Print evidence records that support a skill. |

## Review And Curation

| Command | Purpose |
| --- | --- |
| `traccia review --project-root PATH` | List pending review items. |
| `traccia review --accept ITEM_ID --project-root PATH` | Accept a review item and update the graph. |
| `traccia review --reject ITEM_ID --project-root PATH` | Reject a review item. |
| `traccia lock SKILL_ID --project-root PATH` | Add a manual lock override for a skill. |
| `traccia hide SKILL_ID --project-root PATH` | Hide a skill in graph state. |
| `traccia alias add SKILL_ID ALIAS --project-root PATH` | Add a manual alias for a skill. |

## Export Commands

| Command | Output |
| --- | --- |
| `traccia export graph --project-root PATH` | Refresh and print `graph/graph.json`. |
| `traccia export profile --project-root PATH` | Refresh and print `profile/skill.md`. |
| `traccia export skill-md --project-root PATH` | Refresh and print `tree/nodes/`. |
| `traccia export obsidian --project-root PATH` | Write `exports/obsidian/`. |
| `traccia export debug-report --project-root PATH` | Write `exports/debug/report.json` and `exports/debug/report.md`. |
| `traccia export viewer --project-root PATH` | Write `exports/viewer/`. |
| `traccia export admin --project-root PATH` | Write `exports/viewer-admin/`. |
| `traccia export publish --project-root PATH` | Write `exports/viewer-public/` by default. |

Viewer export options:

| Option | Meaning |
| --- | --- |
| `--no-sound` | Disable viewer SFX by default. |
| `--output-dir NAME` | For `publish`, choose the output directory under `exports/`. |
