# Finished Run Viewer Decisions

This file records the current planning decisions for the finished-run skill graph viewer.
It is a design handoff for execution, not an implementation spec.

## Constraints

- The main goal is reading the final skill graph, not auditing the execution trace.
- The viewer should feel game-like, minimalist, and professional.
- The public viewer should use a black/graphite palette with Traccia logo
  green as the primary accent, plus restrained copper, moss, and bone accents.
  Blue must not be the default accent.
- Execution for the current redesign is direct in this repository.

## Accepted Decisions

1. Optimize the viewer for reading the final skill graph. Keep run-audit details available through supporting panels only.
2. Use a deterministic constellation/radial cluster layout by default, with
   domains arranged as organic regions rather than a rigid layered grid.
3. Group primarily by taxonomy/domain hierarchy. Overlay evidence-driven signals inside nodes.
4. Show a curated readable subset by default. Put hidden, disputed, low-confidence, stale, and weak-signal nodes behind filters or review/admin modes.
5. Use node size for skill level/mastery. Use ring or border treatment for confidence.
6. Use color for domain/category. Use shape, border, icon, and opacity for status so status is not color-only.
7. Use light progression language only where Traccia has matching data, such as level, XP, acquired, current, and historical peak.
8. Keep edges quiet by default. Highlight edges and paths on focus or selection.
9. Open node details in a compact desktop selection dock, with a subtle graph
   halo/focus path on the selected node. The dock should lead with a Node
   Brief: `What`, `Trust`, `Evidence`, and `Next`. Every line in that brief
   must be backed by a public node field, public provenance summary field, or
   public edge; unsupported lines are omitted rather than filled with generic
   copy. `Next` must filter broad hub/domain nodes such as `Programming` and
   disappear when no useful connected public node remains.
10. Include search and a small filter bar in v1.
11. Include a compact supporting timeline for selected nodes or filtered graph state.
12. Use a dark, restrained game canvas as the primary style direction.
13. Use subtle functional motion only: smooth pan/zoom, selected path
    brightening, selection dock transitions, and bottom-sheet transitions.
14. Start with one primary map mode: `Skill Map`.
15. Integrate the viewer into the existing export flow as a static viewer generated from `graph/graph.json`.
16. Export as a folder with separate HTML, JS, CSS, and data files.
17. Use a hybrid canvas + SVG viewer for large public graphs. Canvas owns the
    bulk node/edge raster layer; SVG owns domain labels, selected-path
    overlays, capped accessibility nodes, and virtual labels. Do not use
    WebGL in v1.
18. Compute layout in the browser for the first version.
19. Do not support manual node repositioning in v1.
20. Treat "delete/comment out node" as viewer curation, not graph deletion.
21. Store shared curation inside the export folder, not browser local storage.
22. Provide two explicit export targets: an admin curation export and a public publish export.
23. Keep admin curation v1 to visibility and emphasis only:
    - Hide or mute node from public map.
    - Restore hidden node.
    - Feature or pin important node.
    - Collapse or expand domain regions.
    - Add a short public-facing note or label override.
24. Let the admin viewer write `curation.json` directly when running locally, with a clear save action.
25. Physically remove hidden nodes, hidden edges, and private/redacted provenance from the public export data.
26. Use phased droid execution tasks rather than one full implementation mission.
27. Phase 1 should build the read-only public viewer only.
28. Phase 2 should add the admin curation workflow.
29. Do not include raw evidence excerpts in the public bundle by default.
30. Public viewer should expose confidence and uncertainty elegantly through confidence rings, reliability badges, freshness states, and evidence strength summaries.
31. Do not support comparing this finished run to a previous run in v1.
32. Do not include a featured summary strip or panel in v1. Keep the public viewer focused on the skill tree only.
33. Include compact node detail surfaces in v1 so confidence, freshness,
    provenance summaries, connected public nodes, and timeline fields have a
    clean secondary surface.
    Desktop uses a HUD-aligned selection dock instead of a full-height drawer;
    mobile uses an expandable bottom sheet.
