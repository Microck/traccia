"""Tests for the finished-run public skill map viewer export.

Covers the public graph projection contract (decision 50), the static export
folder structure, and the CLI command surface.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import traccia.viewer as viewer_module
from traccia.cli import app
from traccia.config import load_config, write_config
from traccia.curation import (
    build_public_bundle,
    empty_curation,
    is_disputed_approved,
    is_domain_collapsed,
    is_low_confidence_approved,
    is_node_featured,
    is_node_hidden,
    load_curation,
    merge_curation,
    node_curation_entry,
    save_curation,
)
from traccia.viewer import (
    build_public_graph,
    export_admin_viewer,
    export_viewer,
    publish_public_bundle,
)


def initialize_repo(runner: CliRunner, project_root: Path) -> None:
    result = runner.invoke(app, ["init", str(project_root)])
    assert result.exit_code == 0, result.stdout
    config = load_config(project_root / "config" / "config.yaml")
    config.backend.provider = "fake"
    write_config(project_root / "config" / "config.yaml", config)


def ingest_corpus(runner: CliRunner, project_root: Path) -> str:
    corpus_root = Path("tests/fixtures/corpus").resolve()
    result = runner.invoke(
        app, ["ingest-dir", str(corpus_root), "--project-root", str(project_root)]
    )
    assert result.exit_code == 0, result.stdout
    return result.stdout


# ---------------------------------------------------------------------------
# build_public_graph unit tests
# ---------------------------------------------------------------------------


def test_build_public_graph_strips_raw_provenance_and_excerpts() -> None:
    """Public graph must not contain raw excerpts, evidence IDs, or source paths."""
    raw_graph = {
        "nodes": [
            {
                "id": "skill.python",
                "name": "Python",
                "kind": "skill",
                "description": "Programming::general purpose language",
                "level": 4,
                "confidence": 0.9,
                "freshness": "active",
                "status": "active",
                "coreSelfCentrality": 0.8,
                "historicalPeakLevel": 4,
                "provenance": [
                    {
                        "evidenceId": "ev_secret_123",
                        "sourceId": "src_secret_456",
                        "excerpt": "sensitive raw quote with /home/user/secret.py",
                        "evidenceType": "implemented",
                        "reliability": "tier_a",
                        "confidence": 0.95,
                        "source": {
                            "filename": "secret.py",
                            "uri": "file:///home/user/secret.py",
                            "sourceCategory": "produced_artifact",
                            "sourceFamily": "generic",
                        },
                    }
                ],
            }
        ],
        "edges": [],
        "metadata": {"generated_by": "traccia-renderer-v1"},
    }

    public = build_public_graph(raw_graph)
    assert len(public["nodes"]) == 1
    node = public["nodes"][0]

    # Public-safe fields present
    assert node["id"] == "skill.python"
    assert node["name"] == "Python"
    assert node["domain"] == "Programming"
    assert node["level"] == 4
    assert node["confidence"] == 0.9

    # Description should be the branch detail after ::
    assert "general purpose language" in node["description"]

    # No raw provenance
    assert "provenance" not in node
    assert "excerpt" not in json.dumps(node)
    assert "ev_secret" not in json.dumps(node)
    assert "src_secret" not in json.dumps(node)
    assert "file:///home" not in json.dumps(node)
    assert "secret.py" not in json.dumps(node)

    # Provenance summary is public-safe
    ps = node["provenanceSummary"]
    assert ps["evidenceCount"] == 1
    assert ps["evidenceTypes"]["implemented"] == 1
    assert ps["reliabilityTiers"]["tier_a"] == 1
    assert ps["sourceCategories"]["produced_artifact"] == 1
    assert ps["strongEvidenceCount"] == 1
    assert "excerpt" not in json.dumps(ps)
    assert "evidenceId" not in json.dumps(ps)


def test_build_public_graph_excludes_hidden_disputed_review_nodes() -> None:
    raw_graph = {
        "nodes": [
            {"id": "a", "name": "A", "kind": "skill", "confidence": 0.8, "status": "active"},
            {"id": "b", "name": "B", "kind": "skill", "confidence": 0.8, "status": "hidden"},
            {"id": "c", "name": "C", "kind": "skill", "confidence": 0.8, "status": "disputed"},
            {"id": "d", "name": "D", "kind": "skill", "confidence": 0.8, "status": "review"},
        ],
        "edges": [],
    }
    public = build_public_graph(raw_graph)
    ids = {n["id"] for n in public["nodes"]}
    assert ids == {"a"}


def test_build_public_graph_excludes_low_confidence_nodes() -> None:
    raw_graph = {
        "nodes": [
            {"id": "a", "name": "A", "kind": "skill", "confidence": 0.3, "status": "active"},
            {"id": "b", "name": "B", "kind": "skill", "confidence": 0.1, "status": "active"},
            {"id": "c", "name": "C", "kind": "skill", "confidence": 0.5, "status": "active"},
        ],
        "edges": [],
    }
    public = build_public_graph(raw_graph)
    ids = {n["id"] for n in public["nodes"]}
    assert "c" in ids
    assert "a" in ids  # 0.3 >= 0.25 threshold
    assert "b" not in ids  # 0.1 < 0.25 threshold


def test_build_public_graph_drops_edges_to_excluded_nodes() -> None:
    raw_graph = {
        "nodes": [
            {"id": "a", "name": "A", "kind": "skill", "confidence": 0.8, "status": "active"},
            {"id": "b", "name": "B", "kind": "skill", "confidence": 0.8, "status": "hidden"},
        ],
        "edges": [
            {
                "edge_id": "e1",
                "from_skill_id": "a",
                "to_skill_id": "b",
                "edge_type": "related_to",
                "weight": 0.5,
            }
        ],
    }
    public = build_public_graph(raw_graph)
    assert len(public["edges"]) == 0


def test_build_public_graph_preserves_edge_styles() -> None:
    raw_graph = {
        "nodes": [
            {"id": "a", "name": "A", "kind": "skill", "confidence": 0.8, "status": "active"},
            {"id": "b", "name": "B", "kind": "skill", "confidence": 0.8, "status": "active"},
        ],
        "edges": [
            {
                "edge_id": "e1",
                "from_skill_id": "a",
                "to_skill_id": "b",
                "edge_type": "parent_of",
                "weight": 0.9,
            }
        ],
    }
    public = build_public_graph(raw_graph)
    assert len(public["edges"]) == 1
    edge = public["edges"][0]
    assert edge["fromId"] == "a"
    assert edge["toId"] == "b"
    assert edge["edgeType"] == "parent_of"
    assert edge["weight"] == 0.9


def test_build_public_graph_provenance_summary_aggregates_multiple_evidence() -> None:
    raw_graph = {
        "nodes": [
            {
                "id": "s",
                "name": "S",
                "kind": "skill",
                "confidence": 0.8,
                "status": "active",
                "provenance": [
                    {
                        "evidenceType": "implemented",
                        "reliability": "tier_a",
                        "source": {"sourceCategory": "produced_artifact", "sourceFamily": "generic"},
                        "timeReference": "2024-03-01",
                    },
                    {
                        "evidenceType": "mentioned",
                        "reliability": "tier_c",
                        "source": {"sourceCategory": "social_or_community_trace", "sourceFamily": "reddit_export"},
                        "timeReference": "2024-06-15",
                    },
                    {
                        "evidenceType": "taught",
                        "reliability": "tier_b",
                        "source": {"sourceCategory": "authored_content", "sourceFamily": "generic"},
                        "timeReference": "2024-01-10",
                    },
                ],
            }
        ],
        "edges": [],
    }
    public = build_public_graph(raw_graph)
    ps = public["nodes"][0]["provenanceSummary"]
    assert ps["evidenceCount"] == 3
    assert ps["evidenceTypes"] == {"implemented": 1, "mentioned": 1, "taught": 1}
    assert ps["reliabilityTiers"] == {"tier_a": 1, "tier_b": 1, "tier_c": 1}
    assert ps["strongEvidenceCount"] == 2  # implemented + taught
    assert ps["earliestAt"] == "2024-01-10"
    assert ps["latestAt"] == "2024-06-15"


def test_build_public_graph_empty_provenance_returns_zero_summary() -> None:
    raw_graph = {
        "nodes": [
            {"id": "s", "name": "S", "kind": "skill", "confidence": 0.8, "status": "active"},
        ],
        "edges": [],
    }
    public = build_public_graph(raw_graph)
    ps = public["nodes"][0]["provenanceSummary"]
    assert ps["evidenceCount"] == 0
    assert ps["evidenceTypes"] == {}


def test_build_public_graph_domain_extraction() -> None:
    raw_graph = {
        "nodes": [
            {
                "id": "s1",
                "name": "S1",
                "kind": "skill",
                "confidence": 0.8,
                "status": "active",
                "description": "Data Engineering::pipeline orchestration",
            },
            {
                "id": "s2",
                "name": "S2",
                "kind": "skill",
                "confidence": 0.8,
                "status": "active",
                "description": "no separator here",
            },
        ],
        "edges": [],
    }
    public = build_public_graph(raw_graph)
    n1 = next(n for n in public["nodes"] if n["id"] == "s1")
    n2 = next(n for n in public["nodes"] if n["id"] == "s2")
    assert n1["domain"] == "Data Engineering"
    assert n1["description"] == "pipeline orchestration"
    assert n2["domain"] == "Uncategorized"
    assert n2["description"] == "no separator here"


# ---------------------------------------------------------------------------
# export_viewer integration tests
# ---------------------------------------------------------------------------


def test_export_viewer_creates_static_folder(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    export_path = export_viewer(tmp_path)

    assert export_path == tmp_path / "exports" / "viewer"
    assert export_path.exists()
    assert (export_path / "index.html").exists()
    assert (export_path / "graph.json").exists()
    assert (export_path / "config.json").exists()
    assert (export_path / "assets" / "viewer.css").exists()
    assert (export_path / "assets" / "viewer.js").exists()
    assert (export_path / "assets" / "sfx.js").exists()

    # Public graph is valid JSON and has expected shape
    public_graph = json.loads((export_path / "graph.json").read_text())
    assert "nodes" in public_graph
    assert "edges" in public_graph
    assert "metadata" in public_graph
    assert public_graph["metadata"]["generated_by"] == "traccia-viewer-v1"

    # Config has sound enabled by default
    config = json.loads((export_path / "config.json").read_text())
    assert config["enableSound"] is True
    assert config["version"] == 1


def _write_minimal_graph(project_root: Path) -> None:
    """Write a minimal graph.json for export_viewer unit tests."""
    graph_dir = project_root / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "skill.test",
                        "name": "Test",
                        "kind": "skill",
                        "description": "Testing::test skill",
                        "level": 3,
                        "confidence": 0.8,
                        "freshness": "active",
                        "status": "active",
                        "coreSelfCentrality": 0.5,
                        "historicalPeakLevel": 3,
                        "provenance": [
                            {
                                "evidenceId": "ev_1",
                                "sourceId": "src_1",
                                "evidenceType": "implemented",
                                "reliability": "tier_a",
                                "source": {"sourceCategory": "produced_artifact", "sourceFamily": "generic"},
                                "timeReference": "2024-01-01",
                            }
                        ],
                    }
                ],
                "edges": [],
                "metadata": {"generated_by": "traccia-renderer-v1"},
            }
        )
    )


def _write_fake_font_package(font_root: Path, font_files) -> None:
    """Create fake files with a supported local viewer font package shape."""
    for _family, _weight, _target_name, candidates in font_files:
        font_path = font_root / candidates[0]
        font_path.parent.mkdir(parents=True, exist_ok=True)
        font_path.write_bytes(candidates[0].encode())


def _set_missing_viewer_font_packages(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        viewer_module,
        "_VIEWER_FONT_PACKAGES",
        (
            (
                "mixed-forma-diatype",
                tmp_path / "missing-font-assets",
                viewer_module._VIEWER_MIXED_FONT_FILES,
            ),
            (
                "forma",
                tmp_path / "missing-forma",
                viewer_module._VIEWER_FORMA_FONT_FILES,
            ),
            (
                "diatype",
                tmp_path / "missing-diatype",
                viewer_module._VIEWER_DIATYPE_FONT_FILES,
            ),
        ),
    )


def test_export_viewer_with_no_sound_flag(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path, enable_sound=False)
    config = json.loads((tmp_path / "exports" / "viewer" / "config.json").read_text())
    assert config["enableSound"] is False


def test_export_viewer_html_references_assets_and_data(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    export_root = tmp_path / "exports" / "viewer"
    html = (export_root / "index.html").read_text()
    assert "assets/viewer.css" in html
    assert "assets/viewer.js" in html
    assert "assets/sfx.js" in html
    assert '<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">' in html
    favicon = export_root / "assets" / "favicon.svg"
    assert favicon.exists()
    assert "<svg" in favicon.read_text()
    assert "assets/viewer.css?v=" in html
    assert "assets/viewer.js?v=" in html
    assert "assets/sfx.js?v=" in html
    assert "graph.json?v=" in html
    assert "graph.json" in html
    assert "config.json" in html or "config.json" not in html  # config is fetched dynamically


def test_export_admin_viewer_html_references_favicon(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_admin_viewer(tmp_path)
    export_root = tmp_path / "exports" / "viewer-admin"
    html = (export_root / "index.html").read_text()

    assert '<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">' in html
    favicon = export_root / "assets" / "favicon.svg"
    assert favicon.exists()
    assert "<svg" in favicon.read_text()


def test_export_viewer_omits_font_faces_when_local_fonts_are_missing(
    tmp_path: Path, monkeypatch
) -> None:
    _write_minimal_graph(tmp_path)
    stale_fonts = tmp_path / "exports" / "viewer" / "assets" / "fonts"
    stale_fonts.mkdir(parents=True)
    (stale_fonts / "old-font.ttf").write_bytes(b"stale")
    monkeypatch.delenv("TRACCIA_VIEWER_FONT_DIR", raising=False)
    _set_missing_viewer_font_packages(tmp_path, monkeypatch)

    export_viewer(tmp_path)

    assets_dir = tmp_path / "exports" / "viewer" / "assets"
    css = (assets_dir / "viewer.css").read_text()
    assert "@font-face" not in css
    assert "Traccia UI" in css
    assert not (assets_dir / "fonts").exists()


def test_export_viewer_copies_configured_forma_fonts(
    tmp_path: Path, monkeypatch
) -> None:
    _write_minimal_graph(tmp_path)
    font_root = tmp_path / "font-source"
    _write_fake_font_package(font_root, viewer_module._VIEWER_FORMA_FONT_FILES)
    monkeypatch.setenv("TRACCIA_VIEWER_FONT_DIR", str(font_root))

    export_viewer(tmp_path)

    assets_dir = tmp_path / "exports" / "viewer" / "assets"
    css = (assets_dir / "viewer.css").read_text()
    copied_fonts = sorted((assets_dir / "fonts").iterdir())
    assert "@font-face" in css
    assert 'font-family: "Traccia UI";' in css
    assert 'font-family: "Traccia Label";' in css
    assert 'font-family: "Traccia Display";' in css
    assert 'font-family: "Traccia Mono";' in css
    assert 'url("fonts/traccia-label-regular.ttf") format("truetype")' in css
    assert 'url("fonts/traccia-mono-regular.otf") format("opentype")' in css
    assert len(copied_fonts) == len(viewer_module._VIEWER_FORMA_FONT_FILES)


def test_export_viewer_prefers_mixed_forma_and_diatype_fonts(
    tmp_path: Path, monkeypatch
) -> None:
    _write_minimal_graph(tmp_path)
    font_root = tmp_path / "font-assets"
    _write_fake_font_package(font_root, viewer_module._VIEWER_MIXED_FONT_FILES)
    monkeypatch.delenv("TRACCIA_VIEWER_FONT_DIR", raising=False)
    monkeypatch.setattr(
        viewer_module,
        "_VIEWER_FONT_PACKAGES",
        (
            (
                "mixed-forma-diatype",
                font_root,
                viewer_module._VIEWER_MIXED_FONT_FILES,
            ),
            (
                "forma",
                tmp_path / "missing-forma",
                viewer_module._VIEWER_FORMA_FONT_FILES,
            ),
            (
                "diatype",
                tmp_path / "missing-diatype",
                viewer_module._VIEWER_DIATYPE_FONT_FILES,
            ),
        ),
    )

    export_viewer(tmp_path)

    fonts_dir = tmp_path / "exports" / "viewer" / "assets" / "fonts"
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    assert 'font-family: "Traccia UI";' in css
    assert 'font-family: "Traccia Display";' in css
    assert (fonts_dir / "traccia-ui-regular.ttf").read_bytes() == (
        b"forma-djr-fonts/FormaDJRText-Regular.ttf"
    )
    assert (fonts_dir / "traccia-display-regular.ttf").read_bytes() == (
        b"abc-diatype-fonts/Diatype-Extended/ABCDiatypeExtended-Regular.ttf"
    )
    assert (fonts_dir / "traccia-mono-regular.ttf").read_bytes() == (
        b"abc-diatype-fonts/Diatype-Semi-Mono/ABCDiatypeSemi-Mono-Regular.ttf"
    )


def test_export_viewer_falls_back_to_diatype_fonts(
    tmp_path: Path, monkeypatch
) -> None:
    _write_minimal_graph(tmp_path)
    forma_root = tmp_path / "missing-forma"
    diatype_root = tmp_path / "diatype-source"
    _write_fake_font_package(diatype_root, viewer_module._VIEWER_DIATYPE_FONT_FILES)
    monkeypatch.delenv("TRACCIA_VIEWER_FONT_DIR", raising=False)
    monkeypatch.setattr(
        viewer_module,
        "_VIEWER_FONT_PACKAGES",
        (
            ("forma", forma_root, viewer_module._VIEWER_FORMA_FONT_FILES),
            ("diatype", diatype_root, viewer_module._VIEWER_DIATYPE_FONT_FILES),
        ),
    )

    export_viewer(tmp_path)

    assets_dir = tmp_path / "exports" / "viewer" / "assets"
    css = (assets_dir / "viewer.css").read_text()
    copied_fonts = sorted(font.name for font in (assets_dir / "fonts").iterdir())
    assert "@font-face" in css
    assert 'font-family: "Traccia Display";' in css
    assert "traccia-display-regular.ttf" in css
    assert "traccia-mono-regular.ttf" in css
    assert len(copied_fonts) == len(viewer_module._VIEWER_DIATYPE_FONT_FILES)


def test_export_viewer_js_has_no_external_dependencies(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    sfx = (tmp_path / "exports" / "viewer" / "assets" / "sfx.js").read_text()
    # No CDN or external script tags
    for content in (js, sfx):
        assert "cdn.jsdelivr" not in content
        assert "unpkg.com" not in content
        assert "<script src=" not in content


def test_export_viewer_sfx_is_procedural_web_audio(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    sfx = (tmp_path / "exports" / "viewer" / "assets" / "sfx.js").read_text()
    assert "AudioContext" in sfx or "webkitAudioContext" in sfx
    assert "createOscillator" in sfx
    assert "createGain" in sfx
    assert 'const STORAGE_KEY = "traccia-viewer-sound-enabled-v2"' in sfx
    # No audio asset file references
    assert ".mp3" not in sfx
    assert ".wav" not in sfx
    assert ".ogg" not in sfx


def test_export_viewer_css_has_dark_theme_and_responsive(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    assert "prefers-color-scheme" in css
    assert "prefers-reduced-motion" in css
    assert "@media (max-width" in css or "@media (max-width:" in css
    assert "--bg" in css  # uses CSS custom properties


def test_export_viewer_css_uses_black_palette_without_blue_default(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()

    assert "--bg: oklch(0.116 0.003 285.885)" in css
    assert "--accent: oklch(0.529 0.07 178.573)" in css
    assert "--domain-3: oklch(0.638 0.1 40.978)" in css  # copper
    assert "--domain-2: oklch(0.62 0.045 160.104)" in css  # moss
    assert "#6cb6ff" not in css
    assert "#2563eb" not in css
    assert "transition: all" not in css


def test_export_viewer_installs_motion_transition_hooks(tmp_path: Path) -> None:
    """Public viewer motion should use cheap CSS hooks, not per-frame JS polish."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    export_root = tmp_path / "exports" / "viewer"
    html = (export_root / "index.html").read_text()
    css = (export_root / "assets" / "viewer.css").read_text()
    js = (export_root / "assets" / "viewer.js").read_text()

    assert 'aria-label="Toggle sound" aria-pressed="true"' in html
    assert 'class="t-icon-swap sound-icon-swap" data-state="on"' in html
    assert 'class="filter-panel t-panel-slide"' in html
    assert 'class="legend t-panel-slide"' in html
    assert 'class="selection-dock t-panel-slide"' in html
    assert 'class="sheet t-panel-slide"' in html
    assert 'class="t-shimmer" data-text="Loading skill map..."' in html

    assert ".t-icon-swap" in css
    assert ".t-shimmer::before" in css
    assert "@keyframes t-shimmer" in css
    assert "@media (hover: hover) and (pointer: fine)" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ".t-panel-slide" in css

    assert 'const DATA_VERSION = "20260624-focus-field-1"' in js
    assert "function setPanelOpen" in js
    assert "function setDetailSurfaceOpen" in js
    assert 'swap.dataset.state = on ? "on" : "off"' in js


