# ingest architecture

## goal

Turn large personal data exports into stable, reviewable source materials without pretending every file is the same thing.

## contract

The ingest pipeline is archive-first and source-family-aware.

For every ingest run:
- preserve the raw archive or source file unchanged
- discover every ingestable material inside it
- classify each material into a source family
- record that decision in a manifest under `state/manifests/`
- only then parse, extract evidence, and update the graph

## source of truth

The rendered graph is not the source of truth during ingest.

The durable source of truth is `state/catalog.sqlite`, especially:
- `sources` for imported source metadata
- `source_spans` for parsed source offsets
- `evidence_items` for model-extracted evidence tied to one source
- `extraction_checkpoints` for resumable chunk extraction inside one source
- graph tables for the latest rendered projection over stored evidence

This means extraction and graph scoring are intentionally separate phases:

1. A material is parsed into spans.
2. Large materials are split into chunks.
3. Each chunk is sent to the extractor with only that source context.
4. The extractor emits evidence records, not skill levels.
5. Evidence records are stored with source ID, span offsets, quotes, candidate skills, evidence type, confidence, and time references.
6. Graph recompute loads all stored evidence, groups it by candidate skill, canonicalizes against the existing catalog, and scores the affected skill state from the merged evidence history.

The system must not compress a batch of materials into one summary and then infer skills from that summary. Batch boundaries are allowed for scheduling graph refreshes, but not for replacing per-source evidence.

## live graph refresh cadence

Directory ingest checkpoints raw progress after every material, so a crash, quota limit, or mount failure does not require starting from zero.

Live graph refreshes are a separate operator-facing projection. On large runs, they are batched by `graph_refresh.live_checkpoint_material_interval` and `graph_refresh.live_checkpoint_min_interval_seconds`. The default is:

```yaml
graph_refresh:
  live_checkpoint_material_interval: 25
  live_checkpoint_min_interval_seconds: 1800.0
  small_run_live_checkpoint_material_limit: 10
```

For small runs, the graph can refresh immediately because the overhead is low and fast visual feedback is useful. For large archive runs, batching avoids repeatedly rescoring a nearly identical graph after every single source while preserving per-material evidence and resumability.

Changing graph refresh cadence must not change final output semantics. The final graph sync still recomputes from all stored evidence.

## source families

Current families:

| family | intent | examples |
|---|---|---|
| `generic` | fallback path for ordinary text-like files | markdown, txt, code, loose csv/json |
| `google_takeout` | Google export bundles with product-specific subtrees | `Takeout/`, `archive_browser.html`, `My Activity/` |
| `discord_data_package` | Discord personal data packages | `account/user.json`, `messages/index.json`, `servers/index.json` |
| `twitter_archive` | X/Twitter account archives | `data/account.js`, `data/tweets.js`, `Your archive.html` |
| `reddit_export` | Reddit account export layouts | `comments.csv`, `posts.csv`, `conversations.json` |
| `instagram_export` | Instagram export bundles and Meta account downloads scoped to Instagram | `Instagram/`, `profile_information/`, `followers_and_following/` |
| `facebook_export` | Facebook export bundles and Meta account downloads scoped to Facebook | `Facebook/`, `your_facebook_activity/`, `profile_information/` |

Family detection is heuristic and intentionally explicit. Unknown layouts fall back to `generic` instead of silently being forced into a wrong adapter.

## ingest manifest

Each ingest run writes one manifest file:

```json
{
  "manifest_id": "ingest_rrss_data_ab12cd34ef",
  "root_uri": "file:///data/personal-archive",
  "generated_at": "2026-04-19T12:00:00+00:00",
  "materials": [
    {
      "relative_import_path": "personal-archive/reddit-export/comments.csv",
      "source_path": "/mnt/archive/personal-archive/reddit-export.zip",
      "archive_member": "comments.csv",
      "source_family": "reddit_export",
      "source_family_subproduct": "comments",
      "detection_reason": "matched Reddit export marker: comments.csv",
      "status": "processed",
      "source_id": "src_comments_a1b2c3"
    }
  ]
}
```

This is the run contract for large exports. If parsing or scoring changes later, the manifest still shows:
- what was discovered
- where it came from
- what family it was treated as
- whether it was processed or skipped

Discovery summaries and `state/progress.json` also keep a `by_family_subproduct` breakdown so a long-running scan can be checked at a more useful granularity than just top-level families.

## adapter direction

Source-family adapters are now part of the ingest path for known messy export shapes.

Intended flow:

1. `discover`
2. `detect family`
3. `expand container`
4. `normalize into family-specific records`
5. `chunk normalized records`
6. `run LLM extraction on normalized chunks`

Currently wired adapters:

| family | adapter |
|---|---|
| `google_takeout` | export HTML cleanup plus contextual text wrapping for loose text files |
| `instagram_export` / `facebook_export` | HTML export cleanup that drops CSS boilerplate and keeps the visible conversation or activity text |
| `twitter_archive` | `window.YTD...` JavaScript payload normalization into record-oriented text |
| `reddit_export` | CSV row normalization into record-oriented text with timestamps and subreddit context |

That is the line between “can ingest big exports” and “can ingest big exports reliably”.

Known export families are first-class lanes. Everything else still flows through the generic file-by-file path instead of being rejected.

## document normalization

Document-like files are a separate concern from archive-family detection.

For `pdf` and `docx` materials:
- normalize before chunking
- prefer markdown-preserving local conversion over plain-text extraction
- default to a local-first provider order, with PDFs preferring `marker -> docling -> markitdown -> native` and DOCX preferring `docling -> markitdown -> native`
- keep OCR as a separate provider choice, not an OpenAI-bound plugin inside the normalizer
- prefer free/local OCR engines such as Docling auto OCR, Tesseract, EasyOCR, or RapidOCR when OCR is needed

The chosen normalizer and OCR usage belong in source metadata so later review can distinguish plain extraction from LLM-assisted document recovery.

## non-goals

- no fake universal binary parser
- no corpus-wide LLM pass over raw archives
- no archive-family guesses hidden inside prompts
- no direct dependency on provider HTML viewers when structured files exist