34. Support domain collapse/expand in both public and admin viewers. Public collapse state is temporary per browser session; admin default collapse state can be saved into `curation.json`.
35. Search should match skill names, domains, areas, and descriptions in v1. Do not search aliases, raw provenance, or evidence in the public viewer unless public-safe summaries are added later.
36. Keep search always visible, and keep domain, status, freshness,
    confidence, and evidence type reachable through a compact collapsible HUD
    filter panel instead of a full-width filter bar.
37. Include a small subdued minimap, and make it collapsible so it supports orientation without adding visual noise.
38. Do not show edge type labels on the canvas by default. Communicate edge
    meaning through line style and reveal exact edge type on hover, selection,
    or in the node detail surface.
39. Include keyboard navigation in v1: Tab focus for nodes and controls, Enter
    or Space to select a node, Escape to close the detail surface, search focus
    affordance, and arrow-key movement between nearby/focused nodes if the
    graph library supports it cleanly.
40. Do not include a non-graph fallback list or table in v1. Keep the public
    experience skill-tree-first, using search, filters, keyboard focus,
    minimap, and node detail surfaces for navigation and inspection.
41. Design desktop as the main target, but treat mobile as primary enough to be responsive, usable, and verified. Mobile should not be a neglected fallback.
42. On mobile, use an expandable bottom sheet for node details so users keep map context while still having room for detail inspection.
43. Include a compact collapsible legend explaining domain colors, confidence rings, status shapes/icons, freshness treatment, and edge styles.
44. Visually distinguish current level from historical peak subtly. Current
    level drives node size/fill; historical peak appears in the node detail
    surface and optionally as a faint outer ghost ring only when it is higher
    than current level.
45. Dim stale or historical skills slightly on the main map while keeping them readable. Use reduced saturation or a small freshness icon, and let filters isolate active/current skills.
46. Do not include disputed or review-state nodes in the public publish bundle by default. Admin can see them; public publication requires explicit opt-in and clear disputed/review visual marking.
47. Do not publish low-confidence nodes by default. Keep them admin-visible unless explicitly approved in curation.
48. Admin curation may explicitly approve low-confidence nodes for public publish, but must not edit the confidence score. Public viewer still shows confidence honestly.
49. Use automatic conservative public provenance summaries in v1, with optional manual public notes through curation. Summaries may include counts, evidence types, reliability tiers, source categories, and timestamps, but must not rewrite private excerpts into public prose.
50. Publish output must use a separate public graph contract, not a lightly filtered copy of the admin graph. It may include only intentionally public fields: node identity, public label/description, kind/domain, level, confidence, freshness/status, public-safe metrics, public-safe provenance summary, and public edges. It must exclude raw source paths, raw excerpts, sensitive evidence IDs, hidden/private nodes, and hidden/private edges.
51. Public node IDs should remain the same as internal skill IDs unless a skill ID leaks private information. For sensitive IDs, publish should generate stable public alias IDs and keep the mapping admin-only.
52. Public viewer URLs should support hash deep links to nodes, such as
    `#node=<public-node-id>`. Opening a deep link should select the node,
    center it, highlight its local path, and open the node detail surface.
53. Show skill-area labels as subtle interactive SVG labels near branch roots.
    Do not repeat area labels on every node or draw duplicate canvas labels for
    the same area.
54. Include minimal SFX in v1, but treat sound as tactile UI feedback, not atmosphere. Do not add music, ambient loops, hover chirps, pan/zoom sounds, or per-keystroke search sounds.
55. Make SFX original. Use the Lisse and Highlighters sites as interaction-tone references only: small event vocabulary, low volume, short sounds, gesture-gated audio unlock, subtle variation, and careful rate limiting. Do not copy or derive from their audio assets.
56. Prefer a small procedural Web Audio sound engine for the first implementation so the export stays original, small, and self-contained. Use generated static audio files only if droid determines Web Audio cannot hit the intended quality or compatibility bar.
57. SFX should be enabled only after the user's first interaction, with a visible mute toggle in the compact toolbar. Remember the viewer-local preference in browser storage for that public export. No sound should play before a user gesture.
58. The public sound palette should feel like a clean skill-map interface: soft glass/graphite ticks, muted tonal blooms, and short filtered noise transients. Avoid arcade coins, fantasy spell sounds, sci-fi alarms, orchestral stingers, and aggressive high-frequency clicks.
59. Use sound only for meaningful state changes:
    - Node select or deep-link focus: soft two-layer tick, about 60-110 ms.
    - Drawer open or close: very quiet slide/bloom, about 100-160 ms.
    - Domain collapse or expand: compact fold/unfold cue, about 80-140 ms.
    - Filter application or clear action: dry switch cue, about 35-70 ms.
    - Admin curation save or publish success: rare restrained confirmation, about 140-220 ms.
