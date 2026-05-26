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
2. Materials are kept whole when they fit the extraction character budget; only oversized materials are split into chunks.
3. Each chunk is sent to the extractor with only that source context.
4. The extractor emits evidence records, not skill levels.
5. Evidence records are stored with source ID, span offsets, quotes, candidate skills, evidence type, confidence, and time references.
6. Graph recompute loads all stored evidence, groups it by candidate skill, canonicalizes against the existing catalog, and scores the affected skill state from the merged evidence history.

The system must not compress a batch of materials into one summary and then infer skills from that summary. Batch boundaries are allowed for scheduling graph refreshes, but not for replacing per-source evidence.

Agent logs have an additional attribution rule. Parsed artifacts keep user, assistant, tool, system, and thinking spans for auditability, but evidence extraction receives only user/human/developer spans. This prevents model outputs, tool logs, or hidden reasoning transcripts from being re-attributed as the user's own skills.

## staged ingest beside graph scoring

Long-running graph scoring can run from a stable evidence snapshot while another process prepares more input. The safe concurrent path is `traccia stage-dir`, which does discovery, source-family detection, raw import linking, parsing, source/span storage, manifests, and progress checkpoints only.

`stage-dir` intentionally does not call the LLM extractor, does not recompute the graph, and does not run deletion sync. Prepared materials are marked as `prepared` in the ingest run state, so a later normal `traccia ingest-dir` can resume from them and perform evidence extraction plus graph sync. This keeps the active scorer from competing with a second LLM caller while still allowing slow filesystem discovery and parsing work to advance.

For already-known sources, `stage-dir` trusts the existing parsed artifact instead of rehashing remote files. This makes it useful for mounted folders where the likely goal is to find new material without spending hours revalidating every old file through FUSE.

During discovery, `state/progress.json` reports both `seen_this_scan` and the split between `already_tracked` and `new_to_run_state`. `seen_this_scan` is not a claim that those files are new; it is only the current filesystem walk count.

Use this mode when an existing scoring process was already started before the newer coordination code was available. Future worker orchestration can add a shared LLM lease, but old already-running processes cannot acquire a lock that did not exist when they were started.

Full extraction can also run beside graph scoring if every runner has been started with the shared LLM lease code. In that mode, use normal ingest with graph and deletion sync disabled:

```bash
traccia ingest-dir /path/to/archive --project-root my-traccia --no-sync-graph --no-sync-deletions
```

The LLM lease coordinates extractor, canonicalizer, and scorer requests through `TRACCIA_LLM_LEASE_PATH` or `/tmp/traccia-llm-request.lock`. Canonicalizer and serial scorer requests acquire the lease exclusively. Extractor requests and parallel skill scorer requests acquire shared slots when their worker counts are above `1`. Ingest can still parse files and write source/evidence records while scoring owns graph table writes. Newly extracted evidence is durable immediately, but it is not reflected in the rendered graph until the next graph scoring pass includes it.

## graph scoring modes

Graph scoring has two modes:

| mode | behavior |
|---|---|
| `incremental` | default; reuse unchanged candidate canonicalization and final skill score caches |
| `full` | bypass graph scoring caches and rerun canonicalization/scoring from stored evidence |

Use incremental for normal archive growth:

```bash
traccia score --mode incremental --project-root my-traccia
```

Use full when auditing, repairing, or intentionally changing scoring semantics:

```bash
traccia score --mode full --project-root my-traccia
```

Skill scoring supports bounded internal parallelism:

```bash
traccia score --mode incremental --project-root my-traccia --parallel-scores 4
```

The config default is:

```yaml
graph_scoring:
  parallel_scores: 4
```

This pool is deliberately narrower than running multiple scorer processes. The
parent process still owns canonicalization, cache writes, progress files, graph
checkpoints, and final graph replacement. Worker threads only call `score_skill`
for cache-missing skills and return strict score payloads to the parent. Because
each score request contains only one skill plus that skill's merged evidence
history, parallelism changes scheduling and quota burn rate, not the information
available to the scoring model.

Directory ingest also accepts `--score-mode incremental`, `--score-mode full`, or
`--score-mode none`. `none` stores source/evidence records and leaves graph
projection refresh for a later `traccia score` run.

Incremental scoring is not "only brand-new candidate names." It means only changed
graph facts. If a new source adds evidence to an existing skill, that skill is
rescored once from the merged evidence history. If a source introduces a new
candidate skill, the new candidate is canonicalized and the resulting skill is
scored. Unchanged candidate decisions and unchanged final skill evidence
fingerprints are reused from SQLite caches.

