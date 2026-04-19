from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

from traccia.config import load_config
from traccia.models import EvidenceItem
from traccia.storage import Storage
from traccia.utils import sentence_case_summary, slugify


def render_project(project_root: Path, *, storage: Storage) -> None:
    config = load_config(project_root / "config" / "config.yaml")
    skill_rows = storage.list_skill_rows()
    evidence_items = storage.list_evidence()
    edges = storage.list_edges()
    evidence_by_skill = _evidence_by_skill(skill_rows=skill_rows, evidence_items=evidence_items)
    graph_payload = _build_graph_payload(skill_rows, edges)
    tree_payload = _build_tree_payload(skill_rows)

    (project_root / "graph" / "graph.json").write_text(json.dumps(graph_payload, indent=2) + "\n")
    (project_root / "graph" / "tree.json").write_text(json.dumps(tree_payload, indent=2) + "\n")
    _write_tree_markdown(project_root=project_root, tree_payload=tree_payload)
    _write_node_pages(
        project_root=project_root,
        skill_rows=skill_rows,
        evidence_by_skill=evidence_by_skill,
        edges=edges,
        allow_raw_excerpt_export=config.privacy.allow_raw_excerpt_export,
        redact_source_paths=config.privacy.redact_source_paths_in_exports,
    )
    _write_profile(
        project_root=project_root,
        skill_rows=skill_rows,
        evidence_by_skill=evidence_by_skill,
        allow_raw_excerpt_export=config.privacy.allow_raw_excerpt_export,
        redact_source_paths=config.privacy.redact_source_paths_in_exports,
    )
    _write_viewer(project_root=project_root, graph_payload=graph_payload, tree_payload=tree_payload)


def export_obsidian(project_root: Path) -> Path:
    destination = project_root / "exports" / "obsidian"
    destination.mkdir(parents=True, exist_ok=True)
    storage = Storage(project_root)
    config = load_config(project_root / "config" / "config.yaml")
    skill_rows = storage.list_skill_rows()
    edges = storage.list_edges()
    evidence_items = storage.list_evidence()
    sources = {str(row["source_id"]): row for row in storage.list_sources()}
    evidence_by_skill = _evidence_by_skill(skill_rows=skill_rows, evidence_items=evidence_items)

    shutil.rmtree(destination, ignore_errors=True)
    destination.mkdir(parents=True, exist_ok=True)
    for directory_name in ("Skills", "Domains", "Evidence", "Sources", "Profiles", "Graph"):
        (destination / directory_name).mkdir(parents=True, exist_ok=True)

    shutil.copytree(project_root / "graph", destination / "Graph", dirs_exist_ok=True)
    _write_obsidian_home(destination=destination, skill_rows=skill_rows)
    _write_obsidian_domain_notes(destination=destination, skill_rows=skill_rows)
    _write_obsidian_skill_notes(
        destination=destination,
        skill_rows=skill_rows,
        evidence_by_skill=evidence_by_skill,
        edges=edges,
        allow_raw_excerpt_export=config.privacy.allow_raw_excerpt_export,
        redact_source_paths=config.privacy.redact_source_paths_in_exports,
    )
    _write_obsidian_evidence_notes(
        destination=destination,
        evidence_items=evidence_items,
        skill_rows=skill_rows,
        sources=sources,
        allow_raw_excerpt_export=config.privacy.allow_raw_excerpt_export,
        redact_source_paths=config.privacy.redact_source_paths_in_exports,
    )
    _write_obsidian_source_notes(destination=destination, sources=sources)
    _write_obsidian_profile_notes(destination=destination, project_root=project_root)
    return destination


def ascii_tree(project_root: Path) -> str:
    tree_payload = json.loads((project_root / "graph" / "tree.json").read_text())
    lines: list[str] = []
    for root in tree_payload["roots"]:
        lines.append(root["name"])
        for child in root["children"]:
            lines.append(f"  - {child['name']} (L{child['level']})")
    return "\n".join(lines)


def mermaid_tree(project_root: Path) -> str:
    tree_payload = json.loads((project_root / "graph" / "tree.json").read_text())
    lines = ["graph TD"]
    for root in tree_payload["roots"]:
        root_id = root["id"].replace(".", "_")
        lines.append(f"  {root_id}[{root['name']}]")
        for child in root["children"]:
            child_id = child["id"].replace(".", "_")
            lines.append(f"  {root_id} --> {child_id}[{child['name']} L{child['level']}]")
    return "\n".join(lines)