def test_export_viewer_applies_lightweight_default_filters(tmp_path: Path) -> None:
    """First load should render a smaller useful skill set by default."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    export_root = tmp_path / "exports" / "viewer"
    html = (export_root / "index.html").read_text()
    js = (export_root / "assets" / "viewer.js").read_text()

    assert "20260624-focus-field-1" in html
    assert '<label class="filterbar__label" for="filter-domain">Area</label>' in html
    assert '<option value="">All areas</option>' in html
    assert "<h3 class=\"legend__heading\">Skill areas</h3>" in html
    assert '<option value="current">Current + warming</option>' in html
    assert '<select id="filter-scope"' in html
    assert '<option value="320">Balanced 320</option>' in html
    assert '<option value="240">Curated 240</option>' in html
    assert '<option value="500">Comfort 500</option>' in html
    assert '<option value="750">Expanded 750</option>' in html
    assert '<option value="1000">Dense 1000</option>' in html
    assert '<option value="all">All matching</option>' in html
    assert "const DEFAULT_FILTERS = Object.freeze" in js
    assert 'freshness: "current"' in js
    assert "minConfidence: 0.75" in js
    assert "maxSkills: 1000" in js
    assert 'filters.freshness === "current"' in js
    assert 'freshness !== "active" && freshness !== "warming"' in js
    assert "var layoutNodes = getVisibleNodes()" in js
    assert "buildPresentationTree(layoutNodes)" in js
    assert "function applyScopeLimit" in js
    assert "function nodeTreeRank" in js
    assert "byBranch[branch].sort(compareTreeRank)" in js
    assert "filters = emptyFilters()" in js
    assert 'maxSkills: "all"' in js
    assert "syncFilterControls()" in js


def test_export_viewer_html_uses_inline_svg_toolbar_icons(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    html = (tmp_path / "exports" / "viewer" / "index.html").read_text()

    assert '<svg class="icon"' in html
    assert 'viewBox="0 0 256 256"' in html
    assert "M229.66,218.34" in html  # Phosphor magnifying-glass
    assert "M228.92,49.69" in html  # Phosphor map-trifold
    assert "M128,80a48,48" in html  # Phosphor gear-six
    assert "M200,136a8,8" in html  # Phosphor funnel-simple
    assert "&#128" not in html
    assert "&#9432" not in html
    assert "&#9637" not in html
    assert "&#8962" not in html
    assert "&times;" not in html


def test_viewer_js_renders_canvas_backed_skill_labels(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "maxNodeLabels" in js
    assert "maxNodeLabels: 1000" in js
    assert "maxMobileNodeLabels: 180" in js
    assert "mobileLabelViewportWidth: 700" in js
    assert "canvasLabelMinScreenPx: 10" in js
    assert "canvasLabelMaxScreenPx: 12" in js
    assert "function renderVirtualLabels" not in js
    assert "function renderCanvasSkillLabels" in js
    assert "function drawCanvasSkillLabel" in js
    assert "function canvasLabelFontFamily" in js
    assert "function maxRenderedNodeLabels" in js
    assert "function isConstrainedLabelViewport" in js
    assert "function shouldRenderNodeLabel" not in js
    assert "function labelPriority" not in js
    assert "function getLabelCandidateBounds" not in js
    assert "function requestLabelReveal" not in js
    assert "pendingLabelRevealIds" not in js
    assert "labelMustRender" in js
    assert "g.appendChild(labelText)" not in js
    assert "function createNodeLabel" not in js
    assert "ctx.strokeText(text, point.x, y)" in js
    assert "ctx.fillText(text, point.x, y)" in js
    assert "persistentLabelPriority(node)" in js


def test_viewer_js_renders_text_consistently_across_zoom(tmp_path: Path) -> None:
    """Graph text must not mix screen-fixed and graph-scaled behavior."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "labelScale: 0.45" in js
    assert "labelMovementPad: 1600" in js
    assert "activeLabelCap = focusDisplay && focusDisplay.active" in js
    assert "maxLabels = maxRenderedNodeLabels(activeLabelCap)" in js
    label_body = js.split("function renderCanvasSkillLabels", 1)[1].split(
        "function drawCanvasSkillLabel", 1
    )[0]
    assert "getLabelCandidateBounds()" not in label_body
    assert "persistentLabelPriority(node)" in label_body
    assert "Math.round(activeLabelCap * viewSettings.labelDensity)" in js
    assert "VIEW.maxMobileNodeLabels" in js
    assert "function shouldRenderNodeLabel" not in js
    assert "function labelPriority" not in js
    assert "function getLabelCandidateBounds" not in js

    render_canvas_body = js.split("function renderCanvas", 1)[1].split(
        "function getCanvasDrawNodes", 1
    )[0]
    assert "renderCanvasSkillLabels(ctx, canvasNodeIds)" in render_canvas_body
    branch_links_body = js.split("function renderZoomBranchLinks", 1)[1].split(
        "function treeLinkVisible", 1
    )[0]
    assert "var localBounds = bounds || getGraphViewportBounds(VIEW.canvasEdgeCullPad)" in branch_links_body
    assert "safeViewScale() < VIEW.detailZoomMedium ? VIEW.canvasEdgeCullPad : 24" not in branch_links_body
    assert '(11 / viewScale) + "px sans-serif"' not in render_canvas_body
    assert "canvasLevelTextFontSize(drawR)" in render_canvas_body
    assert "function levelTextScreenPx" in js
    assert "function canvasLevelTextFontSize" in js
    assert "function svgLevelTextFontSize" not in js
    assert "function syncSvgLevelTextScale" not in js
    assert "svgLevelElements" not in js

    synthetic_body = js.split("function renderSyntheticTreeNodes", 1)[1].split(
        "function shouldRenderSyntheticTreeLabel", 1
    )[0]
    assert "/ viewScale) + \"px sans-serif\"" not in synthetic_body
    assert "p.y + r + 18 / viewScale" not in synthetic_body
    assert 'node.kind === "tree-root" ? 22 : 18' in synthetic_body

    focus_label_body = js.split("function scheduleSettledFocusLabels", 1)[1].split(
        "function setFocusCanvasPreview", 1
    )[0]
    assert "}, 120);" in focus_label_body
    assert "8000" not in focus_label_body

    settled_canvas_body = js.split("function scheduleSettledCanvasRedraw", 1)[1].split(
        "function resetCanvasBitmapTransform", 1
    )[0]
    assert "scheduleViewUpdate(true, true)" in settled_canvas_body


