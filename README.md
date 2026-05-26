<div align="center">
  <img src=".github/assets/traccia-logo.svg" alt="traccia logo" width="220">
  <h1>traccia</h1>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-000000?style=flat-square" alt="python badge">
  <img src="https://img.shields.io/badge/license-MIT-000000?style=flat-square" alt="mit license badge">
</p>


---

`traccia` turns personal archives into a skill graph that can explain itself. feed it notes, code, docs, AI chats, exported platform data, and the usual pile of half-structured personal history. it keeps the source files untouched, extracts evidence with timestamps, and renders a graph that shows where a skill came from, how deep it looks, how current it is, and how central it is to the broader archive.

the project is built for mixed archives rather than one clean source of truth. that includes repo history, google activity, social profiles, AI conversation logs, and everything else that tends to accumulate around a real person over time. the point is not to pretend those signals mean the same thing. `traccia` keeps weak signals weak, strong evidence strong, and the trail visible enough to challenge later.

## why

most archive tools are good at storing material and bad at telling the skill story. most profile tools do the opposite. they compress everything into a pitch, flatten uncertainty, and throw away the evidence trail that would let you inspect the claim later.

`traccia` is trying to keep both sides intact. the files stay raw. the evidence is extracted one source at a time. the graph records when a skill first appeared, when it likely crossed from ambient interest into learned capability, and when there was strong enough proof to treat it as demonstrated work. that makes the output more useful for reflection, review, and long-range memory than a resume-shaped summary.

## install

`traccia` already ships a real console script. the Python package is still the canonical implementation, but the repo now also includes a thin npm wrapper for people who want to install or run the CLI from a Node-first environment without rewriting the tool in JavaScript.

| path | command | result |
| --- | --- | --- |
| repo-local workflow | `uv sync` | keeps `uv run traccia ...` available inside the project |
| bare `traccia` command with live local edits | `uv tool install -e .` | installs the console script on your `PATH` in editable mode |
| standard editable install without `uv tool` | `pip install -e .` | installs the same console script through pip |
| npm one-off wrapper | `npx @microck/traccia doctor .` | downloads the wrapper, then shells out to `uvx --from traccia traccia ...` |
| npm global wrapper | `npm install -g @microck/traccia` | installs a `traccia` command on your `PATH`, backed by `uvx` |

the unscoped npm package name `traccia` is already taken, so the wrapper is published as `@microck/traccia`. the installed command is still `traccia`.

the wrapper does not embed Python. it still expects `uv` and `uvx` to exist on your machine, because its only job is to hand execution off to the real Python package cleanly.

if you want the wrapper to pull the heavier document stack by default, set `TRACCIA_UVX_SPEC='traccia[document-markdown]'` before running it. if you are working inside this repo and want the wrapper to exercise the local checkout instead of PyPI, set `TRACCIA_USE_LOCAL_REPO=1`. that maintainer mode switches the wrapper from `uvx --from traccia traccia ...` to `uv run traccia ...` from the repo root.

if you just want the shortest path from a clone, `uv tool install -e .` is still the cleanest direct install.

document normalization providers are optional because some of them are heavy. the base install keeps the core CLI light, while the document stack can be added when you actually need high-quality local PDF and DOCX parsing:

| extra | command | what it adds |
| --- | --- | --- |
| docling only | `uv sync --extra docling` | local markdown conversion plus local OCR backends such as tesseract, easyocr, and rapidocr |
| marker only | `uv sync --extra marker` | stronger local PDF-to-markdown conversion, especially for layout-heavy PDFs |
| full local document stack | `uv sync --extra document-markdown` | marker + docling + markitdown fallback chain |

## first run

```bash
uv tool install -e .
traccia init my-traccia
traccia ingest-dir /path/to/archive --project-root my-traccia
traccia tree --project-root my-traccia
traccia explain python --project-root my-traccia
traccia review --project-root my-traccia
traccia export obsidian --project-root my-traccia
traccia export debug-report --project-root my-traccia
```