60. Keep repeated interactions stable and non-fatiguing. Use at most subtle pitch, timing, or filter variation on frequent sounds, and reserve larger variation for rare admin confirmations. Rate-limit overlapping one-shots so rapid graph navigation does not smear into noise.
61. Respect accessibility and context. If the browser exposes reduced-motion or similar preference signals, keep visual motion reduced and keep SFX minimal; always let the explicit mute toggle win. Do not make SFX necessary to understand state.
62. Put the sound setting in the public export config so a publishable bundle can default sound on or off per export. Recommended default for the first public viewer is sound on after first interaction, at very low gain, with the mute toggle obvious.
63. Use an off-black/graphite public viewer palette as the canonical theme.
    Keep `prefers-color-scheme` present for browser integration, but do not
    switch the public viewer into a light dashboard palette.
64. Treat each domain's highest-importance public node as a keystone. Importance
    is deterministic and comes from featured status, level, confidence,
    centrality, and public evidence count.
65. Render node labels virtually. Labels should be reserved for selected nodes,
    focused neighbors, search matches, featured nodes, keystones, and high-zoom
    in-viewport nodes, with a hard cap for normal labels.
66. Batch graph DOM updates with `DocumentFragment` and replace completed SVG
    layers at once. Avoid per-node incremental appends into live SVG groups.
67. Batch pan, zoom, minimap viewport updates, and virtual-label refreshes with
    `requestAnimationFrame` so pointer movement does not synchronously rewrite
    the SVG transform on every input event.
68. Avoid `transition: all` in public viewer CSS. Transition only the properties
    that actually change.
69. Public toolbar and close controls should use ASCII text or inline SVG icons.
    Do not ship emoji entities or decorative themed icons in the public viewer.
70. Keep the admin/public curation and redaction boundaries unchanged. The
    redesign changes presentation and client-side layout/performance only.
71. Do not put every rendered public node in the accessibility tree or tab
    order. Large public graphs can exceed 12k nodes, and thousands of SVG
    `role="button"` refs create browser and assistive-technology overhead.
72. Use a roving priority node accessibility model. The selected node, focused
    path/neighbors, search matches, keystones, featured nodes, and a capped
    high-priority visible set may receive `role="button"`, `tabindex="0"`, and
    `aria-label`; other rendered nodes stay visually clickable but are
    `aria-hidden` until promoted by selection, search, or priority.
73. Handle node click and Enter/Space activation with event delegation on the
    node SVG layer. Do not attach per-node click or keydown handlers in large
    public graphs.
74. Public skill areas should render as a generated radial skill tree, not
    free-scattered clusters, raw source-domain folders, or overlapping region
    bubbles. The public presentation hierarchy is `Skill Map -> Skill Area ->
    Branch Topic -> Skill`. It is a viewer-only hierarchy over the flat source
    graph and does not mutate the graph contract.
75. Pan and zoom should follow graph/map camera patterns from D3, Sigma,
    Leaflet, Pixi Viewport, MapLibre, and panzoom: active drag stays directly
    attached to the pointer, recent pan samples feed a short post-release
    inertia pass, and mouse-wheel zoom uses a cursor-anchored interruptible
    animation. Do not smooth active drag by globally lerping the camera toward
    a target, because that reads as input latency rather than polish.
