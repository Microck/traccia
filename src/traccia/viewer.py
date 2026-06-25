"""Finished-run skill graph viewer export (Phases 1 and 2).

Phase 1 produces the read-only public viewer: a self-contained static export
folder from ``graph/graph.json``, projected into a separate public graph
contract that contains only public-safe fields.

Phase 2 adds the admin curation viewer and the publish workflow:
- ``export_admin_viewer`` writes a full-graph admin viewer plus curation.json
  so an admin can hide/mute, restore, feature/pin, collapse/expand domains,
  and add public label/note overrides.
- ``publish_public_bundle`` generates a separate redacted public bundle from
  ``graph.json + curation.json``, physically excluding hidden nodes, hidden
  edges, private/redacted provenance, raw source paths, raw excerpts,
  sensitive evidence IDs, disputed/review nodes (unless approved), and
  low-confidence nodes (unless approved).

Design contract (see docs/finished-run-viewer-decisions.md).
"""

from __future__ import annotations

import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Node statuses that are never included in the public bundle.
# The viewer is read-only public: hidden, disputed, and review-state nodes
# are admin-visible only by default (decisions 46, 47).
_PUBLIC_HIDDEN_STATUSES = frozenset({"hidden", "disputed", "review"})

# Fields from the internal graph node that are intentionally NOT carried into
# the public graph contract (decision 50).
_PUBLIC_NODE_FIELDS = (
    "id",
    "name",
    "kind",
    "domain",
    "description",
    "level",
    "confidence",
    "freshness",
    "status",
    "coreSelfCentrality",
    "historicalPeakLevel",
    "historicalPeakAt",
    "acquiredAt",
    "acquisitionBasis",
    "firstLearnedAt",
    "lastEvidenceAt",
    "provenanceSummary",
)

# Fields from the internal edge that survive into the public graph contract.
_PUBLIC_EDGE_FIELDS = (
    "edgeId",
    "fromId",
    "toId",
    "edgeType",
    "weight",
)

