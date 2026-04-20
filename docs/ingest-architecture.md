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
  "root_uri": "file:///data/rrss-data",
  "generated_at": "2026-04-19T12:00:00+00:00",
  "materials": [
    {
      "relative_import_path": "rrss-data/reddit-export/comments.csv",
      "source_path": "/mnt/gdrive2/rrss-data/reddit-export.zip",
      "archive_member": "comments.csv",
      "source_family": "reddit_export",
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