76. Public map trees should be presented as top-level skill areas, not as
    nested raw-domain paths such as `Programming / Media & Creative`. Raw graph
    domains remain source metadata in node details, but filters, legend entries,
    cluster labels, and branch colors use skill-area names so users read the map
    as a skill tree instead of a taxonomy accident.
77. Node radius should primarily encode level/mastery. Keystone, featured, and
    high-importance treatment should use rings, glow, and path emphasis instead
    of radius bonuses, so an L2/L3 notable does not appear physically larger
    than an ordinary L4/L5 skill.
78. Visible labels use a display-name normalization layer. Raw graph labels
    remain searchable and visible in node details when they differ, but canvas
labels, detail titles, ARIA labels, filters, and legend entries should use
    cleaned display labels with preserved technical casing for tokens such as
    API, CSS, JSON, LLM, GitHub, iOS, and .NET.
79. Branch-topic labels should not render at the fitted overview. They appear
    when zoomed in enough for local reading (`VIEW.topicLabelScale`, currently
    0.42) or when the topic is part of the selected focus path. The overview
    should read from trunk lines, area labels, and node glyphs first.

## Research Notes

- Skill trees in games work best when the visible structure communicates progression, specialization, and meaningful differences. For this finished-run viewer, that means domain regions, landmark nodes, confidence/freshness encodings, search, minimap, and detail drawers matter more than RPG mechanics like points, unlock costs, or respec.
- Large skill graphs create an appealing "wow" moment, but community feedback around Path of Exile-style trees repeatedly points to readability problems when labels, regions, and important nodes are not organized clearly.
- Diablo-style clustered trees and World of Warcraft's Dragonflight talents both reinforce the value of clear node types, search, starter/default views, and loadout-like curation. For this viewer, the comparable pattern is a curated default public map plus admin curation, not public editing.
- Material Design's sound guidance supports using silence deliberately, keeping frequent UX sounds understated, and reserving bigger "hero" cues for rare moments. This viewer should avoid hero sounds except possibly admin publish success.
- Lisse's website uses a compact set of small WebM interaction sounds plus synthesized slider ticks. The useful reference pattern is low asset weight, event-specific cues, preloading/gesture handling, and rate-capped continuous feedback.
- Highlighters' website uses a dedicated audio facade and engine with small MP3 families, decoded buffers, shuffle/no-repeat behavior, low gain values, gesture-gated playback, and explicit fade/rate controls. The useful reference pattern is a cohesive material family and restrained variation, not copying the sounds.
- Game-audio community feedback is split on variation for UI sounds, but the practical consensus is that frequent UI feedback should be stable, short, dry, quiet, and non-fatiguing. Variation should be subtle enough that the event identity remains recognizable.
- Pan/zoom implementation research points to three separate motion layers.
  Direct manipulation should remain immediate under the pointer; inertia
  belongs after release, using recent viewport samples; wheel zoom should be
  normalized by device type and animated for about 180-220 ms around the cursor.
  Primary source checks included D3's `d3-zoom`/`interpolateZoom`, Pixi
  Viewport's `Wheel` and `Decelerate` plugins, Leaflet's drag and scroll-wheel
  handlers, Sigma's camera and mouse captor, MapLibre/Mapbox scroll zoom, and
  `anvaka/panzoom` kinetic scrolling.
- The black skill-tree design draft is useful only as structural direction:
  organic radial clusters, keystone nodes, sparse labels, quiet edges, selected
  path brightening, and graphite/green/copper/moss color balance. Do not copy
  its fantasy typography, themed copy, icons, or RPG-specific controls.
- Obsidian Canvas is not the best performance reference for this public viewer
  because Canvas cards can contain rich DOM/media content, and community
  reports show lag when many cards or images are visible or remounted while
  panning. The useful Obsidian lesson is from graph-style rendering: keep the
  graph itself in a canvas/WebGL-like pixel layer, keep CSS/DOM out of the bulk
  node path, avoid mount/unmount churn during pan/zoom, and degrade detail
  rather than hiding the underlying node glyphs.