# The source tree ships the normalized viewer font subset so clean checkouts
# export the same typography. The ignored private font folder remains a local
# override path for foundry/source packages when rebuilding or experimenting.
_VIEWER_COMMITTED_FONT_SOURCE_DIR = Path(__file__).with_name("assets") / "fonts"
_VIEWER_DIATYPE_FONT_SOURCE_DIR = (
    Path(__file__).resolve().parents[2] / "private" / "font-assets" / "abc-diatype-fonts"
)
_VIEWER_FORMA_FONT_SOURCE_DIR = (
    Path(__file__).resolve().parents[2] / "private" / "font-assets" / "forma-djr-fonts"
)
_VIEWER_FONT_ASSET_ROOT = Path(__file__).resolve().parents[2] / "private" / "font-assets"
_VIEWER_FAVICON_SOURCE = Path(__file__).with_name("assets") / "favicon.svg"
_VIEWER_MIXED_FONT_FILES = (
    (
        "Traccia UI",
        400,
        "traccia-ui-regular.ttf",
        (
            "forma-djr-fonts/FormaDJRText-Regular.ttf",
            "forma-djr-fonts/FormaDJRText-Regular-Testing.ttf",
        ),
    ),
    (
        "Traccia UI",
        500,
        "traccia-ui-medium.ttf",
        (
            "forma-djr-fonts/FormaDJRText-Medium.ttf",
            "forma-djr-fonts/FormaDJRText-Medium-Testing.ttf",
        ),
    ),
    (
        "Traccia UI",
        700,
        "traccia-ui-bold.ttf",
        (
            "forma-djr-fonts/FormaDJRText-Bold.ttf",
            "forma-djr-fonts/FormaDJRText-Bold-Testing.ttf",
        ),
    ),
    (
        "Traccia Label",
        400,
        "traccia-label-regular.ttf",
        (
            "forma-djr-fonts/FormaDJRMicro-Regular.ttf",
            "forma-djr-fonts/FormaDJRMicro-Regular-Testing.ttf",
        ),
    ),
    (
        "Traccia Label",
        500,
        "traccia-label-medium.ttf",
        (
            "forma-djr-fonts/FormaDJRMicro-Medium.ttf",
            "forma-djr-fonts/FormaDJRMicro-Medium-Testing.ttf",
        ),
    ),
    (
        "Traccia Label",
        700,
        "traccia-label-bold.ttf",
        (
            "forma-djr-fonts/FormaDJRMicro-Bold.ttf",
            "forma-djr-fonts/FormaDJRMicro-Bold-Testing.ttf",
        ),
    ),
    (
        "Traccia Display",
        400,
        "traccia-display-regular.ttf",
        ("abc-diatype-fonts/Diatype-Extended/ABCDiatypeExtended-Regular.ttf",),
    ),
    (
        "Traccia Display",
        500,
        "traccia-display-medium.ttf",
        ("abc-diatype-fonts/Diatype-Extended/ABCDiatypeExtended-Medium.ttf",),
    ),
    (
        "Traccia Display",
        700,
        "traccia-display-bold.ttf",
        ("abc-diatype-fonts/Diatype-Extended/ABCDiatypeExtended-Bold.ttf",),
    ),
    (
        "Traccia Mono",
        400,
        "traccia-mono-regular.ttf",
        ("abc-diatype-fonts/Diatype-Semi-Mono/ABCDiatypeSemi-Mono-Regular.ttf",),
    ),
    (
        "Traccia Mono",
        500,
        "traccia-mono-medium.ttf",
        ("abc-diatype-fonts/Diatype-Semi-Mono/ABCDiatypeSemi-Mono-Medium.ttf",),
    ),
    (
        "Traccia Mono",
        700,
        "traccia-mono-bold.ttf",
        ("abc-diatype-fonts/Diatype-Semi-Mono/ABCDiatypeSemi-Mono-Bold.ttf",),
    ),
)
_VIEWER_FORMA_FONT_FILES = (
    (
        "Traccia UI",
        400,
        "traccia-ui-regular.ttf",
        ("FormaDJRText-Regular.ttf", "FormaDJRText-Regular-Testing.ttf"),
    ),
    (
        "Traccia UI",
        500,
        "traccia-ui-medium.ttf",
        ("FormaDJRText-Medium.ttf", "FormaDJRText-Medium-Testing.ttf"),
    ),
    (
        "Traccia UI",
        700,
        "traccia-ui-bold.ttf",
        ("FormaDJRText-Bold.ttf", "FormaDJRText-Bold-Testing.ttf"),
    ),
    (
        "Traccia Label",
        400,
        "traccia-label-regular.ttf",
        ("FormaDJRMicro-Regular.ttf", "FormaDJRMicro-Regular-Testing.ttf"),
    ),
    (
        "Traccia Label",
        500,
        "traccia-label-medium.ttf",
        ("FormaDJRMicro-Medium.ttf", "FormaDJRMicro-Medium-Testing.ttf"),
    ),
    (
        "Traccia Label",
        700,
        "traccia-label-bold.ttf",
        ("FormaDJRMicro-Bold.ttf", "FormaDJRMicro-Bold-Testing.ttf"),
    ),
    (
        "Traccia Display",
        400,
        "traccia-display-regular.ttf",
        ("FormaDJRDeck-Regular.ttf", "FormaDJRDeck-Regular-Testing.ttf"),
    ),
    (
        "Traccia Display",
        500,
        "traccia-display-medium.ttf",
        ("FormaDJRDeck-Medium.ttf", "FormaDJRDeck-Medium-Testing.ttf"),
    ),
    (
        "Traccia Display",
        700,
        "traccia-display-bold.ttf",
        ("FormaDJRDeck-Bold.ttf", "FormaDJRDeck-Bold-Testing.ttf"),
    ),
    (
        "Traccia Mono",
        400,
        "traccia-mono-regular.otf",
        ("FormaDJRMono-Regular.otf", "FormaDJRMono-Regular-Testing.otf"),
    ),
    (
        "Traccia Mono",
        500,
        "traccia-mono-medium.otf",
        ("FormaDJRMono-Medium.otf", "FormaDJRMono-Medium-Testing.otf"),
    ),
    (
        "Traccia Mono",
        700,
        "traccia-mono-bold.otf",
        ("FormaDJRMono-Bold.otf", "FormaDJRMono-Bold-Testing.otf"),
    ),
)
_VIEWER_DIATYPE_FONT_FILES = (
    (
        "Traccia UI",
        400,
        "traccia-ui-regular.ttf",
        ("ABC Diatype Regular.ttf", "Diatype/ABC Diatype Regular.ttf"),
    ),
    (
        "Traccia UI",
        500,
        "traccia-ui-medium.ttf",
        ("ABC Diatype Medium.ttf", "Diatype/ABC Diatype Medium.ttf"),
    ),
    (
        "Traccia UI",
        700,
        "traccia-ui-bold.ttf",
        ("ABC Diatype Bold.ttf", "Diatype/ABC Diatype Bold.ttf"),
    ),
    (
        "Traccia Label",
        400,
        "traccia-label-regular.ttf",
        ("ABC Diatype Regular.ttf", "Diatype/ABC Diatype Regular.ttf"),
    ),
    (
        "Traccia Label",
        500,
        "traccia-label-medium.ttf",
        ("ABC Diatype Medium.ttf", "Diatype/ABC Diatype Medium.ttf"),
    ),
    (
        "Traccia Label",
        700,
        "traccia-label-bold.ttf",
        ("ABC Diatype Bold.ttf", "Diatype/ABC Diatype Bold.ttf"),
    ),
    (
        "Traccia Display",
        400,
        "traccia-display-regular.ttf",
        ("Diatype-Extended/ABCDiatypeExtended-Regular.ttf",),
    ),
    (
        "Traccia Display",
        500,
        "traccia-display-medium.ttf",
        ("Diatype-Extended/ABCDiatypeExtended-Medium.ttf",),
    ),
    (
        "Traccia Display",
        700,
        "traccia-display-bold.ttf",
        ("Diatype-Extended/ABCDiatypeExtended-Bold.ttf",),
    ),
    (
        "Traccia Mono",
        400,
        "traccia-mono-regular.ttf",
        ("Diatype-Semi-Mono/ABCDiatypeSemi-Mono-Regular.ttf",),
    ),
    (
        "Traccia Mono",
        500,
        "traccia-mono-medium.ttf",
        ("Diatype-Semi-Mono/ABCDiatypeSemi-Mono-Medium.ttf",),
    ),
    (
        "Traccia Mono",
        700,
        "traccia-mono-bold.ttf",
        ("Diatype-Semi-Mono/ABCDiatypeSemi-Mono-Bold.ttf",),
    ),
)
_VIEWER_COMMITTED_FONT_FILES = tuple(
    (family, weight, target_name, (target_name,))
    for family, weight, target_name, _candidates in _VIEWER_MIXED_FONT_FILES
)
_VIEWER_FONT_PACKAGES = (
    ("committed-viewer-subset", _VIEWER_COMMITTED_FONT_SOURCE_DIR, _VIEWER_COMMITTED_FONT_FILES),
    ("mixed-forma-diatype", _VIEWER_FONT_ASSET_ROOT, _VIEWER_MIXED_FONT_FILES),
    ("forma", _VIEWER_FORMA_FONT_SOURCE_DIR, _VIEWER_FORMA_FONT_FILES),
    ("diatype", _VIEWER_DIATYPE_FONT_SOURCE_DIR, _VIEWER_DIATYPE_FONT_FILES),
)


