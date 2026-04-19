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
    model: str = "gpt-4o-2024-08-06"
    api_key_env: str = "OPENAI_API_KEY"
    base_url: str = "https://api.openai.com/v1"
    api_style: str = "chat_completions"
    structured_output_mode: str = "json_schema"
    timeout_seconds: int = 60
    max_retries: int = 3


class TracciaConfig(TracciaModel):
    schema_version: int = 1
    project_name: str = "traccia"
    paths: TracciaPaths = Field(default_factory=TracciaPaths)
    pipeline: PipelineVersions = Field(default_factory=PipelineVersions)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    rendering: RenderingConfig = Field(default_factory=RenderingConfig)
    backend: BackendConfig = Field(default_factory=BackendConfig)


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
