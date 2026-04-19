import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

from typer.testing import CliRunner

from traccia.cli import app
from traccia.config import TracciaConfig, load_config
from traccia.llm import CanonicalizationRequest, OpenAICompatibleBackend, ScoringRequest
from traccia.models import EvidenceItem
from traccia.pipeline_support import build_skill_node


def test_init_creates_phase_zero_layout(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["init", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "config" / "config.yaml").exists()
    assert (tmp_path / "config" / "prompts" / "extract_evidence.md").exists()
    assert (tmp_path / "state" / "catalog.sqlite").exists()
    assert (tmp_path / "state" / "review_queue.jsonl").exists()
    assert (tmp_path / "tree" / "index.md").exists()
    assert (tmp_path / "tree" / "log.md").exists()
    assert (tmp_path / "graph" / "graph.json").exists()
    assert (tmp_path / "graph" / "tree.json").exists()
    assert (tmp_path / "CLAUDE.md").exists()

    config = load_config(tmp_path / "config" / "config.yaml")
    assert config.project_name == "traccia"
    assert config.thresholds.consumption_max_level == 2


def test_help_lists_phase_zero_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "lint" in result.stdout
    assert "doctor" in result.stdout
    assert "review" in result.stdout


def test_init_preserves_existing_config_without_force(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "config" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("schema_version: 1\nproject_name: keep-me\n")

    result = runner.invoke(app, ["init", str(tmp_path)])

    assert result.exit_code == 0
    assert load_config(config_path).project_name == "keep-me"


def test_doctor_reports_backend_state_without_failing_for_missing_auth(tmp_path: Path) -> None:
    runner = CliRunner()
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0, init_result.stdout

    result = runner.invoke(app, ["doctor", str(tmp_path)])

    assert result.exit_code == 0, result.stdout
    assert "backend:" in result.stdout
    assert "backend auth: missing env var OPENAI_API_KEY" in result.stdout
    assert "Phase 0 scaffold looks healthy." in result.stdout


def test_doctor_check_backend_requires_auth_for_live_provider(tmp_path: Path) -> None:
    runner = CliRunner()
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0, init_result.stdout

    result = runner.invoke(app, ["doctor", str(tmp_path), "--check-backend"])

    assert result.exit_code == 1
    assert "backend auth: missing env var OPENAI_API_KEY" in result.stdout


def test_openai_compatible_backend_uses_openai_style_http_contract(monkeypatch) -> None:
    requests: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/models":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"data": [{"id": "stub-model"}]}).encode("utf-8"))

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/chat/completions":
                self.send_error(404)
                return
            content_length = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            requests.append(payload)
            response = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "level": 3,
                                    "confidence": 0.88,
                                    "recency_score": 0.7,
                                    "breadth_score": 0.4,
                                    "depth_score": 0.8,
                                    "artifact_score": 0.6,
                                    "teaching_score": 0.2,
                                    "freshness": "active",
                                    "status": "active",
                                    "manual_note": None,
                                    "rationale": "stubbed response",
                                }
                            )
                        }
                    }
                ]
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            del format, args

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        monkeypatch.setenv("TEST_OPENAI_COMPATIBLE_KEY", "test-key")
        config = TracciaConfig.model_validate(
            {
                "project_name": "fixture-traccia",
                "backend": {
                    "provider": "openai_compatible",
                    "model": "stub-model",
                    "api_key_env": "TEST_OPENAI_COMPATIBLE_KEY",
                    "base_url": f"http://127.0.0.1:{server.server_port}",
                    "api_style": "chat_completions",
                    "structured_output_mode": "json_schema",
                    "timeout_seconds": 5,
                    "max_retries": 1,
                },
            }
        )
        backend = OpenAICompatibleBackend(config)
        payload = backend.score_skill(
            prompt="Return a score payload.",
            request=ScoringRequest(
                skill=build_skill_node("Python"),
                evidence_items=[
                    EvidenceItem.model_validate(
                        {
                            "evidence_id": "ev_python",
                            "source_id": "src_python",
                            "span_start": 0,
                            "span_end": 10,
                            "quote": "Built a Python CLI.",
                            "evidence_type": "implemented",
                            "signal_class": "artifact_backed_work",
                            "skill_candidates": ["Python"],
                            "artifact_candidates": [],
                            "time_reference": "2026-04-01",
                            "reliability": "tier_a",
                            "extractor_version": "phase-0",
                            "confidence": 0.9,
                        }
                    )
                ],
                thresholds={"consumption_max_level": 2},
                locked=False,
                hidden=False,
            ),
        )

        assert payload.level == 3
        assert backend.healthcheck() == "backend reachable, models=1"
        assert requests[0]["response_format"]["type"] == "json_schema"
        assert requests[0]["messages"][0]["role"] == "system"
    finally:
        server.shutdown()
        thread.join(timeout=5)