def _font_package_missing_files(
    font_source_dir: Path, font_files: tuple[tuple[str, int, str, tuple[str, ...]], ...]
) -> list[str]:
    missing = []
    for family, weight, _target_name, candidates in font_files:
        if _find_viewer_font_file(font_source_dir, candidates) is None:
            choices = ", ".join(str(font_source_dir / candidate) for candidate in candidates)
            missing.append(f"{family} {weight}: {choices}")
    return missing


def _resolve_viewer_font_package() -> (
    tuple[str, Path, tuple[tuple[str, int, str, tuple[str, ...]], ...]] | None
):
    """Return the first complete local viewer font package."""
    configured = os.environ.get("TRACCIA_VIEWER_FONT_DIR")
    if configured:
        font_dir = Path(configured).expanduser()
        if not font_dir.exists():
            raise FileNotFoundError(
                "TRACCIA_VIEWER_FONT_DIR points to a missing directory: "
                f"{font_dir}"
            )
        for package_name, _default_dir, font_files in _VIEWER_FONT_PACKAGES:
            if not _font_package_missing_files(font_dir, font_files):
                return package_name, font_dir, font_files
        raise FileNotFoundError(
            "TRACCIA_VIEWER_FONT_DIR does not contain a complete supported "
            f"viewer font package: {font_dir}"
        )

    for package_name, font_dir, font_files in _VIEWER_FONT_PACKAGES:
        if font_dir.exists() and not _font_package_missing_files(font_dir, font_files):
            return package_name, font_dir, font_files
    return None