def test_viewer_js_uses_generated_skill_tree_layout_contract(tmp_path: Path) -> None:
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "treeAreaRadius" in js
    assert "treeTopicRadius" in js
    assert "treeSkillRadius" in js
    assert "treeSkillRowSpacing" in js
    assert "function seededJitter" in js
    assert "function nodeImportance" in js
    assert "function buildPresentationTree" in js
    assert "function branchTopicForNode" in js
    assert "function syntheticTreeNode" in js
    assert "function slugifySyntheticId" in js
    assert "originX" in js
    assert "areaNodeId" in js


# ---------------------------------------------------------------------------
# Static asset behavior: domain collapse/expand, keyboard a11y, search label
# ---------------------------------------------------------------------------


def test_viewer_search_placeholder_omits_aliases(tmp_path: Path) -> None:
    """Search placeholder must not claim alias search if aliases are absent.

    The public graph contract (decision 50) does not include aliases, so the
    search placeholder must be truthful about what is actually searched
    (skill names, domains, descriptions).
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    html = (tmp_path / "exports" / "viewer" / "index.html").read_text()
    assert "aliases" not in html
    assert "Search skills, areas, descriptions" in html


def test_viewer_js_has_domain_collapse_expand(tmp_path: Path) -> None:
    """Public viewer JS must support session-level domain collapse/expand.

    Decision 34: support domain collapse/expand in both public and admin
    viewers, with public collapse state temporary per browser session.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    # Session-level state variable for collapsed domains
    assert "collapsedDomains" in js
    # Toggle function
    assert "function toggleDomain" in js
    assert "isDomainCollapsed" in js
    assert "function getDisplayedNodeIds" in js
    assert "updateLegendStats(displayed.size)" in js
    # SFX domain toggle is called on collapse/expand
    assert "sfx.domainToggle" in js


def test_viewer_js_domain_labels_are_interactive(tmp_path: Path) -> None:
    """Domain labels must be clickable and keyboard accessible.

    The SVG text elements for domain labels must have role=button, tabindex=0,
    click handlers, and keyboard (Enter/Space) handlers.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    # Domain labels get interactive attributes
    assert 'setAttribute("role", "button")' in js
    assert 'setAttribute("tabindex", "0")' in js
    # Domain label click focuses the area; modifier-click preserves collapse.
    assert "focusDomain(domain, true)" in js
    assert "e.shiftKey || e.altKey" in js
    assert "toggleDomain(domain)" in js
    # Domain label keyboard handler responds to Enter and Space
    assert '"Enter"' in js
    # aria-expanded reflects collapse state
    assert "aria-expanded" in js


def test_viewer_css_domain_labels_are_interactive(tmp_path: Path) -> None:
    """Domain label CSS must enable pointer interaction (no pointer-events:none)."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    # The standalone domain-label rule must not block pointer events.
    # Find the rule that starts with ".domain-label {" (not a compound
    # selector like ".graph-svg .domain-label {").
    import re

    match = re.search(r"(^|\n)\.domain-label \{([^}]*)\}", css)
    assert match, "standalone .domain-label {} rule not found"
    domain_label_block = match.group(2)
    assert "pointer-events: none" not in domain_label_block
    # Should have cursor pointer
    assert "cursor: pointer" in domain_label_block
    # Collapsed state styling
    assert ".domain-label.collapsed" in css
    assert ".domain-label.selected" in css
    # Focus-visible styling for keyboard navigation
    assert ".domain-label:focus-visible" in css


def test_viewer_js_nodes_use_roving_priority_accessibility(tmp_path: Path) -> None:
    """Only priority nodes should enter the accessibility tree.

    Large public graphs can contain 12k+ rendered nodes. Making every node a
    focusable SVG button creates a huge browser/AT surface, so the public
    viewer keeps rendered nodes visually clickable while promoting only a
    selected/search/keystone/priority set into tab order.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    assert "maxAccessibleNodes" in js
    assert "function getAccessibleNodeIds" in js
    assert "function nodeMustEnterAccessibilityTree" in js
    assert "function nodeShouldEnterAccessibilityTree" in js
    assert "function nodeAccessibilityPriority" in js
    assert "function applyNodeAccessibility" in js
    assert "function nodeAriaLabel" in js
    assert 'setAttribute("aria-hidden", "true")' in js
    assert 'setAttribute("tabindex", "0")' in js
    assert 'setAttribute("role", "button")' in js
    assert 'setAttribute("aria-label", nodeAriaLabel(node))' in js


def test_viewer_js_uses_delegated_node_events(tmp_path: Path) -> None:
    """Node click and keyboard activation must be delegated to the node layer."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function bindNodeLayerEvents" in js
    assert 'dom.graph_nodes.addEventListener("click", handleGraphNodeClick)' in js
    assert 'dom.graph_nodes.addEventListener("keydown", handleGraphNodeKeydown)' in js
    assert "function handleGraphNodeClick" in js
    assert "function handleGraphNodeKeydown" in js
    assert "function graphNodeFromEvent" in js
    assert '"Enter"' in js
    assert 'g.addEventListener("click"' not in js
    assert 'g.addEventListener("keydown"' not in js


def test_viewer_css_nodes_have_focus_visible_style(tmp_path: Path) -> None:
    """Node CSS must show a visible focus ring for keyboard navigation."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    assert ".graph-node:focus-visible" in css
    assert ".graph-node__focus-ring" in css
    assert "outline: none" in css
    assert css.index(".graph-node.focused .graph-node__focus-ring") < css.index(
        ".graph-node.selected .graph-node__focus-ring"
    )


def test_viewer_js_animates_selection_and_guards_drag_clicks(tmp_path: Path) -> None:
    """Node selection should animate the viewport and not fire after a drag."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "const DRAG_SELECT_THRESHOLD = 5" in js
    assert "const PAN_INERTIA = {" in js
    assert "sampleWindowMs: 130" in js
    assert "maxDurationMs: 560" in js
    assert "const WHEEL_ZOOM = {" in js
    assert "smoothMs" not in js
    assert "trackpadRate: 1 / 170" in js
    assert "let cameraGestureActive = false" in js
    assert "let wheelCameraActive = false" in js
    assert "function holdWheelCameraActive" in js
    assert "return cameraGestureActive || wheelCameraActive || !!panInertiaFrame || !!viewTweenFrame" in js
    assert "let targetViewState = { x: 0, y: 0, scale: 1 }" in js
    assert "let wheelZoomState = null" not in js
    assert "let panSamples = []" in js
    assert "let suppressNextGraphClick = false" in js
    assert "function centerOnNode(id, animated)" in js
    assert "function selectionDetailInset" in js
    assert "function stopViewTween" in js
    assert "function stopCameraAnimation" in js
    assert "function stopPanInertia" in js
    assert "function setDirectView" in js
    assert "function animateViewTo(target, durationMs)" in js
    assert "animateViewTo(target, 240)" in js
    assert "function runWheelZoom" not in js
    assert "function startPanInertia" in js
    assert "function recordPanSample" in js
    assert "var base = targetViewState" in js
    assert "Math.pow(2, -pixels * rate)" in js
    assert "zoomTargetForScale(cx, cy" in js
    assert "function viewForGraphPointAtScreen" in js
    assert "startGraphX: (centerX - viewState.x) / safeViewScale()" in js
    assert "viewForGraphPointAtScreen(cx, cy, touchState.startGraphX, touchState.startGraphY, nextScale)" in js
    assert "prefersReducedMotion()" in js
    assert "suppressNextGraphClick = true" in js
    assert "selectNode(nodeId, true)" in js
    assert "selectNode(hitId, true)" in js
    assert "centerOnNode(id, fromInteraction)" in js
    assert "resetView(true)" in js


def test_viewer_js_has_focus_field_display_contract(tmp_path: Path) -> None:
    """Committed node/domain focus must share display state across render paths."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "let activeFocus = null" in js
    assert "let focusDisplay = null" in js
    assert "const FOCUS_ANIMATION_MS = 260" in js
    assert "function buildFocusDisplayState" in js
    assert "function startFocusTransition" in js
    assert "function getDisplayPoint" in js
    assert "function getDisplayAlpha" in js
    assert "function getDisplayScale" in js
    assert "function getHitPriority" in js
    assert "function getDisplayZ" in js
    assert "function renderFocusFrame" in js
    assert "function applyFocusDisplayToSvg" in js
    assert "function clearanceSlotPoint" in js
    assert "function openFocusDock" in js
    assert "function hydrateFocusDockWhenIdle" in js
    assert "if (isCameraAnimating())" in js
    assert "setTimeout(hydrateFocusDockWhenIdle, 1200)" in js
    assert "setTimeout(hydrateFocusDockWhenIdle, 30000)" in js
    assert "function buildDomainFocus" in js
    assert "function buildNodeFocus" in js
    assert "function clearCommittedFocus" in js
    assert "activeFocus = buildDomainFocus(domain)" in js
    assert "activeFocus = buildNodeFocus(id)" in js
    assert "path.style.opacity" in js
    assert "g.style.opacity = String(getDisplayAlpha(node.id))" in js
    assert "function drawCanvasSkillLabel" in js
    assert "var r = nodeRadius(node) * getDisplayScale(node.id)" in js
    assert "var displayAlpha = Math.max(0.2, getDisplayAlpha(node.id))" in js
    assert "fillText(text, point.x, y)" in js
    assert "renderFocusFrame(false)" in js
    assert "var hitPriority = Math.max(0.08, getHitPriority(node.id))" in js
    assert "weightedDist = dist / hitPriority" in js
    assert "function focusStateQuietsId" not in js
    alpha_body = js.split("function getDisplayAlpha", 1)[1].split("function getDisplayScale", 1)[0]
    scale_body = js.split("function getDisplayScale", 1)[1].split("function getHitPriority", 1)[0]
    z_body = js.split("function getDisplayZ", 1)[1].split("function isFocusQuieted", 1)[0]
    assert "focusQuietAlpha" not in alpha_body
    assert "focusQuietScale" not in scale_body
    assert "quietIds" not in z_body
    assert ".graph-node.quieted" in css
    assert ".focus-shelf" in css
    assert ".focus-row" in css


def test_viewer_js_smooths_control_state_changes(tmp_path: Path) -> None:
    """Controls that show, hide, or disclose panels should use animated state hooks."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function setSearchClearVisible" in js
    assert "function syncDisclosureButton" in js
    assert 'dataset.visible = "true"' in js
    assert 'dataset.visible = "false"' in js
    assert 'setAttribute("aria-pressed", String(panel.dataset.open === "true"))' in js
    assert ".search-field__clear[data-visible=\"true\"]" in css
    assert ".filter-panel[data-open=\"true\"] .filterbar__group" in css
    assert ".legend[data-open=\"true\"] .legend__section" in css
    assert ".minimap.collapsed" in css
    assert "transition-property: width" not in css
    assert "transform: scaleX(var(--confidence-scale, 0))" in css


def test_viewer_js_reveals_labels_and_detail_content(tmp_path: Path) -> None:
    """Selection/detail changes reveal text, but zoom redraws must not replay labels."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert ".graph-node__label.is-new" not in css
    assert ".graph-svg.camera-moving #graph-zoom" in css
    assert "pointer-events: none" in css
    camera_rule = css.split(".graph-svg.camera-moving #graph-zoom", 1)[1].split("}", 1)[0]
    assert "opacity" not in camera_rule
    assert "transition-property: opacity" not in css.split("/* ===================================================================\n   Nodes", 1)[0]
    assert ".detail-reveal" in css
    assert ".detail-reveal.is-new" in css
    assert ".detail-answer" in css
    assert ".detail-more" in css
    assert "let pendingLabelRevealIds = new Set()" not in js
    assert "function requestLabelReveal(ids)" not in js
    assert "requestLabelReveal([id])" not in js
    assert "pendingLabelRevealIds" not in js
    assert "function revealNewLabels" not in js
    assert "function revealDetailContent" in js
    assert 'classList.toggle("camera-moving", cameraAnimating)' in js
    apply_idx = js.index("function applyViewTransform")
    apply_body = js[apply_idx : js.index("function syncDotBackgroundTransform", apply_idx)]
    assert "dom.graph_zoom.setAttribute" in apply_body
    assert "if (!cameraAnimating)" not in apply_body
    assert 'classList.add("detail-reveal", "is-new")' in js
    assert 'classList.remove("is-new")' in js
    assert "revealDetailContent(dom.drawer_body)" in js
    assert "revealDetailContent(dom.sheet_body)" in js
    assert "dom.graph_labels.replaceChildren(fragment);\n    revealNewLabels();" not in js


def test_viewer_js_builds_selection_dock_node_brief(tmp_path: Path) -> None:
    """Desktop node detail should lead with a useful public-field-backed brief."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    html = (tmp_path / "exports" / "viewer" / "index.html").read_text()
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "Selected node details" in html
    assert "selection-dock__title" in html
    assert ".selection-dock {" in css
    assert "function nodeWhatLines" in js
    assert "function nodeTrustLines" in js
    assert "function nodeEvidenceLines" in js
    assert "function nodeNextHtml" in js
    assert "function connectedNodeSuggestions" in js
    assert "function isUsefulNextCandidate" in js
    assert "function connectedNodeScore" in js
    assert "function topSummaryKeys" in js
    assert 'detailLines("What"' in js
    assert 'detailLines("Trust"' in js
    assert 'detailLines("Evidence"' in js
    assert 'detailBlock("Next"' in js
    assert "data-next-node-id" in js
    assert "handleDetailNextClick" in js
    assert "Connected" in js
    assert "detailSummaryRows" in js
    assert '<dl class="detail-list">' in js
    assert ".detail-list" in css
    assert "detail-tag" not in js
    assert "detail-tags" not in js
    assert ".detail-tag" not in css
    assert ".detail-tags" not in css
    detail_kicker_rule = css.split(".detail-kicker {", 1)[1].split("}", 1)[0]
    assert "border-left" not in detail_kicker_rule
    assert "padding-left" not in detail_kicker_rule
    assert 'kind === "domain"' in js
    assert "/^domain[._-]/" in js
    assert 'edge.edgeType === "parent_of"' in js
    assert '<details class="detail-more">' in js
    assert "No public description exported; using display label" in js
    assert 'confidencePct < 45 ? "Weak signal: " : ""' in js
    assert ".detail-next-list" in css
    assert ".detail-next-item" in css
    assert "evidence-tick" not in css
    assert "evidence-tick" not in js
    assert "public evidence items" in js
    assert 'detailAnswer("Strength"' not in js
    assert 'detailAnswer("Why"' not in js
    assert 'detailAnswer("Where"' not in js