def _build_graph_payload(skill_rows: list[dict[str, object]], edges) -> dict[str, object]:
    nodes: list[dict[str, object]] = []
    for row in skill_rows:
        nodes.append(
            {
                "id": row["skill_id"],
                "name": row["name"],
                "kind": row["kind"],
                "description": row["description"],
                "level": row["level"] or 0,
                "confidence": row["state_confidence"] or 0.0,
                "freshness": row["freshness"],
                "coreSelfCentrality": row["core_self_centrality"] or 0.0,
                "firstSeenAt": row["first_seen_at"],
                "firstLearnedAt": row["first_learned_at"],
                "firstStrongEvidenceAt": row["first_strong_evidence_at"],
                "recencyScore": row["recency_score"] or 0.0,
                "lastEvidenceAt": row["last_evidence_at"],
                "lastStrongEvidenceAt": row["last_strong_evidence_at"],
                "historicalPeakLevel": row["historical_peak_level"] or row["level"] or 0,
                "historicalPeakAt": row["historical_peak_at"],
                "acquiredAt": row["acquired_at"],
                "acquisitionBasis": row["acquisition_basis"],
                "status": row["state_status"] or row["status"],
            }
        )
    return {
        "nodes": nodes,
        "edges": [edge.model_dump(mode="json") for edge in edges],
        "metadata": {"generated_by": "traccia-renderer-v1"},
    }


def _build_tree_payload(skill_rows: list[dict[str, object]]) -> dict[str, object]:
    roots = [row for row in skill_rows if row["kind"] == "domain"]
    children_by_domain: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in skill_rows:
        if row["kind"] == "domain":
            continue
        domain_name = row["description"].split("::", maxsplit=1)[0] if isinstance(row["description"], str) and "::" in row["description"] else "Programming"
        children_by_domain[domain_name].append(row)

    serialized_roots: list[dict[str, object]] = []
    for root in roots:
        children = sorted(children_by_domain.get(root["name"], []), key=lambda item: (-int(item["level"] or 0), str(item["name"])))
        serialized_roots.append(
            {
                "id": root["skill_id"],
                "name": root["name"],
                "children": [
                    {"id": child["skill_id"], "name": child["name"], "level": child["level"] or 0}
                    for child in children
                    if child["state_status"] != "hidden"
                ],
            }
        )
    return {"roots": serialized_roots, "metadata": {"generated_by": "traccia-renderer-v1"}}


def _evidence_by_skill(
    *, skill_rows: list[dict[str, object]], evidence_items: list[EvidenceItem]
) -> dict[str, list[EvidenceItem]]:
    evidence_map: dict[str, list[EvidenceItem]] = defaultdict(list)
    skill_names = {str(row["name"]): str(row["skill_id"]) for row in skill_rows if row["kind"] != "domain"}
    for evidence_item in evidence_items:
        for candidate in evidence_item.skill_candidates:
            skill_id = skill_names.get(candidate)
            if skill_id:
                evidence_map[skill_id].append(evidence_item)
    return evidence_map


def _write_tree_markdown(*, project_root: Path, tree_payload: dict[str, object]) -> None:
    lines = ["# Skill Tree", ""]
    for root in tree_payload["roots"]:
        lines.append(f"## {root['name']}")
        if root["children"]:
            for child in root["children"]:
                lines.append(f"- {child['name']} (L{child['level']})")
        else:
            lines.append("- No visible nodes yet.")
        lines.append("")
    (project_root / "tree" / "index.md").write_text("\n".join(lines).rstrip() + "\n")


