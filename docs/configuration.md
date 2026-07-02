# Configuration Reference

Project configuration lives at `config/config.yaml` inside a Traccia project.
The schema is defined in `src/traccia/config.py` and validated by Pydantic.

Run validation with:

```bash
traccia lint my-traccia
traccia doctor my-traccia
```

## Core Fields

| Field | Default | Meaning |
| --- | --- | --- |
| `schema_version` | `1` | Config schema version. |
| `project_name` | `traccia` | Display name for the project. |
| `paths` | see below | Project directory names. |
| `pipeline` | `phase-0` versions | Parser, extractor, canonicalizer, scorer, and renderer versions. |

Default paths:

```yaml
paths:
  raw_inbox: raw/inbox
  raw_imported: raw/imported
  parsed: parsed
  evidence: evidence
  graph: graph
  tree: tree
  profile: profile
  state: state
  exports: exports
```

## Backend

The default backend is an OpenAI-compatible chat completions endpoint:

```yaml
backend:
  provider: openai_compatible
  model: gpt-5-chat-latest
  api_key_env: OPENAI_API_KEY
  base_url: https://api.openai.com/v1
  api_style: chat_completions
  structured_output_mode: json_schema
  supports_vision: false
  vision_detail: auto
  timeout_seconds: 60
  max_retries: 3
```

For deterministic tests:

```yaml
backend:
  provider: fake
```

## Extraction Lane Pool

Use `backend.extraction_backends` when evidence extraction should use multiple
OpenAI-style backends while canonicalization and scoring stay on the primary
backend.

```yaml
backend:
  provider: openai_compatible
  model: glm-5-turbo
  api_key_env: CLIPROXYAPI_KEY
  base_url: http://127.0.0.1:8317/v1
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

## Ingest And Scoring

```yaml
ingest:
  parallel_extractions: 1

graph_scoring:
  parallel_scores: 1

graph_refresh:
  live_checkpoints_enabled: false
  live_checkpoint_material_interval: 25
  live_checkpoint_min_interval_seconds: 1800.0
  small_run_live_checkpoint_material_limit: 10
```

`parallel_extractions` controls material-level evidence extraction inside one
ingest process. `parallel_scores` controls final per-skill scoring. Discovery,
manifest writes, graph cache writes, progress writes, and final rendering stay
parent-side serialized.

## Thresholds

```yaml
thresholds:
  strong_evidence_auto_create: 0.85
  review_confidence_floor: 0.6
  consumption_max_level: 2
```

Consumption-led evidence can show awareness or study, but it cannot push a skill
beyond the configured maximum without stronger action evidence.

## Privacy

```yaml
privacy:
  default_sensitivity: private
  redact_source_paths_in_exports: true
  allow_raw_excerpt_export: false
```

The defaults avoid raw paths and raw excerpts in rendered exports. The public
publish export applies stronger filtering and writes a separate redacted bundle.

## Document Normalization

```yaml
document_normalization:
  provider: auto
  ocr_provider: auto
```

PDF and DOCX inputs pass through document normalization. Optional extras add
heavier local providers:

```bash
uv sync --extra docling
uv sync --extra marker
uv sync --extra document-markdown
```

## Multimodal

```yaml
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

If image context requires vision and the active backend does not support it,
Traccia delays the material rather than silently treating OCR-only text as
equivalent.

## Google Takeout

```yaml
google_takeout:
  relevance_mode: skill_relevant
  gmail_mode: metadata_plus_sent
  youtube_enrichment: detailed
  photos_mode: fast_vision
  drive_mode: selective_docs
  max_photo_vision_samples_per_folder: 8
```

The Google Takeout policy is deterministic and runs before model calls. It is
designed to keep zero-value account metadata, caches, raw binaries, sidecars,
and bulk runtime data from spending model quota.