def test_viewer_css_hidden_rule_overrides_component_display(tmp_path: Path) -> None:
    """CSS display rules must not defeat the native [hidden] attribute.

    Bug: `.loading-state { display: flex }` (and the same pattern on
    `.selection-dock`, `.sheet`, `.empty-state`) has the same specificity as the
    UA default `[hidden] { display: none }` and appears later in source
    order, so it won the cascade. After graph load the viewer JS sets
    `loadingState.hidden = true`, but the element stayed visible and the
    "Loading skill map..." overlay never disappeared.

    The exported viewer.css must include a `[hidden]` reset rule with
    `display: none !important` that covers loading-state and the shared
    overlays/panels, so the hidden attribute truly hides those elements
    regardless of their class-based display rule.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()

    # The reset must exist as a real rule and force display:none over any
    # class display rule via the important layer.
    assert "[hidden] { display: none !important; }" in css

    # The component rules must still define their own visible display so the
    # reset (not source order) is what makes [hidden] win the cascade.
    # Target the actual rule selectors, not bare substring mentions that may
    # also appear inside explanatory comments.
    assert ".empty-state, .loading-state {" in css
    assert "display: flex" in css

    # Sanity: the reset must precede the loading-state component rule in the
    # stylesheet so it is available before any class display rule is parsed.
    hidden_rule_idx = css.index("[hidden] { display: none !important; }")
    loading_rule_idx = css.index(".empty-state, .loading-state {")
    assert hidden_rule_idx < loading_rule_idx, (
        "[hidden] reset must precede .loading-state component rule"
    )
    """The main graph SVG must not be aria-hidden.

    Nodes and domain labels rendered inside #graph-svg are keyboard focusable
    (decisions 39, 34) with aria-labels. An aria-hidden ancestor removes all
    descendants from the accessibility tree, so the SVG must instead expose an
    accessible label. The decorative minimap SVG stays aria-hidden.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    html = (tmp_path / "exports" / "viewer" / "index.html").read_text()

    # Isolate the #graph-svg opening tag so the check targets the main graph,
    # not incidental substrings elsewhere in the document.
    graph_svg_tag = html.split('id="graph-svg"')[1].split(">", 1)[0]
    # The <svg ...> tag starts just before id="graph-svg"; reconstruct it.
    pre = html.split('id="graph-svg"')[0]
    svg_open = pre.rsplit("<svg", 1)[1] + 'id="graph-svg"' + graph_svg_tag

    assert 'aria-hidden="true"' not in svg_open, (
        "main graph SVG is aria-hidden, which hides its focusable nodes from a11y tree"
    )
    # SVG should expose a label so AT users know what the group represents.
    assert 'role="group"' in svg_open
    assert "aria-label" in svg_open

    # The decorative minimap SVG must remain hidden from AT.
    minimap_after = html.split('id="minimap-svg"')[1].split(">", 1)[0]
    minimap_svg_open = (
        html.split('id="minimap-svg"')[0].rsplit("<svg", 1)[1]
        + 'id="minimap-svg"'
        + minimap_after
    )
    assert 'aria-hidden="true"' in minimap_svg_open


def test_viewer_sfx_has_domain_toggle_method(tmp_path: Path) -> None:
    """SFX engine must include the domainToggle method (decision 59)."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    sfx = (tmp_path / "exports" / "viewer" / "assets" / "sfx.js").read_text()
    assert "domainToggle" in sfx
    # domainToggle should handle expanding parameter
    assert "expanding" in sfx


def test_viewer_js_arrow_navigation_skips_collapsed_domains(tmp_path: Path) -> None:
    """Arrow navigation must skip nodes inside collapsed domains."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    # navigateArrow should check isDomainCollapsed
    assert "isDomainCollapsed" in js


