"""Export actual viewers from the repository's synthetic corpus and fake backend."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from traccia.config import load_config, write_config
from traccia.curation import empty_curation, save_curation

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).parent / ".fixture"
PROJECT = WORK / "project"


def cli(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "traccia", *args], cwd=ROOT, check=True)


if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir()
cli("init", str(PROJECT))
config_path = PROJECT / "config" / "config.yaml"
config = load_config(config_path)
config.backend.provider = "fake"
write_config(config_path, config)
cli("ingest-dir", str(ROOT / "tests" / "fixtures" / "corpus"), "--project-root", str(PROJECT))
raw = json.loads((PROJECT / "graph" / "graph.json").read_text())
nodes = raw["nodes"]
if len(nodes) < 3:
    raise RuntimeError("Synthetic corpus must produce at least three graph nodes")
curation = empty_curation()
curation["nodes"][nodes[-1]["id"]] = {"hidden": True}
save_curation(PROJECT / "exports" / "viewer" / "curation.json", curation)
for kind in ("viewer", "admin", "publish"):
    cli("export", kind, "--project-root", str(PROJECT), "--no-sound")
public = json.loads((PROJECT / "exports" / "viewer-public" / "graph.json").read_text())
admin_node = next(node for node in nodes if node["kind"] == "skill")
manifest = {
    "adminNode": {"id": admin_node["id"], "name": admin_node["name"]},
    "hiddenId": nodes[-1]["id"],
    "publicNames": [n["name"] for n in public["nodes"]],
}
(WORK / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest))
