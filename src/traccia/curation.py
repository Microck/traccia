"""Phase 2 admin curation model and publish redaction.

This module defines the curation.json contract that admins author against
the finished-run viewer, and the publish step that produces a redacted
public bundle from ``graph.json + curation.json``.

Design contract (see docs/finished-run-viewer-decisions.md):

- Admin curation v1 covers visibility and emphasis only (decisions 23-25):
  hide/mute, restore, feature/pin, collapse/expand domains, public label
  and note overrides.
- Admin saves ``curation.json`` into the export folder (decision 24).
- Publish physically removes hidden nodes, hidden edges, private/redacted
  provenance, raw source paths, raw excerpts, sensitive evidence IDs,
  disputed/review nodes, and low-confidence nodes (decisions 25, 29, 46-50).
- Public node IDs stay the same as internal IDs unless a skill ID leaks
  private information. For sensitive IDs, publish generates stable public
  alias IDs and keeps the mapping admin-only (decision 51).
- Admin may approve low-confidence nodes for publish, but must not edit the
  confidence score (decision 48).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Curation schema version
# ---------------------------------------------------------------------------

CURATION_VERSION = 1

# Default low-confidence threshold below which nodes are excluded from the
# public bundle unless explicitly approved by curation (decision 47).
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.25

# Statuses that are excluded from the public bundle by default (decisions
# 46, 50). Admin must explicitly approve them via curation overrides.
_PUBLISH_DEFAULT_EXCLUDED_STATUSES = frozenset({"hidden", "disputed", "review"})

# Patterns in a skill ID that suggest it may leak private information.
# When matched, publish generates a stable public alias instead of using
# the raw internal ID (decision 51).
_SENSITIVE_ID_PATTERNS = (
    "@",
    "/",
    "\\",
    ":",
    " ",
)

# Set of strong evidence types used for provenance strength summaries.
_STRONG_EVIDENCE_TYPES = frozenset(
    {"implemented", "designed", "debugged", "taught", "produced_artifact"}
)


# ---------------------------------------------------------------------------
# Curation data model
# ---------------------------------------------------------------------------


def empty_curation() -> dict[str, object]:
    """Return a blank curation.json payload matching the current schema."""
    return {
        "version": CURATION_VERSION,
        "nodes": {},
        "domains": {},
        "global": {
            "defaultCollapsedDomains": [],
        },
    }


def node_curation_entry(
    *,
    hidden: bool | None = None,
    featured: bool | None = None,
    public_label: str | None = None,
    public_note: str | None = None,
    approve_low_confidence: bool | None = None,
    approve_disputed: bool | None = None,
) -> dict[str, object]:
    """Build a single per-node curation override entry.

    Only non-None fields are stored so the curation file stays compact.
    """
    entry: dict[str, object] = {}
    if hidden is not None:
        entry["hidden"] = hidden
    if featured is not None:
        entry["featured"] = featured
    if public_label is not None:
        entry["publicLabel"] = public_label
    if public_note is not None:
        entry["publicNote"] = public_note
    if approve_low_confidence is not None:
        entry["approveLowConfidence"] = approve_low_confidence
    if approve_disputed is not None:
        entry["approveDisputed"] = approve_disputed
    return entry


def domain_curation_entry(
    *,
    collapsed: bool | None = None,
    public_label: str | None = None,
) -> dict[str, object]:
    """Build a single per-domain curation override entry."""
    entry: dict[str, object] = {}
    if collapsed is not None:
        entry["collapsed"] = collapsed
    if public_label is not None:
        entry["publicLabel"] = public_label
    return entry


# ---------------------------------------------------------------------------
# Load / save / merge
# ---------------------------------------------------------------------------


def load_curation(path: Path) -> dict[str, object]:
    """Load a curation.json file, returning an empty curation if missing.

    This is tolerant of a missing file (returns a blank curation) but
    raises ``ValueError`` if the file exists but is malformed JSON, so the
    admin does not silently lose curation work to a corrupt file.
    """
    if not path.exists():
        return empty_curation()
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid curation JSON at {path}: {exc}") from exc
    return _normalize_curation(data)


def save_curation(path: Path, curation: dict[str, object]) -> None:
    """Write curation.json to the given path, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_curation(curation)
    path.write_text(json.dumps(normalized, indent=2) + "\n")