the finished-run skill map viewer has a three-step curation and publish workflow:

```bash
# phase 1: generate the read-only public viewer from the current graph
traccia export viewer --project-root my-traccia

# phase 2 admin: generate the admin curation viewer with the full graph
# (includes hidden, disputed, review, and low-confidence nodes)
traccia export admin --project-root my-traccia

# after curating in the admin viewer (hide/mute, feature/pin, collapse domains,
# add public label/note overrides, approve low-confidence or disputed nodes),
# save curation.json into exports/viewer/, then publish:

# phase 2 publish: generate the redacted public bundle from graph + curation
traccia export publish --project-root my-traccia
```

the admin viewer writes `curation.json` into `exports/viewer/curation.json` when
served locally. when running from a static file server, the save action triggers
a browser download of `curation.json` instead. the publish step reads that
curation file and produces `exports/viewer-public/` with a separate public graph
contract that physically excludes hidden nodes, hidden edges, raw provenance,
raw excerpts, sensitive evidence IDs, disputed/review nodes (unless approved),
and low-confidence nodes (unless approved). public node IDs remain the same as
internal IDs unless a skill ID leaks private information, in which case stable
`pub_<hash>` aliases are generated with the mapping kept admin-only.

if a long graph scoring run is already active and you want to prepare more files without
starting a second LLM lane, use staged ingest:

```bash
traccia stage-dir /path/to/archive --project-root my-traccia
```

`stage-dir` discovers materials, detects source families, links raw files into
`raw/imported/`, parses spans, and writes resumable progress. it deliberately does not
call the LLM extractor, does not recompute the graph, and does not run deletion sync.
prepared materials are marked as `prepared`, so a later normal `traccia ingest-dir` can
extract evidence and sync the graph from that checkpoint.

if you want full evidence extraction while a separate graph scorer is already running,
run normal ingest with graph and deletion sync disabled:

```bash
traccia ingest-dir /path/to/archive --project-root my-traccia --no-sync-graph --no-sync-deletions
```

live LLM calls are coordinated through an advisory lease at
`TRACCIA_LLM_LEASE_PATH` or `/tmp/traccia-llm-request.lock` by default. graph
canonicalization and serial scoring use the lease exclusively. evidence extraction
and parallel skill scoring use shared lease slots only when you explicitly raise
their worker counts. the active scorer owns graph table writes; newly extracted
evidence is stored in SQLite and will be included in the next graph scoring pass.

graph scoring has two modes:

| mode | command | use it for |
| --- | --- | --- |
| incremental | `traccia score --mode incremental --project-root my-traccia` | normal operation; reuses unchanged candidate and skill score caches |
| full | `traccia score --mode full --project-root my-traccia` | repair, audit, or model/prompt changes where every graph decision should be rerun |

Skill scoring can also run with a bounded internal worker pool:

```bash
traccia score --mode incremental --project-root my-traccia --parallel-scores 4
```

The same default can live in config:

```yaml
graph_scoring:
  parallel_scores: 4
```

Only final skill scoring is parallelized. Candidate canonicalization, cache writes,
progress writes, graph checkpoints, and final rendering stay parent-side serialized.
Each worker receives the same per-skill prompt payload it would receive in a serial
run, so the final skill states should match one-worker scoring when the same model
and deterministic backend behavior are used. Use a value that matches available
provider quota; higher values spend quota faster but do not improve per-skill
reasoning quality.

normal `ingest` and `ingest-dir` runs use incremental scoring by default. pass
`--score-mode full` to force a full scoring pass after ingest, or
`--score-mode none` to extract evidence without touching graph projections.
scoring progress is written to `state/graph-score-progress.json`; ingest progress
continues to live in `state/progress.json`.

scoring also writes run telemetry for later analysis. `state/graph-score-runs.jsonl`
is an append-only event stream with run IDs, model, score mode, cache hit/miss
counts, candidate progress, and final totals. `state/catalog.sqlite` also stores
one summary row per scoring run in `pipeline_runs`. These artifacts avoid raw
source excerpts and omit candidate/skill display names from the JSONL stream.