Scoring progress is separate from ingest progress:

| file | meaning |
|---|---|
| `state/progress.json` | current directory/material ingest state |
| `state/graph-score-progress.json` | current graph scoring mode, cache hit/miss counts, changed work, and active candidate/skill |
| `state/graph-score-runs.jsonl` | append-only scoring run event stream keyed by run ID, model, score mode, progress, cache stats, and final totals |
| `state/catalog.sqlite:pipeline_runs` | one SQLite summary row per graph scoring run |

The rendered graph remains a projection over `state/catalog.sqlite`. A crash during
scoring does not delete source evidence or completed score cache rows.

Directory ingest also supports bounded parallel extraction inside one ingest process:

```bash
traccia ingest-dir /path/to/archive --project-root my-traccia --parallel-extractions 4
```

The same value can live in config as a fallback when no lane pool is configured:

```yaml
ingest:
  parallel_extractions: 4
```

The default is `1`. Values above `1` only parallelize evidence extraction for separate materials. Discovery, resume decisions, manifest writes, progress writes, deletion sync, live graph checkpoints, and final graph recompute are still parent-side serialized. Workers use separate pipeline/backend/storage handles, then return material outcomes to the parent process. This avoids sharing one backend client or SQLite connection across threads, and it keeps graph scoring from racing against active evidence writes.

Parallel extraction is intentionally batched. A graph checkpoint may run between completed worker batches, but never while workers are still writing parsed spans or evidence. This keeps the per-source extraction contract intact while allowing operators to spend more available model quota when the backend and machine can handle it.

For split-provider extraction, configure `backend.extraction_backends` instead of only
raising `ingest.parallel_extractions`. The lane pool can mix providers, but the graph
canonicalizer and scorer still stay on the primary backend:

```yaml
backend:
  provider: openai_compatible
  model: glm-5-turbo
  api_key_env: CLIPROXYAPI_KEY
  base_url: http://127.0.0.1:8317/v1
  api_style: chat_completions
  structured_output_mode: json_schema
  extraction_backends:
    - name: glm
      model: glm-5-turbo
      api_key_env: CLIPROXYAPI_KEY
      base_url: http://127.0.0.1:8317/v1
      parallel_extractions: 5
    - name: gemini
      model: star-gemini-3.5-flash
      api_key_env: CLIPROXYAPI_KEY
      base_url: http://127.0.0.1:8317/v1
      supports_vision: true
      parallel_extractions: 3
```

In that configuration the effective extraction pool is 8, but it is still one
pipeline with one resumable source state, not two independent ingest jobs.

Targeted subfolder ingests should use `--import-prefix` when the source identity must remain anchored to a larger archive path. For example, ingesting only `rrss-data/08042026/Twitter` should still use the import prefix `rrss-data/08042026/Twitter`; otherwise the same files would be reidentified under a shorter `twitter/...` prefix. The same rule disambiguates multiple account exports that both end in `extracted/Takeout`.

## linked media and vision gating

Linked media belongs to the parent source context. If a tweet, post, message, or export row references local media, the parser keeps attachment metadata on the same parsed document instead of creating an unrelated source.

Image attachments have an additional extraction rule:
- If the active backend is vision-capable (`multimodal.enable_vision=true` and `backend.supports_vision=true`), Traccia may send the resolved image bytes alongside the text payload.
- If the active backend is not vision-capable, Traccia must mark the material as `delayed` instead of extracting it with text alone.
- A later run with a vision-capable backend, for example `star-gemini-3-flash` through an OpenAI-style proxy, must retry delayed materials from the same resumable run state.

This prevents silent quality loss. OCR text, alt text, filenames, and contextual hints are useful, but they are not equivalent to a vision model inspecting the image in context.

## remote media enrichment

Remote media URLs also stay attached to the parent source. If a Google Takeout activity row, playlist entry, comment, tweet, note, chat log, or other source mentions a YouTube or direct audio/video URL, Traccia stores the original record and adds recovered media context as attachment text.

The default remote media lane is high-context rather than transcript-only:

```yaml
multimodal:
  enable_remote_media_enrichment: true
  remote_media_enrichment_command: summarize
  remote_media_enrichment_video_mode: understand
  enable_remote_media_slides: true
  enable_remote_media_slides_ocr: true
```

That runs `summarize --extract --video-mode understand --slides --slides-ocr` for eligible remote media. The intent is to recover topics that are often absent from weak metadata: CAD, Blender, machining, code walkthroughs, design lectures, diagrams, and slide-heavy tutorials.