def _find_viewer_font_file(font_source_dir: Path, candidates: tuple[str, ...]) -> Path | None:
    for candidate in candidates:
        font_path = font_source_dir / candidate
        if font_path.exists():
            return font_path
    return None


def _viewer_font_face_css(
    copied_fonts: list[tuple[str, int, str]]
) -> str:
    blocks = []
    for family, weight, target_name in copied_fonts:
        font_format = "opentype" if target_name.lower().endswith(".otf") else "truetype"
        blocks.append(
            "\n".join(
                (
                    "@font-face {",
                    f'  font-family: "{family}";',
                    f'  src: url("fonts/{target_name}") format("{font_format}");',
                    f"  font-weight: {weight};",
                    "  font-style: normal;",
                    "  font-display: swap;",
                    "}",
                )
            )
        )
    return "\n".join(blocks) + "\n\n" if blocks else ""


def _copy_viewer_font_assets(assets_dir: Path) -> str:
    """Copy the resolved viewer font package into a generated viewer bundle."""
    fonts_dir = assets_dir / "fonts"
    if fonts_dir.exists():
        shutil.rmtree(fonts_dir)

    font_package = _resolve_viewer_font_package()
    if font_package is None:
        return ""
    _package_name, font_source_dir, font_files = font_package

    missing = _font_package_missing_files(font_source_dir, font_files)
    if missing:
        missing_list = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Viewer font assets are incomplete:\n" + missing_list
        )

    fonts_dir.mkdir(parents=True, exist_ok=True)
    copied_fonts = []
    for family, weight, target_name, candidates in font_files:
        source_path = _find_viewer_font_file(font_source_dir, candidates)
        if source_path is None:
            continue
        shutil.copyfile(source_path, fonts_dir / target_name)
        copied_fonts.append((family, weight, target_name))
    return _viewer_font_face_css(copied_fonts)


def _copy_viewer_favicon_asset(assets_dir: Path) -> None:
    """Copy the package favicon into a generated static viewer bundle."""
    if not _VIEWER_FAVICON_SOURCE.exists():
        raise FileNotFoundError(f"Viewer favicon asset is missing: {_VIEWER_FAVICON_SOURCE}")
    shutil.copyfile(_VIEWER_FAVICON_SOURCE, assets_dir / "favicon.svg")


