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
traccia viewer --project-root my-traccia
```

`traccia viewer` prints the `file://` URI for the generated static viewer. It does not
start a web server; regenerate the viewer with `traccia render` or any ingest command
that refreshes projections.

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
| remote media enrichment | on | detects eligible remote media URLs in source text and tries to recover transcript-like text with `summarize --extract`, mainly for youtube and direct audio or video links |
| raw vision to the LLM | off | sends the actual image bytes to the backend only when you explicitly enable vision and mark the backend as vision-capable |

that split is deliberate. OpenAI-style endpoint compatibility does not guarantee that a model or proxy really supports multimodal image input. `traccia` therefore keeps the context-preserving attachment path on by default, while the raw image lane stays opt-in.

the remote URL lane is deliberately narrower than "summarize every link". for now it only targets media-shaped URLs where transcript recovery materially improves evidence quality without replacing the original source record. a youtube watch URL inside a google activity export is a good example. a random article URL is not.

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
  max_attachments_per_source: 4
  max_attachment_text_characters: 1200
  max_attachment_transcript_characters: 8000
  max_image_bytes: 5000000
  ocr_timeout_seconds: 20
  transcription_timeout_seconds: 1800
  remote_media_enrichment_timeout_seconds: 180
```

in practice, `enable_linked_attachments: true` should stay on unless you explicitly want text-only parsing. `enable_vision: true` should only be enabled when the chosen backend model and proxy actually accept image inputs, and `backend.supports_vision: true` should only be marked on for those known-good multimodal endpoints.

`enable_local_image_ocr: true` keeps free local attachment text extraction available even with vision disabled. `enable_local_media_transcription: true` keeps local transcripts available for attached audio and video files. `audio_transcription_provider: auto` currently means "use local `whisper` when it exists, otherwise skip transcription cleanly", and `ffmpeg` is still the local preprocessing step that strips or normalizes audio before transcription.

`enable_remote_media_enrichment: true` enables the new `summarize` lane for remote media URLs that are found inline in the source text. the default command is `summarize`, but `remote_media_enrichment_command` can point at another binary path if you keep it somewhere custom. disabling that flag leaves the original URLs in the source text but stops the extra transcript recovery pass.

with that setup, a post plus its screenshot, photo, chart, or attached image can be analyzed together without forcing every backend into a vision-only contract.

audio and video attachments now follow the same principle. if a source references a local clip, `traccia` can extract a local transcript and attach it back to the parent source context instead of treating the clip as a detached second-class file. that keeps the text post, the media metadata, and the recovered speech in one extraction bundle. if the source instead carries a remote youtube or direct media URL, `traccia` can now recover transcript-like text through `summarize --extract` and keep that alongside the original source event instead of flattening the whole thing into an ungrounded summary.

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

the ingest side also writes manifests and live progress state with family and subproduct counts. that means a long-running scan can be inspected as “twitter archive direct-messages” or “instagram export messages” instead of just “generic text files”, and discovery works without requiring backend auth so you can classify an archive before spending any model quota.

directory ingests now also keep a persistent run-state file under `state/ingest-runs/`. if a long scan stops because the backend hits quota or cooldown, the next `ingest-dir` run can fast-resume already completed materials instead of re-parsing and re-extracting them from zero. the immutable manifest snapshots in `state/manifests/` still record what each individual run did, while the resumable state is the mutable operator-facing checkpoint.

long directory runs still checkpoint raw ingest state after each material, but live graph refreshes are batched by default. that keeps crash recovery file-granular while spending model quota on extracting new evidence instead of repeatedly rescoring nearly identical intermediate graphs. tune this under `graph_refresh` in `config.yaml`; the default updates small runs immediately and large runs every 25 newly processed materials or at the final graph sync.

the batch is not a summarization boundary. each material is still parsed independently, large materials are extracted chunk by chunk, and every accepted evidence item is stored separately in SQLite with its source, span, quote, candidate skills, confidence, and timestamps. graph recompute then loads the stored evidence table and compares candidate skills against the existing catalog. that means delayed graph refreshes should not lose per-file or per-chunk information; they only delay when the rendered graph catches up.

each render also now writes a post-run debug bundle under `exports/debug/`. `report.json` is the machine-readable artifact, while `report.md` is the human-readable summary. they include source counts, parser and family breakdowns, attachment counts, evidence distributions, top skills, and pointers to the latest ingest progress, manifest, and resumable run-state files. if you want to regenerate that after review actions or a manual graph rebuild, run `traccia export debug-report`.

the rendering side produces markdown node pages, profile exports, `graph.json`, `tree.json`, an ascii tree, a local static viewer, and an obsidian vault export with actual note generation instead of a dead folder dump.

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
| `viewer/index.html` | local static viewer |
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
| `traccia rebuild` | recompute the graph from stored material |
| `traccia tree` | print the current tree |
| `traccia explain` / `traccia why` | inspect one skill node |
| `traccia evidence` | list evidence connected to a skill |
| `traccia review` | process uncertain graph changes |
| `traccia alias` | manage canonical aliases |
| `traccia export ...` | write graph, profile, markdown, and obsidian projections |
| `traccia viewer` | print the generated static viewer URI |

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