def _write_node_pages(
    *,
    project_root: Path,
    skill_rows: list[dict[str, object]],
    evidence_by_skill: dict[str, list[EvidenceItem]],
    edges,
    allow_raw_excerpt_export: bool,
    redact_source_paths: bool,
) -> None:
    nodes_dir = project_root / "tree" / "nodes"
    skill_name_by_id = {str(row["skill_id"]): str(row["name"]) for row in skill_rows}
    for row in skill_rows:
        if row["kind"] == "domain":
            continue
        skill_evidence = evidence_by_skill.get(str(row["skill_id"]), [])
        summary = sentence_case_summary(
            [
                _render_evidence_text(
                    evidence,
                    allow_raw_excerpt_export=allow_raw_excerpt_export,
                    redact_source_paths=redact_source_paths,
                )
                for evidence in skill_evidence
            ]
        ) or "No evidence yet."
        lines = [
            "---",
            f"skill_id: {row['skill_id']}",
            f"kind: {row['kind']}",
            f"name: {row['name']}",
            f"level: {row['level'] or 0}",
            f"confidence: {row['state_confidence'] or 0.0}",
            f"freshness: {row['freshness'] or 'historical'}",
            f"core_self_centrality: {row['core_self_centrality'] or 0.0}",
            f"locked: {bool(row['locked'])}",
            "---",
            "",
            f"# {row['name']}",
            "",
            "## Placement",
            _placement_summary(row),
            "",
            "## Timeline",
            _timeline_summary(row),
            "",
            "## Summary",
            summary,
            "",
            "## Why this exists",
        ]
        for evidence in skill_evidence:
            lines.append(
                f"- `{evidence.evidence_id}` ({evidence.evidence_type.value}, {evidence.signal_class.value}): "
                f"{_render_evidence_text(evidence, allow_raw_excerpt_export=allow_raw_excerpt_export, redact_source_paths=redact_source_paths)}"
            )
        lines.extend(
            [
                "",
                "## Level rationale",
                f"Current level is L{row['level'] or 0} based on {len(skill_evidence)} evidence item(s) and confidence {row['state_confidence'] or 0.0:.2f}.",
                (
                    f"Estimated acquisition is {row['acquired_at'] or 'unknown'}"
                    + (
                        f" via {str(row['acquisition_basis']).replace('_', ' ')}."
                        if row["acquisition_basis"]
                        else "."
                    )
                ),
                (
                    f"Historical peak is L{row['historical_peak_level'] or row['level'] or 0}"
                    + (
                        f" at {row['historical_peak_at']}."
                        if row["historical_peak_at"]
                        else "."
                    )
                ),
                f"Core-self centrality is {(row['core_self_centrality'] or 0.0):.2f}.",
                "",
                "## Freshness",
                _freshness_summary(row),
                "",
                "## Connections",
                _connection_summary(str(row["skill_id"]), edges=edges, skill_name_by_id=skill_name_by_id),
            ]
        )
        (nodes_dir / f"{row['skill_id']}.md").write_text("\n".join(lines).rstrip() + "\n")


def _write_profile(
    *,
    project_root: Path,
    skill_rows: list[dict[str, object]],
    evidence_by_skill: dict[str, list[EvidenceItem]],
    allow_raw_excerpt_export: bool,
    redact_source_paths: bool,
) -> None:
    visible_skills = [row for row in skill_rows if row["kind"] != "domain" and row["state_status"] != "hidden"]
    strongest = sorted(visible_skills, key=lambda row: (-(row["level"] or 0), -(row["state_confidence"] or 0.0), row["name"]))[:5]
    lines = ["# Skill Profile", "", "## Strengths"]
    for row in strongest:
        evidence_summaries = ", ".join(
            _render_evidence_text(
                evidence,
                allow_raw_excerpt_export=allow_raw_excerpt_export,
                redact_source_paths=redact_source_paths,
            )
            for evidence in evidence_by_skill.get(str(row["skill_id"]), [])[:2]
        )
        lines.append(
            f"- {row['name']} (L{row['level'] or 0}, confidence {(row['state_confidence'] or 0.0):.2f}, "
            f"peak L{row['historical_peak_level'] or row['level'] or 0}, "
            f"centrality {(row['core_self_centrality'] or 0.0):.2f}) - {evidence_summaries}"
        )
    (project_root / "profile" / "skill.md").write_text("\n".join(lines).rstrip() + "\n")
    (project_root / "profile" / "strengths.md").write_text("\n".join(lines).rstrip() + "\n")

    gap_lines = ["# Gaps", ""]
    for row in sorted(visible_skills, key=lambda item: ((item["level"] or 0), item["name"]))[:5]:
        if (row["level"] or 0) <= 2:
            gap_lines.append(f"- {row['name']} is early-stage at L{row['level'] or 0}.")
    (project_root / "profile" / "gaps.md").write_text("\n".join(gap_lines).rstrip() + "\n")

    artifact_lines = ["# Artifacts", ""]
    for row in visible_skills:
        supporting_evidence = evidence_by_skill.get(str(row["skill_id"]), [])
        preview = sentence_case_summary(
            [
                _render_evidence_text(
                    evidence,
                    allow_raw_excerpt_export=allow_raw_excerpt_export,
                    redact_source_paths=redact_source_paths,
                )
                for evidence in supporting_evidence[:2]
            ]
        ) or "No exportable excerpt."
        artifact_lines.append(
            f"- {row['name']} is supported by {len(supporting_evidence)} evidence item(s). {preview}"
        )
    (project_root / "profile" / "artifacts.md").write_text("\n".join(artifact_lines).rstrip() + "\n")