def merge_curation(
    base: dict[str, object], override: dict[str, object]
) -> dict[str, object]:
    """Merge an override curation into a base curation.

    Override values take precedence. This is used when the admin viewer
    applies staged changes on top of the loaded curation.
    """
    merged = _normalize_curation(base)
    override = _normalize_curation(override)

    for node_id, entry in override.get("nodes", {}).items():
        existing = merged["nodes"].get(node_id, {})
        existing.update(entry)
        # Drop explicit None values so unsetting a field works.
        existing = {k: v for k, v in existing.items() if v is not None}
        if existing:
            merged["nodes"][node_id] = existing
        else:
            merged["nodes"].pop(node_id, None)

    for domain, entry in override.get("domains", {}).items():
        existing = merged["domains"].get(domain, {})
        existing.update(entry)
        existing = {k: v for k, v in existing.items() if v is not None}
        if existing:
            merged["domains"][domain] = existing
        else:
            merged["domains"].pop(domain, None)

    merged_global = merged.get("global", {})
    merged_global.update(override.get("global", {}))
    merged["global"] = merged_global
    return merged


def _normalize_curation(data: object) -> dict[str, object]:
    """Ensure a raw dict has all expected top-level keys."""
    if not isinstance(data, dict):
        return empty_curation()
    nodes = data.get("nodes", {})
    domains = data.get("domains", {})
    global_section = data.get("global", {})
    if not isinstance(nodes, dict):
        nodes = {}
    if not isinstance(domains, dict):
        domains = {}
    if not isinstance(global_section, dict):
        global_section = {}
    return {
        "version": data.get("version", CURATION_VERSION),
        "nodes": dict(nodes),
        "domains": dict(domains),
        "global": {
            "defaultCollapsedDomains": list(
                global_section.get("defaultCollapsedDomains", [])
            ),
        },
    }


# ---------------------------------------------------------------------------
# Curation accessors (read-time convenience)
# ---------------------------------------------------------------------------


def is_node_hidden(curation: dict[str, object], node_id: str) -> bool:
    """Check if a node is marked hidden in curation."""
    entry = curation.get("nodes", {}).get(node_id, {})
    return bool(entry.get("hidden", False))


def is_node_featured(curation: dict[str, object], node_id: str) -> bool:
    """Check if a node is marked featured/pinned in curation."""
    entry = curation.get("nodes", {}).get(node_id, {})
    return bool(entry.get("featured", False))


def node_public_label(curation: dict[str, object], node_id: str) -> str | None:
    """Return the public label override for a node, or None."""
    entry = curation.get("nodes", {}).get(node_id, {})
    label = entry.get("publicLabel")
    return str(label) if label else None


def node_public_note(curation: dict[str, object], node_id: str) -> str | None:
    """Return the public note override for a node, or None."""
    entry = curation.get("nodes", {}).get(node_id, {})
    note = entry.get("publicNote")
    return str(note) if note else None


def is_low_confidence_approved(curation: dict[str, object], node_id: str) -> bool:
    """Check if a low-confidence node is explicitly approved for publish."""
    entry = curation.get("nodes", {}).get(node_id, {})
    return bool(entry.get("approveLowConfidence", False))


def is_disputed_approved(curation: dict[str, object], node_id: str) -> bool:
    """Check if a disputed/review node is explicitly approved for publish."""
    entry = curation.get("nodes", {}).get(node_id, {})
    return bool(entry.get("approveDisputed", False))


def is_domain_collapsed(curation: dict[str, object], domain: str) -> bool:
    """Check if a domain is marked collapsed by default in curation."""
    entry = curation.get("domains", {}).get(domain, {})
    return bool(entry.get("collapsed", False))


def domain_public_label(curation: dict[str, object], domain: str) -> str | None:
    """Return the public label override for a domain, or None."""
    entry = curation.get("domains", {}).get(domain, {})
    label = entry.get("publicLabel")
    return str(label) if label else None


# ---------------------------------------------------------------------------
# Publish: redacted public bundle generation
# ---------------------------------------------------------------------------