if you want one ingest process to extract multiple independent materials at once,
set `ingest.parallel_extractions` in `config/config.yaml` or pass
`--parallel-extractions N` to `ingest-dir`:

```bash
traccia ingest-dir /path/to/archive --project-root my-traccia --parallel-extractions 4
```

the default is `1`. higher values only parallelize evidence extraction for separate
materials. resume checks, manifests, progress writes, deletion sync, and live graph
checkpoints stay parent-side serialized. final graph scoring can separately use
`graph_scoring.parallel_scores`, and it still recomputes from durable per-source
evidence rather than from compressed batches.

for a split lane pool, configure `backend.extraction_backends` instead of only
raising `ingest.parallel_extractions`. the lane pool decides which OpenAI-style
backend handles extraction, while the primary backend still handles canonicalization
and scoring:

```yaml
backend:
  provider: openai_compatible
  model: glm-5-turbo
  api_key_env: CLIPROXYAPI_KEY
  base_url: http://127.0.0.1:8317/v1
  api_style: chat_completions
  structured_output_mode: json_schema
  supports_vision: false
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

in that layout, extraction workers are split 5/3 across glm and gemini, but graph
canonicalization and scoring still stay on the primary backend model.

when targeting a subfolder from a larger mounted archive, pass `--import-prefix` to
keep stable source IDs. this avoids duplicating a folder that was originally ingested
from a higher root, and it prevents two different accounts with the same folder name
from colliding:

```bash
traccia ingest-dir /mnt/gdrive2/rrss-data/08042026/Twitter \
  --project-root my-traccia \
  --import-prefix rrss-data/08042026/Twitter \
  --no-sync-graph \
  --no-sync-deletions
```

During discovery, `state/progress.json` separates `seen_this_scan` from
`already_tracked` and `new_to_run_state`. The scan count is just the number of
materials seen while walking the folder; `new_to_run_state` is the useful number when
you want to know what was not part of the previous resumable run.

for deterministic local testing, switch the generated config to:

```yaml
backend:
  provider: fake
```

for a live model, the current backend contract is an openai-style `v1/chat/completions` endpoint:

```yaml
backend:
  provider: openai_compatible
  model: gpt-5-chat-latest
  api_key_env: OPENAI_API_KEY
  base_url: https://api.openai.com/v1
  api_style: chat_completions
  structured_output_mode: json_schema
```

any provider that clones the same request and response shape can be used by swapping `base_url`, `model`, and `api_key_env`. the current implementation deliberately targets `chat_completions` because it remains the most commonly copied interface across hosted and self-hosted providers, even if some vendors now prefer newer APIs for their own stacks.

## backend surface

| key | example | meaning |
| --- | --- | --- |
| `provider` | `openai_compatible` | live LLM backend that speaks an OpenAI-style HTTP contract |
| `model` | `gpt-5-chat-latest` | current chat-capable example model id; replace it with any compatible model your provider exposes |
| `api_key_env` | `OPENAI_API_KEY` | environment variable that holds the credential |
| `base_url` | `https://api.openai.com/v1` | root URL for the compatible endpoint |
| `api_style` | `chat_completions` | the only live API style supported right now |
| `structured_output_mode` | `json_schema` | primary structured-output mode; `json_object` is also supported |
| `supports_vision` | `false` | whether this backend should be trusted to accept multimodal image parts on the OpenAI-style endpoint |
| `vision_detail` | `auto` | image detail hint passed to multimodal-capable backends when raw images are sent |

## linked media and vision

`traccia` now treats linked media as part of the same source context instead of as a detached second source. if a tweet, post, message, or export record references local media, the parent source can carry that attachment context into evidence extraction.

there are two separate layers here:

