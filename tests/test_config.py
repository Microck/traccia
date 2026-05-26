from __future__ import annotations

from traccia.config import ExtractionBackendConfig, default_config, dump_config_text, load_config


def test_config_round_trip_preserves_defaults(tmp_path) -> None:
    config = default_config(project_name="roundtrip")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(dump_config_text(config), encoding="utf-8")

    loaded = load_config(config_path)

    assert loaded == config
    assert loaded.project_name == "roundtrip"


def test_graph_refresh_defaults_match_large_ingest_policy() -> None:
    config = default_config()

    assert config.graph_refresh.live_checkpoints_enabled is False
    assert config.graph_refresh.live_checkpoint_material_interval == 25
    assert config.graph_refresh.live_checkpoint_min_interval_seconds == 1800.0
    assert config.graph_refresh.small_run_live_checkpoint_material_limit == 10


def test_ingest_defaults_keep_extraction_serial() -> None:
    config = default_config()

    assert config.ingest.parallel_extractions == 1


def test_graph_scoring_defaults_keep_skill_scoring_serial() -> None:
    config = default_config()

    assert config.graph_scoring.parallel_scores == 1


def test_extraction_backend_pool_round_trips(tmp_path) -> None:
    config = default_config()
    config.graph_scoring.parallel_scores = 4
    config.backend.extraction_backends = [
        ExtractionBackendConfig(
            name="glm",
            model="glm-5-turbo",
            api_key_env="CLIPROXYAPI_KEY",
            base_url="http://127.0.0.1:8317/v1",
            parallel_extractions=5,
        ),
        ExtractionBackendConfig(
            name="gemini",
            model="star-gemini-3.5-flash",
            api_key_env="CLIPROXYAPI_KEY",
            base_url="http://127.0.0.1:8317/v1",
            parallel_extractions=3,
        ),
    ]

    config_path_text = dump_config_text(config)
    loaded_path = tmp_path / "config.yaml"
    loaded_path.write_text(config_path_text, encoding="utf-8")
    loaded = load_config(loaded_path)

    assert [lane.name for lane in loaded.backend.extraction_backends] == ["glm", "gemini"]
    assert sum(lane.parallel_extractions for lane in loaded.backend.extraction_backends) == 8
    assert loaded.graph_scoring.parallel_scores == 4


def test_remote_media_enrichment_defaults_to_visual_youtube_context() -> None:
    config = default_config()

    assert config.multimodal.enable_remote_media_enrichment is True
    assert config.multimodal.remote_media_enrichment_command == "summarize"
    assert config.multimodal.remote_media_enrichment_video_mode == "understand"
    assert config.multimodal.enable_remote_media_slides is True
    assert config.multimodal.enable_remote_media_slides_ocr is True