- Source checks behind that decision:
  Obsidian Hub documents Graph View as `<canvas>`/WebGL-rendered, which is why
  normal CSS cannot directly style graph nodes and links. The community Canvas
  performance patch identified two DOM-heavy failure modes: media nodes
  unmounting/remounting while zoomed out and `backface-visibility: hidden`
  increasing layout work. MDN canvas guidance aligns with the viewer strategy:
  avoid expensive text/shadow work, batch draw calls where practical, use
  `requestAnimationFrame`, layer static/dynamic work when useful, and cap DOM
  overlays separately from pixel rendering.
- Skill-tree research points away from pure graph layouts for the default
  public view. Strong game examples use visible specialization paths, landmark
  nodes, and branch regions: Path of Exile distinguishes small passives,
  notables, and keystones; its official guidance also relies on search and
  shortest-path highlighting for a 1,325-node tree. Diablo/WoW-style trees use
  rows, gates, and branch grouping to imply progression. For Traccia this means
  no fake unlock rules, but a visual grammar of branch lanes, mastery tiers,
  and keystone anchors.
- Graph drawing readability research supports the same direction. The most
  relevant metrics are node occlusion, edge crossing, edge crossing angle, edge
  tunneling, node size, spatial grouping, and label size. The viewer should
  optimize the default view for all nodes remaining visible as low-detail
  glyphs, while using smaller ordinary node radii, capped labels, quieter
  non-focus edges, and branch lanes to keep clusters countable.
- The active rrss public export is extremely unbalanced by raw domain: almost
  all public nodes are under `Programming`, with only a few nodes under raw
  domains such as `Data`, `Documentation`, `Operations`, and `Collaboration`.
  The public viewer therefore treats visual grouping as a skill-area layer for
  every skill node, not only for oversized domains.
- Skill areas include General Craft, Web & Interface, Code & Tooling,
  AI & Automation, Data & Analysis, Systems & Operations, Media & Creative,
  Product & Planning, Security & Privacy, Communication, and Docs & Knowledge.
  The raw domain is still visible in node details when it differs from the
  area, but users should not see branches as children of `Programming` just
  because the extraction layer over-bucketed the source graph.
- The viewer now generates branch-topic nodes beneath skill areas so the map
  has an actual readable tree depth over the flat source graph. Branch topics
  are deterministic presentation labels derived from skill names, descriptions,
  and the chosen skill area. They are not stored back into the source graph.
- Large translucent area ellipses were removed because their overlap looked
  like layout collision rather than meaningful intersection. Structure now
  comes from trunk lines, branch-topic nodes, selected-path highlighting, and
  small area glows.

## Execution Phases

### Phase 1: Read-Only Public Viewer

- Consume existing `graph/graph.json`.
- Render the curated skill map with deterministic browser layout.
- Support pan/zoom, search, filters, focus path highlighting, a desktop
  selection dock, and a mobile bottom sheet.
- Use minimalist professional game styling.
- Export as a static folder.

### Phase 2: Admin Curation And Publish Flow

- Admin viewer loads the full `graph.json`.
- Admin can hide/mute, restore, feature/pin, collapse domains, and add public label/note overrides.
- Admin saves `curation.json` into the export folder.
- Publish step generates a redacted public bundle from `graph.json + curation.json`.
- Public bundle contains no hidden nodes, hidden edges, or private/redacted provenance.

**Status: implemented.**

- `traccia export admin` generates `exports/viewer-admin/` with the full graph, curation.json, and admin viewer assets.
- The admin viewer supports hide/mute, restore, feature/pin, collapse/expand domains, public label/note overrides, low-confidence approval, and disputed/review approval.
- Save action writes `curation.json` directly when running locally (via fetch PUT). When direct filesystem writes are not possible (static file server, browser-only), it triggers a browser download of `curation.json` so the admin can place it in the export folder manually.
- `traccia export publish` generates `exports/viewer-public/` with a fully redacted public bundle from `graph.json + curation.json`.
- The publish step physically excludes hidden nodes, hidden edges, private/redacted provenance, raw source paths, raw excerpts, sensitive evidence IDs, disputed/review nodes (unless explicitly approved), and low-confidence nodes (unless explicitly approved).
- Public node IDs remain the same as internal IDs unless a skill ID contains characters that suggest private information (email addresses, file paths, spaces). For those, publish generates deterministic `pub_<hash>` alias IDs and writes the admin-only mapping to `alias-map.json` alongside the public bundle (this file must not be deployed publicly).
- Public viewer redesign now uses a generated radial skill tree, keystone
  treatment, sparse virtual labels, batched SVG layer replacement, and
  requestAnimationFrame pan/zoom updates.