def test_viewer_js_arrow_navigation_works_from_focused_node(tmp_path: Path) -> None:
    """Arrow navigation must work from Tab-focused node, not only selected."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    # The global keydown handler should detect focused graph-node elements
    assert "graph-node" in js
    assert "focusedNodeId" in js


def test_publish_public_bundle_has_updated_search_placeholder(tmp_path: Path) -> None:
    """The published public bundle must also have the corrected placeholder."""
    _write_minimal_graph(tmp_path)
    publish_public_bundle(tmp_path)
    html = (tmp_path / "exports" / "viewer-public" / "index.html").read_text()
    assert "aliases" not in html
    assert "Search skills, areas, descriptions" in html


# ---------------------------------------------------------------------------
# CLI command test
# ---------------------------------------------------------------------------


def test_cli_export_viewer_command(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    result = runner.invoke(
        app, ["export", "viewer", "--project-root", str(tmp_path)]
    )

    assert result.exit_code == 0, result.stdout
    export_path = tmp_path / "exports" / "viewer"
    assert str(export_path) in result.stdout
    assert (export_path / "index.html").exists()
    assert (export_path / "graph.json").exists()


def test_cli_export_viewer_no_sound_flag(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    result = runner.invoke(
        app, ["export", "viewer", "--project-root", str(tmp_path), "--no-sound"]
    )

    assert result.exit_code == 0, result.stdout
    config = json.loads((tmp_path / "exports" / "viewer" / "config.json").read_text())
    assert config["enableSound"] is False


def test_cli_export_viewer_in_help(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    assert "viewer" in result.stdout


# ---------------------------------------------------------------------------
# End-to-end: public bundle excludes private data from real corpus
# ---------------------------------------------------------------------------


def test_export_viewer_public_bundle_has_no_raw_excerpts(tmp_path: Path) -> None:
    """The public graph.json must not contain raw evidence excerpts or source IDs."""
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    export_viewer(tmp_path)
    public_graph = json.loads((tmp_path / "exports" / "viewer" / "graph.json").read_text())
    serialized = json.dumps(public_graph)

    assert "provenance" not in serialized or '"provenance"' not in serialized
    assert "excerpt" not in serialized
    assert "evidenceId" not in serialized
    assert "sourceId" not in serialized.split('"provenanceSummary"')[0]  # no raw source IDs on nodes

    # All nodes should have provenanceSummary, not provenance
    for node in public_graph["nodes"]:
        assert "provenanceSummary" in node
        assert "provenance" not in node or not isinstance(node.get("provenance"), list)


def test_export_viewer_public_bundle_has_nodes_from_corpus(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    export_viewer(tmp_path)
    public_graph = json.loads((tmp_path / "exports" / "viewer" / "graph.json").read_text())
    node_names = {n["name"] for n in public_graph["nodes"]}
    # The test corpus produces Python, SQLite, Rust
    assert "Python" in node_names
    assert len(public_graph["nodes"]) >= 3


def test_export_viewer_viewer_not_created_by_normal_render(tmp_path: Path) -> None:
    """Normal render_project should not create the viewer folder (only export viewer does)."""
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    # After ingest, viewer folder should not exist yet
    assert not (tmp_path / "exports" / "viewer").exists()


# ===========================================================================
# Phase 2: curation model tests
# ===========================================================================


def test_empty_curation_has_expected_shape() -> None:
    c = empty_curation()
    assert c["version"] == 1
    assert c["nodes"] == {}
    assert c["domains"] == {}
    assert c["global"]["defaultCollapsedDomains"] == []


def test_node_curation_entry_only_stores_non_none() -> None:
    entry = node_curation_entry(hidden=True, public_label="Custom Label")
    assert entry == {"hidden": True, "publicLabel": "Custom Label"}


def test_load_curation_returns_empty_when_missing(tmp_path: Path) -> None:
    curation = load_curation(tmp_path / "nonexistent.json")
    assert curation["nodes"] == {}


def test_save_and_load_curation_roundtrip(tmp_path: Path) -> None:
    curation = empty_curation()
    curation["nodes"]["skill.python"] = node_curation_entry(hidden=True)
    curation["domains"]["Programming"] = {"collapsed": True}

    path = tmp_path / "curation.json"
    save_curation(path, curation)

    loaded = load_curation(path)
    assert loaded["nodes"]["skill.python"]["hidden"] is True
    assert loaded["domains"]["Programming"]["collapsed"] is True


def test_load_curation_raises_on_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "curation.json"
    path.write_text("{ not valid json")
    try:
        load_curation(path)
        raise AssertionError("Expected ValueError")
    except ValueError as exc:
        assert "Invalid curation JSON" in str(exc)


def test_merge_curation_override_takes_precedence() -> None:
    base = empty_curation()
    base["nodes"]["a"] = {"hidden": True, "featured": False}

    override = empty_curation()
    override["nodes"]["a"] = {"hidden": False}

    merged = merge_curation(base, override)
    assert merged["nodes"]["a"]["hidden"] is False
    assert merged["nodes"]["a"]["featured"] is False


def test_merge_curation_unsets_field_with_none() -> None:
    base = empty_curation()
    base["nodes"]["a"] = {"hidden": True, "publicLabel": "old"}

    override = empty_curation()
    override["nodes"]["a"] = {"publicLabel": None}

    merged = merge_curation(base, override)
    assert "publicLabel" not in merged["nodes"]["a"]


def test_curation_accessors() -> None:
    curation = empty_curation()
    curation["nodes"]["a"] = node_curation_entry(
        hidden=True, featured=True, public_label="Override",
        public_note="Note", approve_low_confidence=True, approve_disputed=True,
    )
    curation["domains"]["Programming"] = {"collapsed": True, "publicLabel": "Code"}

    assert is_node_hidden(curation, "a") is True
    assert is_node_featured(curation, "a") is True
    assert is_low_confidence_approved(curation, "a") is True
    assert is_disputed_approved(curation, "a") is True
    assert is_domain_collapsed(curation, "Programming") is True


# ===========================================================================
# Phase 2: build_public_bundle (publish redaction) tests
# ===========================================================================


def _sample_graph() -> dict[str, object]:
    return {
        "nodes": [
            {
                "id": "skill.python",
                "name": "Python",
                "kind": "skill",
                "description": "Programming::general purpose language",
                "level": 4,
                "confidence": 0.9,
                "freshness": "active",
                "status": "active",
                "coreSelfCentrality": 0.8,
                "historicalPeakLevel": 4,
                "provenance": [
                    {
                        "evidenceId": "ev_secret_123",
                        "sourceId": "src_secret_456",
                        "excerpt": "sensitive raw quote with /home/user/secret.py",
                        "evidenceType": "implemented",
                        "reliability": "tier_a",
                        "source": {
                            "filename": "secret.py",
                            "uri": "file:///home/user/secret.py",
                            "sourceCategory": "produced_artifact",
                            "sourceFamily": "generic",
                        },
                    }
                ],
            },
            {
                "id": "skill.hidden_one",
                "name": "Hidden",
                "kind": "skill",
                "confidence": 0.8,
                "status": "hidden",
            },
            {
                "id": "skill.disputed_one",
                "name": "Disputed",
                "kind": "skill",
                "confidence": 0.8,
                "status": "disputed",
            },
            {
                "id": "skill.low_conf",
                "name": "LowConf",
                "kind": "skill",
                "confidence": 0.1,
                "status": "active",
            },
            {
                "id": "skill.user@email.com/private",
                "name": "SensitiveID",
                "kind": "skill",
                "confidence": 0.8,
                "status": "active",
                "description": "Personal::private notes",
            },
        ],
        "edges": [
            {
                "edge_id": "e1",
                "from_skill_id": "skill.python",
                "to_skill_id": "skill.hidden_one",
                "edge_type": "related_to",
                "weight": 0.5,
            },
        ],
        "metadata": {"generated_by": "traccia-renderer-v1"},
    }


def test_publish_excludes_hidden_nodes_by_default() -> None:
    public, _ = build_public_bundle(_sample_graph(), empty_curation())
    ids = {n["id"] for n in public["nodes"]}
    assert "skill.python" in ids
    assert "skill.hidden_one" not in ids


def test_publish_excludes_disputed_unless_approved() -> None:
    public, _ = build_public_bundle(_sample_graph(), empty_curation())
    ids = {n["id"] for n in public["nodes"]}
    assert "skill.disputed_one" not in ids

    curation = empty_curation()
    curation["nodes"]["skill.disputed_one"] = {"approveDisputed": True}
    public, _ = build_public_bundle(_sample_graph(), curation)
    ids = {n["id"] for n in public["nodes"]}
    assert "skill.disputed_one" in ids


def test_publish_excludes_low_confidence_unless_approved() -> None:
    public, _ = build_public_bundle(_sample_graph(), empty_curation())
    ids = {n["id"] for n in public["nodes"]}
    assert "skill.low_conf" not in ids

    curation = empty_curation()
    curation["nodes"]["skill.low_conf"] = {"approveLowConfidence": True}
    public, _ = build_public_bundle(_sample_graph(), curation)
    ids = {n["id"] for n in public["nodes"]}
    assert "skill.low_conf" in ids
    # Confidence score must not be edited (decision 48)
    node = next(n for n in public["nodes"] if n["id"] == "skill.low_conf")
    assert node["confidence"] == 0.1


def test_publish_curation_hidden_overrides_status() -> None:
    """A node hidden via curation must be excluded even if status is active."""
    curation = empty_curation()
    curation["nodes"]["skill.python"] = {"hidden": True}
    public, _ = build_public_bundle(_sample_graph(), curation)
    ids = {n["id"] for n in public["nodes"]}
    assert "skill.python" not in ids


def test_publish_drops_edges_to_excluded_nodes() -> None:
    public, _ = build_public_bundle(_sample_graph(), empty_curation())
    assert len(public["edges"]) == 0


def test_publish_strips_raw_provenance_and_excerpts() -> None:
    public, _ = build_public_bundle(_sample_graph(), empty_curation())
    serialized = json.dumps(public)
    assert "excerpt" not in serialized
    assert "evidenceId" not in serialized
    assert "sourceId" not in serialized
    assert "file:///" not in serialized
    assert "secret.py" not in serialized


def test_publish_provenance_summary_is_public_safe() -> None:
    public, _ = build_public_bundle(_sample_graph(), empty_curation())
    node = next(n for n in public["nodes"] if n["id"] == "skill.python")
    ps = node["provenanceSummary"]
    assert ps["evidenceCount"] == 1
    assert ps["evidenceTypes"] == {"implemented": 1}
    assert ps["strongEvidenceCount"] == 1


def test_publish_applies_public_label_override() -> None:
    curation = empty_curation()
    curation["nodes"]["skill.python"] = {"publicLabel": "Python (Custom)"}
    public, _ = build_public_bundle(_sample_graph(), curation)
    node = next(n for n in public["nodes"] if n["id"] == "skill.python")
    assert node["name"] == "Python (Custom)"


def test_publish_applies_public_note_override() -> None:
    curation = empty_curation()
    curation["nodes"]["skill.python"] = {"publicNote": "This is a public note"}
    public, _ = build_public_bundle(_sample_graph(), curation)
    node = next(n for n in public["nodes"] if n["id"] == "skill.python")
    assert node["publicNote"] == "This is a public note"


def test_publish_applies_domain_label_override() -> None:
    curation = empty_curation()
    curation["domains"]["Programming"] = {"publicLabel": "Software Dev"}
    public, _ = build_public_bundle(_sample_graph(), curation)
    node = next(n for n in public["nodes"] if n["id"] == "skill.python")
    assert node["domain"] == "Software Dev"


def test_publish_featured_flag_carried_through() -> None:
    curation = empty_curation()
    curation["nodes"]["skill.python"] = {"featured": True}
    public, _ = build_public_bundle(_sample_graph(), curation)
    node = next(n for n in public["nodes"] if n["id"] == "skill.python")
    assert node["featured"] is True


# ===========================================================================
# Phase 2: alias mapping tests (decision 51)
# ===========================================================================


def test_publish_generates_alias_for_sensitive_ids() -> None:
    public, alias_map = build_public_bundle(_sample_graph(), empty_curation())
    # The sensitive ID should be aliased
    assert "skill.user@email.com/private" in alias_map
    alias = alias_map["skill.user@email.com/private"]
    assert alias.startswith("pub_")

    # The public graph should use the alias, not the raw ID
    ids = {n["id"] for n in public["nodes"]}
    assert alias in ids
    assert "skill.user@email.com/private" not in ids


def test_publish_alias_is_stable() -> None:
    """The same sensitive ID always maps to the same alias."""
    graph = _sample_graph()
    _, alias_map_1 = build_public_bundle(graph, empty_curation())
    _, alias_map_2 = build_public_bundle(graph, empty_curation())
    assert alias_map_1 == alias_map_2


def test_publish_alias_map_excludes_normal_ids() -> None:
    public, alias_map = build_public_bundle(_sample_graph(), empty_curation())
    # Normal dot-separated IDs should not be aliased
    assert "skill.python" not in alias_map


def test_publish_no_raw_id_in_serialized_output() -> None:
    """The raw sensitive ID must not appear anywhere in the public graph JSON."""
    public, _ = build_public_bundle(_sample_graph(), empty_curation())
    serialized = json.dumps(public)
    assert "user@email.com" not in serialized
    assert "private" not in serialized or '"private"' not in serialized


# ===========================================================================
# Phase 2: admin viewer export tests
# ===========================================================================


def _write_minimal_graph_for_admin(project_root: Path) -> None:
    """Write a graph.json with hidden, disputed, and low-confidence nodes."""
    graph_dir = project_root / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "skill.normal",
                        "name": "Normal",
                        "kind": "skill",
                        "description": "Programming::normal skill",
                        "level": 3,
                        "confidence": 0.8,
                        "freshness": "active",
                        "status": "active",
                        "coreSelfCentrality": 0.5,
                        "historicalPeakLevel": 3,
                    },
                    {
                        "id": "skill.hidden_status",
                        "name": "HiddenStatus",
                        "kind": "skill",
                        "confidence": 0.8,
                        "status": "hidden",
                    },
                    {
                        "id": "skill.disputed",
                        "name": "Disputed",
                        "kind": "skill",
                        "confidence": 0.8,
                        "status": "disputed",
                    },
                    {
                        "id": "skill.low_confidence",
                        "name": "LowConfidence",
                        "kind": "skill",
                        "confidence": 0.1,
                        "status": "active",
                    },
                ],
                "edges": [],
                "metadata": {"generated_by": "traccia-renderer-v1"},
            }
        )
    )


def test_export_admin_viewer_creates_folder(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    export_path = export_admin_viewer(tmp_path)

    assert export_path == tmp_path / "exports" / "viewer-admin"
    assert export_path.exists()
    assert (export_path / "index.html").exists()
    assert (export_path / "graph.json").exists()
    assert (export_path / "curation.json").exists()
    assert (export_path / "config.json").exists()
    assert (export_path / "assets" / "admin.css").exists()
    assert (export_path / "assets" / "admin.js").exists()
    assert (export_path / "assets" / "sfx.js").exists()


def test_admin_viewer_graph_contains_all_nodes(tmp_path: Path) -> None:
    """Admin viewer graph.json must include hidden, disputed, and low-confidence nodes."""
    _write_minimal_graph_for_admin(tmp_path)
    export_admin_viewer(tmp_path)
    admin_graph = json.loads(
        (tmp_path / "exports" / "viewer-admin" / "graph.json").read_text()
    )
    ids = {n["id"] for n in admin_graph["nodes"]}
    # Admin viewer has the FULL graph, nothing redacted
    assert "skill.normal" in ids
    assert "skill.hidden_status" in ids
    assert "skill.disputed" in ids
    assert "skill.low_confidence" in ids


def test_admin_viewer_config_has_admin_mode(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    export_admin_viewer(tmp_path)
    config = json.loads(
        (tmp_path / "exports" / "viewer-admin" / "config.json").read_text()
    )
    assert config["mode"] == "admin"
    assert "curationSummary" in config
    assert config["curationSummary"]["totalNodes"] == 4


def test_admin_viewer_loads_existing_curation(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    # Pre-populate curation.json in the public viewer folder
    viewer_dir = tmp_path / "exports" / "viewer"
    viewer_dir.mkdir(parents=True, exist_ok=True)
    existing = empty_curation()
    existing["nodes"]["skill.normal"] = {"hidden": True}
    save_curation(viewer_dir / "curation.json", existing)

    export_admin_viewer(tmp_path)
    admin_curation = json.loads(
        (tmp_path / "exports" / "viewer-admin" / "curation.json").read_text()
    )
    assert admin_curation["nodes"]["skill.normal"]["hidden"] is True


def test_admin_viewer_html_references_admin_assets(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    export_admin_viewer(tmp_path)
    html = (tmp_path / "exports" / "viewer-admin" / "index.html").read_text()
    assert "assets/admin.css" in html
    assert "assets/admin.js" in html
    assert "assets/sfx.js" in html
    assert "graph.json" in html
    assert "curation.json" in html


def test_admin_viewer_js_has_curation_controls(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    export_admin_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer-admin" / "assets" / "admin.js").read_text()
    assert "saveCuration" in js
    assert "curation-hidden" in js
    assert "curation-featured" in js
    assert "approveLowConfidence" in js
    assert "approveDisputed" in js
    assert "collapsedDomains" in js


def test_admin_viewer_css_has_curation_styles(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    export_admin_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer-admin" / "assets" / "admin.css").read_text()
    assert ".curation-toggle" in css
    assert ".curation-summary" in css
    assert "prefers-reduced-motion" in css


# ===========================================================================
# Phase 2: publish_public_bundle export tests
# ===========================================================================


def test_publish_public_bundle_creates_folder(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    publish_path = publish_public_bundle(tmp_path)

    assert publish_path == tmp_path / "exports" / "viewer-public"
    assert publish_path.exists()
    assert (publish_path / "index.html").exists()
    assert (publish_path / "graph.json").exists()
    assert (publish_path / "config.json").exists()
    assert (publish_path / "assets" / "viewer.css").exists()
    assert (publish_path / "assets" / "viewer.js").exists()
    assert (publish_path / "assets" / "sfx.js").exists()


def test_publish_public_bundle_excludes_hidden_and_disputed(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    publish_public_bundle(tmp_path)
    public_graph = json.loads(
        (tmp_path / "exports" / "viewer-public" / "graph.json").read_text()
    )
    ids = {n["id"] for n in public_graph["nodes"]}
    assert "skill.normal" in ids
    assert "skill.hidden_status" not in ids
    assert "skill.disputed" not in ids
    assert "skill.low_confidence" not in ids


def test_publish_public_bundle_applies_curation(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    # Write curation.json that approves disputed and low-confidence nodes
    viewer_dir = tmp_path / "exports" / "viewer"
    viewer_dir.mkdir(parents=True, exist_ok=True)
    curation = empty_curation()
    curation["nodes"]["skill.disputed"] = {"approveDisputed": True}
    curation["nodes"]["skill.low_confidence"] = {"approveLowConfidence": True}
    curation["nodes"]["skill.normal"] = {"hidden": True}
    save_curation(viewer_dir / "curation.json", curation)

    publish_public_bundle(tmp_path)
    public_graph = json.loads(
        (tmp_path / "exports" / "viewer-public" / "graph.json").read_text()
    )
    ids = {n["id"] for n in public_graph["nodes"]}
    # normal is now hidden via curation
    assert "skill.normal" not in ids
    # disputed and low_confidence are now approved
    assert "skill.disputed" in ids
    assert "skill.low_confidence" in ids


def test_publish_public_bundle_writes_alias_map_when_needed(tmp_path: Path) -> None:
    graph_dir = tmp_path / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / "graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "user@email.com/private_notes",
                        "name": "Private",
                        "kind": "skill",
                        "confidence": 0.8,
                        "status": "active",
                    },
                    {
                        "id": "skill.normal",
                        "name": "Normal",
                        "kind": "skill",
                        "confidence": 0.8,
                        "status": "active",
                    },
                ],
                "edges": [],
            }
        )
    )
    publish_public_bundle(tmp_path)
    alias_path = tmp_path / "exports" / "viewer-public" / "alias-map.json"
    assert alias_path.exists()
    alias_data = json.loads(alias_path.read_text())
    assert alias_data["_admin_only"] is True
    assert "user@email.com/private_notes" in alias_data["mapping"]


def test_publish_public_bundle_no_alias_map_when_not_needed(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    publish_public_bundle(tmp_path)
    alias_path = tmp_path / "exports" / "viewer-public" / "alias-map.json"
    assert not alias_path.exists()


def test_publish_public_bundle_config_has_public_mode(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    publish_public_bundle(tmp_path)
    config = json.loads(
        (tmp_path / "exports" / "viewer-public" / "config.json").read_text()
    )
    assert config["mode"] == "public"


# ===========================================================================
# Phase 2: CLI command tests
# ===========================================================================


def test_cli_export_admin_command(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    result = runner.invoke(
        app, ["export", "admin", "--project-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.stdout
    export_path = tmp_path / "exports" / "viewer-admin"
    assert str(export_path) in result.stdout
    assert (export_path / "index.html").exists()


def test_cli_export_publish_command(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    result = runner.invoke(
        app, ["export", "publish", "--project-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.stdout
    publish_path = tmp_path / "exports" / "viewer-public"
    assert str(publish_path) in result.stdout
    assert (publish_path / "index.html").exists()


def test_cli_export_publish_with_output_dir(tmp_path: Path) -> None:
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    result = runner.invoke(
        app,
        ["export", "publish", "--project-root", str(tmp_path), "--output-dir", "custom-public"],
    )
    assert result.exit_code == 0, result.stdout
    publish_path = tmp_path / "exports" / "custom-public"
    assert (publish_path / "index.html").exists()


def test_cli_export_admin_in_help(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["export", "--help"])
    assert result.exit_code == 0
    assert "admin" in result.stdout
    assert "publish" in result.stdout


# ===========================================================================
# Phase 2: browser asset expectation tests
# ===========================================================================


def test_admin_viewer_sfx_is_procedural_web_audio(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    export_admin_viewer(tmp_path)
    sfx = (tmp_path / "exports" / "viewer-admin" / "assets" / "sfx.js").read_text()
    assert "AudioContext" in sfx
    assert ".mp3" not in sfx
    assert ".wav" not in sfx


def test_admin_viewer_html_has_save_button(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    export_admin_viewer(tmp_path)
    html = (tmp_path / "exports" / "viewer-admin" / "index.html").read_text()
    assert "save-curation" in html
    assert "Save" in html


def test_admin_viewer_motion_and_toast_assets_are_valid(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    export_admin_viewer(tmp_path)
    admin_root = tmp_path / "exports" / "viewer-admin"
    css = (admin_root / "assets" / "admin.css").read_text()
    js = (admin_root / "assets" / "admin.js").read_text()

    assert "transition: all" not in css
    assert "dom.save-toast" not in js
    assert "dom.save_toast" in js


def test_publish_public_bundle_viewer_is_same_as_phase1_viewer(tmp_path: Path) -> None:
    """The published public bundle should use the same Phase 1 viewer assets."""
    _write_minimal_graph_for_admin(tmp_path)
    publish_public_bundle(tmp_path)
    html = (tmp_path / "exports" / "viewer-public" / "index.html").read_text()
    # Phase 1 viewer references
    assert "assets/viewer.css" in html
    assert "assets/viewer.js" in html
    assert "assets/sfx.js" in html


def test_publish_public_bundle_has_no_raw_provenance_in_json(tmp_path: Path) -> None:
    _write_minimal_graph_for_admin(tmp_path)
    publish_public_bundle(tmp_path)
    public_graph = json.loads(
        (tmp_path / "exports" / "viewer-public" / "graph.json").read_text()
    )
    serialized = json.dumps(public_graph)
    assert "provenance" not in serialized or '"provenance"' not in serialized
    assert "excerpt" not in serialized
    assert "evidenceId" not in serialized


# ===========================================================================
# Phase 2: integration end-to-end test
# ===========================================================================


def test_full_curation_publish_workflow(tmp_path: Path) -> None:
    """End-to-end: admin curation -> save -> publish -> verify redaction."""
    runner = CliRunner()
    initialize_repo(runner, tmp_path)
    ingest_corpus(runner, tmp_path)

    # Step 1: Generate admin viewer
    admin_path = export_admin_viewer(tmp_path)
    assert admin_path.exists()

    # Step 2: Admin authors curation (simulating the save action)
    viewer_dir = tmp_path / "exports" / "viewer"
    viewer_dir.mkdir(parents=True, exist_ok=True)
    curation = empty_curation()
    # Find the first skill and hide it
    admin_graph = json.loads((admin_path / "graph.json").read_text())
    first_skill_id = None
    for node in admin_graph["nodes"]:
        if node.get("status") == "active" and node.get("confidence", 0) >= 0.25:
            first_skill_id = node["id"]
            break
    assert first_skill_id is not None
    curation["nodes"][first_skill_id] = {"hidden": True}
    save_curation(viewer_dir / "curation.json", curation)

    # Step 3: Publish
    publish_path = publish_public_bundle(tmp_path)
    public_graph = json.loads((publish_path / "graph.json").read_text())
    public_ids = {n["id"] for n in public_graph["nodes"]}
    assert first_skill_id not in public_ids


# ===========================================================================
# Phase 3: canvas raster layer + floating game-map HUD tests
# ===========================================================================


def test_viewer_html_has_canvas_raster_layer(tmp_path: Path) -> None:
    """The public viewer HTML must include a canvas element for bulk rendering.

    With 12k+ node public graphs, creating SVG DOM elements for every node
    and edge causes severe lag. The viewer now uses a canvas raster layer
    for bulk nodes/edges, keeping SVG only for domain labels, the capped
    accessible node set, and focus-path overlays.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    html = (tmp_path / "exports" / "viewer" / "index.html").read_text()
    assert 'id="graph-canvas"' in html
    assert "graph-canvas" in html


