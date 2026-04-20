from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = REPO_ROOT / "npm" / "bin" / "traccia.js"


def _require_node() -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required to test the npm wrapper")
    return node


def _write_fake_command(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        "pathlib.Path(os.environ['TRACE_FILE']).write_text("
        "json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd()}))\n"
        "raise SystemExit(int(os.environ.get('FAKE_EXIT_CODE', '0')))\n"
    )
    path.chmod(0o755)


def _run_wrapper(
    tmp_path: Path,
    command_name: str,
    *,
    args: list[str],
    extra_env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    _write_fake_command(fake_bin_dir / command_name)
    trace_file = tmp_path / "trace.json"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{env['PATH']}"
    env["TRACE_FILE"] = str(trace_file)
    if extra_env:
        env.update(extra_env)

    completed = subprocess.run(
        [_require_node(), str(WRAPPER_PATH), *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    return completed, json.loads(trace_file.read_text())


def test_npm_wrapper_uses_uvx_by_default(tmp_path: Path) -> None:
    completed, trace = _run_wrapper(tmp_path, "uvx", args=["doctor", "."])

    assert completed.returncode == 0
    assert trace["argv"] == ["--from", "traccia", "traccia", "doctor", "."]


def test_npm_wrapper_allows_custom_uvx_spec(tmp_path: Path) -> None:
    completed, trace = _run_wrapper(
        tmp_path,
        "uvx",
        args=["ingest-dir", "archive"],
        extra_env={"TRACCIA_UVX_SPEC": "traccia[document-markdown]"},
    )

    assert completed.returncode == 0
    assert trace["argv"] == [
        "--from",
        "traccia[document-markdown]",
        "traccia",
        "ingest-dir",
        "archive",
    ]


def test_npm_wrapper_can_target_the_local_repo_checkout(tmp_path: Path) -> None:
    completed, trace = _run_wrapper(
        tmp_path,
        "uv",
        args=["tree", "--project-root", "demo"],
        extra_env={"TRACCIA_USE_LOCAL_REPO": "1"},
    )

    assert completed.returncode == 0
    assert trace["argv"] == ["run", "traccia", "tree", "--project-root", "demo"]
    assert Path(trace["cwd"]) == REPO_ROOT


def test_npm_wrapper_propagates_subprocess_exit_codes(tmp_path: Path) -> None:
    completed, trace = _run_wrapper(
        tmp_path,
        "uvx",
        args=["doctor", "."],
        extra_env={"FAKE_EXIT_CODE": "23"},
    )

    assert completed.returncode == 23
    assert trace["argv"] == ["--from", "traccia", "traccia", "doctor", "."]