| layer | default | what it does |
| --- | --- | --- |
| linked attachments | on | discovers media references, resolves local files when possible, and attaches labels plus local OCR text to the parent source context |
| remote media enrichment | on | detects eligible remote media URLs in source text and tries to recover transcript plus visual tutorial context with `summarize --extract`, mainly for youtube and direct audio or video links |
| raw vision to the LLM | off | sends the actual image bytes to the backend only when you explicitly enable vision and mark the backend as vision-capable |

that split is deliberate. OpenAI-style endpoint compatibility does not guarantee that a model or proxy really supports multimodal image input. `traccia` therefore keeps the context-preserving attachment path on by default, while the raw image lane stays opt-in.

the remote URL lane is deliberately narrower than "summarize every link". for now it only targets media-shaped URLs where transcript and visual-context recovery materially improve evidence quality without replacing the original source record. a youtube watch URL inside a google activity export is a good example. a random article URL is not.

the config looks like this:

```yaml
backend:
  supports_vision: false
  vision_detail: auto

multimodal:
  enable_linked_attachments: true
  enable_vision: false
  enable_local_image_ocr: true
  enable_local_media_transcription: true
  enable_remote_media_enrichment: true
  audio_transcription_provider: auto
  audio_transcription_model: turbo
  audio_transcription_device: cpu
  remote_media_enrichment_command: summarize
  remote_media_enrichment_video_mode: understand
  enable_remote_media_slides: true
  enable_remote_media_slides_ocr: true
  max_attachments_per_source: 4
  max_attachment_text_characters: 1200
  max_attachment_transcript_characters: 8000
  max_image_bytes: 5000000
  ocr_timeout_seconds: 20
  transcription_timeout_seconds: 1800
  remote_media_enrichment_timeout_seconds: 180
```

in practice, `enable_linked_attachments: true` should stay on unless you explicitly want text-only parsing. `enable_vision: true` should only be enabled when the chosen backend model and proxy actually accept image inputs, and `backend.supports_vision: true` should only be marked on for those known-good multimodal endpoints.

when a material has resolved local image attachments and the active backend is not vision-capable, `traccia` now delays that material instead of extracting it with a text-only model. delayed entries are written to the manifest and resumable run-state as `status: delayed`; rerunning the same project with a vision backend such as `star-gemini-3-flash` processes those entries from the same source context. this keeps a tweet/post/message and its images together without letting a non-vision model silently miss the image content.

`enable_local_image_ocr: true` keeps free local attachment text extraction available even with vision disabled. `enable_local_media_transcription: true` keeps local transcripts available for attached audio and video files. `audio_transcription_provider: auto` currently means "use local `whisper` when it exists, otherwise skip transcription cleanly", and `ffmpeg` is still the local preprocessing step that strips or normalizes audio before transcription.

`enable_remote_media_enrichment: true` enables the `summarize` lane for remote media URLs that are found inline in the source text. the default command is `summarize`, but `remote_media_enrichment_command` can point at another binary path if you keep it somewhere custom. disabling that flag leaves the original URLs in the source text but stops the extra remote enrichment pass.

the remote media default is intentionally high-context: `remote_media_enrichment_video_mode: understand`, `enable_remote_media_slides: true`, and `enable_remote_media_slides_ocr: true`. for youtube, that asks `summarize` to combine transcript extraction with slide/screenshot extraction and OCR. this is useful for watch history, comments, playlists, activity records, visual tutorials, CAD/Blender/code walkthroughs, diagrams, and lecture slides where the video title alone is weak.

that default is a real media toolchain, not just a single python dependency. install `summarize`, `ffmpeg`, `yt-dlp`, and `tesseract` for the full `understand + slides + OCR` lane. when captions are not available and `summarize` must fall back to audio transcription, it also needs either a supported transcription API key (`GROQ_API_KEY`, `ASSEMBLYAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY`, `GOOGLE_API_KEY`, `OPENAI_API_KEY`, or `FAL_KEY`) or a local whisper.cpp setup visible to `summarize`. local whisper.cpp means both a `whisper-cli` binary, or `SUMMARIZE_WHISPER_CPP_BINARY`, and a model file. `summarize` defaults to `~/.summarize/cache/whisper-cpp/models/ggml-base.bin`; override it with `SUMMARIZE_WHISPER_CPP_MODEL_PATH`. run `traccia doctor` to see whether remote media enrichment is `ready`, `degraded`, or `disabled`, including the exact whisper.cpp model path being checked.