The default lane requires more than the `summarize` binary. Full YouTube visual enrichment needs `ffmpeg`, `yt-dlp`, and `tesseract` for OCR. If captions are unavailable and `summarize` falls back to audio transcription, it also needs either a supported transcription API key (`GROQ_API_KEY`, `ASSEMBLYAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, or `FAL_KEY`) or a local whisper.cpp setup available to `summarize`. Local whisper.cpp requires both the `whisper-cli` binary, or `SUMMARIZE_WHISPER_CPP_BINARY`, and a model file. `summarize` checks `SUMMARIZE_WHISPER_CPP_MODEL_PATH` first and otherwise defaults to `~/.summarize/cache/whisper-cpp/models/ggml-base.bin`. `traccia doctor` reports this as `status=ready`, `status=degraded`, or `status=disabled` without failing normal doctor checks.

Operators can set `remote_media_enrichment_video_mode: transcript` plus both slide flags to `false` for a faster transcript-only lane, or set `enable_remote_media_enrichment: false` to keep only the original URLs.

## live graph refresh cadence

Directory ingest checkpoints raw progress after every material, so a crash, quota limit, or mount failure does not require starting from zero.

Live graph refreshes are a separate operator-facing projection. They are disabled by default because full graph scoring can dominate multi-hour archive ingests. Directory ingest still checkpoints raw progress and extraction checkpoints after each material/chunk, then runs one full graph sync at final completion.

If live checkpoints are explicitly enabled, large runs batch them by `graph_refresh.live_checkpoint_material_interval` and `graph_refresh.live_checkpoint_min_interval_seconds`. The material interval is counted against newly extracted evidence items, not merely files that were parsed. Files that produce no evidence still checkpoint raw progress, but they do not trigger an expensive graph rescore by themselves.

```yaml
graph_refresh:
  live_checkpoints_enabled: false
  live_checkpoint_material_interval: 25
  live_checkpoint_min_interval_seconds: 1800.0
  small_run_live_checkpoint_material_limit: 10
```

For small runs, enabling live checkpoints can refresh the graph immediately after new evidence because the overhead is low and fast visual feedback is useful. For large archive runs, the default final-only graph sync avoids repeatedly rescoring a nearly identical graph while preserving per-material evidence and resumability.

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

## Google Takeout relevance policy

Google Takeout is a high-noise export family. A useful ingest should not spend quota on every file simply because it exists in the archive. The discovery layer applies a product-aware skip policy before parsing:

| area | ingested | skipped |
|---|---|---|
| Gmail / `Correo` | message headers, dates, subjects, labels, sent-message body snippets | received-message bodies by default, user settings exports |
| YouTube / YouTube Music | history, comments, subscriptions, metadata, URLs, transcript enrichment when available | raw uploaded video binaries |
| Google Photos / `Google Fotos` | deterministic fast-vision image samples paired with sidecar metadata | standalone sidecar JSON, non-image bulk media |
| Drive | selected document, code, notebook, spreadsheet, calendar, and text formats | archives, caches, game/runtime data, opaque media, unsupported binaries |
| account and device products | nothing by default | account, payment, device, profile, alert, and product-survey metadata |

The policy lives in `src/traccia/google_takeout.py` instead of in prompts. This keeps discovery deterministic, testable, and inspectable before any model call happens.

Google Photos sidecars are intentionally paired with sampled image materials. The source text records the sidecar metadata, and the parsed source carries the image as an attachment. If the active backend is not vision-capable, the material is marked `delayed` so a later run with `multimodal.enable_vision: true` and `backend.supports_vision: true` can process the same image context.

The default configuration is:

```yaml
google_takeout:
  relevance_mode: skill_relevant
  gmail_mode: metadata_plus_sent
  youtube_enrichment: detailed
  photos_mode: fast_vision
  drive_mode: selective_docs
  max_photo_vision_samples_per_folder: 8
```

This is a relevance filter, not a claim that skipped files have no personal meaning. The contract is narrower: skipped files have low expected skill-evidence value relative to their parsing cost, privacy risk, or redundancy.

Supported mode values:

| key | values |
|---|---|
| `relevance_mode` | `skill_relevant`, `off` |
| `gmail_mode` | `metadata_plus_sent`, `off` |
| `photos_mode` | `fast_vision`, `off` |
| `drive_mode` | `selective_docs`, `all`, `off` |

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
- whether it was processed, skipped, delayed, or failed

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

That is the line between "can ingest big exports" and "can ingest big exports reliably".

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
- no direct dependency on provider HTML pages when structured files exist