- Public node accessibility now uses a capped roving priority set plus
  delegated node-layer events, so large graphs do not expose every rendered
  node as an individual focusable button.

## Open Decisions

### Review Resolution Notes

The following review gaps were addressed in the public viewer implementation:

1. **Domain collapse/expand in session (decision 34)**: Implemented in the
   public viewer. Domain labels are now SVG text elements with `role="button"`,
   `tabindex="0"`, click handlers, and Enter/Space keyboard activation. Collapse
   state is tracked in a session-level `collapsedDomains` object (not persisted
   to localStorage or curation.json, per the public-viewer contract). Collapsed
   domains hide their nodes and connecting edges. The `sfx.domainToggle(expanding)`
   sound fires on each toggle.

2. **Keyboard focusable/selectable SVG nodes (decision 39)**: Public nodes use
   a roving priority focus model. Only selected nodes, focused path/neighbors,
   search matches, keystones, featured nodes, and a capped priority set carry
   `tabindex="0"`, `role="button"`, and descriptive `aria-label` values. Other
   rendered nodes remain mouse-clickable but `aria-hidden`. Enter and Space
   activate focused nodes through delegated node-layer handlers. Arrow
   navigation works from either the selected node or the Tab-focused node,
   moves keyboard focus to the new target, and skips nodes inside collapsed
   domains.

3. **Search placeholder truthfulness**: The public graph contract (decision 50)
   does not include aliases. The search placeholder was corrected from
   "Search skills, aliases, domains..." to "Search skills, domains,
   descriptions..." to match what `nodeMatchesSearch` actually searches (name,
   domain, description). No alias search was implemented because the public
   bundle intentionally strips alias data.

## Performance and HUD Redesign

### Problem

The original public viewer created SVG DOM elements for every visible node
and edge. With the real public graph at ~12,858 nodes and ~12,853 edges,
this meant ~25,000+ SVG path/circle/text elements in the DOM on initial
load, and the entire graph layer was rebuilt on every pan/zoom interaction.
The result was severe lag and an unresponsive UI. Additionally, the top UI
used two full-width bars (a dashboard toolbar and a filter bar) which felt
structured and dashboard-like rather than game-like.

### Canvas Raster Layer (Performance Fix)

The viewer now uses a hybrid canvas + SVG architecture:

- **Canvas raster layer** (`<canvas id="graph-canvas">`) draws ALL visible
  node glyphs as pixels at every zoom level, plus bulk edges where they are
  useful for the current view. This is the performance workhorse: no DOM
  elements per node or edge. Canvas redraw is batched into
  `requestAnimationFrame` alongside the SVG transform, minimap viewport,
  and virtual label refresh, so pan/zoom never synchronously redraws.

- **SVG overlay layer** (`<svg id="graph-svg">`) keeps only:
  - Domain region labels (interactive, keyboard focusable)
  - The capped accessible node set (max 260 nodes for AT/keyboard)
  - Virtual labels (capped at 180, viewport-aware)
  - Focus-path highlighted edges (only when a node is selected)

- **Canvas hit-testing** handles clicks on nodes that are only drawn as
  pixels (not in the SVG accessible set). The click handler converts screen
  coordinates to graph coordinates and finds the nearest visible node within
  a hit radius.

- **No node glyph culling**: node glyphs are not hidden by zoom, importance,
  or viewport tests. Every in-filter, uncollapsed node remains represented on
  the canvas. Performance comes from cheaper low-zoom glyph detail, capped
  labels, capped SVG accessibility nodes, and edge/backdrop culling.