if you want the faster lane, set `remote_media_enrichment_video_mode: transcript` and turn both slide flags off. if you want no remote lookups, set `enable_remote_media_enrichment: false`.

with that setup, a post plus its screenshot, photo, chart, or attached image can be analyzed together without forcing every backend into a vision-only contract.

audio and video attachments now follow the same principle. if a source references a local clip, `traccia` can extract a local transcript and attach it back to the parent source context instead of treating the clip as a detached second-class file. that keeps the text post, the media metadata, and the recovered speech in one extraction bundle. if the source instead carries a remote youtube or direct media URL, `traccia` can now recover transcript plus visual context through `summarize --extract` and keep that alongside the original source event instead of flattening the whole thing into an ungrounded summary.

## google takeout

Google Takeout archives are not treated as a flat pile of files. `traccia` applies a product-aware relevance policy before parsing so the run spends model quota on skill-bearing material and skips account metadata, empty exports, raw binaries, caches, indexes, and bulk runtime/game data.

The default policy is:

| product | default behavior | why |
| --- | --- | --- |
| Gmail / `Correo` | keep headers and labels for all messages, include body snippets only for sent mail | received mail often describes other people or newsletters; sent mail is stronger self-authored evidence |
| YouTube / YouTube Music | keep history, comments, subscriptions, metadata, and URLs; skip raw uploaded video binaries | titles, comments, watch history, and transcripts are usually higher-value than uploading large media blobs |
| Google Photos / `Google Fotos` | sample a small number of images per folder and pair each image with its sidecar JSON | photos can be useful, but full photo libraries are expensive and repetitive |
| Drive | keep selective document/code/data formats; skip archives, game/runtime data, large media, and unsupported binaries | Drive mixes authored work with bulk backups, dependencies, and opaque media |
| account/payment/device products | skip by default | these exports are usually identity or settings metadata, not skill evidence |

Google Photos sidecar JSON files are not ingested as standalone evidence. They are paired with sampled image materials so a vision-capable backend sees the image and the metadata in the same source context. If the configured backend cannot process vision input, those image materials are marked `delayed` and can be resumed later with a vision backend instead of being silently degraded to text-only extraction.

YouTube URLs found in Takeout records use the same remote media enrichment lane described above by default. If `summarize` can recover a transcript, slide OCR, or useful extract, that text stays attached to the original Takeout record. Deleted, private, or unavailable videos fall back to the original title, URL, timestamp, and surrounding activity record.

The relevant config block is:

```yaml
google_takeout:
  relevance_mode: skill_relevant
  gmail_mode: metadata_plus_sent
  youtube_enrichment: detailed
  photos_mode: fast_vision
  drive_mode: selective_docs
  max_photo_vision_samples_per_folder: 8
```

Set `max_photo_vision_samples_per_folder: 0` if you want to skip Google Photos images entirely. Keep it small for huge Takeout archives unless you are intentionally spending vision quota on photo analysis.

Supported mode values are intentionally simple right now:

| key | useful values |
| --- | --- |
| `relevance_mode` | `skill_relevant` or `off` |
| `gmail_mode` | `metadata_plus_sent` or `off` |
| `photos_mode` | `fast_vision` or `off` |
| `drive_mode` | `selective_docs`, `all`, or `off` |

## document normalization

`traccia` now treats document normalization and OCR as separate concerns. that split is deliberate. converting a file into clean markdown is one problem. deciding how to recover text from scanned pages or embedded images is another.

the default path is local-first and format-aware:

