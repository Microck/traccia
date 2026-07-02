# Ingestion Guide

Ingestion turns files into source records, spans, evidence, graph state, and
rendered outputs. The main contract is source-scoped extraction: the first LLM
pass sees one source or one source chunk, not the whole archive.

## Flow

```text
discover -> classify family -> import raw material -> parse spans
  -> extract evidence -> store evidence -> score graph -> render exports
```

The graph is not updated from a lossy batch summary. It is recomputed from
durable source and evidence records in `state/catalog.sqlite`.

## Preview A Directory

```bash
traccia discover-dir /path/to/archive --project-root my-traccia
traccia discover-dir /path/to/archive --project-root my-traccia --format json
```

Discovery reports material counts, direct files, archive members, source
families, and source-family subproducts.

## Full Directory Ingest

```bash
traccia ingest-dir /path/to/archive --project-root my-traccia
```

This is the normal path. It discovers, imports, parses, extracts evidence,
scores the graph, renders outputs, and syncs deletions in the import scope.

For a mounted archive or a subfolder that should keep stable source IDs, pass
an import prefix:

```bash
traccia ingest-dir /mnt/gdrive2/rrss-data/08042026/Twitter \
  --project-root my-traccia \
  --import-prefix rrss-data/08042026/Twitter
```

## Staged Ingest

Use staging when a long graph scoring run is already active or when you want to
prepare filesystem work without model calls:

```bash
traccia stage-dir /path/to/archive --project-root my-traccia
```

`stage-dir` discovers, classifies, imports, parses, stores source/span records,
writes manifests, and checkpoints progress. It does not extract evidence,
recompute the graph, or mark deletions.

Later, run normal ingest against the same scope to extract evidence and update
the graph.

## Extract Without Graph Sync

If you want evidence extraction but not graph scoring:

```bash
traccia ingest-dir /path/to/archive \
  --project-root my-traccia \
  --no-sync-graph \
  --no-sync-deletions
```

Or use:

```bash
traccia ingest-dir /path/to/archive --project-root my-traccia --score-mode none
```

Then score later:

```bash
traccia score --project-root my-traccia
```

## Scoring Modes

| Mode | Use it for |
| --- | --- |
| `incremental` | Normal operation. Reuses unchanged candidate and skill score caches. |
| `full` | Audits, repairs, prompt/model changes, or scoring behavior changes. |
| `none` | Ingest source/evidence records without graph scoring. Available on ingest commands. |

Examples:

```bash
traccia score --mode incremental --project-root my-traccia
traccia score --mode full --project-root my-traccia
traccia ingest-dir /path/to/archive --project-root my-traccia --score-mode none
```

## Parallelism

Evidence extraction can use a bounded material-level worker pool:

```bash
traccia ingest-dir /path/to/archive --project-root my-traccia --parallel-extractions 4
```

Skill scoring can use a separate bounded worker pool:

```bash
traccia score --project-root my-traccia --parallel-scores 4
```

These settings spend quota faster. They do not merge materials into one prompt,
and they do not make graph writes concurrent.

## Source Families

Discovery classifies materials before parsing. Current families are:

| Family | Examples |
| --- | --- |
| `generic` | Markdown, text, code, loose CSV/JSON, ordinary documents. |
| `google_takeout` | `Takeout/`, `archive_browser.html`, Google product export trees. |
| `discord_data_package` | Discord account and message package layouts. |
| `twitter_archive` | X/Twitter archive files such as `data/account.js` and `data/tweets.js`. |
| `reddit_export` | Reddit comments, posts, and conversations exports. |
| `instagram_export` | Instagram export bundles and Meta account download subtrees. |
| `facebook_export` | Facebook export bundles and Meta account download subtrees. |

Unknown layouts fall back to `generic`.

## Linked Attachments And Vision

Linked images, video, audio, documents, and links belong to the parent source
context. If vision is required and the active backend is not vision-capable,
Traccia marks the material as delayed instead of extracting lower-quality text
alone.

To process delayed image-heavy materials, enable vision and use a backend with
`supports_vision: true`.

## Progress Files

| File | Meaning |
| --- | --- |
| `state/progress.json` | Current ingest progress and material status. |
| `state/manifests/<ingest-id>.json` | Discovery and processing outcomes for one run. |
| `state/graph-score-progress.json` | Active graph scoring progress. |
| `state/graph-score-runs.jsonl` | Append-only graph scoring run telemetry. |

Re-run the same ingest command after a crash, quota issue, or mount interruption.
The pipeline uses durable source, parsed, evidence, and progress state to resume.