def build_public_bundle(
    raw_graph: dict[str, object],
    curation: dict[str, object] | None = None,
    *,
    enable_sound: bool = True,
    low_confidence_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
) -> tuple[dict[str, object], dict[str, str]]:
    """Build a redacted public graph bundle from the internal graph + curation.

    Returns a tuple of ``(public_graph, alias_map)``.

    The ``public_graph`` is the separate public contract (decision 50) with
    only intentionally public fields. The ``alias_map`` maps internal node
    IDs to public alias IDs for sensitive IDs (decision 51); it is empty when
    no IDs need aliasing and must be kept admin-only.

    Excludes (decisions 25, 29, 46-50):
    - Hidden nodes (curation ``hidden`` or internal ``status=hidden``)
    - Disputed/review nodes unless explicitly approved in curation
    - Low-confidence nodes unless explicitly approved in curation
    - Hidden edges (any edge touching an excluded node)
    - Raw source paths, raw excerpts, sensitive evidence IDs
    - Private/redacted provenance detail

    Applies curation overrides:
    - Public label/note overrides replace internal labels
    - Featured/pin status is carried as a public flag
    """
    if curation is None:
        curation = empty_curation()

    raw_nodes = raw_graph.get("nodes", [])
    raw_edges = raw_graph.get("edges", [])
    if not isinstance(raw_nodes, list):
        raw_nodes = []
    if not isinstance(raw_edges, list):
        raw_edges = []

    # First pass: determine which nodes survive the publish filter.
    surviving_node_ids: set[str] = set()
    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            continue
        node_id = str(raw_node.get("id") or "")
        if not node_id:
            continue
        if not _should_publish_node(
            raw_node, curation, low_confidence_threshold=low_confidence_threshold
        ):
            continue
        surviving_node_ids.add(node_id)

    # Build alias map for sensitive IDs (decision 51).
    alias_map = _build_alias_map(surviving_node_ids)

    # Second pass: project surviving nodes into the public contract.
    public_nodes: list[dict[str, object]] = []
    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            continue
        node_id = str(raw_node.get("id") or "")
        if node_id not in surviving_node_ids:
            continue
        public_node = _project_public_node(raw_node, curation, alias_map)
        public_nodes.append(public_node)

    # Third pass: filter edges to only those between surviving nodes.
    public_edges: list[dict[str, object]] = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, dict):
            continue
        from_id = _edge_endpoint(raw_edge, ("from_skill_id", "fromSkillId", "from"))
        to_id = _edge_endpoint(raw_edge, ("to_skill_id", "toSkillId", "to"))
        if from_id not in surviving_node_ids or to_id not in surviving_node_ids:
            continue
        public_edges.append(
            {
                "edgeId": str(
                    raw_edge.get("edge_id") or raw_edge.get("edgeId")
                    or f"{from_id}->{to_id}"
                ),
                "fromId": alias_map.get(from_id, from_id),
                "toId": alias_map.get(to_id, to_id),
                "edgeType": str(
                    raw_edge.get("edge_type") or raw_edge.get("edgeType") or "related_to"
                ),
                "weight": float(raw_edge.get("weight") or 0.5),
            }
        )

    metadata = raw_graph.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    public_metadata = {
        "generated_by": "traccia-viewer-v1",
        "source_generated_by": metadata.get("generated_by"),
        "enableSound": enable_sound,
    }

    public_graph = {
        "nodes": public_nodes,
        "edges": public_edges,
        "metadata": public_metadata,
    }
    return public_graph, alias_map


def _should_publish_node(
    raw_node: dict[str, object],
    curation: dict[str, object],
    *,
    low_confidence_threshold: float,
) -> bool:
    """Determine if a node should appear in the public bundle.

    A node is excluded if:
    - It is hidden via curation override (decision 23).
    - Its internal status is hidden, disputed, or review, and curation has
      not explicitly approved disputed/review nodes (decisions 46, 50).
    - Its confidence is below the low-confidence threshold and curation has
      not explicitly approved it (decision 47).
    """
    node_id = str(raw_node.get("id") or "")

    # Curation hidden override takes top priority.
    if is_node_hidden(curation, node_id):
        return False

    status = str(raw_node.get("status") or "active").lower()

    # Hidden internal status is always excluded.
    if status == "hidden":
        return False

    # Disputed/review nodes need explicit admin approval (decision 46).
    if status in ("disputed", "review") and not is_disputed_approved(
        curation, node_id
    ):
        return False

    # Low-confidence nodes need explicit admin approval (decision 47).
    confidence = float(raw_node.get("confidence") or 0.0)
    return not (
        confidence < low_confidence_threshold
        and not is_low_confidence_approved(curation, node_id)
    )


def _build_alias_map(node_ids: set[str]) -> dict[str, str]:
    """Generate stable public alias IDs for sensitive internal node IDs.

    Public IDs remain the same as internal IDs unless a skill ID contains
    characters that suggest it leaks private information (email addresses,
    file paths, spaces, etc). For those, a deterministic ``pub_<hash>``
    alias is generated (decision 51).

    The mapping is returned as ``{internal_id: public_alias}`` and must be
    kept admin-only; it never ships in the public bundle.
    """
    alias_map: dict[str, str] = {}
    for node_id in sorted(node_ids):
        if _is_sensitive_id(node_id):
            alias_map[node_id] = _stable_alias(node_id)
    return alias_map


def _is_sensitive_id(node_id: str) -> bool:
    """Check if a node ID may leak private information (decision 51)."""
    return any(pattern in node_id for pattern in _SENSITIVE_ID_PATTERNS)


def _stable_alias(node_id: str) -> str:
    """Generate a deterministic public alias for a sensitive internal ID."""
    digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:12]
    return f"pub_{digest}"