def export_viewer(project_root: Path, *, enable_sound: bool = True) -> Path:
    """Generate the read-only public viewer bundle into ``exports/viewer/``.

    Reads the existing ``graph/graph.json``, projects it into a public-safe
    graph contract, and writes the static viewer assets alongside the public
    data. Returns the path to the generated export folder.

    If a ``curation.json`` exists in the project root or in
    ``exports/viewer/``, its overrides are applied during projection.
    """
    # Import here to avoid a module-level circular dependency.
    from traccia.curation import build_public_bundle, load_curation

    graph_path = project_root / "graph" / "graph.json"
    raw_graph = json.loads(graph_path.read_text())

    curation = load_curation(project_root / "exports" / "viewer" / "curation.json")
    public_graph, _alias_map = build_public_bundle(
        raw_graph, curation, enable_sound=enable_sound
    )

    export_root = project_root / "exports" / "viewer"
    export_root.mkdir(parents=True, exist_ok=True)

    (export_root / "graph.json").write_text(json.dumps(public_graph, indent=2) + "\n")
    (export_root / "config.json").write_text(
        json.dumps({"enableSound": enable_sound, "version": 1}, indent=2) + "\n"
    )

    write_viewer_assets(export_root)
    return export_root


def build_public_graph(raw_graph: dict[str, object]) -> dict[str, object]:
    """Project the internal graph payload into a public-safe contract.

    This strips raw provenance detail, excerpts, source paths, hidden/private
    nodes, and hidden/private edges. It replaces per-evidence provenance with
    aggregated public-safe summaries (counts, evidence types, reliability
    tiers, source categories, timestamps) per decisions 49 and 50.
    """
    raw_nodes = raw_graph.get("nodes", [])
    raw_edges = raw_graph.get("edges", [])
    if not isinstance(raw_nodes, list):
        raw_nodes = []
    if not isinstance(raw_edges, list):
        raw_edges = []

    public_nodes: list[dict[str, object]] = []
    public_node_ids: set[str] = set()

    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            continue
        status = str(raw_node.get("status") or "active").lower()
        if status in _PUBLIC_HIDDEN_STATUSES:
            continue
        # Decision 47: do not publish low-confidence nodes by default.
        confidence = float(raw_node.get("confidence") or 0.0)
        if confidence < 0.25:
            continue

        public_node = _project_public_node(raw_node)
        public_nodes.append(public_node)
        public_node_ids.add(str(public_node["id"]))

    public_edges: list[dict[str, object]] = []
    for raw_edge in raw_edges:
        if not isinstance(raw_edge, dict):
            continue
        from_id = _edge_endpoint(raw_edge, ("from_skill_id", "fromSkillId", "from"))
        to_id = _edge_endpoint(raw_edge, ("to_skill_id", "toSkillId", "to"))
        if from_id not in public_node_ids or to_id not in public_node_ids:
            continue
        edge_type = str(raw_edge.get("edge_type") or raw_edge.get("edgeType") or "related_to")
        weight = float(raw_edge.get("weight") or 0.5)
        public_edges.append(
            {
                "edgeId": str(raw_edge.get("edge_id") or raw_edge.get("edgeId") or f"{from_id}->{to_id}"),
                "fromId": from_id,
                "toId": to_id,
                "edgeType": edge_type,
                "weight": weight,
            }
        )

    metadata = raw_graph.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    public_metadata = {
        "generated_by": "traccia-viewer-v1",
        "source_generated_by": metadata.get("generated_by"),
    }

    return {
        "nodes": public_nodes,
        "edges": public_edges,
        "metadata": public_metadata,
    }


