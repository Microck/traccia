from __future__ import annotations

from traccia.config import default_config, dump_config_text, load_config


def test_config_round_trip_preserves_defaults(tmp_path) -> None:
    config = default_config(project_name="roundtrip")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(dump_config_text(config), encoding="utf-8")

    loaded = load_config(config_path)

    assert loaded == config
    assert loaded.project_name == "roundtrip"


def test_graph_refresh_defaults_match_large_ingest_policy() -> None:
    config = default_config()

    assert config.graph_refresh.live_checkpoint_material_interval == 25
    assert config.graph_refresh.live_checkpoint_min_interval_seconds == 1800.0
    assert config.graph_refresh.small_run_live_checkpoint_material_limit == 10