def _write_viewer(*, project_root: Path, graph_payload: dict[str, object], tree_payload: dict[str, object]) -> None:
    viewer_path = project_root / "viewer" / "index.html"
    graph_json = json.dumps(graph_payload).replace("</", "<\\/")
    tree_json = json.dumps(tree_payload).replace("</", "<\\/")
    viewer_path.write_text(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Traccia Viewer</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f3efe5;
        --panel: rgba(255, 252, 246, 0.92);
        --ink: #1d1a16;
        --muted: #6b6257;
        --line: rgba(54, 40, 23, 0.14);
        --accent: #b4562d;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: "Iosevka Etoile", "IBM Plex Sans", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(180, 86, 45, 0.16), transparent 30%),
          linear-gradient(180deg, #f7f3ea 0%, var(--bg) 100%);
      }}
      main {{
        display: grid;
        grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
        gap: 1rem;
        padding: 1.5rem;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 1rem;
        box-shadow: 0 12px 40px rgba(38, 28, 18, 0.08);
        backdrop-filter: blur(14px);
      }}
      h1, h2, h3 {{ margin: 0 0 0.75rem; }}
      p {{ color: var(--muted); line-height: 1.5; }}
      input {{
        width: 100%;
        padding: 0.75rem 0.9rem;
        border-radius: 12px;
        border: 1px solid var(--line);
        background: white;
        font: inherit;
      }}
      ul {{ list-style: none; padding: 0; margin: 0; }}
      li + li {{ margin-top: 0.5rem; }}
      button {{
        width: 100%;
        text-align: left;
        padding: 0.75rem 0.9rem;
        border: 1px solid transparent;
        border-radius: 12px;
        background: #fff;
        color: inherit;
        cursor: pointer;
      }}
      button:hover, button[data-active="true"] {{
        border-color: rgba(180, 86, 45, 0.35);
        background: rgba(180, 86, 45, 0.08);
      }}
      .pill {{
        display: inline-block;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        background: rgba(180, 86, 45, 0.12);
        color: var(--accent);
        font-size: 0.9rem;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0;
      }}
      .stat {{
        padding: 0.85rem;
        border-radius: 14px;
        background: rgba(29, 26, 22, 0.04);
        border: 1px solid var(--line);
      }}
      .stat strong {{
        display: block;
        font-size: 1.1rem;
      }}
      .tree-root + .tree-root {{ margin-top: 1rem; }}
      @media (max-width: 860px) {{
        main {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="panel">
        <h1>Traccia Viewer</h1>
        <p>Search the generated skill graph and inspect current versus historical state without leaving the exported bundle.</p>
        <input id="search" type="search" placeholder="Search skills, domains, or freshness">
        <div id="counts" class="grid"></div>
        <ul id="results"></ul>
      </section>
      <section class="panel">
        <div id="details"></div>
        <div id="tree"></div>
      </section>
    </main>
    <script>
      const graph = {graph_json};
      const tree = {tree_json};
      const resultsEl = document.getElementById("results");
      const detailsEl = document.getElementById("details");
      const treeEl = document.getElementById("tree");
      const countsEl = document.getElementById("counts");
      const searchEl = document.getElementById("search");

      const visibleNodes = graph.nodes.filter((node) => node.kind !== "domain");
      let activeId = visibleNodes[0]?.id ?? graph.nodes[0]?.id ?? null;

      function renderCounts() {{
        const counts = [
          ["Skills", visibleNodes.length],
          ["Active", visibleNodes.filter((node) => node.freshness === "active").length],
          ["Historical", visibleNodes.filter((node) => node.freshness === "historical").length],
        ];
        countsEl.innerHTML = counts
          .map(([label, value]) => `<div class="stat"><span>${{label}}</span><strong>${{value}}</strong></div>`)
          .join("");
      }}

      function renderResults() {{
        const query = searchEl.value.trim().toLowerCase();
        const filtered = visibleNodes.filter((node) => {{
          if (!query) return true;
          return [node.name, node.kind, node.freshness, node.status].some((value) =>
            String(value || "").toLowerCase().includes(query)
          );
        }});
        resultsEl.innerHTML = filtered
          .map((node) => `
            <li>
              <button data-id="${{node.id}}" data-active="${{String(node.id === activeId)}}">
                <strong>${{node.name}}</strong><br>
                <span>${{node.kind}} · L${{node.level}} · ${{node.freshness}}</span>
              </button>
            </li>
          `)
          .join("");
        for (const button of resultsEl.querySelectorAll("button")) {{
          button.addEventListener("click", () => {{
            activeId = button.dataset.id;
            renderResults();
            renderDetails();
          }});
        }}
      }}

      function renderDetails() {{
        const node = graph.nodes.find((item) => item.id === activeId);
        if (!node) {{
          detailsEl.innerHTML = "<p>No skill nodes available yet.</p>";
          return;
        }}
        detailsEl.innerHTML = `
          <h2>${{node.name}}</h2>
          <p>${{node.description || "No description available."}}</p>
          <div>
            <span class="pill">Level L${{node.level}}</span>
            <span class="pill">Peak L${{node.historicalPeakLevel}}</span>
            <span class="pill">${{node.freshness}}</span>
            <span class="pill">${{node.status}}</span>
          </div>
          <div class="grid">
            <div class="stat"><span>Confidence</span><strong>${{Number(node.confidence || 0).toFixed(2)}}</strong></div>
            <div class="stat"><span>Recency</span><strong>${{Number(node.recencyScore || 0).toFixed(2)}}</strong></div>
            <div class="stat"><span>Centrality</span><strong>${{Number(node.coreSelfCentrality || 0).toFixed(2)}}</strong></div>
            <div class="stat"><span>First Seen</span><strong>${{node.firstSeenAt || "n/a"}}</strong></div>
            <div class="stat"><span>First Strong</span><strong>${{node.firstStrongEvidenceAt || "n/a"}}</strong></div>
            <div class="stat"><span>Last Evidence</span><strong>${{node.lastEvidenceAt || "n/a"}}</strong></div>
            <div class="stat"><span>Peak Reached</span><strong>${{node.historicalPeakAt || "n/a"}}</strong></div>
          </div>
        `;
      }}

      function renderTree() {{
        treeEl.innerHTML = `
          <h3>Tree Roots</h3>
          ${{
            tree.roots.map((root) => `
              <div class="tree-root">
                <strong>${{root.name}}</strong>
                <ul>
                  ${{
                    root.children.map((child) => `<li>${{child.name}} (L${{child.level}})</li>`).join("") ||
                    "<li>No visible nodes yet.</li>"
                  }}
                </ul>
              </div>
            `).join("")
          }}
        `;
      }}

      renderCounts();
      renderResults();
      renderDetails();
      renderTree();
      searchEl.addEventListener("input", renderResults);
    </script>
  </body>
</html>
""",
    )


def _render_evidence_text(
    evidence: EvidenceItem,
    *,
    allow_raw_excerpt_export: bool,
    redact_source_paths: bool,
) -> str:
    if not allow_raw_excerpt_export:
        return f"Grounded {evidence.evidence_type.value} evidence from {evidence.source_id}."
    return _sanitize_export_text(evidence.quote, redact_source_paths=redact_source_paths)


def _sanitize_export_text(text: str, *, redact_source_paths: bool) -> str:
    sanitized = text
    if redact_source_paths:
        sanitized = re.sub(r"file://\S+", "[REDACTED_PATH]", sanitized)
        sanitized = re.sub(r"(?<![A-Za-z]):?/(?:[^\\s/]+/)+[^\\s]+", "[REDACTED_PATH]", sanitized)
    sanitized = re.sub(
        r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[:=]\s*([^\s,;]+)",
        lambda match: f"{match.group(1)}=[REDACTED]",
        sanitized,
    )
    sanitized = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}\b", "[REDACTED]", sanitized)
    sanitized = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED]", sanitized)
    return sanitized


def _freshness_summary(row: dict[str, object]) -> str:
    freshness = str(row["freshness"] or "historical")
    last_evidence = row["last_evidence_at"] or "unknown"
    last_strong = row["last_strong_evidence_at"] or "unknown"
    return (
        f"{freshness}. Last evidence at {last_evidence}. "
        f"Last strong evidence at {last_strong}."
    )


def _timeline_summary(row: dict[str, object]) -> str:
    acquisition_summary = (
        f"Estimated acquisition at {row['acquired_at'] or 'unknown'}"
        + (
            f" via {str(row['acquisition_basis']).replace('_', ' ')}. "
            if row["acquisition_basis"]
            else ". "
        )
    )
    return (
        f"First seen at {row['first_seen_at'] or 'unknown'}. "
        f"First learned at {row['first_learned_at'] or 'unknown'}. "
        f"First strong evidence at {row['first_strong_evidence_at'] or 'unknown'}. "
        f"{acquisition_summary}"
        f"Historical peak L{row['historical_peak_level'] or row['level'] or 0} "
        f"at {row['historical_peak_at'] or 'unknown'}."
    )


def _placement_summary(row: dict[str, object]) -> str:
    description = str(row["description"] or "")
    if "::" not in description:
        return "Primary branch is not yet classified."
    domain_name, branch_description = description.split("::", maxsplit=1)
    return f"Domain: {domain_name}. Branch meaning: {branch_description}"


def _connection_summary(
    skill_id: str,
    *,
    edges,
    skill_name_by_id: dict[str, str],
) -> str:
    connection_lines: list[str] = []
    for edge in edges:
        if str(edge.to_skill_id) == skill_id:
            source_name = skill_name_by_id.get(str(edge.from_skill_id), str(edge.from_skill_id))
            connection_lines.append(f"- inbound {edge.edge_type.value}: {source_name}")
        elif str(edge.from_skill_id) == skill_id:
            target_name = skill_name_by_id.get(str(edge.to_skill_id), str(edge.to_skill_id))
            connection_lines.append(f"- outbound {edge.edge_type.value}: {target_name}")
    if not connection_lines:
        return "No explicit graph connections yet beyond evidence clustering."
    return "\n".join(connection_lines)


def _write_obsidian_home(*, destination: Path, skill_rows: list[dict[str, object]]) -> None:
    visible_skills = [row for row in skill_rows if row["kind"] != "domain" and row["state_status"] != "hidden"]
    strongest = sorted(
        visible_skills,
        key=lambda row: (-(row["level"] or 0), -(row["state_confidence"] or 0.0), str(row["name"])),
    )[:8]
    lines = [
        "---",
        "type: home",
        "generated_by: traccia",
        "---",
        "",
        "# Traccia Vault",
        "",
        "## Domains",
    ]
    for row in skill_rows:
        if row["kind"] == "domain":
            lines.append(f"- [[Domains/{_obsidian_note_name(str(row['name']))}|{row['name']}]]")
    lines.extend(["", "## Strongest Current Skills"])
    for row in strongest:
        lines.append(
            f"- [[Skills/{_obsidian_note_name(str(row['name']))}|{row['name']}]] "
            f"(L{row['level'] or 0}, {row['freshness'] or 'historical'})"
        )
    (destination / "Home.md").write_text("\n".join(lines).rstrip() + "\n")


def _write_obsidian_domain_notes(*, destination: Path, skill_rows: list[dict[str, object]]) -> None:
    children_by_domain: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in skill_rows:
        if row["kind"] == "domain":
            continue
        domain_name = _domain_name_for_row(row)
        children_by_domain[domain_name].append(row)

    for row in skill_rows:
        if row["kind"] != "domain":
            continue
        children = sorted(
            children_by_domain.get(str(row["name"]), []),
            key=lambda child: (-(child["level"] or 0), str(child["name"])),
        )
        lines = [
            "---",
            "type: domain",
            f"domain: {row['name']}",
            "---",
            "",
            f"# {row['name']}",
            "",
            f"- Back to [[Home]]",
            "",
            "## Skills",
        ]
        if children:
            for child in children:
                lines.append(
                    f"- [[Skills/{_obsidian_note_name(str(child['name']))}|{child['name']}]] "
                    f"(L{child['level'] or 0})"
                )
        else:
            lines.append("- No visible nodes yet.")
        (destination / "Domains" / f"{_obsidian_note_name(str(row['name']))}.md").write_text(
            "\n".join(lines).rstrip() + "\n"
        )


def _write_obsidian_skill_notes(
    *,
    destination: Path,
    skill_rows: list[dict[str, object]],
    evidence_by_skill: dict[str, list[EvidenceItem]],
    edges,
    allow_raw_excerpt_export: bool,
    redact_source_paths: bool,
) -> None:
    skill_name_by_id = {str(row["skill_id"]): str(row["name"]) for row in skill_rows}
    for row in skill_rows:
        if row["kind"] in {"domain"} or row["state_status"] == "hidden":
            continue
        domain_name = _domain_name_for_row(row)
        note_lines = [
            "---",
            "type: skill",
            f"skill_id: {row['skill_id']}",
            f"kind: {row['kind']}",
            f"level: {row['level'] or 0}",
            f"confidence: {row['state_confidence'] or 0.0}",
            f"freshness: {row['freshness'] or 'historical'}",
            f"core_self_centrality: {row['core_self_centrality'] or 0.0}",
            f"historical_peak_level: {row['historical_peak_level'] or row['level'] or 0}",
            "---",
            "",
            f"# {row['name']}",
            "",
            f"- Domain: [[Domains/{_obsidian_note_name(domain_name)}|{domain_name}]]",
            f"- Back to [[Home]]",
            "",
            "## Timeline",
            f"- First seen: {row['first_seen_at'] or 'unknown'}",
            f"- First learned: {row['first_learned_at'] or 'unknown'}",
            f"- First strong evidence: {row['first_strong_evidence_at'] or 'unknown'}",
            (
                f"- Estimated acquisition: {row['acquired_at'] or 'unknown'}"
                + (
                    f" ({str(row['acquisition_basis']).replace('_', ' ')})"
                    if row["acquisition_basis"]
                    else ""
                )
            ),
            f"- Last strong evidence: {row['last_strong_evidence_at'] or 'unknown'}",
            f"- Historical peak: L{row['historical_peak_level'] or row['level'] or 0} at {row['historical_peak_at'] or 'unknown'}",
            "",
            "## Summary",
            _placement_summary(row),
            "",
            "## Evidence",
        ]
        skill_evidence = evidence_by_skill.get(str(row["skill_id"]), [])
        if skill_evidence:
            for evidence in skill_evidence[:12]:
                note_lines.append(
                    f"- [[Evidence/{evidence.evidence_id}|{evidence.evidence_id}]] "
                    f"({evidence.evidence_type.value}, {evidence.signal_class.value})"
                )
        else:
            note_lines.append("- No evidence notes yet.")
        note_lines.extend(
            [
                "",
                "## Connections",
                _connection_summary_obsidian(
                    str(row["skill_id"]),
                    edges=edges,
                    skill_name_by_id=skill_name_by_id,
                ),
                "",
                "## Evidence Summary",
            ]
        )
        summary = sentence_case_summary(
            [
                _render_evidence_text(
                    evidence,
                    allow_raw_excerpt_export=allow_raw_excerpt_export,
                    redact_source_paths=redact_source_paths,
                )
                for evidence in skill_evidence[:4]
            ]
        ) or "No evidence yet."
        note_lines.append(summary)
        (destination / "Skills" / f"{_obsidian_note_name(str(row['name']))}.md").write_text(
            "\n".join(note_lines).rstrip() + "\n"
        )


def _write_obsidian_evidence_notes(
    *,
    destination: Path,
    evidence_items: list[EvidenceItem],
    skill_rows: list[dict[str, object]],
    sources: dict[str, dict[str, object]],
    allow_raw_excerpt_export: bool,
    redact_source_paths: bool,
) -> None:
    skill_names = {str(row["name"]) for row in skill_rows if row["kind"] != "domain"}
    for evidence in evidence_items:
        linked_skills = [name for name in evidence.skill_candidates if name in skill_names]
        source_row = sources.get(str(evidence.source_id))
        source_note = (
            f"[[Sources/{_obsidian_note_name(str(source_row.get('title') or evidence.source_id))}|{source_row.get('title') or evidence.source_id}]]"
            if source_row
            else str(evidence.source_id)
        )
        lines = [
            "---",
            "type: evidence",
            f"evidence_id: {evidence.evidence_id}",
            f"evidence_type: {evidence.evidence_type.value}",
            f"signal_class: {evidence.signal_class.value}",
            f"source_id: {evidence.source_id}",
            f"reliability: {evidence.reliability.value}",
            f"time_reference: {evidence.time_reference or ''}",
            "---",
            "",
            f"# {evidence.evidence_id}",
            "",
            f"- Source: {source_note}",
            "",
            "## Linked Skills",
        ]
        if linked_skills:
            for skill_name in linked_skills:
                lines.append(f"- [[Skills/{_obsidian_note_name(skill_name)}|{skill_name}]]")
        else:
            lines.append("- No canonical skill links yet.")
        lines.extend(
            [
                "",
                "## Quote",
                _render_evidence_text(
                    evidence,
                    allow_raw_excerpt_export=allow_raw_excerpt_export,
                    redact_source_paths=redact_source_paths,
                ),
            ]
        )
        (destination / "Evidence" / f"{evidence.evidence_id}.md").write_text(
            "\n".join(lines).rstrip() + "\n"
        )


def _write_obsidian_source_notes(
    *,
    destination: Path,
    sources: dict[str, dict[str, object]],
) -> None:
    for source_id, row in sources.items():
        title = str(row.get("title") or source_id)
        lines = [
            "---",
            "type: source",
            f"source_id: {source_id}",
            f"source_type: {row.get('source_type') or ''}",
            f"source_category: {row.get('source_category') or ''}",
            f"status: {row.get('status') or ''}",
            "---",
            "",
            f"# {title}",
            "",
            f"- Back to [[Home]]",
            f"- URI: `{row.get('uri') or ''}`",
            f"- Category: `{row.get('source_category') or ''}`",
        ]
        (destination / "Sources" / f"{_obsidian_note_name(title)}.md").write_text(
            "\n".join(lines).rstrip() + "\n"
        )


def _write_obsidian_profile_notes(*, destination: Path, project_root: Path) -> None:
    for filename in ("skill.md", "strengths.md", "gaps.md", "artifacts.md"):
        source_path = project_root / "profile" / filename
        if not source_path.exists():
            continue
        title = source_path.stem.replace("-", " ").title()
        content = source_path.read_text()
        lines = [
            "---",
            "type: profile",
            f"title: {title}",
            "---",
            "",
            f"# {title}",
            "",
            "- Back to [[Home]]",
            "",
            content.strip(),
        ]
        (destination / "Profiles" / filename).write_text("\n".join(lines).rstrip() + "\n")


def _obsidian_note_name(value: str) -> str:
    return slugify(value).replace("-", " ")


def _domain_name_for_row(row: dict[str, object]) -> str:
    description = str(row.get("description") or "")
    if "::" in description:
        return description.split("::", maxsplit=1)[0]
    return "Programming"


def _connection_summary_obsidian(
    skill_id: str,
    *,
    edges,
    skill_name_by_id: dict[str, str],
) -> str:
    lines: list[str] = []
    for edge in edges:
        if str(edge.to_skill_id) == skill_id:
            source_name = skill_name_by_id.get(str(edge.from_skill_id))
            if source_name:
                lines.append(f"- inbound `{edge.edge_type.value}` from [[Skills/{_obsidian_note_name(source_name)}|{source_name}]]")
        elif str(edge.from_skill_id) == skill_id:
            target_name = skill_name_by_id.get(str(edge.to_skill_id))
            if target_name:
                lines.append(f"- outbound `{edge.edge_type.value}` to [[Skills/{_obsidian_note_name(target_name)}|{target_name}]]")
    if not lines:
        return "- No explicit graph connections yet."
    return "\n".join(lines)