def _edge_endpoint(edge: dict[str, object], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = edge.get(key)
        if value:
            return str(value)
    return ""


def _project_public_node(raw_node: dict[str, object]) -> dict[str, object]:
    """Build a single public-safe node from an internal graph node."""
    domain = _domain_for_node(raw_node)
    description = _public_description(raw_node)
    provenance_summary = _provenance_summary(raw_node.get("provenance"))

    public_node: dict[str, object] = {
        "id": str(raw_node["id"]),
        "name": str(raw_node.get("name") or raw_node.get("id") or "unknown"),
        "kind": str(raw_node.get("kind") or "skill"),
        "domain": domain,
        "description": description,
        "level": int(raw_node.get("level") or 0),
        "confidence": float(raw_node.get("confidence") or 0.0),
        "freshness": str(raw_node.get("freshness") or "historical"),
        "status": str(raw_node.get("status") or "active"),
        "coreSelfCentrality": float(raw_node.get("coreSelfCentrality") or 0.0),
        "historicalPeakLevel": int(
            raw_node.get("historicalPeakLevel") or raw_node.get("level") or 0
        ),
        "provenanceSummary": provenance_summary,
    }

    # Optional timestamp fields, carried only when present (public-safe).
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

    # Defensive: only keep whitelisted public fields.
    return {key: value for key, value in public_node.items() if key in _PUBLIC_NODE_FIELDS}


def _domain_for_node(raw_node: dict[str, object]) -> str:
    """Extract the domain label for a node.

    Internal graph nodes store domain context inside the description as
    ``Domain::branch detail``. This splits that so the viewer can group by
    domain without leaking the full internal description verbatim when it
    contains sensitive branch notes.
    """
    description = str(raw_node.get("description") or "")
    if "::" in description:
        return description.split("::", maxsplit=1)[0].strip() or "Uncategorized"
    kind = str(raw_node.get("kind") or "")
    if kind == "domain":
        return str(raw_node.get("name") or "Uncategorized")
    return "Uncategorized"


def _public_description(raw_node: dict[str, object]) -> str:
    """Return a public-safe description for a node.

    The internal description may carry ``Domain::branch detail``. For the
    public bundle, the branch detail after ``::`` is the meaningful skill
    description. If no ``::`` separator exists, the description is passed
    through as-is (it is already considered public-safe label text).
    """
    description = str(raw_node.get("description") or "")
    if "::" in description:
        parts = description.split("::", maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            return parts[1].strip()
        return ""
    return description


def _provenance_summary(raw_provenance: object) -> dict[str, object]:
    """Aggregate raw per-evidence provenance into a public-safe summary.

    Per decisions 29, 49, and 50: no raw excerpts, no raw evidence IDs, no raw
    source paths. This produces counts, evidence-type breakdowns, reliability
    tier breakdowns, source-category breakdowns, and timestamp range, which
    are all public-safe metadata about evidence strength.
    """
    if not isinstance(raw_provenance, list) or not raw_provenance:
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

    evidence_types: dict[str, int] = defaultdict(int)
    reliability_tiers: dict[str, int] = defaultdict(int)
    source_categories: dict[str, int] = defaultdict(int)
    source_families: dict[str, int] = defaultdict(int)
    timestamps: list[str] = []
    strong_count = 0

    strong_types = {"implemented", "designed", "debugged", "taught", "produced_artifact"}

    for item in raw_provenance:
        if not isinstance(item, dict):
            continue
        evidence_type = str(item.get("evidenceType") or "mentioned")
        evidence_types[evidence_type] += 1
        if evidence_type in strong_types:
            strong_count += 1

        reliability = str(item.get("reliability") or "tier_d")
        reliability_tiers[reliability] += 1

        source = item.get("source")
        if isinstance(source, dict):
            category = str(source.get("sourceCategory") or "unknown")
            source_categories[category] += 1
            family = str(source.get("sourceFamily") or "unknown")
            source_families[family] += 1

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


# ---------------------------------------------------------------------------
# Static viewer asset writing
# ---------------------------------------------------------------------------

# Assets are co-located as Python string constants so the export stays
# self-contained, has no build step, and ships inside the wheel. Phase 1
# intentionally avoids a JS bundler.

from traccia.viewer_assets import (  # noqa: E402  - circular-safe local import
    VIEWER_CSS,
    VIEWER_HTML,
    VIEWER_JS,
    VIEWER_SFX_JS,
)


def write_viewer_assets(export_root: Path) -> None:
    """Write the static HTML, CSS, JS, and SFX engine into the export folder."""
    assets_dir = export_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    font_css = _copy_viewer_font_assets(assets_dir)
    _copy_viewer_favicon_asset(assets_dir)

    (export_root / "index.html").write_text(VIEWER_HTML)
    (assets_dir / "viewer.css").write_text(font_css + VIEWER_CSS)
    (assets_dir / "viewer.js").write_text(VIEWER_JS)
    (assets_dir / "sfx.js").write_text(VIEWER_SFX_JS)


# ---------------------------------------------------------------------------
# Phase 2: admin curation viewer export
# ---------------------------------------------------------------------------

from traccia.viewer_assets import (  # noqa: E402  - circular-safe local import
    ADMIN_VIEWER_CSS,
    ADMIN_VIEWER_HTML,
    ADMIN_VIEWER_JS,
)


def export_admin_viewer(project_root: Path, *, enable_sound: bool = True) -> Path:
    """Generate the admin curation viewer bundle into ``exports/viewer-admin/``.

    The admin viewer loads the full ``graph.json`` (admin-visible, includes
    hidden/disputed/review/low-confidence nodes) plus an optional
    ``curation.json``. The admin can apply curation overrides (hide/mute,
    restore, feature/pin, collapse/expand domains, public label/note
    overrides) and save the result as ``curation.json``.

    When running locally (the export folder is on a writable filesystem),
    the admin viewer's save action writes ``curation.json`` directly into
    ``exports/viewer/curation.json`` so the publish step can consume it.
    When direct filesystem writes are not possible (browser-only), the save
    action triggers a browser download of ``curation.json``.

    Returns the path to the generated admin export folder.
    """
    graph_path = project_root / "graph" / "graph.json"
    raw_graph = json.loads(graph_path.read_text())

    export_root = project_root / "exports" / "viewer-admin"
    export_root.mkdir(parents=True, exist_ok=True)

    # The admin viewer consumes the FULL internal graph (not redacted).
    # This is the admin-only data; it never ships to the public bundle.
    (export_root / "graph.json").write_text(json.dumps(raw_graph, indent=2) + "\n")

    # Load or initialize curation.json so the admin viewer starts from the
    # current curation state. It is copied into the admin export folder so
    # the viewer can load it, and also symlinked/copied to the public viewer
    # folder location so the publish step finds it in the canonical spot.
    from traccia.curation import empty_curation, load_curation

    curation_path = project_root / "exports" / "viewer" / "curation.json"
    curation = load_curation(curation_path) if curation_path.exists() else empty_curation()
    (export_root / "curation.json").write_text(json.dumps(curation, indent=2) + "\n")

    # Write a compact summary of curation state for the admin viewer to
    # display without re-parsing the full curation file.
    curation_summary = _build_admin_curation_summary(raw_graph, curation)

    (export_root / "config.json").write_text(
        json.dumps(
            {
                "enableSound": enable_sound,
                "version": 1,
                "mode": "admin",
                "curationSummary": curation_summary,
            },
            indent=2,
        )
        + "\n"
    )

    write_admin_viewer_assets(export_root)
    return export_root


def _build_admin_curation_summary(
    raw_graph: dict[str, object], curation: dict[str, object]
) -> dict[str, object]:
    """Build a compact summary of how many nodes/domains have curation overrides."""
    from traccia.curation import (
        is_disputed_approved,
        is_domain_collapsed,
        is_low_confidence_approved,
        is_node_featured,
        is_node_hidden,
    )

    raw_nodes = raw_graph.get("nodes", [])
    if not isinstance(raw_nodes, list):
        raw_nodes = []

    hidden_count = 0
    featured_count = 0
    low_confidence_approved_count = 0
    disputed_approved_count = 0
    nodes_with_overrides = 0

    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            continue
        node_id = str(raw_node.get("id") or "")
        if not node_id:
            continue
        has_override = False
        if is_node_hidden(curation, node_id):
            hidden_count += 1
            has_override = True
        if is_node_featured(curation, node_id):
            featured_count += 1
            has_override = True
        if is_low_confidence_approved(curation, node_id):
            low_confidence_approved_count += 1
            has_override = True
        if is_disputed_approved(curation, node_id):
            disputed_approved_count += 1
            has_override = True
        if has_override:
            nodes_with_overrides += 1

    domains = curation.get("domains", {})
    collapsed_domains = [
        d for d in (domains.keys() if isinstance(domains, dict) else []) if is_domain_collapsed(curation, d)
    ]

    return {
        "totalNodes": len(raw_nodes),
        "hiddenCount": hidden_count,
        "featuredCount": featured_count,
        "lowConfidenceApprovedCount": low_confidence_approved_count,
        "disputedApprovedCount": disputed_approved_count,
        "nodesWithOverrides": nodes_with_overrides,
        "collapsedDomains": collapsed_domains,
    }


def write_admin_viewer_assets(export_root: Path) -> None:
    """Write the admin viewer HTML, CSS, and JS into the export folder."""
    assets_dir = export_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    font_css = _copy_viewer_font_assets(assets_dir)
    _copy_viewer_favicon_asset(assets_dir)

    # Admin viewer reuses the public SFX engine (same procedural sounds).
    (export_root / "index.html").write_text(ADMIN_VIEWER_HTML)
    (assets_dir / "admin.css").write_text(font_css + ADMIN_VIEWER_CSS)
    (assets_dir / "admin.js").write_text(ADMIN_VIEWER_JS)
    (assets_dir / "sfx.js").write_text(VIEWER_SFX_JS)


# ---------------------------------------------------------------------------
# Phase 2: publish redacted public bundle
# ---------------------------------------------------------------------------


def publish_public_bundle(
    project_root: Path, *, enable_sound: bool = True, output_dir: str | None = None
) -> Path:
    """Generate a redacted public bundle from ``graph.json + curation.json``.

    This is the publish step (decision 22, 25, 50). It reads the full internal
    graph and the admin-authored curation, applies all redaction rules, and
    writes a separate public bundle with its own viewer assets.

    The output goes to ``exports/viewer-public/`` by default (or the specified
    ``output_dir`` under ``exports/``). The public bundle is fully
    self-contained and safe to deploy publicly.

    Returns the path to the published public export folder.
    """
    from traccia.curation import build_public_bundle, load_curation

    graph_path = project_root / "graph" / "graph.json"
    raw_graph = json.loads(graph_path.read_text())

    curation = load_curation(project_root / "exports" / "viewer" / "curation.json")

    public_graph, alias_map = build_public_bundle(
        raw_graph, curation, enable_sound=enable_sound
    )

    folder_name = output_dir or "viewer-public"
    export_root = project_root / "exports" / folder_name
    export_root.mkdir(parents=True, exist_ok=True)

    (export_root / "graph.json").write_text(json.dumps(public_graph, indent=2) + "\n")
    (export_root / "config.json").write_text(
        json.dumps(
            {"enableSound": enable_sound, "version": 1, "mode": "public"},
            indent=2,
        )
        + "\n"
    )

    # Write the admin-only alias map next to the public bundle. This file
    # maps internal IDs to public aliases for sensitive IDs. It is NOT part
    # of the public bundle and must not be deployed. It exists so the admin
    # can resolve public IDs back to internal IDs when needed.
    if alias_map:
        (export_root / "alias-map.json").write_text(
            json.dumps(
                {"_admin_only": True, "mapping": alias_map}, indent=2
            )
            + "\n"
        )

    write_viewer_assets(export_root)
    return export_root