| input | default `auto` chain | why |
| --- | --- | --- |
| pdf | `marker -> docling -> markitdown -> native` | marker is the strongest local PDF path here for layout-heavy markdown output, docling is the strongest local OCR-capable fallback, markitdown is a lighter markdown fallback, native is last-resort plain text |
| docx | `docling -> markitdown -> native` | docling is the better structured local default for office documents, while markitdown remains a useful markdown fallback |

the providers do different jobs:

| provider | what it is for | tradeoff |
| --- | --- | --- |
| `auto` | best default, local-first fallback chain | behavior depends on installed optional tools |
| `marker` | strongest wired local PDF markdown path | heavier dependency, currently wired for PDF only in `traccia` |
| `docling` | best all-around local document parser with local OCR backends | larger install than the base package |
| `markitdown` | lightweight markdown-oriented fallback | weaker on difficult scanned/layout-heavy documents |
| `native` | plain text extraction only | lowest fidelity, but minimal dependencies |

OCR is configured separately:

| `ocr_provider` | effect |
| --- | --- |
| `auto` | use the provider's local automatic OCR path; for docling this means local OCR engine auto-detection |
| `none` | disable OCR entirely and only use extractable document text |
| `tesseract` / `tesseract_cli` / `easyocr` / `rapidocr` | force a specific local docling OCR backend |

that means OCR is no longer tied to OpenAI or any hosted vision API. if you want the whole stack local and free, keep the backend fake or point the scoring backend somewhere else entirely. the document parser does not need OpenAI for OCR anymore.

### enable or disable it

the default config is already:

```yaml
document_normalization:
  provider: auto
  ocr_provider: auto
```

force the strongest wired local PDF path:

```yaml
document_normalization:
  provider: marker
  ocr_provider: auto
```

disable marker and keep everything in the docling lane:

```yaml
document_normalization:
  provider: docling
  ocr_provider: auto
```

disable OCR completely:

```yaml
document_normalization:
  provider: auto
  ocr_provider: none
```

fall all the way back to plain-text extraction:

```yaml
document_normalization:
  provider: native
  ocr_provider: none
```

the practical difference is simple. if your PDFs are born-digital and layout-heavy, `marker` is usually the best local first try. if your documents are scanned, mixed, multilingual, or need a specific free OCR engine, `docling` is the more controllable path. `markitdown` stays useful as a lighter markdown fallback, not as the main OCR system.

## doctor

`traccia doctor` now checks more than the scaffold. it also prints the optional local capability surface so you can see what the current machine can actually do before launching a multi-hour ingest.

it reports document normalization availability for `docling`, `markitdown`, and `marker_single`, local image OCR availability through `tesseract`, local media transcription availability through `ffmpeg`, `ffprobe`, and `whisper`, remote media enrichment availability through `summarize`, and backend auth plus optional backend health when `--check-backend` is used.

that split matters in practice. a project can be structurally healthy while still missing the local tools needed for OCR or transcription, and `doctor` now makes that visible up front.

## what it does today

the current build already handles immutable source intake into `raw/imported/`, file-by-file parsing with span tracking, source classification across authored material and activity traces, and evidence extraction that tries to separate real work from ambient interest. known export families no longer go straight through the same raw path either. google takeout html, csv, json, calendar `.ics`, and gmail `.mbox` exports now get normalized into cleaner record-oriented text before the model sees them, while twitter `window.YTD` javascript payloads and reddit csv bundles also pass through family-aware adapters instead of the raw fallback lane.

that normalization layer also now discovers linked media attachments generically. when a supported export references local media, the parent source can carry attachment metadata, local OCR text, and optional raw image input into the same extraction request instead of losing the relationship between the text and the media. when the source text itself includes eligible remote media URLs, the same attachment lane can now recover transcript-like text through `summarize` without replacing the original export record.

for google takeout specifically, the parser is no longer limited to a generic text wrapper. youtube subscription, comment, and video metadata csvs are now turned into cleaner row-oriented records, broad google json exports such as profile and chrome history are summarized into structured blocks, calendar `.ics` exports become event records, and gmail `.mbox` dumps are compacted into per-message blocks with headers plus body snippets. that is still not the same thing as a perfect first-party schema adapter for every google product, but it is materially better than treating the whole export as opaque text.

