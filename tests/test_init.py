import json
import os
import stat
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from typer.testing import CliRunner

import traccia.llm as llm_module
from traccia.cli import app
from traccia.config import TracciaConfig, load_config
from traccia.llm import OpenAICompatibleBackend, ScoringRequest
from traccia.models import EvidenceItem
from traccia.pipeline_support import build_skill_node


def _local_ingest_loop_script() -> Path:
    runner_script = Path(__file__).resolve().parents[1] / "scripts" / "traccia-ingest-loop.sh"
    if not runner_script.exists():
        pytest.skip("local-only ingest loop runner script is not tracked in the public repo")
    return runner_script


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
    assert config.document_normalization.provider == "auto"
    assert config.document_normalization.ocr_provider == "auto"


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
    assert "document normalization:" in result.stdout
    assert "image OCR" in result.stdout
    assert "media transcription" in result.stdout
    assert "remote media enrichment" in result.stdout
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


def test_openai_compatible_backend_repairs_invalid_json_escapes(monkeypatch) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/chat/completions":
                self.send_error(404)
                return
            content = (
                '{"level": 3, "confidence": 0.88, "recency_score": 0.7, "breadth_score": 0.4, '
                '"depth_score": 0.8, "artifact_score": 0.6, "teaching_score": 0.2, '
                '"freshness": "active", "status": "active", "manual_note": null, '
                '"rationale": "Recovered path C:\\Users\\alice"}'
            )
            response = {"choices": [{"message": {"content": content}}]}
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
        assert "C:\\Users\\alice" in payload.rationale
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_traccia_ingest_loop_honors_long_backend_cooldown_window(tmp_path: Path) -> None:
    runner_script = _local_ingest_loop_script()
    project_root = tmp_path / "project"
    input_root = tmp_path / "input"
    fake_bin = tmp_path / "bin"
    sleep_record = tmp_path / "sleep-seconds.txt"
    runner_env = project_root / "state" / "runner.env"

    project_root.mkdir()
    input_root.mkdir()
    fake_bin.mkdir()
    runner_env.parent.mkdir(parents=True)
    runner_env.write_text("export CLIPROXYAPI_KEY=test-key\n")

    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "cat <<'EOF'",
                "BackendError: LLM backend request failed (429):",
                '{"error":{"code":"model_cooldown","message":"All credentials for model star-gemini-3-flash are cooling down via provider star-gemini-bridge","model":"star-gemini-3-flash","provider":"star-gemini-bridge","reset_seconds":1781,"reset_time":"29m41s"}}',
                "EOF",
                "exit 1",
                "",
            ]
        )
    )
    fake_uv.chmod(fake_uv.stat().st_mode | stat.S_IEXEC)

    fake_sleep = fake_bin / "sleep"
    fake_sleep.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                f"printf '%s' \"$1\" > {sleep_record}",
                "exit 99",
                "",
            ]
        )
    )
    fake_sleep.chmod(fake_sleep.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["CLIPROXYAPI_KEY"] = "test-key"
    env["UV_BIN"] = str(fake_uv)
    env["TRACCIA_GLM_LOCK_PATH"] = str(tmp_path / "glm.lock")
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    completed = subprocess.run(
        [str(runner_script), str(input_root), str(project_root), str(runner_env)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 99
    assert sleep_record.read_text() == "1781"
    log_text = (project_root / "runner.log").read_text()
    assert "cooldown detected from backend output" in log_text
    assert "sleeping 1781s before retry" in log_text


def test_traccia_ingest_loop_honors_wrapped_reset_seconds_from_log_output(tmp_path: Path) -> None:
    runner_script = _local_ingest_loop_script()
    project_root = tmp_path / "project"
    input_root = tmp_path / "input"
    fake_bin = tmp_path / "bin"
    sleep_record = tmp_path / "sleep-seconds.txt"
    runner_env = project_root / "state" / "runner.env"

    project_root.mkdir()
    input_root.mkdir()
    fake_bin.mkdir()
    runner_env.parent.mkdir(parents=True)
    runner_env.write_text("export CLIPROXYAPI_KEY=test-key\n")

    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "cat <<'EOF'",
                "BackendError: LLM backend request failed (429): ",
                '{"error":{"code":"model_cooldown","message":"All credentials for model ',
                "star-gemini-3-flash are cooling down via provider ",
                'star-gemini-bridge","model":"star-gemini-3-flash","provider":"star-gemini-bridge","rese',
                't_seconds":973,"reset_time":"16m13s"}}',
                "EOF",
                "exit 1",
                "",
            ]
        )
    )
    fake_uv.chmod(fake_uv.stat().st_mode | stat.S_IEXEC)

    fake_sleep = fake_bin / "sleep"
    fake_sleep.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                f"printf '%s' \"$1\" > {sleep_record}",
                "exit 99",
                "",
            ]
        )
    )
    fake_sleep.chmod(fake_sleep.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["CLIPROXYAPI_KEY"] = "test-key"
    env["UV_BIN"] = str(fake_uv)
    env["TRACCIA_GLM_LOCK_PATH"] = str(tmp_path / "glm.lock")
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    completed = subprocess.run(
        [str(runner_script), str(input_root), str(project_root), str(runner_env)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 99
    assert sleep_record.read_text() == "973"
    log_text = (project_root / "runner.log").read_text()
    assert "cooldown detected from backend output" in log_text
    assert "sleeping 973s before retry" in log_text


def test_traccia_ingest_loop_honors_gemini_human_quota_reset_duration(tmp_path: Path) -> None:
    runner_script = _local_ingest_loop_script()
    project_root = tmp_path / "project"
    input_root = tmp_path / "input"
    fake_bin = tmp_path / "bin"
    sleep_record = tmp_path / "sleep-seconds.txt"
    runner_env = project_root / "state" / "runner.env"

    project_root.mkdir()
    input_root.mkdir()
    fake_bin.mkdir()
    runner_env.parent.mkdir(parents=True)
    runner_env.write_text("export CLIPROXYAPI_KEY=test-key\n")

    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "cat <<'EOF'",
                'BackendError: LLM backend request failed (502): {"error":{"message":"All providers failed for model \\"gemini-3-flash\\". Last error: You have exhausted your capacity on this model. Your quota will reset after',
                '9h40m8s.","type":"provider_error","param":null,"code":"provider_error"}}',
                "EOF",
                "exit 1",
                "",
            ]
        )
    )
    fake_uv.chmod(fake_uv.stat().st_mode | stat.S_IEXEC)

    fake_sleep = fake_bin / "sleep"
    fake_sleep.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                f"printf '%s' \"$1\" > {sleep_record}",
                "exit 99",
                "",
            ]
        )
    )
    fake_sleep.chmod(fake_sleep.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["CLIPROXYAPI_KEY"] = "test-key"
    env["UV_BIN"] = str(fake_uv)
    env["TRACCIA_GLM_LOCK_PATH"] = str(tmp_path / "glm.lock")
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    completed = subprocess.run(
        [str(runner_script), str(input_root), str(project_root), str(runner_env)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 99
    assert sleep_record.read_text() == "34808"
    log_text = (project_root / "runner.log").read_text()
    assert "cooldown detected from backend output" in log_text
    assert "sleeping 34808s before retry" in log_text


def test_openai_compatible_backend_uses_full_validation_retry_budget(monkeypatch) -> None:
    attempts = {"count": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/chat/completions":
                self.send_error(404)
                return
            attempts["count"] += 1
            if attempts["count"] < 3:
                content = "{ definitely not valid json }"
            else:
                content = json.dumps(
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
                        "rationale": "recovered on retry",
                    }
                )
            response = {"choices": [{"message": {"content": content}}]}
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
                    "max_retries": 3,
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

        assert payload.rationale == "recovered on retry"
        assert attempts["count"] == 3
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_openai_compatible_backend_uses_longer_backoff_for_auth_unavailable(monkeypatch) -> None:
    attempts = {"count": 0}
    sleep_calls: list[float] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/chat/completions":
                self.send_error(404)
                return
            attempts["count"] += 1
            if attempts["count"] < 3:
                body = {
                    "error": {
                        "message": "auth_unavailable: no auth available (providers=star-gemini-bridge, model=star-gemini-3-flash)",
                        "type": "server_error",
                        "code": "internal_server_error",
                    }
                }
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode("utf-8"))
                return

            content = json.dumps(
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
                    "rationale": "recovered after auth retry",
                }
            )
            response = {"choices": [{"message": {"content": content}}]}
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
        monkeypatch.setattr(llm_module.time, "sleep", sleep_calls.append)
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
                    "max_retries": 3,
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

        assert payload.rationale == "recovered after auth retry"
        backend_retry_sleeps = [duration for duration in sleep_calls if duration >= 0.5]
        assert backend_retry_sleeps[:2] == [5.0, 10.0]
    finally:
        server.shutdown()
        thread.join(timeout=5)