def _edge_endpoint(edge: dict[str, object], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = edge.get(key)
        if value:
            return str(value)
    return ""


def _project_public_node(
    raw_node: dict[str, object],
    curation: dict[str, object],
    alias_map: dict[str, str],
) -> dict[str, object]:
    """Build a single public-safe node with curation overrides applied."""
    node_id = str(raw_node["id"])
    public_id = alias_map.get(node_id, node_id)

    domain = _domain_for_node(raw_node)
    domain_label = domain_public_label(curation, domain) or domain
    description = _public_description(raw_node)
    public_note = node_public_note(curation, node_id)
    public_label = node_public_label(curation, node_id)

    name = str(raw_node.get("name") or raw_node.get("id") or "unknown")
    if public_label:
        name = public_label

    public_node: dict[str, object] = {
        "id": public_id,
        "name": name,
        "kind": str(raw_node.get("kind") or "skill"),
        "domain": domain_label,
        "description": description,
        "level": int(raw_node.get("level") or 0),
        "confidence": float(raw_node.get("confidence") or 0.0),
        "freshness": str(raw_node.get("freshness") or "historical"),
        "status": str(raw_node.get("status") or "active"),
        "coreSelfCentrality": float(raw_node.get("coreSelfCentrality") or 0.0),
        "historicalPeakLevel": int(
            raw_node.get("historicalPeakLevel") or raw_node.get("level") or 0
        ),
        "provenanceSummary": _provenance_summary(raw_node.get("provenance")),
        "featured": is_node_featured(curation, node_id),
    }

    if public_note:
        public_node["publicNote"] = public_note

    # Optional public-safe timestamp fields.
    for field in (
        "historicalPeakAt",
        "acquiredAt",
        "acquisitionBasis",
        "firstLearnedAt",
        "lastEvidenceAt",
    ):
        value = raw_node.get(field)
        if value not in (None, ""):
            public_node[field] = value

    return public_node


def _domain_for_node(raw_node: dict[str, object]) -> str:
    """Extract the domain label for a node."""
    description = str(raw_node.get("description") or "")
    if "::" in description:
        return description.split("::", maxsplit=1)[0].strip() or "Uncategorized"
    kind = str(raw_node.get("kind") or "")
    if kind == "domain":
        return str(raw_node.get("name") or "Uncategorized")
    return "Uncategorized"


def _public_description(raw_node: dict[str, object]) -> str:
    """Return a public-safe description for a node."""
    description = str(raw_node.get("description") or "")
    if "::" in description:
        parts = description.split("::", maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            return parts[1].strip()
        return ""
    return description


def _provenance_summary(raw_provenance: object) -> dict[str, object]:
    """Aggregate raw per-evidence provenance into a public-safe summary.

    Per decisions 29, 49, and 50: no raw excerpts, no raw evidence IDs, no
    raw source paths. Produces counts, evidence-type breakdowns, reliability
    tier breakdowns, source-category breakdowns, and timestamp range.
    """
    if not isinstance(raw_provenance, list) or not raw_provenance:
        return _empty_provenance_summary()

    evidence_types: dict[str, int] = {}
    reliability_tiers: dict[str, int] = {}
    source_categories: dict[str, int] = {}
    source_families: dict[str, int] = {}
    timestamps: list[str] = []
    strong_count = 0

    for item in raw_provenance:
        if not isinstance(item, dict):
            continue
        evidence_type = str(item.get("evidenceType") or "mentioned")
        evidence_types[evidence_type] = evidence_types.get(evidence_type, 0) + 1
        if evidence_type in _STRONG_EVIDENCE_TYPES:
            strong_count += 1

        reliability = str(item.get("reliability") or "tier_d")
        reliability_tiers[reliability] = reliability_tiers.get(reliability, 0) + 1

        source = item.get("source")
        if isinstance(source, dict):
            category = str(source.get("sourceCategory") or "unknown")
            source_categories[category] = source_categories.get(category, 0) + 1
            family = str(source.get("sourceFamily") or "unknown")
            source_families[family] = source_families.get(family, 0) + 1

        time_ref = item.get("timeReference")
        if isinstance(time_ref, str) and time_ref:
            timestamps.append(time_ref)

    timestamps.sort()

    return {
        "evidenceCount": len(raw_provenance),
        "evidenceTypes": dict(sorted(evidence_types.items())),
        "reliabilityTiers": dict(sorted(reliability_tiers.items())),
        "sourceCategories": dict(sorted(source_categories.items())),
        "sourceFamilies": dict(sorted(source_families.items())),
        "earliestAt": timestamps[0] if timestamps else None,
        "latestAt": timestamps[-1] if timestamps else None,
        "strongEvidenceCount": strong_count,
    }


def _empty_provenance_summary() -> dict[str, object]:
    return {
        "evidenceCount": 0,
        "evidenceTypes": {},
        "reliabilityTiers": {},
        "sourceCategories": {},
        "sourceFamilies": {},
        "earliestAt": None,
        "latestAt": None,
        "strongEvidenceCount": 0,
    }