the ingest side also writes manifests and live progress state with family and subproduct counts. that means a long-running scan can be inspected as "twitter archive direct-messages" or "instagram export messages" instead of just "generic text files", and discovery works without requiring backend auth so you can classify an archive before spending any model quota.

directory ingests now also keep a persistent run-state file under `state/ingest-runs/`. if a long scan stops because the backend hits quota or cooldown, the next `ingest-dir` run can fast-resume already completed materials instead of re-parsing and re-extracting them from zero. the immutable manifest snapshots in `state/manifests/` still record what each individual run did, while the resumable state is the mutable operator-facing checkpoint.

if you temporarily run different backend/model lanes in separate project roots, merge the completed source evidence back into the canonical project instead of comparing two final skill tables by hand:

```bash
traccia merge-project /path/to/other-traccia-project --project-root /path/to/canonical-project
```

`merge-project` imports source, span, and evidence records, then rebuilds the target graph by default. it intentionally does not import the other project's final skill rows or extraction checkpoints, because skills are derived from evidence and checkpoints are only safe inside the exact run that created them. use `--no-rebuild` when the target project is actively ingesting and should pick up the imported evidence at its next normal graph refresh.

long directory runs still checkpoint raw ingest state after each material, but live graph refreshes are disabled by default. that keeps crash recovery file-granular while spending model quota on extracting new evidence instead of repeatedly rescoring nearly identical intermediate graphs. tune this under `graph_refresh` in `config.yaml` if you want opt-in live checkpoints; the default is final-only graph sync. parsed files that produce no evidence still resume correctly, and final output semantics are unchanged because the final graph is derived from the stored evidence table.

the batch is not a summarization boundary. each material is still parsed independently, materials are kept whole when they fit the extraction budget, oversized materials are extracted chunk by chunk, and every accepted evidence item is stored separately in SQLite with its source, span, quote, candidate skills, confidence, and timestamps. agent-log parsed artifacts keep assistant, tool, system, and thinking spans for audit, but extraction only receives user/human/developer spans so model output is not re-attributed as user skill. graph recompute then loads the stored evidence table and compares candidate skills against the existing catalog. that means delayed graph refreshes should not lose per-file or per-chunk information; they only delay when the rendered graph catches up.

each render also now writes a post-run debug bundle under `exports/debug/`. `report.json` is the machine-readable artifact, while `report.md` is the human-readable summary. they include source counts, parser and family breakdowns, attachment counts, evidence distributions, top skills, and pointers to the latest ingest progress, manifest, and resumable run-state files. if you want to regenerate that after review actions or a manual graph rebuild, run `traccia export debug-report`.

the rendering side produces markdown node pages, profile exports, `graph.json`, `tree.json`, an ascii tree, and an obsidian vault export with actual note generation instead of a dead folder dump.

## input surface

`traccia` is aimed at mixed personal archives, not just project repos. the current input shape looks like this:

| source class | examples | current treatment |
| --- | --- | --- |
| authored material | markdown, plain text, docs, notes, READMEs | parsed directly and cited back with spans where possible |
| code and technical artifacts | python, js, ts, tsx, rust, go, sql | treated as stronger evidence when they show actual implementation work |
| structured exports | json, csv, pdf, docx | parsed into document records and evidence candidates, with local markdown normalization for documents when optional providers are installed |
| activity exports | AI conversation JSON, reddit JSON, google activity JSON | normalized into a common structure before evidence extraction |
| broader archive direction | social profiles, issue trackers, twitter or x exports, more takeout-style dumps | explicitly in scope for future expansion, but not all implemented yet |

the intended archive boundary is wider than the current parser list. the system is meant to grow toward bigger archive imports without treating every interaction as equal proof of competence.

in practice the ingest model is hybrid. major export families get explicit adapters where the raw provider format is especially bad for downstream extraction, and everything else still gets ingested one file at a time through the generic parser path. that keeps the pipeline open-ended without pretending every export structure deserves identical handling.