- **Device pixel ratio support** ensures crisp rendering on retina/HiDPI
  displays by scaling the canvas backing store by `devicePixelRatio`.

- **CSS var() color resolution**: Canvas cannot use `var(--domain-N)` CSS
  custom properties, so the viewer resolves them to concrete hex values
  from computed styles once at init and on resize.

This drops DOM element count from ~25k to a few hundred, making pan/zoom
smooth even on the largest public graphs.

### Floating Game-Map HUD (UI Redesign)

The top UI was replaced from two full-width bars to a floating game-map HUD:

- **Brand/status island** (top-left): compact floating block with the app
  mark, title, and a live node count status line.
- **Command/search island** (top-center): floating search pill.
- **Action island** (top-right): compact icon stack for filters, legend,
  minimap, sound, and reset.
- **Collapsible filter panel**: folds out from the action island when the
  filter button is clicked. Not a second full-width bar. Toggled with the
  `F` keyboard shortcut.

All HUD islands use `position: fixed`, `backdrop-filter: blur()`, and
floating shadows to feel like a game map overlay rather than a dashboard.
The viewport is full-bleed behind them.

### Visual Changes

- Palette shifted slightly deeper (`--bg: #050506`) for a darker game canvas.
- Viewport background uses radial gradients for subtle domain-region glow.
- Nodes drawn on canvas use the same domain colors, confidence rings,
  keystone rings, glow, and search-match highlights as before.
- Level text only renders on canvas when zoomed in past 0.5x scale to avoid
  clutter at low zoom.
- SVG overlay nodes and edges keep all existing visual treatments.

### All-Node Glyphs, Generated Tree, Deferred Labels

The real public graph (~12k nodes) can become a laggy green hairball at
default zoom if every node is rendered with full detail. The current contract
keeps every node glyph visible while reducing the expensive detail layers:

1. **All-node canvas glyph set**: `buildCanvasNodeSet` includes every
   in-filter, uncollapsed node. The canvas node pass does not apply
   importance thresholds, global budgets, per-domain budgets, or viewport
   tests to node glyphs. At low zoom, non-landmark nodes draw with cheaper
   detail: no inner dot, no level text, and thinner strokes. Selected nodes,
   focus neighbors, featured nodes, keystones, and search matches keep richer
   treatment.

2. **Generated radial tree scaffold**: `buildPresentationTree` creates a
   viewer-only hierarchy of `Skill Map -> Skill Area -> Branch Topic -> Skill`.
   `renderZoomBranchLinks` draws the trunk and branch links on canvas before
   node glyphs. `renderSyntheticTreeNodes` draws only synthetic root, area, and
   topic anchors; area names are handled by the SVG area-label layer so they do
   not render twice.

3. **Topic label LOD**: Branch-topic labels are hidden at the fitted overview
   and appear only at closer zoom or on the focused path. This keeps the first
   view from becoming a label cloud while preserving local branch names when a
   user navigates into an area.

4. **Deferred label and canvas recomputation**: Panning (mouse `mousemove` and
   touch `touchmove`) calls `scheduleViewUpdate(false, false)`, so virtual
   labels and the expensive all-node canvas redraw are not rebuilt on every
   pan event. The current canvas bitmap is transformed by the compositor while
   input is active, then `scheduleSettledCanvasRedraw` refreshes the full
   pixel layer when the interaction settles. Zoom routes through
   `scheduleZoomLabelRefresh`, which throttles expensive label rebuilds with a
   short timer (`zoomLabelTimer`).

5. **HUD active scale**: `.hud-btn:active` uses `scale(0.96)` instead of
   `scale(0.92)` for a subtler press affordance.

6. **Responsive atlas fitting**: `resetView` uses viewport-relative padding
   and layout bounds instead of a fixed desktop margin. Browser resizes
   debounce a canvas resize plus `resetView`, so switching between desktop
   and mobile keeps the full public atlas in frame instead of preserving a
   stale transform from the previous viewport.
