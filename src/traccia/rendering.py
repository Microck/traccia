from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from traccia.config import load_config
from traccia.models import EvidenceItem
from traccia.storage import Storage
from traccia.utils import sentence_case_summary, slugify


def render_project(project_root: Path, *, storage: Storage) -> None:
    config = load_config(project_root / "config" / "config.yaml")
    skill_rows = storage.list_skill_rows()
    evidence_items = storage.list_evidence()
    sources = {str(row["source_id"]): row for row in storage.list_sources()}
    edges = storage.list_edges()
    evidence_by_skill = _evidence_by_skill(skill_rows=skill_rows, evidence_items=evidence_items)
    graph_payload = _build_graph_payload(
        skill_rows=skill_rows,
        edges=edges,
        evidence_by_skill=evidence_by_skill,
        sources=sources,
        allow_raw_excerpt_export=config.privacy.allow_raw_excerpt_export,
        redact_source_paths=config.privacy.redact_source_paths_in_exports,
    )
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
    _write_debug_report(
        project_root=project_root,
        storage=storage,
        skill_rows=skill_rows,
        evidence_items=evidence_items,
    )


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

def export_debug_report(project_root: Path) -> Path:
    storage = Storage(project_root)
    skill_rows = storage.list_skill_rows()
    evidence_items = storage.list_evidence()
    return _write_debug_report(
        project_root=project_root,
        storage=storage,
        skill_rows=skill_rows,
        evidence_items=evidence_items,
    )


def _build_graph_payload(
    *,
    skill_rows: list[dict[str, object]],
    edges,
    evidence_by_skill: dict[str, list[EvidenceItem]],
    sources: dict[str, dict[str, object]],
    allow_raw_excerpt_export: bool,
    redact_source_paths: bool,
) -> dict[str, object]:
    nodes: list[dict[str, object]] = []
    for row in skill_rows:
        skill_id = str(row["skill_id"])
        nodes.append(
            {
                "id": skill_id,
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
                "provenance": _graph_node_provenance(
                    evidence_items=evidence_by_skill.get(skill_id, []),
                    sources=sources,
                    allow_raw_excerpt_export=allow_raw_excerpt_export,
                    redact_source_paths=redact_source_paths,
                ),
            }
        )
    return {
        "nodes": nodes,
        "edges": [edge.model_dump(mode="json") for edge in edges],
        "metadata": {"generated_by": "traccia-renderer-v1"},
    }


def _graph_node_provenance(
    *,
    evidence_items: list[EvidenceItem],
    sources: dict[str, dict[str, object]],
    allow_raw_excerpt_export: bool,
    redact_source_paths: bool,
) -> list[dict[str, object]]:
    provenance: list[dict[str, object]] = []
    for evidence in sorted(evidence_items, key=lambda item: item.evidence_id):
        source_row = sources.get(str(evidence.source_id))
        provenance.append(
            {
                "evidenceId": evidence.evidence_id,
                "sourceId": evidence.source_id,
                "source": _graph_source_provenance(
                    source_row=source_row,
                    redact_source_paths=redact_source_paths,
                ),
                "spanStart": evidence.span_start,
                "spanEnd": evidence.span_end,
                "evidenceType": evidence.evidence_type.value,
                "signalClass": evidence.signal_class.value,
                "reliability": evidence.reliability.value,
                "confidence": evidence.confidence,
                "timeReference": evidence.time_reference,
                "excerpt": _render_evidence_text(
                    evidence,
                    allow_raw_excerpt_export=allow_raw_excerpt_export,
                    redact_source_paths=redact_source_paths,
                ),
            }
        )
    return provenance


def _graph_source_provenance(
    *,
    source_row: dict[str, object] | None,
    redact_source_paths: bool,
) -> dict[str, object]:
    if source_row is None:
        return {}

    metadata = _source_metadata(source_row)
    payload: dict[str, object] = {
        "title": source_row.get("title"),
        "filename": metadata.get("filename"),
        "sourceType": source_row.get("source_type"),
        "sourceCategory": source_row.get("source_category"),
        "parser": source_row.get("parser"),
        "sourceFamily": metadata.get("source_family"),
        "sourceFamilySubproduct": metadata.get("source_family_subproduct"),
    }
    if not redact_source_paths:
        payload["uri"] = source_row.get("uri")
        payload["relativeImportPath"] = metadata.get("relative_import_path")
    return {key: value for key, value in payload.items() if value not in (None, "")}