def test_viewer_css_has_canvas_layer_styling(tmp_path: Path) -> None:
    """Canvas must be positioned behind the SVG overlay as a full-bleed layer."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    assert ".graph-canvas" in css
    assert "position: absolute" in css
    assert "inset: 0" in css
    assert "pointer-events: none" in css


def test_viewer_svg_nodes_are_interaction_overlay_not_duplicate_glyphs(tmp_path: Path) -> None:
    """Canvas owns node visuals; SVG nodes stay as hit targets and state overlays."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert ".graph-node__hit" in css
    assert "pointer-events: all" in css
    assert 'hit.setAttribute("class", "graph-node__hit")' in js
    assert "Math.max(r + 10, 20)" in js
    assert 'setAttribute("class", "graph-node__circle' not in js
    assert 'setAttribute("class", "graph-node__level")' not in js
    assert 'setAttribute("class", "graph-node__inner")' not in js


def test_viewer_js_has_canvas_render_pipeline(tmp_path: Path) -> None:
    """The viewer JS must render bulk nodes/edges to canvas, not SVG DOM."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    # Canvas context setup
    assert "getContext" in js
    assert "function initCanvas" in js
    assert "function resizeCanvas" in js
    # Canvas render function draws nodes and edges
    assert "function renderCanvas" in js
    assert "function scheduleCanvasRedraw" in js
    # Canvas must redraw on pan/zoom (batched with SVG transform)
    assert "canvasRedrawPending" in js
    # Hit-testing for clicks on canvas-only nodes
    assert "function hitTestNode" in js
    # Device pixel ratio support for crisp rendering
    assert "devicePixelRatio" in js


def test_viewer_js_reports_initialization_failures(tmp_path: Path) -> None:
    """Initialization failures after fetch must not leave the loading overlay stuck."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    init_idx = js.index("async function init")
    init_body = js[init_idx:js.index("  function showError", init_idx)]
    assert "const DATA_VERSION" in js
    assert 'fetch("graph.json?v=" + DATA_VERSION)' in init_body
    assert 'fetch("config.json?v=" + DATA_VERSION)' in init_body
    assert 'var loadStage = "loading graph data"' in init_body
    assert "graphRes.ok" in init_body
    assert "graph.json returned HTTP" in init_body
    assert 'loadStage = "laying out skill map"' in init_body
    assert "Skill map initialization failed during " in init_body
    assert "Failed to initialize skill map" in init_body


def test_viewer_js_canvas_redraws_in_request_animation_frame(tmp_path: Path) -> None:
    """Canvas transforms and optional redraws must be batched into requestAnimationFrame."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    # scheduleViewUpdate must handle canvas bitmap transforms, optional canvas
    # redraws, and label refresh inside one animation frame.
    assert "function scheduleViewUpdate" in js
    # The scheduleViewUpdate function body must reference renderCanvas and
    # requestAnimationFrame. Extract the function body up to the next
    # top-level "function " or "---" comment separator.
    idx = js.index("function scheduleViewUpdate")
    body = js[idx:]
    # Find the end: next "function " at the start of a line after a newline.
    end = body.find("\n  // ---", 10)
    if end == -1:
        end = body.find("\n  function ", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "renderCanvas" in body
    assert "applyCanvasBitmapTransform" in body
    assert "requestAnimationFrame" in body
    assert "canvasRedrawPending" in body
    assert "var cameraAnimating = isCameraAnimating()" in body
    assert body.index("applyCanvasBitmapTransform()") < body.index("applyViewTransform()")
    assert "if (canvasRedrawPending && !cameraAnimating)" in body
    assert "if (!cameraAnimating) renderMinimapViewport()" in body
    assert "labelsRefreshPending" not in js


def test_viewer_js_uses_retained_canvas_bitmap_cache(tmp_path: Path) -> None:
    """Canvas redraws should complete offscreen before replacing visible pixels."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "let canvasBitmap = null" in js
    assert "let canvasBitmapCtx = null" in js
    assert "let canvasCachePad = 0" in js
    assert "canvasCachePadMin" in js
    assert "canvasCachePadMax" in js
    assert "canvasCachePadMin: 1800" in js
    assert "canvasCachePadMax: 2200" in js
    assert "canvasViewportPad: 720" in js
    assert "canvasMaxDpr: 1.35" in js
    assert "cameraPanSettleMs: 360" in js
    assert "cameraZoomLabelSettleMs: 180" in js
    assert "cameraZoomCanvasSettleMs: 260" in js
    assert "cameraActiveRenderMinIntervalMs: 180" in js
    assert 'canvasBitmap = document.createElement("canvas")' in js
    assert 'canvasBitmap.getContext("2d")' in js
    assert "dom.graph_canvas.style.left = (-canvasViewportPad)" in js
    assert 'dom.graph_canvas.style.right = "auto"' in js
    assert 'dom.graph_canvas.style.transformOrigin = canvasViewportPad + "px " + canvasViewportPad + "px"' in js
    assert "function canvasCachePadForRect" in js
    assert "function canvasCacheSourceRect" in js
    assert "function canvasCacheCoversCurrentView" in js
    assert "function visibleCanvasViewportMissPx" in js
    assert "function visibleCanvasCoversViewport" in js
    assert "function blitCanvasBitmapCache" in js
    assert "function applyCanvasBitmapFallbackTransform" in js
    assert "function applySvgBitmapTransform" in js
    assert "setGraphZoomTransform(blittedCanvasViewState)" in js
    assert "dom.graph_svg.style.transform = \"translate3d(\" + t.x" in js
    render_body = js.split("function renderCanvas", 1)[1].split("function getCanvasDrawNodes", 1)[0]
    assert "var ctx = canvasBitmapCtx || canvasCtx" in render_body
    assert "viewState.x + canvasCachePad" in render_body
    assert "VIEW.canvasEdgeCullPad + canvasCachePad" in render_body
    assert "blitCanvasBitmapCache()" in render_body
    apply_body = js.split("function applyCanvasBitmapTransform", 1)[1].split(
        "  // --- Presentation tree scaffold ---", 1
    )[0]
    active_body = apply_body.split("if (isCameraAnimating())", 1)[1].split(
        "scheduleSettledCanvasRedraw", 1
    )[0]
    assert "canvasCacheCoversCurrentView()" in apply_body
    assert "isCameraAnimating()" in apply_body
    assert "visibleCanvasTransformWithinPad()" in apply_body
    assert "blitCanvasBitmapCache()" in apply_body
    assert "cameraCacheActiveBlit" in active_body
    assert "cameraCacheActiveRedraw" in active_body
    assert "cameraCacheDeferredMiss" in active_body
    assert "VIEW.cameraActiveRenderMinIntervalMs" in active_body
    assert "renderCanvas()" in active_body
    assert "blitCanvasBitmapCache()" in active_body
    assert "cameraCacheBlit" not in active_body
    assert "canvasCacheCoversCurrentView()" in active_body
    assert "focusDisplay && focusDisplay.active ? 1200 : VIEW.cameraPanSettleMs" in apply_body
    assert "renderCanvas()" in apply_body
    settled_body = js.split("function scheduleSettledCanvasRedraw", 1)[1].split(
        "function resetCanvasBitmapTransform", 1
    )[0]
    assert "isCameraAnimating()" in settled_body
    assert "scheduleSettledCanvasRedraw(Math.max(80" in settled_body