## output surface

after ingest, `traccia` renders a graph plus several practical projections around it:

| artifact | purpose |
| --- | --- |
| `tree/index.md` | top-level skill tree snapshot |
| `tree/nodes/*.md` | per-skill pages with evidence, timestamps, related skills, and reasoning |
| `tree/log.md` | render log and longitudinal notes |
| `graph/graph.json` | full graph export for tooling, including per-node evidence provenance |
| `graph/tree.json` | simplified tree projection |
| `profile/skill.md` | profile-style summary built from the graph |
| `exports/obsidian/` | obsidian-friendly note graph export |

each skill node is meant to answer the questions that normal profile tools dodge. where does this skill fit. what evidence supports it. which source file did that evidence come from. how deep does the work look. how current is it. when did it first show up. when does it look learned rather than merely noticed. when was there strong enough evidence to trust it. how tightly does it connect back into the rest of the self-model.

`graph/graph.json` carries this as a compact `provenance` array on each node. by default it keeps full source paths redacted, but still exposes source IDs, filenames, parser/source-family metadata, evidence IDs, timestamps, evidence types, confidence, and redacted excerpts. set `privacy.redact_source_paths_in_exports: false` if you want exported graph nodes to include `uri` and `relativeImportPath` as well.

## scoring stance

`traccia` keeps current mastery and core-self centrality separate on purpose. those are related, but they are not the same thing. a skill can be central because it keeps showing up across the archive while still being shallow. another skill can be deep but narrow because it only appears in one intense period of work.

that separation matters once you ingest noisy exports. searches, follows, bios, bookmarks, lightweight chats, and stray mentions can support interest, context, or identity. on their own they should not inflate mastery. the system is designed to preserve those lighter signals without letting them pretend to be authored work or repeat implementation evidence.

## command surface

the full command list lives behind `traccia --help`, but the current working surface is already broad enough to use day to day:

| command | use |
| --- | --- |
| `traccia init` | scaffold a new project |
| `traccia doctor` | verify the scaffold and backend config |
| `traccia discover-dir` | classify a directory before ingest and show family/subproduct counts |
| `traccia ingest` / `traccia ingest-dir` | import files into the graph pipeline |
| `traccia score` | update graph scoring with `incremental` or `full` mode |
| `traccia merge-project` | merge source/evidence records from another project into one canonical graph |
| `traccia rebuild` | recompute the graph from stored material |
| `traccia tree` | print the current tree |
| `traccia explain` / `traccia why` | inspect one skill node |
| `traccia evidence` | list evidence connected to a skill |
| `traccia review` | process uncertain graph changes |
| `traccia alias` | manage canonical aliases |
| `traccia export ...` | write graph, profile, markdown, and obsidian projections |

## repo map

| path | purpose |
| --- | --- |
| `docs/spec.md` | product and architecture spec |
| `docs/plan.md` | implementation plan and phase boundaries |
| `docs/decisions.md` | decisions and research conclusions |
| `docs/ingest-architecture.md` | source-family ingest, checkpoint, and graph-refresh contract |
| `docs/architecture-notes.md` | scoring, persistence, and high-risk module notes |
| `docs/references.md` | inspirations and anti-references |
| `src/traccia/` | implementation |
| `tests/` | fixtures and regression coverage |

## verification

the current repo verification path is:

```bash
uv run ruff check src tests
uv run pytest -q
uv build
```

the live external backend path still depends on real credentials and a reachable compatible endpoint. nothing in this README assumes OpenAI specifically. it assumes an OpenAI-style contract.

## automation

github actions now handle the basic release path for the repo. pushes and pull requests run lint, tests, package builds, and a CLI smoke check. version tags matching `v*` build release artifacts and attach them to a github release. pypi publishing is wired for trusted publishing as an opt-in path, and only runs when the repository variable `PYPI_PUBLISH=true` is set and the repository has been registered as a trusted publisher on pypi.
## license

mit
