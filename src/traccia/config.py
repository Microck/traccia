from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field

from traccia.models import Sensitivity, TracciaModel


class TracciaPaths(TracciaModel):
    raw_inbox: str = "raw/inbox"
    raw_imported: str = "raw/imported"
    parsed: str = "parsed"
    evidence: str = "evidence"
    graph: str = "graph"
    viewer: str = "viewer"
    tree: str = "tree"
    profile: str = "profile"
    state: str = "state"
    exports: str = "exports"


class PipelineVersions(TracciaModel):
    parser_version: str = "phase-0"
    extractor_version: str = "phase-0"
    canonicalizer_version: str = "phase-0"
    scorer_version: str = "phase-0"
    renderer_version: str = "phase-0"


class GraphRefreshConfig(TracciaModel):
    live_checkpoint_material_interval: int = Field(default=25, ge=1)
    live_checkpoint_min_interval_seconds: float = Field(default=1800.0, ge=0.0)
    small_run_live_checkpoint_material_limit: int = Field(default=10, ge=0)


class ThresholdConfig(TracciaModel):
    strong_evidence_auto_create: float = Field(default=0.85, ge=0.0, le=1.0)
    review_confidence_floor: float = Field(default=0.6, ge=0.0, le=1.0)
    consumption_max_level: int = Field(default=2, ge=0, le=5)


class PrivacyConfig(TracciaModel):
    default_sensitivity: Sensitivity = Sensitivity.PRIVATE
    redact_source_paths_in_exports: bool = True
    allow_raw_excerpt_export: bool = False


class RenderingConfig(TracciaModel):
    default_tree_format: str = "ascii"
    enable_obsidian_export: bool = True
    enable_viewer_bundle: bool = True


class BackendConfig(TracciaModel):
    provider: str = "openai_compatible"
    model: str = "gpt-5-chat-latest"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1"
    api_style: str = "chat_completions"
    structured_output_mode: str = "json_schema"
    supports_vision: bool = False
    vision_detail: str = "auto"
    timeout_seconds: int = 60
    max_retries: int = 3


class DocumentNormalizationConfig(TracciaModel):
    provider: str = "auto"
    ocr_provider: str = "auto"


class MultimodalConfig(TracciaModel):
    enable_linked_attachments: bool = True
    enable_vision: bool = False
    enable_local_image_ocr: bool = True
    enable_local_media_transcription: bool = True
    enable_remote_media_enrichment: bool = True
    audio_transcription_provider: str = "auto"
    audio_transcription_model: str = "turbo"
    audio_transcription_device: str = "cpu"
    remote_media_enrichment_command: str = "summarize"
    max_attachments_per_source: int = Field(default=4, ge=0, le=32)
    max_attachment_text_characters: int = Field(default=1200, ge=0, le=20000)
    max_attachment_transcript_characters: int = Field(default=8000, ge=0, le=100000)
    max_image_bytes: int = Field(default=5_000_000, ge=1024)
    ocr_timeout_seconds: int = Field(default=20, ge=1, le=300)
    transcription_timeout_seconds: int = Field(default=1800, ge=30, le=14_400)
    remote_media_enrichment_timeout_seconds: int = Field(default=180, ge=10, le=3600)


class TracciaConfig(TracciaModel):
    schema_version: int = 1
    project_name: str = "traccia"
    paths: TracciaPaths = Field(default_factory=TracciaPaths)
    pipeline: PipelineVersions = Field(default_factory=PipelineVersions)
    graph_refresh: GraphRefreshConfig = Field(default_factory=GraphRefreshConfig)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    rendering: RenderingConfig = Field(default_factory=RenderingConfig)
    backend: BackendConfig = Field(default_factory=BackendConfig)
    document_normalization: DocumentNormalizationConfig = Field(
        default_factory=DocumentNormalizationConfig
    )
    multimodal: MultimodalConfig = Field(default_factory=MultimodalConfig)


def default_config(project_name: str = "traccia") -> TracciaConfig:
    return TracciaConfig(project_name=project_name)


def dump_config_text(config: TracciaConfig) -> str:
    data = config.model_dump(mode="json")
    return yaml.safe_dump(data, sort_keys=False)


def write_config(path: Path, config: TracciaConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_config_text(config))


def load_config(path: Path) -> TracciaConfig:
    raw_config = yaml.safe_load(path.read_text()) or {}
    return TracciaConfig.model_validate(raw_config)