def test_viewer_js_only_creates_svg_edges_for_focus_path(tmp_path: Path) -> None:
    """SVG edge DOM elements should only be created for the selected focus path.

    All other edges are drawn on canvas. This prevents 12k+ SVG path elements.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    # renderSvgEdges must early-return when no node is selected
    assert "function renderSvgEdges" in js
    # Extract function body until the next top-level function or section.
    idx = js.index("function renderSvgEdges")
    body = js[idx:]
    end = body.find("\n  // ---", 10)
    if end == -1:
        end = body.find("\n  function ", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "if (!selectedNodeId)" in body
    # Only the generated presentation path gets SVG elements.
    assert "presentationPathIds(selectedNodeId)" in body
    assert "layoutCache.treeLinks" in body
    assert "treeLinkVisible(link, visibleNodeIds)" in body


def test_viewer_js_only_creates_svg_nodes_for_accessible_set(tmp_path: Path) -> None:
    """SVG node DOM elements should only be created for the accessible set.

    All other nodes are drawn on canvas. This keeps the DOM at a few hundred
    elements instead of 12k+.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    assert "function renderSvgNodes" in js
    idx = js.index("function renderSvgNodes")
    body = js[idx:]
    end = body.find("\n  // ---", 10)
    if end == -1:
        end = body.find("\n  function ", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    # Must skip nodes not in the accessible set
    assert "accessibleNodeIds.has(node.id)" in body


def test_viewer_js_culls_edges_not_canvas_nodes(tmp_path: Path) -> None:
    """Node visibility is all-node; only expensive edge/backdrop work is culled."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function buildCanvasNodeSet" in js
    node_set_body = js.split("function buildCanvasNodeSet", 1)[1].split(
        "function edgeVisibleOnCanvas", 1
    )[0]
    assert "pointInBounds" not in node_set_body
    assert "visibleNodeIds.forEach" in node_set_body
    assert "drawable.add(id)" in node_set_body

    render_body = js.split("function renderCanvas", 1)[1].split("function scheduleCanvasRedraw", 1)[0]
    assert "canvasEdgeCullPad" in render_body
    assert "pointInBounds(from, bounds)" in render_body


def test_viewer_js_canvas_handles_domain_colors_as_hex(tmp_path: Path) -> None:
    """Canvas must resolve CSS var() colors to concrete hex values.

    Canvas 2D context cannot use CSS custom properties like var(--domain-1),
    so the viewer must resolve them from computed styles.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    assert "function resolveDomainColors" in js
    assert "resolvedDomainColors" in js
    assert "function nodeColorHex" in js
    assert "getPropertyValue" in js


def test_viewer_html_has_bottom_action_dock_not_full_width_bars(tmp_path: Path) -> None:
    """The UI must be a floating game-map HUD, not full-width dashboard bars.

    Old design: a full-width toolbar + full-width filterbar.
    New design: bottom-center icon action dock, a toggleable search panel,
    legend-hosted stats, and collapsible utility panels.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    html = (tmp_path / "exports" / "viewer" / "index.html").read_text()
    # Floating HUD islands
    assert "hud-island" in html
    assert "hud-brand" not in html
    assert 'id="hud-status"' not in html
    assert "hud-search" in html
    assert "hud-actions" in html
    assert 'id="legend-stats"' in html
    assert 'id="search-toggle"' in html
    assert 'id="search-panel"' in html
    assert 'role="search"' in html
    # No full-width toolbar element
    assert 'class="toolbar"' not in html
    # Filter panel is collapsible, not a full-width bar
    assert 'class="filter-panel t-panel-slide"' in html
    assert "filter-toggle" in html


def test_viewer_css_hud_islands_are_floating(tmp_path: Path) -> None:
    """HUD islands must float, with the action dock at bottom center."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    assert ".hud-island {" in css
    hud_block = css.split(".hud-island {")[1].split("}")[0]
    assert "position: fixed" in hud_block
    assert "z-index" in hud_block
    # Each island must have its own positioning
    assert ".hud-brand" not in css
    assert ".hud-search {" in css
    assert ".hud-actions {" in css
    actions_block = css.split(".hud-actions {", 1)[1].split("}", 1)[0]
    assert "bottom: 14px" in actions_block
    assert "left: 50%" in actions_block
    assert "translateX(-50%)" in actions_block
    assert "top: 14px" not in actions_block
    search_block = css.split(".hud-search {", 1)[1].split("}", 1)[0]
    assert "bottom: 68px" in search_block
    assert "opacity: 0" in search_block


def test_viewer_js_filter_panel_is_toggleable(tmp_path: Path) -> None:
    """The filter panel must toggle open/closed via the filter button."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    assert "dom.filter_toggle" in js
    assert "dom.search_toggle" in js
    assert "togglePanel(dom.search_panel)" in js
    assert "openSearchPanel()" in js
    assert "togglePanel(dom.filter_bar)" in js
    assert "function setPanelOpen" in js
    assert 'el.dataset.open = "true"' in js
    assert 'el.dataset.open = "false"' in js


def test_viewer_action_dock_has_icon_only_toolbar_hooks(tmp_path: Path) -> None:
    """The bottom HUD behaves like an icon-only toolbar/dock."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    export_dir = tmp_path / "exports" / "viewer"
    html = (export_dir / "index.html").read_text()
    css = (export_dir / "assets" / "viewer.css").read_text()

    assert 'id="action-dock"' in html
    assert 'role="toolbar"' in html
    assert 'aria-label="Map controls"' in html
    assert 'id="toolbar-indicator"' in html
    assert 'class="hud-toolbar__indicator"' in html
    assert html.count("data-toolbar-item") == 7
    assert "hud-btn__label" not in html
    assert "data-label=" not in html
    assert 'title="' not in html.split('id="action-dock"', 1)[1].split("</div>", 1)[0]

    assert ".hud-toolbar__indicator {" in css
    assert "--toolbar-indicator-x" in css
    assert "--toolbar-indicator-width" in css
    assert "translate3d(var(--toolbar-indicator-x)" in css
    assert ".hud-btn__label" not in css
    assert "max-width: 0" not in css


def test_viewer_js_moves_toolbar_indicator_between_dock_items(tmp_path: Path) -> None:
    """The dock highlight follows hovered/focused/open toolbar buttons."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function initToolbarDockMotion" in js
    assert "function syncToolbarIndicator" in js
    assert "function activeToolbarButton" in js
    assert "getBoundingClientRect()" in js
    assert 'querySelectorAll("[data-toolbar-item]")' in js
    assert 'setProperty("--toolbar-indicator-x"' in js
    assert 'setProperty("--toolbar-indicator-opacity", "1")' in js
    assert 'setProperty("--toolbar-indicator-opacity", "0")' in js
    assert 'button.addEventListener("pointerenter"' in js
    assert 'button.addEventListener("focusin"' in js
    assert "syncToolbarIndicator(activeToolbarButton())" in js
    active_body = js.split("function activeToolbarButton", 1)[1].split(
        "function syncToolbarIndicator", 1
    )[0]
    assert "dom.sound_toggle" not in active_body


def test_viewer_has_render_settings_controls(tmp_path: Path) -> None:
    """The public viewer exposes local rendering controls for dense graphs."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    export_dir = tmp_path / "exports" / "viewer"
    html = (export_dir / "index.html").read_text()
    css = (export_dir / "assets" / "viewer.css").read_text()
    js = (export_dir / "assets" / "viewer.js").read_text()

    assert 'id="settings-toggle"' in html
    assert 'id="settings-panel"' in html
    assert 'id="setting-dim"' in html
    assert 'value="0.25"' in html
    assert 'id="setting-node-size"' in html
    assert 'id="setting-line-strength"' in html
    assert 'id="setting-label-density"' in html
    assert 'id="setting-separation"' in html
    assert 'id="setting-show-lines"' in html
    assert 'id="setting-show-categories"' in html
    assert 'id="setting-show-category-labels"' in html
    assert 'id="setting-show-skill-labels"' in html
    assert 'id="setting-show-level-badges"' in html
    assert 'id="setting-show-background-dots"' in html
    assert ".settings-panel" in css
    assert ".settings-toggle-row" in css
    assert ".viewport::before" in css
    assert '.viewport[data-dots="false"]::before' in css
    assert "--dot-offset-x" in css
    assert "--dot-offset-y" in css
    assert "DEFAULT_VIEW_SETTINGS" in js
    assert "contextDimming: 0.25" in js
    assert "showLines: true" in js
    assert "showCategories: true" in js
    assert "showCategoryLabels: true" in js
    assert "showSkillLabels: true" in js
    assert "showLevelBadges: true" in js
    assert "showBackgroundDots: true" in js
    assert "VIEW_SETTINGS_STORAGE_KEY" in js
    assert "loadViewSettings()" in js
    assert "viewSettings.contextDimming" in js
    assert "viewSettings.nodeScale" in js
    assert "viewSettings.lineStrength" in js
    assert "viewSettings.labelDensity" in js
    assert "viewSettings.separation" in js
    assert "viewSettings.showLines" in js
    assert "viewSettings.showCategories" in js
    assert "viewSettings.showCategoryLabels" in js
    assert "viewSettings.showSkillLabels" in js
    assert "viewSettings.showLevelBadges" in js
    assert "viewSettings.showBackgroundDots" in js
    assert "bindSettingRange(dom.setting_dim" in js
    assert "bindSettingCheckbox(dom.setting_show_lines" in js
    assert "bindSettingCheckbox(dom.setting_show_categories" in js
    assert "bindSettingCheckbox(dom.setting_show_category_labels" in js
    assert "bindSettingCheckbox(dom.setting_show_skill_labels" in js
    assert "bindSettingCheckbox(dom.setting_show_level_badges" in js
    assert "bindSettingCheckbox(dom.setting_show_background_dots" in js
    assert "function applyBackgroundDotsSetting" in js
    assert "function syncDotBackgroundTransform" in js
    assert 'setProperty("--dot-offset-x"' in js
    assert "togglePanel(dom.settings_panel)" in js


def test_viewer_js_render_settings_gate_visual_layers(tmp_path: Path) -> None:
    """Layer toggles hide visual families without changing node filters."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    render_canvas_body = js.split("function renderCanvas", 1)[1].split(
        "function getCanvasDrawNodes", 1
    )[0]
    assert "if (viewSettings.showCategories)" in render_canvas_body
    assert "if (viewSettings.showLines)" in render_canvas_body
    assert "viewSettings.showLines && selectedNodeId" in render_canvas_body
    assert "viewSettings.showLevelBadges && !mediumDetail" in render_canvas_body

    domain_body = js.split("function renderDomainLabels", 1)[1].split(
        "function renderSvgEdges", 1
    )[0]
    assert "!viewSettings.showCategories || !viewSettings.showCategoryLabels" in domain_body

    edge_body = js.split("function renderSvgEdges", 1)[1].split(
        "function presentationPathIds", 1
    )[0]
    assert "if (!selectedNodeId)" in edge_body
    assert "if (!viewSettings.showLines)" in edge_body

    label_body = js.split("function renderCanvasSkillLabels", 1)[1].split(
        "function drawCanvasSkillLabel", 1
    )[0]
    assert "persistentLabelPriority(node)" in label_body
    assert "if (!layoutCache || !viewSettings.showSkillLabels) return" in label_body

    hit_body = js.split("function hitTestNode", 1)[1].split("function syntheticTreeLabelHit", 1)[0]
    assert "if (viewSettings.showCategories)" in hit_body


def test_viewer_js_canvas_click_does_hit_test(tmp_path: Path) -> None:
    """Clicks on empty canvas space must hit-test canvas-only nodes.

    Most nodes are only drawn on canvas (not in the SVG accessible set).
    Clicks that pass through the SVG overlay must be hit-tested against
    canvas node positions so users can still select them.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()
    # The canvas click handler must call hitTestNode
    assert "hitTestNode(" in js
    # hitTestNode must convert screen coords to graph coords
    hit_block = js.split("function hitTestNode")[1].split("function ")[0]
    assert "safeViewScale()" in hit_block
    assert "viewState.x" in hit_block


def test_viewer_css_maintains_black_graphite_palette(tmp_path: Path) -> None:
    """The redesign must keep a black/graphite base, no blue default."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    # Deep black/graphite base
    assert "--bg: oklch(0.116 0.003 285.885)" in css
    assert "--accent: oklch(0.529 0.07 178.573)" in css
    # Domain accents: Traccia green, copper, moss, bone
    assert "--domain-3: oklch(0.638 0.1 40.978)" in css  # copper
    assert "--domain-2: oklch(0.62 0.045 160.104)" in css  # moss
    # No blue as default accent
    assert "#6cb6ff" not in css
    assert "#2563eb" not in css
    assert "transition: all" not in css


# ===========================================================================
# Phase 3: all-node canvas rendering, domain backdrops, deferred labels
# ===========================================================================


def test_viewer_js_draws_all_filtered_nodes_on_canvas(tmp_path: Path) -> None:
    """Canvas glyph rendering must not cull nodes by zoom or viewport.

    The user-visible map contract is that every in-filter, uncollapsed node
    remains visually represented at every zoom. Performance must come from
    cheaper glyph detail, capped labels, and capped SVG accessibility nodes,
    not from hiding canvas node glyphs.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function buildCanvasNodeSet" in js
    assert "function buildCanvasLODNodeSet" not in js
    assert "lodImportance" not in js
    idx = js.index("function buildCanvasNodeSet")
    body = js[idx:]
    end = body.find("\n  function ", 10)
    if end == -1:
        end = body.find("\n  // ---", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "matchesFilters(node)" not in body
    assert "visibleNodeIds.forEach" in body
    assert "isNodeCollapsed(node)" in body
    assert "drawable.add(id)" in body
    assert "nodeImportance(node)" not in body


def test_viewer_js_render_canvas_does_not_viewport_cull_node_glyphs(tmp_path: Path) -> None:
    """renderCanvas must iterate the full canvas node set for node glyphs."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    idx = js.index("// --- Draw nodes ---")
    body = js[idx:]
    end = body.find("ctx.globalAlpha = 1;", 40)
    if end == -1:
        end = body.find("\n  function ", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "canvasNodeIds.has(node.id)" in body
    assert "pointInBounds(p, bounds)" not in body
    assert "nodeImportance(node)" not in body
    assert "lowDetail" in body
    assert "detailZoomLow" in js


def test_viewer_js_has_generated_tree_scaffold(tmp_path: Path) -> None:
    """Low zoom should use generated tree links, not decorative region bubbles."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function renderTreeAreaGlows" in js
    assert "function renderSyntheticTreeNodes" in js
    assert "function shouldRenderSyntheticTreeLabel" in js
    assert "topicLabelScale: 0.42" in js
    assert 'if (node.kind === "skill-area") return false' in js
    assert "safeViewScale() >= VIEW.topicLabelScale" in js
    assert "function renderZoomBranchLinks" in js
    assert "branchParents" in js
    assert "childrenByParent" in js
    assert "layoutCache.treeLinks" in js
    assert "localBounds = bounds || getGraphViewportBounds(VIEW.canvasEdgeCullPad)" in js
    assert "VIEW.canvasEdgeCullPad : 24" not in js
    assert "segmentIntersectsBounds(from, to, localBounds)" in js
    assert "function segmentIntersectsBounds" in js
    assert "function renderDomainBackdrops" not in js
    assert "function renderConstellationScaffold" not in js
    assert "constellationRails" not in js
    idx = js.index("function renderCanvas")
    body = js[idx:]
    end = body.find("\n  // ---", 10)
    if end == -1:
        end = body.find("\n  function ", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "renderTreeAreaGlows(ctx, bounds)" in body
    assert "renderZoomBranchLinks(ctx, bounds, canvasNodeIds)" in body
    assert "renderSyntheticTreeNodes(ctx, bounds)" in body
    scaffold_body = body.split("// --- Presentation tree scaffold", 1)[1].split("// --- Draw edges ---", 1)[0]
    assert "focusDisplay && focusDisplay.active" not in scaffold_body
    glow_idx = body.index("renderTreeAreaGlows(ctx, bounds)")
    branch_links_idx = body.index("renderZoomBranchLinks(ctx, bounds, canvasNodeIds)")
    synthetic_idx = body.index("renderSyntheticTreeNodes(ctx, bounds)")
    edges_idx = body.index("--- Draw edges ---")
    assert glow_idx < branch_links_idx < synthetic_idx < edges_idx


def test_viewer_js_uses_straight_geometric_tree_lines(tmp_path: Path) -> None:
    """Tree links should draw as straight segments instead of curved paths."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function straightPath" in js
    assert "quadraticCurveTo" not in js
    assert "curvedPath" not in js
    assert " L\" + to.x + \",\" + to.y" in js


def test_viewer_js_domain_label_commits_area_focus(tmp_path: Path) -> None:
    """Clicking a main area should commit focus without turning it into a filter."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function focusDomain" in js
    assert "filters = defaultFilters()" in js
    assert "activeFocus = buildDomainFocus(domain)" in js
    assert "focusedNodeIds = new Set(activeFocus.labelIds)" in js
    assert "startFocusTransition(buildFocusDisplayState(activeFocus), fromInteraction)" in js
    assert "var focusForDock = activeFocus" in js
    assert "openFocusDock(focusForDock)" in js
    assert "filters.domain = domain" not in js
    assert "filters.maxSkills = \"all\"" not in js
    focus_domain_body = js.split("function focusDomain", 1)[1].split("  // --- Selection & focus path ---", 1)[0]
    assert "centerOnDomain(" not in focus_domain_body


def test_viewer_js_canvas_parent_nodes_commit_tree_focus(tmp_path: Path) -> None:
    """Clicking synthetic parent/topic nodes should focus their descendant skills."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function buildTreeFocus" in js
    assert "function getSyntheticTreeNode" in js
    assert "function collectTreeFocusNodes" in js
    assert "function focusTreeNode" in js
    assert "activeFocus = buildTreeFocus(id)" in js
    assert "focusedNodeIds.add(id)" in js

    hit_body = js.split("function hitTestNode", 1)[1].split("  // --- Filters ---", 1)[0]
    assert "layoutCache.treeNodes" in hit_body
    assert "node._synthetic" in hit_body
    assert "syntheticTreeLabelHit(node, p, gx, gy)" in hit_body
    assert "best = node.id" in hit_body

    click_body = js.split('dom.canvas.addEventListener("click"', 1)[1].split(
        "    // Wheel zoom", 1
    )[0]
    assert "if (nodeById.has(hitId))" in click_body
    assert "selectNode(hitId, true)" in click_body
    assert "focusTreeNode(hitId, true)" in click_body


def test_viewer_js_groups_public_skills_into_skill_areas(tmp_path: Path) -> None:
    """The public map should use first-class areas instead of raw domain folders."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "assignDomainAndVisualGroups" in js
    assert "visualGroupForNode" in js
    assert "classifySkillConstellation" in js
    assert "node._skillArea = group" in js
    assert "node._visualGroup" in js
    assert "return constellation" in js
    assert 'domain + " / " + constellation' not in js
    assert "node.description || \"\") + \" \" + (node.domain || \"\")" in js
    assert "/\\b(ai|llm|model" in js
    assert "\x08" not in js
    assert "isNodeCollapsed(node)" in js
    assert "filters.domain && node._visualGroup !== filters.domain" in js
    assert "if (node.kind === \"domain\") return false" in js


def test_viewer_js_builds_generated_presentation_hierarchy(tmp_path: Path) -> None:
    """The public viewer should render a skill tree over the flat source graph."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert '"Microck"' in js
    assert '"Skill Map", "tree-root"' not in js
    assert "Skill Area" not in js  # visible labels are concrete area names
    assert "function buildPresentationTree" in js
    assert "function branchTopicForNode" in js
    assert "BRANCH_TOPIC_RULES" in js
    assert "__tree_root__" in js
    assert 'node.kind === "tree-root" ? 18' in js
    assert "__tree_area__" in js
    assert "__tree_topic__" in js
    assert "connect(root, area" in js
    assert "connect(area, topic" in js
    assert "connect(topic, skill" in js


def test_viewer_js_normalizes_display_labels_without_mutating_raw_names(tmp_path: Path) -> None:
    """Visible labels should be cleaned while raw source labels remain searchable."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "DISPLAY_TOKEN_CASE" in js
    assert "function displayNameForText" in js
    assert "function shouldPreserveTechnicalLabel" in js
    assert "node._displayName = displayNameForText(node.name || node.id)" in js
    assert "var text = truncate(displayNameForNode(node), 24)" in js
    assert "dom.drawer_title.textContent = displayNameForNode(node)" in js
    assert "<h3>Source label</h3>" in js
    assert "(node._displayName || \"\").toLowerCase().indexOf(q)" in js
    assert "(node.name || \"\").toLowerCase().indexOf(q)" in js


def test_viewer_js_node_size_is_level_first(tmp_path: Path) -> None:
    """L3/L4/L5 nodes should not be outranked by lower-level keystone radius bonuses."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    idx = js.index("function nodeRadius")
    body = js[idx:js.index("function nodeColor", idx)]
    assert "nodeLevelStep" in js
    assert "VIEW.nodeBaseRadius" in body
    assert "VIEW.nodeLevelStep" in body
    assert "nodeImportance(node)" not in body
    assert "_isVisualKeystone" not in body
    assert "r +=" not in body
    assert "Keystone/featured ring. This is emphasis only" in js


def test_viewer_js_full_canvas_set_drives_svg_overlay_and_labels(tmp_path: Path) -> None:
    """SVG overlay nodes and labels must derive from the full canvas node set.

    The SVG layers still cap detail and accessibility, but their candidate
    source must be the full canvas node set so search, selection, and labels
    cannot drift from what the canvas actually draws.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    idx = js.index("function renderGraph")
    body = js[idx:]
    end = body.find("\n  // ---", 10)
    if end == -1:
        end = body.find("\n  function ", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "var nodeSets = refreshVisibleNodeCaches()" in body
    assert "var canvasNodeIds = nodeSets.canvasNodeIds" in body
    assert "getAccessibleNodeIds(canvasNodeIds)" in body
    assert "renderSvgEdges(canvasNodeIds)" in body
    assert "renderSvgNodes(canvasNodeIds, accessibleNodeIds)" in body
    assert "renderVirtualLabels" not in js

    cache_idx = js.index("function refreshVisibleNodeCaches")
    cache_body = js[cache_idx:js.index("function getCachedVisibleNodeIds", cache_idx)]
    assert "cachedVisibleNodeIds = getVisibleNodeIds()" in cache_body
    assert "cachedCanvasNodeIds = buildCanvasNodeSet(cachedVisibleNodeIds)" in cache_body


def test_viewer_js_resize_refits_full_atlas(tmp_path: Path) -> None:
    """Viewport changes must refit the full atlas, especially desktop to mobile."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    reset_idx = js.index("function resetView")
    reset_body = js[reset_idx:js.index("function viewportFitPadding", reset_idx)]
    assert "viewportFitPadding(rect)" in reset_body
    assert "availableWidth" in reset_body
    assert "bounds.minX + bounds.maxX" in reset_body
    assert "layoutCache.centerX" not in reset_body
    assert "layoutCache.totalWidth + 180" not in reset_body

    padding_body = js[js.index("function viewportFitPadding"):js.index("  // --- Deep linking", reset_idx)]
    assert "Math.min(rect.width, rect.height)" in padding_body
    assert "Math.min(90" in padding_body

    resize_idx = js.index('window.addEventListener("resize"')
    resize_body = js[resize_idx:js.index("    });", resize_idx) + len("    });")]
    assert "resizeFitTimer" in resize_body
    assert "resizeCanvas()" in resize_body
    assert "resetView()" in resize_body
    assert "scheduleViewUpdate(true)" not in resize_body


def test_viewer_js_hit_test_uses_full_canvas_node_set(tmp_path: Path) -> None:
    """Canvas hit-testing must select from the same full set that is drawn."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    idx = js.index("function hitTestNode")
    body = js[idx:]
    end = body.find("\n  // ---", 10)
    if end == -1:
        end = body.find("\n  function ", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "getCachedCanvasNodeIds()" in body
    assert "canvasNodeIds.forEach" in body
    assert "nodeImportance(node)" not in body


def test_viewer_js_uses_tree_glows_instead_of_region_bubbles(tmp_path: Path) -> None:
    """renderCanvas must avoid overlap-prone area bubbles.

    The new rooted skill tree may use small area glows and branch strokes, but
    it must not draw large ellipse backdrops that look like accidental overlap.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    # Area palette and helpers still exist for branch/glow accents.
    assert "DOMAIN_BACKDROP_PALETTE" in js
    assert "function domainBackdropColor" in js
    assert "function renderTreeAreaGlows" in js
    assert "function renderDomainBackdrops" not in js
    assert "ctx.ellipse" not in js
    # renderCanvas must invoke tree glows before branch links and nodes.
    idx = js.index("function renderCanvas")
    body = js[idx:]
    end = body.find("\n  // ---", 10)
    if end == -1:
        end = body.find("\n  function ", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "renderTreeAreaGlows(ctx, bounds)" in body
    glow_idx = body.index("renderTreeAreaGlows(ctx, bounds)")
    edges_idx = body.index("--- Draw edges ---")
    assert glow_idx < edges_idx


def test_viewer_js_mouse_pan_defer_labels_and_canvas_redraw(tmp_path: Path) -> None:
    """Mouse panning must transform cheaply and defer heavy canvas redraw.

    Panning should not redraw canvas labels or all canvas nodes on
    every mousemove. Only cheap SVG/canvas bitmap transforms run per frame.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    # Extract the mousemove handler body inside initPanZoom
    idx = js.index('window.addEventListener("mousemove"')
    body = js[idx:]
    end = body.find("\n    });", 10)
    if end == -1:
        end = body.find("\n  });", 10)
    body = body[:end]
    assert "setDirectView({" in body
    assert "recordPanSample(viewState.x, viewState.y, performance.now())" in body
    assert "cameraGestureActive = true" in body
    assert "setCameraTarget({" not in body
    assert "renderGraph()" not in body
    assert "scheduleSettledCanvasRedraw(VIEW.cameraPanSettleMs)" in body


def test_viewer_js_touch_pan_defer_labels_and_canvas_redraw(tmp_path: Path) -> None:
    """Touch panning must transform cheaply and defer heavy canvas redraw."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    # Extract the touchmove handler body inside initPanZoom
    idx = js.index('dom.canvas.addEventListener("touchmove"')
    body = js[idx:]
    end = body.find("\n    }, { passive: false });", 10)
    if end == -1:
        end = body.find("}, { passive: false });", 10)
    body = body[:end]
    assert "setDirectView({" in body
    assert "recordPanSample(viewState.x, viewState.y, performance.now())" in body
    assert "cameraGestureActive = true" in js
    assert "setCameraTarget({" not in body
    assert "renderGraph()" not in body
    assert "scheduleSettledCanvasRedraw(VIEW.cameraPanSettleMs)" in body


def test_viewer_js_zoom_defers_label_refresh(tmp_path: Path) -> None:
    """Zoom must defer/throttle expensive label redraws.

    Zoom can request labels, but the expensive canvas-label redraw must be
    throttled until interaction settles rather than running on every event.
    """
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    js = (tmp_path / "exports" / "viewer" / "assets" / "viewer.js").read_text()

    assert "function scheduleZoomLabelRefresh" in js
    assert "zoomLabelTimer" in js
    # zoomAt must keep the camera in active-input mode briefly; otherwise the
    # settled redraw path can race wheel input and make the graph trail the cursor.
    idx = js.index("function zoomAt")
    body = js[idx:]
    end = body.find("\n  function ", 10)
    if end == -1:
        end = body.find("\n  // ---", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "normalizedWheelPixels(event)" in body
    assert "Math.pow(2, -pixels * rate)" in body
    assert "holdWheelCameraActive(VIEW.cameraZoomCanvasSettleMs)" in body
    assert "setDirectView(target)" in body
    assert "cameraGestureActive = false" not in body
    assert "wheelZoomState = {" not in body
    assert "requestAnimationFrame(runWheelZoom)" not in body
    assert "scheduleViewUpdate(true)" not in body

    idx = js.index("function zoomToScale")
    body = js[idx:]
    end = body.find("\n  function ", 10)
    if end == -1:
        end = body.find("\n  // ---", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "setDirectView(zoomTargetForScale(cx, cy, scale, base))" in body
    assert "scheduleZoomLabelRefresh()" in body
    assert "scheduleViewUpdate(true)" not in body

    assert "function runWheelZoom" not in js
    assert "function startPanInertia" in js
    assert "PAN_INERTIA.friction" in js
    assert "if (isCameraAnimating())" in js

    idx = js.index("function scheduleZoomLabelRefresh")
    body = js[idx:]
    end = body.find("\n  function ", 10)
    if end == -1:
        end = body.find("\n  // ---", 10)
    if end == -1:
        end = len(body)
    body = body[:end]
    assert "renderGraph()" not in body
    assert "renderVirtualLabels()" not in body
    assert "renderMinimapViewport()" in body
    assert "scheduleViewUpdate(false, false)" not in body
    assert "scheduleSettledCanvasRedraw(VIEW.cameraZoomCanvasSettleMs)" in body


def test_viewer_css_hud_btn_active_scale(tmp_path: Path) -> None:
    """.hud-btn:active must use scale(0.96), not scale(0.92)."""
    _write_minimal_graph(tmp_path)
    export_viewer(tmp_path)
    css = (tmp_path / "exports" / "viewer" / "assets" / "viewer.css").read_text()
    assert ".hud-btn:active { transform: scale(0.96); }" in css
    assert "scale(0.92)" not in css