def _source_metadata(source_row: dict[str, object]) -> dict[str, object]:
    metadata_json = source_row.get("metadata_json")
    if not isinstance(metadata_json, str) or not metadata_json:
        return {}
    try:
        payload = json.loads(metadata_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


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


def _write_debug_report(
    *,
    project_root: Path,
    storage: Storage,
    skill_rows: list[dict[str, object]],
    evidence_items: list[EvidenceItem],
) -> Path:
    export_root = project_root / "exports" / "debug"
    export_root.mkdir(parents=True, exist_ok=True)

    sources = storage.list_sources()
    review_items = storage.list_review_items(include_closed=True)
    manual_overrides = storage.list_manual_overrides()
    source_evidence_counts = _count_by(
        [str(item.source_id) for item in evidence_items]
    )
    attachment_summary = _collect_attachment_summary(project_root=project_root)
    latest_progress = _read_json_if_exists(project_root / "state" / "progress.json")
    latest_manifest = _latest_json_file(project_root / "state" / "manifests")
    latest_run_state = _latest_json_file(project_root / "state" / "ingest-runs")

    source_metadata = [
        json.loads(str(row.get("metadata_json") or "{}"))
        for row in sources
    ]
    source_family_counts = _count_by(
        str(metadata.get("source_family") or "unknown") for metadata in source_metadata
    )
    source_family_subproduct_counts = _count_by(
        str(metadata.get("source_family_subproduct") or "none") for metadata in source_metadata
    )

    report_payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "project_root": str(project_root),
        "counts": {
            "sources": len(sources),
            "evidence_items": len(evidence_items),
            "skills": len([row for row in skill_rows if row["kind"] != "domain"]),
            "domains": len([row for row in skill_rows if row["kind"] == "domain"]),
            "pending_review_items": len([row for row in review_items if row["status"] == "pending"]),
            "manual_overrides": len(manual_overrides),
            "parsed_artifacts": len(list((project_root / "parsed").glob("*.json"))),
            "evidence_artifacts": len(list((project_root / "evidence").glob("*.json"))),
        },
        "sources": {
            "by_type": _count_by(str(row.get("source_type") or "unknown") for row in sources),
            "by_category": _count_by(str(row.get("source_category") or "unknown") for row in sources),
            "by_parser": _count_by(str(row.get("parser") or "unknown") for row in sources),
            "by_status": _count_by(str(row.get("status") or "unknown") for row in sources),
            "by_family": source_family_counts,
            "by_family_subproduct": source_family_subproduct_counts,
            "with_attachment_count": attachment_summary["sources_with_attachments"],
            "with_attachment_text_count": attachment_summary["sources_with_attachment_text"],
            "attachment_kinds": attachment_summary["by_kind"],
            "top_sources_by_evidence": sorted(
                (
                    {
                        "source_id": source_id,
                        "evidence_count": count,
                    }
                    for source_id, count in source_evidence_counts.items()
                ),
                key=lambda item: (-int(item["evidence_count"]), str(item["source_id"])),
            )[:20],
            "sources_without_evidence": sorted(
                [
                    str(row["source_id"])
                    for row in sources
                    if source_evidence_counts.get(str(row["source_id"]), 0) == 0
                ]
            )[:50],
        },
        "evidence": {
            "by_type": _count_by(item.evidence_type.value for item in evidence_items),
            "by_signal_class": _count_by(item.signal_class.value for item in evidence_items),
            "by_reliability": _count_by(item.reliability.value for item in evidence_items),
            "top_skill_candidates": _count_top_strings(
                [candidate for item in evidence_items for candidate in item.skill_candidates]
            ),
        },
        "skills": {
            "by_level": _count_by(
                str(int(row["level"] or 0))
                for row in skill_rows
                if row["kind"] != "domain"
            ),
            "by_freshness": _count_by(
                str(row.get("freshness") or "unknown")
                for row in skill_rows
                if row["kind"] != "domain"
            ),
            "by_status": _count_by(
                str(row.get("state_status") or row.get("status") or "unknown")
                for row in skill_rows
                if row["kind"] != "domain"
            ),
            "top_skills": [
                {
                    "skill_id": str(row["skill_id"]),
                    "name": str(row["name"]),
                    "level": int(row["level"] or 0),
                    "confidence": float(row["state_confidence"] or 0.0),
                    "freshness": str(row.get("freshness") or "unknown"),
                    "core_self_centrality": float(row["core_self_centrality"] or 0.0),
                }
                for row in sorted(
                    [row for row in skill_rows if row["kind"] != "domain"],
                    key=lambda row: (
                        -int(row["level"] or 0),
                        -float(row["state_confidence"] or 0.0),
                        str(row["name"]),
                    ),
                )[:20]
            ],
        },
        "ingest": {
            "latest_progress": latest_progress,
            "latest_manifest": latest_manifest,
            "latest_run_state": latest_run_state,
        },
    }

    report_json_path = export_root / "report.json"
    report_md_path = export_root / "report.md"
    report_json_path.write_text(json.dumps(report_payload, indent=2) + "\n")
    report_md_path.write_text(_debug_report_markdown(report_payload).rstrip() + "\n")
    return report_json_path

def _collect_attachment_summary(*, project_root: Path) -> dict[str, object]:
    sources_with_attachments = 0
    sources_with_attachment_text = 0
    by_kind: dict[str, int] = defaultdict(int)

    for parsed_path in (project_root / "parsed").glob("*.json"):
        payload = _read_json_if_exists(parsed_path)
        if not isinstance(payload, dict):
            continue
        attachments = payload.get("attachments") or []
        if not isinstance(attachments, list) or not attachments:
            continue
        sources_with_attachments += 1
        if any(isinstance(item, dict) and item.get("extracted_text") for item in attachments):
            sources_with_attachment_text += 1
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            by_kind[str(attachment.get("kind") or "unknown")] += 1

    return {
        "sources_with_attachments": sources_with_attachments,
        "sources_with_attachment_text": sources_with_attachment_text,
        "by_kind": dict(sorted(by_kind.items())),
    }

def _latest_json_file(directory: Path) -> dict[str, object] | None:
    if not directory.exists():
        return None
    candidates = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime_ns)
    if not candidates:
        return None
    payload = _read_json_if_exists(candidates[-1])
    if isinstance(payload, dict):
        payload["_path"] = str(candidates[-1])
    return payload if isinstance(payload, dict) else None

def _read_json_if_exists(path: Path) -> dict[str, object] | list[object] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None

def _count_by(values) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[str(value)] += 1
    return dict(sorted(counts.items()))

def _count_top_strings(values: list[str], *, limit: int = 20) -> list[dict[str, object]]:
    counts = _count_by(values)
    return [
        {"value": value, "count": count}
        for value, count in sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))[:limit]
    ]

def _debug_report_markdown(report_payload: dict[str, object]) -> str:
    counts = report_payload["counts"]
    sources = report_payload["sources"]
    evidence = report_payload["evidence"]
    skills = report_payload["skills"]
    ingest = report_payload["ingest"]
    latest_progress = ingest.get("latest_progress") or {}
    latest_run_state = ingest.get("latest_run_state") or {}
    latest_manifest = ingest.get("latest_manifest") or {}

    lines = [
        "# Debug Report",
        "",
        f"generated_at: {report_payload['generated_at']}",
        "",
        "## Counts",
        f"- sources: {counts['sources']}",
        f"- evidence_items: {counts['evidence_items']}",
        f"- skills: {counts['skills']}",
        f"- domains: {counts['domains']}",
        f"- pending_review_items: {counts['pending_review_items']}",
        f"- manual_overrides: {counts['manual_overrides']}",
        "",
        "## Source Breakdown",
        f"- by_family: {json.dumps(sources['by_family'], sort_keys=True)}",
        f"- by_type: {json.dumps(sources['by_type'], sort_keys=True)}",
        f"- by_parser: {json.dumps(sources['by_parser'], sort_keys=True)}",
        f"- attachment_kinds: {json.dumps(sources['attachment_kinds'], sort_keys=True)}",
        f"- sources_with_attachments: {sources['with_attachment_count']}",
        f"- sources_with_attachment_text: {sources['with_attachment_text_count']}",
        "",
        "## Evidence Breakdown",
        f"- by_type: {json.dumps(evidence['by_type'], sort_keys=True)}",
        f"- by_signal_class: {json.dumps(evidence['by_signal_class'], sort_keys=True)}",
        f"- by_reliability: {json.dumps(evidence['by_reliability'], sort_keys=True)}",
        "",
        "## Skill Breakdown",
        f"- by_level: {json.dumps(skills['by_level'], sort_keys=True)}",
        f"- by_freshness: {json.dumps(skills['by_freshness'], sort_keys=True)}",
        "",
        "## Latest Ingest",
        f"- progress_status: {latest_progress.get('status', 'unknown')}",
        f"- progress_completed: {((latest_progress.get('progress') or {}).get('completed'))}",
        f"- progress_total: {((latest_progress.get('progress') or {}).get('total'))}",
        f"- latest_run_state_path: {latest_run_state.get('_path', 'n/a')}",
        f"- latest_manifest_path: {latest_manifest.get('_path', 'n/a')}",
        "",
        "## Top Skills",
    ]
    for row in skills["top_skills"][:10]:
        lines.append(
            f"- {row['name']} (L{row['level']}, confidence {row['confidence']:.2f}, freshness {row['freshness']}, centrality {row['core_self_centrality']:.2f})"
        )
    lines.extend(
        [
            "",
            "## Top Skill Candidates In Evidence",
        ]
    )
    for row in evidence["top_skill_candidates"][:10]:
        lines.append(f"- {row['value']}: {row['count']}")
    return "\n".join(lines)


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
            "- Back to [[Home]]",
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
            "- Back to [[Home]]",
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
            "- Back to [[Home]]",
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
