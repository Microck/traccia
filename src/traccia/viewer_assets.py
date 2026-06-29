"""Static viewer asset source strings for the Phase 1 public skill map viewer.

These are kept as Python constants so the export is self-contained, ships
inside the wheel, and needs no JS bundler. The viewer is vanilla JS + SVG
per decision 17 (React Flow-style DOM/SVG nodes, not custom canvas/WebGL).
"""

from __future__ import annotations

VIEWER_HTML = """\
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>Skill Map</title>
<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
<link rel="stylesheet" href="assets/viewer.css?v=20260629-anchor-lock-1">
<link rel="preload" href="graph.json?v=20260629-anchor-lock-1" as="fetch" crossorigin>
</head>
<body class="viewer-loading">

<!-- Floating game-map HUD: compact islands, not full-width bars -->

<!-- Command / search panel (opened from the bottom action dock) -->
<div class="hud-island hud-search t-panel-slide" id="search-panel" role="search" data-open="false" hidden>
  <label class="search-field">
    <span class="search-field__icon" aria-hidden="true">
      <svg class="icon" viewBox="0 0 256 256" focusable="false">
        <path d="M229.66,218.34l-50.07-50.06a88.11,88.11,0,1,0-11.31,11.31l50.06,50.07a8,8,0,0,0,11.32-11.32ZM40,112a72,72,0,1,1,72,72A72.08,72.08,0,0,1,40,112Z"></path>
      </svg>
    </span>
    <input
      id="search-input"
      type="search"
      class="search-field__input"
      placeholder="Search skills, areas, descriptions..."
      autocomplete="off"
      aria-label="Search skills"
      accesskey="/"
    >
    <button id="search-clear" class="search-field__clear" type="button" aria-label="Clear search" hidden>x</button>
  </label>
</div>

<!-- Action dock (bottom-center) -->
<div class="hud-island hud-actions" id="action-dock" role="toolbar" aria-label="Map controls">
  <span class="hud-toolbar__indicator" id="toolbar-indicator" aria-hidden="true"></span>
  <button id="search-toggle" class="hud-btn" type="button" aria-label="Toggle search" data-toolbar-item>
    <svg class="icon" viewBox="0 0 256 256" aria-hidden="true" focusable="false">
      <path d="M229.66,218.34l-50.07-50.06a88.11,88.11,0,1,0-11.31,11.31l50.06,50.07a8,8,0,0,0,11.32-11.32ZM40,112a72,72,0,1,1,72,72A72.08,72.08,0,0,1,40,112Z"></path>
    </svg>
  </button>
  <button id="filter-toggle" class="hud-btn" type="button" aria-label="Toggle filters" data-toolbar-item>
    <svg class="icon" viewBox="0 0 256 256" aria-hidden="true" focusable="false">
      <path d="M200,136a8,8,0,0,1-8,8H64a8,8,0,0,1,0-16H192A8,8,0,0,1,200,136Zm32-56H24a8,8,0,0,0,0,16H232a8,8,0,0,0,0-16Zm-80,96H104a8,8,0,0,0,0,16h48a8,8,0,0,0,0-16Z"></path>
    </svg>
  </button>
  <button id="legend-toggle" class="hud-btn" type="button" aria-label="Toggle legend" data-toolbar-item>
    <svg class="icon" viewBox="0 0 256 256" aria-hidden="true" focusable="false">
      <path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm0,192a88,88,0,1,1,88-88A88.1,88.1,0,0,1,128,216Zm16-40a8,8,0,0,1-8,8,16,16,0,0,1-16-16V128a8,8,0,0,1,0-16,16,16,0,0,1,16,16v40A8,8,0,0,1,144,176ZM112,84a12,12,0,1,1,12,12A12,12,0,0,1,112,84Z"></path>
    </svg>
  </button>
  <button id="settings-toggle" class="hud-btn" type="button" aria-label="Toggle view settings" data-toolbar-item>
    <svg class="icon" viewBox="0 0 256 256" aria-hidden="true" focusable="false">
      <path d="M128,80a48,48,0,1,0,48,48A48.05,48.05,0,0,0,128,80Zm0,80a32,32,0,1,1,32-32A32,32,0,0,1,128,160Zm109.94-52.79a8,8,0,0,0-3.89-5.4l-29.83-17-.12-33.62a8,8,0,0,0-2.83-6.08,111.91,111.91,0,0,0-36.72-20.67,8,8,0,0,0-6.46.59L128,41.85,97.88,25a8,8,0,0,0-6.47-.6A112.1,112.1,0,0,0,54.73,45.15a8,8,0,0,0-2.83,6.07l-.15,33.65-29.83,17a8,8,0,0,0-3.89,5.4,106.47,106.47,0,0,0,0,41.56,8,8,0,0,0,3.89,5.4l29.83,17,.12,33.62a8,8,0,0,0,2.83,6.08,111.91,111.91,0,0,0,36.72,20.67,8,8,0,0,0,6.46-.59L128,214.15,158.12,231a7.91,7.91,0,0,0,3.9,1,8.09,8.09,0,0,0,2.57-.42,112.1,112.1,0,0,0,36.68-20.73,8,8,0,0,0,2.83-6.07l.15-33.65,29.83-17a8,8,0,0,0,3.89-5.4A106.47,106.47,0,0,0,237.94,107.21Zm-15,34.91-28.57,16.25a8,8,0,0,0-3,3c-.58,1-1.19,2.06-1.81,3.06a7.94,7.94,0,0,0-1.22,4.21l-.15,32.25a95.89,95.89,0,0,1-25.37,14.3L134,199.13a8,8,0,0,0-3.91-1h-.19c-1.21,0-2.43,0-3.64,0a8.08,8.08,0,0,0-4.1,1l-28.84,16.1A96,96,0,0,1,67.88,201l-.11-32.2a8,8,0,0,0-1.22-4.22c-.62-1-1.23-2-1.8-3.06a8.09,8.09,0,0,0-3-3.06l-28.6-16.29a90.49,90.49,0,0,1,0-28.26L61.67,97.63a8,8,0,0,0,3-3c.58-1,1.19-2.06,1.81-3.06a7.94,7.94,0,0,0,1.22-4.21l.15-32.25a95.89,95.89,0,0,1,25.37-14.3L122,56.87a8,8,0,0,0,4.1,1c1.21,0,2.43,0,3.64,0a8.08,8.08,0,0,0,4.1-1l28.84-16.1A96,96,0,0,1,188.12,55l.11,32.2a8,8,0,0,0,1.22,4.22c.62,1,1.23,2,1.8,3.06a8.09,8.09,0,0,0,3,3.06l28.6,16.29A90.49,90.49,0,0,1,222.9,142.12Z"></path>
    </svg>
  </button>
  <button id="minimap-toggle" class="hud-btn" type="button" aria-label="Toggle minimap" aria-pressed="false" data-toolbar-item>
    <svg class="icon" viewBox="0 0 256 256" aria-hidden="true" focusable="false">
      <path d="M228.92,49.69a8,8,0,0,0-6.86-1.45L160.93,63.52,99.58,32.84a8,8,0,0,0-5.52-.6l-64,16A8,8,0,0,0,24,56V200a8,8,0,0,0,9.94,7.76l61.13-15.28,61.35,30.68A8.15,8.15,0,0,0,160,224a8,8,0,0,0,1.94-.24l64-16A8,8,0,0,0,232,200V56A8,8,0,0,0,228.92,49.69ZM104,52.94l48,24V203.06l-48-24ZM40,62.25l48-12v127.5l-48,12Zm176,131.5-48,12V78.25l48-12Z"></path>
    </svg>
  </button>
  <button id="sound-toggle" class="hud-btn hud-btn--sound" type="button" aria-label="Toggle sound" aria-pressed="true" data-toolbar-item>
    <span class="t-icon-swap sound-icon-swap" data-state="on" aria-hidden="true">
      <span class="t-icon sound-off" data-icon="off">
        <svg class="icon" viewBox="0 0 256 256" focusable="false">
          <path d="M155.51,24.81a8,8,0,0,0-8.42.88L77.25,80H32A16,16,0,0,0,16,96v64a16,16,0,0,0,16,16H77.25l69.84,54.31A8,8,0,0,0,160,224V32A8,8,0,0,0,155.51,24.81ZM32,96H72v64H32ZM144,207.64,88,164.09V91.91l56-43.55Zm101.66-61.3a8,8,0,0,1-11.32,11.32L216,139.31l-18.34,18.35a8,8,0,0,1-11.32-11.32L204.69,128l-18.35-18.34a8,8,0,0,1,11.32-11.32L216,116.69l18.34-18.35a8,8,0,0,1,11.32,11.32L227.31,128Z"></path>
        </svg>
      </span>
      <span class="t-icon sound-on" data-icon="on">
        <svg class="icon" viewBox="0 0 256 256" focusable="false">
          <path d="M155.51,24.81a8,8,0,0,0-8.42.88L77.25,80H32A16,16,0,0,0,16,96v64a16,16,0,0,0,16,16H77.25l69.84,54.31A8,8,0,0,0,160,224V32A8,8,0,0,0,155.51,24.81ZM32,96H72v64H32ZM144,207.64,88,164.09V91.91l56-43.55Zm54-106.08a40,40,0,0,1,0,52.88,8,8,0,0,1-12-10.58,24,24,0,0,0,0-31.72,8,8,0,0,1,12-10.58ZM248,128a79.9,79.9,0,0,1-20.37,53.34,8,8,0,0,1-11.92-10.67,64,64,0,0,0,0-85.33,8,8,0,1,1,11.92-10.67A79.83,79.83,0,0,1,248,128Z"></path>
        </svg>
      </span>
    </span>
  </button>
  <button id="reset-view" class="hud-btn" type="button" aria-label="Reset view" data-toolbar-item>
    <svg class="icon" viewBox="0 0 256 256" aria-hidden="true" focusable="false">
      <path d="M224,128a96,96,0,0,1-94.71,96H128A95.38,95.38,0,0,1,62.1,197.8a8,8,0,0,1,11-11.63A80,80,0,1,0,71.43,71.39a3.07,3.07,0,0,1-.26.25L44.59,96H72a8,8,0,0,1,0,16H24a8,8,0,0,1-8-8V56a8,8,0,0,1,16,0V85.8L60.25,60A96,96,0,0,1,224,128Z"></path>
    </svg>
  </button>
</div>

<!-- Collapsible filter panel (folds down from HUD) -->
<section class="filter-panel t-panel-slide" id="filter-bar" role="region" aria-label="Filters" data-open="false" hidden>
  <div class="filter-panel__body">
    <div class="filterbar__group">
      <label class="filterbar__label" for="filter-domain">Area</label>
      <select id="filter-domain" class="filterbar__select" aria-label="Filter by skill area">
        <option value="">All areas</option>
      </select>
    </div>
    <div class="filterbar__group">
      <label class="filterbar__label" for="filter-status">Status</label>
      <select id="filter-status" class="filterbar__select" aria-label="Filter by status">
        <option value="">All</option>
        <option value="active">Active</option>
        <option value="stale">Stale</option>
        <option value="historical">Historical</option>
      </select>
    </div>
    <div class="filterbar__group">
      <label class="filterbar__label" for="filter-freshness">Freshness</label>
      <select id="filter-freshness" class="filterbar__select" aria-label="Filter by freshness">
        <option value="">All</option>
        <option value="current">Current + warming</option>
        <option value="active">Active only</option>
        <option value="warming">Warming</option>
        <option value="stale">Stale</option>
        <option value="historical">Historical</option>
      </select>
    </div>
    <div class="filterbar__group">
      <label class="filterbar__label filterbar__label--with-value" for="filter-confidence">
        <span>Min confidence</span>
        <output id="filter-confidence-value" for="filter-confidence">0%</output>
      </label>
      <input id="filter-confidence" type="range" min="0" max="1" step="0.05" value="0" class="filterbar__range" aria-label="Minimum confidence filter">
    </div>
    <div class="filterbar__group">
      <label class="filterbar__label" for="filter-scope">Scope</label>
      <select id="filter-scope" class="filterbar__select" aria-label="Limit visible skills">
        <option value="320">Balanced 320</option>
        <option value="240">Curated 240</option>
        <option value="500">Comfort 500</option>
        <option value="750">Expanded 750</option>
        <option value="1000">Dense 1000</option>
        <option value="all">All matching</option>
      </select>
    </div>
    <div class="filterbar__group">
      <label class="filterbar__label" for="filter-evidence">Evidence type</label>
      <select id="filter-evidence" class="filterbar__select" aria-label="Filter by evidence type">
        <option value="">Any</option>
      </select>
    </div>
    <button id="filter-clear" class="filterbar__clear" type="button">Clear</button>
  </div>
</section>

<!-- View settings panel -->
<section class="settings-panel t-panel-slide" id="settings-panel" role="region" aria-label="View settings" data-open="false" hidden>
  <div class="settings-panel__body">
    <div class="settings-panel__header">
      <span class="settings-panel__title">Rendering</span>
      <button id="settings-reset" class="settings-panel__reset" type="button">Reset</button>
    </div>
    <div class="settings-group">
      <label class="settings-label" for="setting-dim">Context dim <output id="setting-dim-value">25%</output></label>
      <input id="setting-dim" class="settings-range" type="range" min="0.25" max="1" step="0.05" value="0.25">
    </div>
    <div class="settings-group">
      <label class="settings-label" for="setting-node-size">Node size <output id="setting-node-size-value">100%</output></label>
      <input id="setting-node-size" class="settings-range" type="range" min="0.75" max="1.45" step="0.05" value="1">
    </div>
    <div class="settings-group">
      <label class="settings-label" for="setting-line-strength">Line strength <output id="setting-line-strength-value">100%</output></label>
      <input id="setting-line-strength" class="settings-range" type="range" min="0.45" max="1.6" step="0.05" value="1">
    </div>
    <div class="settings-group">
      <label class="settings-label" for="setting-label-density">Label density <output id="setting-label-density-value">100%</output></label>
      <input id="setting-label-density" class="settings-range" type="range" min="0.4" max="1.6" step="0.05" value="1">
    </div>
    <div class="settings-group">
      <label class="settings-label" for="setting-separation">Separation <output id="setting-separation-value">100%</output></label>
      <input id="setting-separation" class="settings-range" type="range" min="0.75" max="1.35" step="0.05" value="1">
    </div>
    <div class="settings-group settings-group--toggles" aria-label="Layer visibility">
      <span class="settings-label">Layers</span>
      <label class="settings-toggle-row" for="setting-show-lines">
        <span>Lines</span>
        <input id="setting-show-lines" class="settings-checkbox" type="checkbox" checked>
      </label>
      <label class="settings-toggle-row" for="setting-show-categories">
        <span>Categories</span>
        <input id="setting-show-categories" class="settings-checkbox" type="checkbox" checked>
      </label>
      <label class="settings-toggle-row" for="setting-show-category-labels">
        <span>Category labels</span>
        <input id="setting-show-category-labels" class="settings-checkbox" type="checkbox" checked>
      </label>
      <label class="settings-toggle-row" for="setting-show-skill-labels">
        <span>Skill labels</span>
        <input id="setting-show-skill-labels" class="settings-checkbox" type="checkbox" checked>
      </label>
      <label class="settings-toggle-row" for="setting-show-level-badges">
        <span>Level badges</span>
        <input id="setting-show-level-badges" class="settings-checkbox" type="checkbox" checked>
      </label>
      <label class="settings-toggle-row" for="setting-show-background-dots">
        <span>Background dots</span>
        <input id="setting-show-background-dots" class="settings-checkbox" type="checkbox" checked>
      </label>
    </div>
  </div>
</section>

<!-- Main graph viewport -->
<main class="viewport" id="viewport" role="main" aria-label="Skill graph">
  <div class="viewport__canvas" id="canvas">
    <div id="graph-camera" class="graph-camera">
      <!-- Canvas raster layer: renders all node glyphs and bulk edges as pixels.
           This is the performance layer for 12k+ node graphs. -->
      <canvas id="graph-canvas" class="graph-canvas" aria-hidden="true"></canvas>

      <!-- SVG overlay layer: keeps only domain labels, the capped interactive
           node set, and selection/focus overlays in the DOM.
           Not aria-hidden: domain labels and the roving priority node set are
           keyboard focusable with aria-labels, so hiding the SVG would remove
           useful controls from the accessibility tree. -->
      <svg id="graph-svg" class="graph-svg" preserveAspectRatio="xMidYMid meet" role="group" aria-label="Skill graph">
        <defs>
          <radialGradient id="node-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="oklch(0.529 0.07 178.573 / 0.28)"/>
            <stop offset="100%" stop-color="oklch(0.529 0.07 178.573 / 0)"/>
          </radialGradient>
        </defs>
        <g id="graph-zoom">
          <g id="graph-domain-labels"></g>
          <g id="graph-edges"></g>
          <g id="graph-nodes"></g>
        </g>
      </svg>
    </div>
  </div>

  <!-- Collapsible minimap -->
  <aside class="minimap" id="minimap" role="complementary" aria-label="Minimap">
    <svg id="minimap-svg" class="minimap__svg" preserveAspectRatio="xMidYMid meet" aria-hidden="true"></svg>
  </aside>

  <!-- Collapsible legend -->
  <aside class="legend t-panel-slide" id="legend" role="complementary" aria-label="Legend" data-open="false" hidden>
    <button class="legend__close" id="legend-close" type="button" aria-label="Close legend">x</button>
    <h2 class="legend__title">Legend</h2>
    <div class="legend__section">
      <h3 class="legend__heading">Skills shown</h3>
      <p class="legend__stats" id="legend-stats" aria-live="polite">scanning</p>
    </div>
    <div class="legend__section">
      <h3 class="legend__heading">Skill areas</h3>
      <ul class="legend__list" id="legend-domains"></ul>
    </div>
    <div class="legend__section">
      <h3 class="legend__heading">Confidence rings</h3>
      <ul class="legend__list">
        <li><span class="ring ring--high"></span> High (>= 0.75)</li>
        <li><span class="ring ring--medium"></span> Medium (>= 0.45)</li>
        <li><span class="ring ring--low"></span> Low (< 0.45)</li>
      </ul>
    </div>
    <div class="legend__section">
      <h3 class="legend__heading">Freshness</h3>
      <ul class="legend__list">
        <li><span class="dot dot--active"></span> Active / current</li>
        <li><span class="dot dot--warming"></span> Warming</li>
        <li><span class="dot dot--stale"></span> Stale</li>
        <li><span class="dot dot--historical"></span> Historical (dimmed)</li>
      </ul>
    </div>
    <div class="legend__section">
      <h3 class="legend__heading">Edge styles</h3>
      <ul class="legend__list">
        <li><span class="eline eline--solid"></span> parent_of / part_of</li>
        <li><span class="eline eline--dashed"></span> related_to / specializes</li>
        <li><span class="eline eline--dotted"></span> uses_tool / produces_artifact</li>
      </ul>
    </div>
  </aside>

  <!-- Empty state -->
  <div class="empty-state" id="empty-state" hidden>
    <p>No nodes match the current filters.</p>
  </div>

  <!-- Loading state -->
  <div class="loading-state" id="loading-state">
    <div class="loading-state__loaders" aria-hidden="true">
      <span class="spiral-loader" style="--spiral-size: 24px">
        <svg class="spiral-loader__phase spiral-loader__phase--fast" viewBox="0 0 16 16" focusable="false">
          <g class="spiral-loader__motion">
            <path class="spiral-loader__path" pathLength="100" d="M0.500 12.500 C4.952 12.500 7.236 8.784 7.525 5.488 C7.755 2.861 6.718 0.500 4.500 0.500 C2.282 0.500 1.245 2.861 1.475 5.488 C1.764 8.784 4.048 12.500 8.500 12.500 C12.952 12.500 15.236 8.784 15.525 5.488 C15.755 2.861 14.718 0.500 12.500 0.500 C10.282 0.500 9.245 2.861 9.475 5.488 C9.764 8.784 12.048 12.500 16.500 12.500 C20.952 12.500 23.236 8.784 23.525 5.488 C23.755 2.861 22.718 0.500 20.500 0.500 C18.282 0.500 17.248 2.861 17.480 5.488 C17.772 8.784 20.057 12.500 24.500 12.500"></path>
          </g>
        </svg>
        <svg class="spiral-loader__phase spiral-loader__phase--slow" viewBox="0 0 16 16" focusable="false">
          <g class="spiral-loader__motion">
            <path class="spiral-loader__path" pathLength="100" d="M0.500 12.500 C4.952 12.500 7.236 8.784 7.525 5.488 C7.755 2.861 6.718 0.500 4.500 0.500 C2.282 0.500 1.245 2.861 1.475 5.488 C1.764 8.784 4.048 12.500 8.500 12.500 C12.952 12.500 15.236 8.784 15.525 5.488 C15.755 2.861 14.718 0.500 12.500 0.500 C10.282 0.500 9.245 2.861 9.475 5.488 C9.764 8.784 12.048 12.500 16.500 12.500 C20.952 12.500 23.236 8.784 23.525 5.488 C23.755 2.861 22.718 0.500 20.500 0.500 C18.282 0.500 17.248 2.861 17.480 5.488 C17.772 8.784 20.057 12.500 24.500 12.500"></path>
          </g>
        </svg>
      </span>
    </div>
    <p class="t-shimmer loading-state__text" id="loading-message" data-text="Loading skill map...">Loading skill map...</p>
  </div>
</main>

<!-- Desktop selection dock: stable node inspector, not a full-height drawer -->
<aside class="selection-dock t-panel-slide" id="drawer" role="complementary" aria-label="Selected node details" aria-hidden="true" data-open="false" hidden>
  <div class="selection-dock__header">
    <h2 class="selection-dock__title" id="drawer-title">-</h2>
    <button class="selection-dock__close" id="drawer-close" type="button" aria-label="Close details (Esc)">x</button>
  </div>
  <div class="selection-dock__body" id="drawer-body"></div>
</aside>

<!-- Mobile bottom sheet -->
<aside class="sheet t-panel-slide" id="sheet" role="complementary" aria-label="Node details" aria-hidden="true" data-open="false" hidden>
  <div class="sheet__handle" id="sheet-handle"></div>
  <div class="sheet__header">
    <h2 class="sheet__title" id="sheet-title">-</h2>
    <button class="sheet__close" id="sheet-close" type="button" aria-label="Close sheet (Esc)">x</button>
  </div>
  <div class="sheet__body" id="sheet-body"></div>
</aside>

<script src="assets/sfx.js?v=20260629-anchor-lock-1" defer></script>
<script src="assets/viewer.js?v=20260629-anchor-lock-1" defer></script>
</body>
</html>
"""

VIEWER_CSS = """\
:root {
  color-scheme: dark;
  /* Deep black/graphite game-map palette with Traccia logo green, copper,
     moss, and bone accents. No blue as a default accent (decision 63). */
  --bg: oklch(0.116 0.003 285.885);
  --bg-elevated: oklch(0.155 0.002 286.152);
  --bg-panel: oklch(0.174 0.004 285.967);
  --bg-panel-strong: oklch(0.201 0.004 286.04);
  --border: oklch(0.241 0.008 285.819);
  --border-strong: oklch(0.303 0.009 285.856);
  --text: oklch(0.934 0.012 91.522);
  --text-muted: oklch(0.671 0.017 86.449);
  --text-dim: oklch(0.455 0.011 78.217);
  --accent: oklch(0.529 0.07 178.573);
  --accent-soft: oklch(0.529 0.07 178.573 / 0.16);
  --accent-strong: oklch(0.701 0.099 177.349);
  --accent-glow: oklch(0.529 0.07 178.573 / 0.36);
  --node-fill: oklch(0.192 0.004 286.018);
  --node-stroke: oklch(0.348 0.011 91.645);
  --edge: oklch(0.389 0.021 84.547);
  --edge-highlight: oklch(0.701 0.099 177.349);
  --shadow: 0 12px 40px oklch(0 0 0 / 0.6);
  --shadow-border: 0 0 0 1px oklch(1 0 0 / 0.06);
  --shadow-border-hover: 0 0 0 1px oklch(0.529 0.07 178.573 / 0.42);

  /* Graphite base with restrained Traccia green, copper, moss, and bone accents. */
  --domain-1: oklch(0.529 0.07 178.573);
  --domain-2: oklch(0.62 0.045 160.104);
  --domain-3: oklch(0.638 0.1 40.978);
  --domain-4: oklch(0.848 0.025 91.642);
  --domain-5: oklch(0.634 0.083 173.364);
  --domain-6: oklch(0.621 0.065 138.365);
  --domain-7: oklch(0.686 0.085 51.211);
  --domain-8: oklch(0.675 0.034 89.186);

  --radius: 10px;
  --radius-sm: 7px;
  --hud-blur: 16px;
  --hud-bg: oklch(0.155 0.002 286.152 / 0.82);
  --motion-ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --motion-ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
  --motion-ease-panel: cubic-bezier(0.22, 1, 0.36, 1);
  --motion-ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
  --motion-press-dur: 120ms;
  --motion-state-dur: 160ms;
  --motion-focus-dur: 180ms;
  --motion-reveal-dur: 220ms;
  --panel-open-dur: 250ms;
  --panel-close-dur: 160ms;
  --panel-translate-y: 10px;
  --panel-blur: 2px;
  --panel-ease: var(--motion-ease-panel);
  --icon-swap-dur: 180ms;
  --icon-swap-blur: 2px;
  --icon-swap-start-scale: 0.72;
  --icon-swap-ease: ease-in-out;
  --shimmer-dur: 1800ms;
  --shimmer-base: var(--text-dim);
  --shimmer-highlight: var(--text);
  --shimmer-band: 400%;
  --shimmer-ease: linear;
  --font-ui: "Traccia UI", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
  --font-label: "Traccia Label", "Traccia UI", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-display: "Traccia Display", "Traccia UI", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "Traccia Mono", "SFMono-Regular", Consolas, monospace;
}

@media (prefers-color-scheme: light) {
  :root {
    color-scheme: dark;
  }
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
  font-family: var(--font-ui);
  font-size: 14px;
  color: var(--text);
  background: var(--bg);
  font-feature-settings: "kern" 1, "liga" 1, "calt" 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  /* Viewport is the single full-bleed surface. HUD islands float above it. */
  position: relative;
  background: var(--bg);
}

/* ===================================================================
   Floating game-map HUD islands (not full-width bars)
   =================================================================== */
.hud-island {
  position: fixed;
  z-index: 25;
  display: flex;
  align-items: center;
  background: var(--hud-bg);
  backdrop-filter: blur(var(--hud-blur));
  -webkit-backdrop-filter: blur(var(--hud-blur));
  box-shadow: var(--shadow-border), var(--shadow);
  border-radius: var(--radius);
  transition-property: box-shadow, transform, opacity;
  transition-duration: 160ms;
  transition-timing-function: var(--motion-ease-out);
}

/* Brand / status island (top-left) */
.t-shimmer {
  position: relative;
  display: inline-block;
  color: var(--shimmer-base);
}
.t-shimmer::before {
  content: attr(data-text);
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: linear-gradient(
    90deg,
    transparent 0%,
    transparent 40%,
    var(--shimmer-highlight) 50%,
    transparent 60%,
    transparent 100%
  );
  background-size: var(--shimmer-band) 100%;
  background-repeat: no-repeat;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  animation: t-shimmer var(--shimmer-dur) var(--shimmer-ease) infinite;
}
@keyframes t-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: 0% 0; }
}

/* Command / search panel (opened from the bottom action dock) */
.hud-search {
  bottom: 68px;
  left: 50%;
  z-index: 34;
  transform: translate(-50%, 8px) scale(0.97);
  padding: 0;
  width: min(440px, calc(100vw - 320px));
  min-width: 200px;
  opacity: 0;
  filter: blur(var(--panel-blur));
  pointer-events: none;
  transform-origin: bottom center;
}
.hud-search[data-open="true"] {
  transform: translate(-50%, 0) scale(1);
  opacity: 1;
  filter: blur(0);
  pointer-events: auto;
}
.search-field {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 0 12px;
  height: 40px;
  border-radius: var(--radius);
  transition:
    box-shadow var(--motion-focus-dur) var(--motion-ease-out),
    background-color var(--motion-focus-dur) var(--motion-ease-out);
}
.search-field:focus-within {
  background: oklch(1 0 0 / 0.025);
  box-shadow: var(--shadow-border-hover);
}
.icon {
  width: 17px;
  height: 17px;
  display: block;
  fill: currentColor;
  stroke: none;
}
.search-field__icon { color: var(--text-dim); flex-shrink: 0; }
.search-field__input {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  outline: none;
}
.search-field__input::placeholder { color: var(--text-dim); }
.search-field__clear {
  width: 24px; height: 24px;
  border: none; background: transparent; color: var(--text-dim); cursor: pointer;
  font-size: 13px; padding: 0; line-height: 1; flex-shrink: 0;
  border-radius: var(--radius-sm);
  opacity: 0;
  transform: scale(0.88);
  transition:
    color var(--motion-state-dur) var(--motion-ease-out),
    background-color var(--motion-state-dur) var(--motion-ease-out),
    opacity var(--motion-state-dur) var(--motion-ease-out),
    transform var(--motion-state-dur) var(--motion-ease-out);
}
.search-field__clear[data-visible="true"] {
  opacity: 1;
  transform: scale(1);
}

/* Action dock (bottom-center) */
.hud-actions {
  bottom: 14px;
  left: 50%;
  right: auto;
  transform: translateX(-50%);
  transition:
    opacity 420ms var(--motion-ease-out),
    transform 420ms var(--motion-ease-out),
    filter 420ms var(--motion-ease-out);
  will-change: opacity, transform, filter;
  --toolbar-indicator-x: 4px;
  --toolbar-indicator-y: 4px;
  --toolbar-indicator-opacity: 0;
  gap: 2px;
  padding: 4px;
  overflow: hidden;
  isolation: isolate;
}
.hud-toolbar__indicator {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 0;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: oklch(1 0 0 / 0.045);
  box-shadow: inset 0 0 0 1px oklch(1 0 0 / 0.045);
  opacity: var(--toolbar-indicator-opacity);
  transform: translate3d(var(--toolbar-indicator-x), var(--toolbar-indicator-y), 0);
  transition:
    opacity 150ms var(--motion-ease-out),
    transform 250ms var(--motion-ease-out);
  will-change: opacity, transform;
  pointer-events: none;
}
.hud-btn {
  display: inline-flex; align-items: center; justify-content: center;
  position: relative;
  z-index: 1;
  width: 36px; height: 36px;
  padding: 0;
  border: none; background: transparent;
  color: var(--text-muted); border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    color var(--motion-state-dur) var(--motion-ease-out),
    box-shadow var(--motion-state-dur) var(--motion-ease-out),
    transform var(--motion-press-dur) var(--motion-ease-out);
}
.hud-btn:active { transform: scale(0.96); }
.hud-btn:not(.hud-btn--sound)[aria-pressed="true"] { color: var(--accent-strong); background: transparent; }
.hud-btn--sound[aria-pressed="false"] { color: var(--accent-strong); background: transparent; }
.hud-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.hud-btn .icon { width: 18px; height: 18px; }

.t-icon-swap {
  position: relative;
  display: inline-grid;
}
.t-icon-swap .t-icon {
  grid-area: 1 / 1;
  transition:
    opacity var(--icon-swap-dur) var(--icon-swap-ease),
    filter var(--icon-swap-dur) var(--icon-swap-ease),
    transform var(--icon-swap-dur) var(--icon-swap-ease);
  will-change: opacity, filter, transform;
}
.t-icon-swap[data-state="off"] .t-icon[data-icon="off"],
.t-icon-swap[data-state="on"] .t-icon[data-icon="on"] {
  opacity: 1;
  filter: blur(0);
  transform: scale(1);
}
.t-icon-swap[data-state="off"] .t-icon[data-icon="on"],
.t-icon-swap[data-state="on"] .t-icon[data-icon="off"] {
  opacity: 0;
  filter: blur(var(--icon-swap-blur));
  transform: scale(var(--icon-swap-start-scale));
}

/* ===================================================================
   Collapsible filter panel (folds out, not a full-width bar)
   =================================================================== */
.filter-panel,
.settings-panel {
  position: fixed;
  top: auto;
  bottom: 68px;
  left: 50%;
  right: auto;
  z-index: 34;
  background: var(--hud-bg);
  backdrop-filter: blur(var(--hud-blur));
  -webkit-backdrop-filter: blur(var(--hud-blur));
  box-shadow: var(--shadow-border), var(--shadow);
  border-radius: var(--radius);
  padding: 4px;
  transform-origin: bottom center;
  transform: translate(-50%, var(--panel-translate-y)) scale(0.97);
  opacity: 0;
  filter: blur(var(--panel-blur));
  pointer-events: none;
  transition:
    transform var(--panel-close-dur) var(--panel-ease),
    opacity var(--panel-close-dur) var(--panel-ease),
    filter var(--panel-close-dur) var(--panel-ease);
  will-change: transform, opacity, filter;
}
.filter-panel[data-open="true"],
.settings-panel[data-open="true"] {
  transform: translate(-50%, 0) scale(1);
  opacity: 1;
  filter: blur(0);
  pointer-events: auto;
  transition:
    transform var(--panel-open-dur) var(--panel-ease),
    opacity var(--panel-open-dur) var(--panel-ease),
    filter var(--panel-open-dur) var(--panel-ease);
}
.filter-panel__body {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  flex-wrap: wrap;
  max-width: 520px;
}
.filterbar__group { display: flex; align-items: center; gap: 5px; }
.filterbar__label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.filterbar__label--with-value {
  min-width: 104px;
  justify-content: space-between;
}
.filterbar__label output {
  color: var(--text);
  min-width: 4ch;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
  display: inline-flex;
  justify-content: flex-end;
  align-items: baseline;
}
.filterbar__select {
  height: 30px; font-size: 12px; color: var(--text);
  background: oklch(0.192 0.004 286.018 / 0.9); border: none;
  box-shadow: var(--shadow-border);
  border-radius: var(--radius-sm); padding: 0 8px;
  transition:
    background-color var(--motion-state-dur) var(--motion-ease-out),
    box-shadow var(--motion-state-dur) var(--motion-ease-out),
    color var(--motion-state-dur) var(--motion-ease-out);
}
.filterbar__select:focus {
  outline: none;
  background: oklch(0.216 0.005 286.06 / 0.95);
  box-shadow: var(--shadow-border-hover);
}
.filterbar__range { width: 112px; }
.filterbar__clear {
  height: 30px; padding: 0 12px;
  font-size: 12px; color: var(--text-muted);
  background: oklch(0.192 0.004 286.018 / 0.5); border: none;
  box-shadow: var(--shadow-border);
  border-radius: var(--radius-sm); cursor: pointer;
  transition-property: color, box-shadow, transform;
  transition-duration: var(--motion-press-dur);
  transition-timing-function: var(--motion-ease-out);
}
.filterbar__clear:active { transform: scale(0.94); }

.settings-panel {
  width: min(320px, calc(100vw - 28px));
}
.settings-panel__body {
  display: grid;
  gap: 12px;
  padding: 12px;
}
.settings-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 2px;
}
.settings-panel__title {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.settings-panel__reset {
  height: 26px;
  padding: 0 10px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  background: oklch(0.192 0.004 286.018 / 0.5);
  border: none;
  box-shadow: var(--shadow-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.settings-group {
  display: grid;
  gap: 6px;
}
.settings-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.settings-label output {
  color: var(--text);
  min-width: 5ch;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
  display: inline-flex;
  justify-content: flex-end;
  align-items: baseline;
}
.numeric-text-readout {
  position: relative;
  display: inline-flex;
  white-space: nowrap !important;
  isolation: isolate;
}
.settings-range,
.filterbar__range {
  --range-progress: 50%;
  --range-track: oklch(0.934 0.012 91.522 / 0.105);
  --range-track-border: oklch(0.934 0.012 91.522 / 0.08);
  --range-fill: oklch(0.62 0.045 160.104 / 0.82);
  --range-thumb: oklch(0.934 0.012 91.522 / 0.9);
  --range-thumb-border: oklch(0.529 0.07 178.573 / 0.42);
  appearance: none;
  -webkit-appearance: none;
  width: 100%;
  height: 32px;
  margin: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
}
.settings-range::-webkit-slider-runnable-track,
.filterbar__range::-webkit-slider-runnable-track {
  height: 8px;
  border-radius: 999px;
  border: 1px solid var(--range-track-border);
  background:
    linear-gradient(
      90deg,
      var(--range-fill) 0%,
      var(--range-fill) var(--range-progress),
      var(--range-track) var(--range-progress),
      var(--range-track) 100%
    );
  box-shadow:
    inset 0 1px 0 oklch(1 0 0 / 0.055),
    inset 0 -1px 0 oklch(0 0 0 / 0.22);
}
.settings-range::-webkit-slider-thumb,
.filterbar__range::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  margin-top: -5px;
  border-radius: 999px;
  border: 1px solid var(--range-thumb-border);
  background: var(--range-thumb);
  box-shadow:
    0 4px 12px oklch(0 0 0 / 0.36),
    0 0 0 4px oklch(0.529 0.07 178.573 / 0.08);
  transition:
    transform 120ms var(--motion-ease-out),
    box-shadow 120ms var(--motion-ease-out),
    border-color 120ms var(--motion-ease-out);
}
.settings-range:hover::-webkit-slider-thumb,
.filterbar__range:hover::-webkit-slider-thumb,
.settings-range:focus-visible::-webkit-slider-thumb,
.filterbar__range:focus-visible::-webkit-slider-thumb,
.settings-range.is-adjusting::-webkit-slider-thumb,
.filterbar__range.is-adjusting::-webkit-slider-thumb {
  border-color: oklch(0.701 0.099 177.349 / 0.72);
  box-shadow:
    0 5px 16px oklch(0 0 0 / 0.44),
    0 0 0 5px oklch(0.529 0.07 178.573 / 0.14);
}
.settings-range:active::-webkit-slider-thumb,
.filterbar__range:active::-webkit-slider-thumb,
.settings-range.is-adjusting::-webkit-slider-thumb,
.filterbar__range.is-adjusting::-webkit-slider-thumb {
  transform: scale(1.08);
}
.settings-range::-moz-range-track,
.filterbar__range::-moz-range-track {
  height: 8px;
  border-radius: 999px;
  border: 1px solid var(--range-track-border);
  background: var(--range-track);
  box-shadow:
    inset 0 1px 0 oklch(1 0 0 / 0.055),
    inset 0 -1px 0 oklch(0 0 0 / 0.22);
}
.settings-range::-moz-range-progress,
.filterbar__range::-moz-range-progress {
  height: 8px;
  border-radius: 999px;
  background: var(--range-fill);
}
.settings-range::-moz-range-thumb,
.filterbar__range::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 1px solid var(--range-thumb-border);
  background: var(--range-thumb);
  box-shadow:
    0 4px 12px oklch(0 0 0 / 0.36),
    0 0 0 4px oklch(0.529 0.07 178.573 / 0.08);
  transition:
    transform 120ms var(--motion-ease-out),
    box-shadow 120ms var(--motion-ease-out),
    border-color 120ms var(--motion-ease-out);
}
.settings-range:hover::-moz-range-thumb,
.filterbar__range:hover::-moz-range-thumb,
.settings-range:focus-visible::-moz-range-thumb,
.filterbar__range:focus-visible::-moz-range-thumb,
.settings-range.is-adjusting::-moz-range-thumb,
.filterbar__range.is-adjusting::-moz-range-thumb {
  border-color: oklch(0.701 0.099 177.349 / 0.72);
  box-shadow:
    0 5px 16px oklch(0 0 0 / 0.44),
    0 0 0 5px oklch(0.529 0.07 178.573 / 0.14);
}
.settings-range:active::-moz-range-thumb,
.filterbar__range:active::-moz-range-thumb,
.settings-range.is-adjusting::-moz-range-thumb,
.filterbar__range.is-adjusting::-moz-range-thumb {
  transform: scale(1.08);
}
.settings-range:focus-visible,
.filterbar__range:focus-visible {
  outline: none;
}
.settings-range:focus-visible::-webkit-slider-runnable-track,
.filterbar__range:focus-visible::-webkit-slider-runnable-track {
  border-color: oklch(0.701 0.099 177.349 / 0.7);
  box-shadow:
    inset 0 1px 0 oklch(1 0 0 / 0.055),
    inset 0 -1px 0 oklch(0 0 0 / 0.22),
    0 0 0 3px oklch(0.529 0.07 178.573 / 0.14);
}
.settings-range:focus-visible::-moz-range-track,
.filterbar__range:focus-visible::-moz-range-track {
  border-color: oklch(0.701 0.099 177.349 / 0.7);
  box-shadow:
    inset 0 1px 0 oklch(1 0 0 / 0.055),
    inset 0 -1px 0 oklch(0 0 0 / 0.22),
    0 0 0 3px oklch(0.529 0.07 178.573 / 0.14);
}
.settings-group--toggles {
  gap: 8px;
}
.settings-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 28px;
  gap: 14px;
  padding: 0 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  cursor: pointer;
}
.settings-checkbox {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: var(--accent);
}

.filter-panel .filterbar__group,
.filter-panel .filterbar__clear,
.settings-panel .settings-panel__header,
.settings-panel .settings-group {
  opacity: 0;
  transform: translateY(4px);
  transition:
    opacity var(--motion-reveal-dur) var(--motion-ease-out),
    transform var(--motion-reveal-dur) var(--motion-ease-out);
}
.filter-panel[data-open="true"] .filterbar__group,
.filter-panel[data-open="true"] .filterbar__clear,
.settings-panel[data-open="true"] .settings-panel__header,
.settings-panel[data-open="true"] .settings-group {
  opacity: 1;
  transform: translateY(0);
}
.filter-panel[data-open="true"] .filterbar__group:nth-child(1) { transition-delay: 20ms; }
.filter-panel[data-open="true"] .filterbar__group:nth-child(2) { transition-delay: 45ms; }
.filter-panel[data-open="true"] .filterbar__group:nth-child(3) { transition-delay: 70ms; }
.filter-panel[data-open="true"] .filterbar__group:nth-child(4) { transition-delay: 95ms; }
.filter-panel[data-open="true"] .filterbar__group:nth-child(5) { transition-delay: 120ms; }
.filter-panel[data-open="true"] .filterbar__group:nth-child(6) { transition-delay: 145ms; }
.filter-panel[data-open="true"] .filterbar__clear { transition-delay: 170ms; }
.settings-panel[data-open="true"] .settings-panel__header { transition-delay: 20ms; }
.settings-panel[data-open="true"] .settings-group:nth-child(2) { transition-delay: 45ms; }
.settings-panel[data-open="true"] .settings-group:nth-child(3) { transition-delay: 70ms; }
.settings-panel[data-open="true"] .settings-group:nth-child(4) { transition-delay: 95ms; }
.settings-panel[data-open="true"] .settings-group:nth-child(5) { transition-delay: 120ms; }
.settings-panel[data-open="true"] .settings-group:nth-child(6) { transition-delay: 145ms; }
.settings-panel[data-open="true"] .settings-group:nth-child(7) { transition-delay: 170ms; }
.settings-panel[data-open="true"] .settings-group:nth-child(8) { transition-delay: 195ms; }

/* ===================================================================
   Viewport (full-bleed graph canvas + SVG overlay)
   =================================================================== */
.viewport {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 30%, oklch(0.529 0.07 178.573 / 0.045), transparent 60%),
    radial-gradient(ellipse at 80% 80%, oklch(0.62 0.045 160.104 / 0.026), transparent 50%),
    var(--bg);
}
.viewport::before {
  content: "";
  position: absolute;
  inset: -28px;
  pointer-events: none;
  background-image: radial-gradient(circle, oklch(0.934 0.012 91.522 / 0.16) 0 1px, transparent 1.25px);
  background-size: 28px 28px;
  background-position: 14px 14px;
  transform: translate3d(var(--dot-offset-x, 0px), var(--dot-offset-y, 0px), 0);
  will-change: transform, opacity;
  opacity: 0.34;
  transition: opacity var(--motion-state-dur) var(--motion-ease-out);
}
.viewport[data-dots="false"]::before {
  opacity: 0;
}
.viewport__canvas {
  position: absolute; inset: 0;
  cursor: grab;
  touch-action: none;
  z-index: 1;
  opacity: 1;
  filter: none;
  transition:
    opacity 460ms var(--motion-ease-out),
    filter 460ms var(--motion-ease-out);
  will-change: opacity, filter;
}
.viewport__canvas.panning { cursor: grabbing; }
body.viewer-loading .viewport__canvas {
  opacity: 0;
  filter: blur(8px);
}
body.viewer-loading .hud-actions {
  opacity: 0;
  transform: translateX(-50%) translateY(14px) scale(0.97);
  filter: blur(6px);
}

/* Canvas raster layer: the performance workhorse for 12k+ nodes.
   Sits behind the SVG overlay. */
.graph-camera {
  position: absolute;
  inset: 0;
  transform-origin: 0 0;
  will-change: transform;
}

.graph-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
  transform-origin: 0 0;
  will-change: transform;
}

/* SVG overlay layer: domain labels, interactive node set, and selection/focus
   overlays. pointer-events stays auto so the overlay
   can receive clicks; the canvas below is purely visual. */
.graph-svg {
  position: absolute;
  inset: 0;
  width: 100%; height: 100%; display: block;
  pointer-events: none;
  transform-origin: 0 0;
  will-change: transform;
}
.graph-svg .graph-node,
.graph-svg .domain-label {
  pointer-events: auto;
}
.graph-svg.camera-moving #graph-zoom {
  pointer-events: none;
}

/* ===================================================================
   Nodes (SVG overlay - only the capped interactive set is here)
   =================================================================== */
.graph-node {
  cursor: pointer;
  transform-box: fill-box;
  transform-origin: center;
}
.graph-node,
.graph-node:focus,
.graph-node:focus-visible {
  outline: none;
}
.graph-node__circle {
  fill: transparent;
  stroke: transparent !important;
  stroke-width: 0;
  opacity: 0;
  pointer-events: none;
}
.graph-node__hit {
  fill: transparent;
  stroke: transparent;
  pointer-events: all;
}
.graph-node__focus-ring {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2.4;
  opacity: 0;
  pointer-events: none;
  transition:
    opacity 160ms var(--motion-ease-out),
    stroke-width 160ms var(--motion-ease-out);
}
.graph-node.focused .graph-node__focus-ring {
  opacity: 0.28;
  stroke-width: 1.4;
}
.graph-node:focus-visible .graph-node__focus-ring,
.graph-node.selected .graph-node__focus-ring {
  opacity: 0.9;
  stroke-width: 2.4;
}
.graph-node__glow {
  fill: url(#node-glow);
  opacity: 0;
  transition-property: opacity;
  transition-duration: 140ms;
  transition-timing-function: var(--motion-ease-out);
}
.graph-node.selected .graph-node__glow { opacity: 0.82; }
.graph-node.focused .graph-node__glow { opacity: 0.36; }

.graph-node.dimmed { opacity: 0.46; }
.graph-node.quieted { pointer-events: none; }
.graph-node.matched .graph-node__focus-ring {
  opacity: 0.9;
  stroke: var(--accent-strong) !important;
  stroke-width: 2.4;
}
.graph-node-hover-ring {
  fill: none;
  stroke: var(--accent);
  stroke-width: 1.8;
  opacity: 0;
  pointer-events: none;
  transition:
    opacity 90ms var(--motion-ease-out),
    stroke-width 90ms var(--motion-ease-out);
}
.graph-node-hover-ring[data-visible="true"] {
  opacity: 0.52;
}

.graph-node__keystone-ring {
  fill: none;
  stroke: var(--accent);
  stroke-width: 1.2;
  stroke-dasharray: 2 5;
  opacity: 0;
  pointer-events: none;
}
.graph-node__inner {
  fill: transparent;
  stroke: transparent;
  stroke-width: 0;
  opacity: 0;
  pointer-events: none;
}

.graph-node__level {
  font-family: var(--font-mono);
  fill: var(--text);
  font-size: 11px;
  font-weight: 650;
  text-anchor: middle;
  dominant-baseline: central;
  pointer-events: none;
  user-select: none;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
  opacity: 0;
}

/* Historical peak ghost ring */
.graph-node__ghost {
  fill: none;
  stroke: var(--text-dim);
  stroke-width: 1;
  stroke-dasharray: 3 3;
  opacity: 0;
}

/* Domain region labels (decision 53, 34) - primary area focus controls */
.domain-label {
  font-family: var(--font-display);
  fill: oklch(0.934 0.012 91.522 / 0.66);
  font-size: 18px;
  font-weight: 650;
  letter-spacing: 0;
  text-anchor: middle;
  cursor: pointer;
  user-select: none;
  opacity: 0.78;
  paint-order: stroke;
  stroke: oklch(0.116 0.003 285.885 / 0.75);
  stroke-width: 8px;
  stroke-linejoin: round;
  transition-property: opacity, fill;
  transition-duration: var(--motion-state-dur);
  transition-timing-function: var(--motion-ease-out);
  transform-box: fill-box;
  transform-origin: center;
}
.domain-label:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
  opacity: 0.8;
}
.domain-label.collapsed {
  opacity: 0.65;
  fill: var(--accent);
}
.domain-label.selected {
  opacity: 0.96;
  fill: var(--text);
}

/* ===================================================================
   Edges (SVG overlay - only selected/focus-path edges are here as DOM)
   =================================================================== */
.graph-edge {
  fill: none;
  stroke: var(--edge);
  stroke-width: 1;
  stroke-linecap: round;
  transition-property: stroke, stroke-width, opacity;
  transition-duration: 150ms;
  transition-timing-function: var(--motion-ease-out);
  opacity: 0.22;
}
.graph-edge.highlighted {
  stroke: var(--edge-highlight);
  stroke-width: 2.2;
  opacity: 0.96;
}
.graph-edge.dimmed { opacity: 0.055; }

/* ===================================================================
   Minimap
   =================================================================== */
.minimap {
  position: fixed;
  bottom: 14px;
  right: 14px;
  width: 180px;
  height: 120px;
  background: var(--hud-bg);
  box-shadow: var(--shadow-border), var(--shadow);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: var(--radius);
  overflow: hidden;
  z-index: 22;
  transition-property: transform, opacity;
  transition-duration: var(--motion-state-dur);
  transition-timing-function: var(--motion-ease-panel);
  transform-origin: bottom right;
}
.minimap.collapsed {
  opacity: 0.72;
  transform: translateY(calc(100% - 28px)) scale(0.98);
}
.minimap__svg { width: 100%; height: 100%; display: block; }
.minimap__viewport {
  fill: var(--accent-soft);
  stroke: var(--accent);
  stroke-width: 1;
}

/* ===================================================================
   Legend
   =================================================================== */
.legend {
  position: fixed;
  top: auto;
  bottom: 68px;
  right: auto;
  left: 50%;
  width: 240px;
  max-height: calc(100vh - 92px);
  overflow-y: auto;
  background: var(--hud-bg);
  box-shadow: var(--shadow-border), var(--shadow);
  backdrop-filter: blur(var(--hud-blur));
  -webkit-backdrop-filter: blur(var(--hud-blur));
  border-radius: var(--radius);
  padding: 14px;
  z-index: 34;
  transform-origin: bottom center;
  transform: translate(-50%, var(--panel-translate-y)) scale(0.97);
  opacity: 0;
  filter: blur(var(--panel-blur));
  pointer-events: none;
  transition:
    transform var(--panel-close-dur) var(--panel-ease),
    opacity var(--panel-close-dur) var(--panel-ease),
    filter var(--panel-close-dur) var(--panel-ease);
  will-change: transform, opacity, filter;
}
.legend[data-open="true"] {
  transform: translate(-50%, 0) scale(1);
  opacity: 1;
  filter: blur(0);
  pointer-events: auto;
  transition:
    transform var(--panel-open-dur) var(--panel-ease),
    opacity var(--panel-open-dur) var(--panel-ease),
    filter var(--panel-open-dur) var(--panel-ease);
}
.legend__close {
  position: absolute; top: 8px; right: 8px;
  width: 28px; height: 28px;
  border: none; background: transparent; color: var(--text-dim);
  font-size: 16px; cursor: pointer; line-height: 1;
  border-radius: var(--radius-sm);
  transition:
    color var(--motion-press-dur) var(--motion-ease-out),
    background-color var(--motion-press-dur) var(--motion-ease-out),
    transform var(--motion-press-dur) var(--motion-ease-out);
}
.legend__close:active { transform: scale(0.94); }
.legend__title { margin: 0 0 10px; font-size: 13px; font-weight: 600; }
.legend__section {
  margin-bottom: 12px;
  opacity: 0;
  transform: translateY(5px);
  transition:
    opacity var(--motion-reveal-dur) var(--motion-ease-out),
    transform var(--motion-reveal-dur) var(--motion-ease-out);
}
.legend[data-open="true"] .legend__section {
  opacity: 1;
  transform: translateY(0);
}
.legend[data-open="true"] .legend__section:nth-of-type(1) { transition-delay: 30ms; }
.legend[data-open="true"] .legend__section:nth-of-type(2) { transition-delay: 55ms; }
.legend[data-open="true"] .legend__section:nth-of-type(3) { transition-delay: 80ms; }
.legend[data-open="true"] .legend__section:nth-of-type(4) { transition-delay: 105ms; }
.legend[data-open="true"] .legend__section:nth-of-type(5) { transition-delay: 130ms; }
.legend__stats {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
}
.legend__heading { margin: 0 0 4px; font-size: 11px; text-transform: uppercase; color: var(--text-dim); letter-spacing: 0.4px; }
.legend__list { list-style: none; margin: 0; padding: 0; font-size: 12px; line-height: 1.8; }
.legend__list li { display: flex; align-items: center; gap: 8px; }

.ring { display: inline-block; width: 14px; height: 14px; border-radius: 50%; border: 2px solid; background: transparent; flex-shrink: 0; }
.ring--high { border-color: var(--domain-2); }
.ring--medium { border-color: var(--accent); }
.ring--low { border-color: var(--text-dim); }

.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot--active { background: var(--domain-2); }
.dot--warming { background: var(--accent); }
.dot--stale { background: var(--domain-3); }
.dot--historical { background: var(--text-dim); }

.eline { display: inline-block; width: 24px; height: 0; border-top-width: 2px; border-top-style: solid; flex-shrink: 0; }
.eline--solid { border-top-style: solid; border-color: var(--text-muted); }
.eline--dashed { border-top-style: dashed; border-color: var(--text-muted); }
.eline--dotted { border-top-style: dotted; border-color: var(--text-muted); }

/* ===================================================================
   Selection dock (desktop)
   =================================================================== */
.selection-dock {
  position: fixed;
  top: 64px;
  right: 14px;
  width: min(360px, calc(100vw - 28px));
  max-height: calc(100vh - 190px);
  background: oklch(0.146 0.004 285.857 / 0.94);
  box-shadow: var(--shadow-border), var(--shadow);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-radius: var(--radius);
  z-index: 30;
  display: flex;
  flex-direction: column;
  transform-origin: top right;
  transform: translateY(8px) scale(0.97);
  opacity: 0;
  filter: blur(var(--panel-blur));
  pointer-events: none;
  transition:
    transform var(--panel-close-dur) var(--motion-ease-drawer),
    opacity var(--panel-close-dur) var(--motion-ease-drawer),
    filter var(--panel-close-dur) var(--motion-ease-drawer);
  will-change: transform, opacity, filter;
}
.selection-dock.open,
.selection-dock[data-open="true"] {
  transform: translateY(0) scale(1);
  opacity: 1;
  filter: blur(0);
  pointer-events: auto;
  transition:
    transform var(--panel-open-dur) var(--motion-ease-drawer),
    opacity var(--panel-open-dur) var(--motion-ease-drawer),
    filter var(--panel-open-dur) var(--motion-ease-drawer);
}
.selection-dock__header {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px;
  padding: 14px 14px 10px 16px;
  box-shadow: 0 1px 0 oklch(1 0 0 / 0.06);
}
.selection-dock__title {
  margin: 0;
  min-width: 0;
  font-family: var(--font-display);
  font-size: 16px;
  line-height: 1.18;
  font-weight: 650;
  text-wrap: balance;
}
.selection-dock__close {
  width: 40px; height: 40px;
  border: none; background: transparent; color: var(--text-dim);
  font-size: 16px; cursor: pointer; line-height: 1; padding: 0;
  border-radius: var(--radius-sm);
  transition:
    color var(--motion-press-dur) var(--motion-ease-out),
    background-color var(--motion-press-dur) var(--motion-ease-out),
    transform var(--motion-press-dur) var(--motion-ease-out);
}
.selection-dock__close:active { transform: scale(0.94); }
.selection-dock__body {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 16px;
}

/* ===================================================================
   Bottom sheet (mobile)
   =================================================================== */
.sheet {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  max-height: 75vh;
  background: oklch(0.146 0.004 285.857 / 0.96);
  box-shadow: 0 -1px 0 oklch(1 0 0 / 0.06), 0 -18px 50px oklch(0 0 0 / 0.4);
  border-radius: 16px 16px 0 0;
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  z-index: 30;
  display: flex;
  flex-direction: column;
  transform: translateY(100%);
  opacity: 0;
  filter: blur(var(--panel-blur));
  transition:
    transform var(--panel-close-dur) var(--motion-ease-drawer),
    opacity var(--panel-close-dur) var(--motion-ease-drawer),
    filter var(--panel-close-dur) var(--motion-ease-drawer);
  will-change: transform, opacity, filter;
}
.sheet.open,
.sheet[data-open="true"] {
  transform: translateY(0);
  opacity: 1;
  filter: blur(0);
  transition:
    transform var(--panel-open-dur) var(--motion-ease-drawer),
    opacity var(--panel-open-dur) var(--motion-ease-drawer),
    filter var(--panel-open-dur) var(--motion-ease-drawer);
}
.sheet__handle {
  width: 36px; height: 4px;
  background: var(--border-strong);
  border-radius: 2px;
  margin: 8px auto 0;
}
.sheet__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 18px;
}
.sheet__title { margin: 0; font-family: var(--font-display); font-size: 16px; font-weight: 650; text-wrap: balance; }
.sheet__close {
  width: 40px; height: 40px;
  border: none; background: transparent; color: var(--text-dim);
  font-size: 16px; cursor: pointer; line-height: 1; padding: 0;
  border-radius: var(--radius-sm);
  transition:
    color var(--motion-press-dur) var(--motion-ease-out),
    background-color var(--motion-press-dur) var(--motion-ease-out),
    transform var(--motion-press-dur) var(--motion-ease-out);
}
.sheet__close:active { transform: scale(0.94); }
.sheet__body { flex: 1; overflow-y: auto; padding: 4px 18px 18px; }

/* ===================================================================
   Drawer/sheet shared content styles
   =================================================================== */
.detail-domain {
  display: block;
  min-width: 0;
  overflow: hidden;
  color: var(--text);
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 650;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-kicker {
  display: grid;
  gap: 3px;
  margin-bottom: 12px;
}
.detail-kind {
  display: block;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.detail-answer {
  margin-bottom: 14px;
}
.detail-answer__label {
  margin: 0 0 4px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.45px;
}
.detail-answer__value {
  margin: 0;
  font-size: 13px;
  line-height: 1.48;
  color: var(--text-muted);
  text-wrap: pretty;
}
.detail-answer__value strong {
  color: var(--text);
  font-weight: 650;
}
.detail-line {
  display: block;
  margin-top: 3px;
}
.detail-next-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 2px;
}
.detail-next-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 38px;
  padding: 8px 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: oklch(0.192 0.004 286.018 / 0.5);
  color: var(--text-muted);
  text-align: left;
  cursor: pointer;
  box-shadow: var(--shadow-border);
  transition:
    background-color var(--motion-state-dur) var(--motion-ease-out),
    color var(--motion-state-dur) var(--motion-ease-out),
    transform var(--motion-press-dur) var(--motion-ease-out);
}
.detail-next-item:hover,
.detail-next-item:focus-visible {
  color: var(--text);
  background: oklch(0.24 0.006 286.033 / 0.68);
  outline: none;
}
.detail-next-item:active { transform: scale(0.985); }
.detail-next-item__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-next-item__meta {
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.35px;
}
.focus-summary strong {
  color: var(--text);
  font-weight: 650;
}
.focus-shelf {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.focus-row {
  min-height: 36px;
}
.focus-count {
  margin: 8px 0 0;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.35px;
}
.detail-meta {
  display: grid; grid-template-columns: auto 1fr; gap: 4px 12px;
  font-size: 13px; margin-bottom: 14px;
}
.detail-meta dt { color: var(--text-dim); }
.detail-meta dd { margin: 0; color: var(--text); }
.detail-confidence-bar {
  height: 6px; background: var(--bg-panel); border-radius: 3px;
  overflow: hidden; margin: 4px 0 12px;
}
.detail-confidence-bar__fill {
  height: 100%; border-radius: 3px;
  width: 100%;
  transform-origin: left center;
  transform: scaleX(var(--confidence-scale, 0));
  transition-property: transform;
  transition-duration: 240ms;
  transition-timing-function: var(--motion-ease-out);
}
.detail-section { margin-bottom: 16px; }
.detail-section h3 {
  margin: 0 0 6px; font-size: 12px; text-transform: uppercase;
  color: var(--text-dim); letter-spacing: 0.4px; font-family: var(--font-mono);
}
.detail-section p { margin: 0; font-size: 13px; line-height: 1.5; color: var(--text-muted); text-wrap: pretty; }
.detail-more {
  margin-top: 4px;
}
.detail-more summary {
  min-height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  list-style: none;
  border-top: 1px solid oklch(1 0 0 / 0.07);
  border-bottom: 1px solid oklch(1 0 0 / 0.07);
  padding: 0;
  transition:
    color var(--motion-state-dur) var(--motion-ease-out),
    transform var(--motion-press-dur) var(--motion-ease-out);
}
.detail-more summary::-webkit-details-marker { display: none; }
.detail-more summary::before {
  content: "+";
  display: inline-grid;
  place-items: center;
  width: 14px;
  height: 18px;
  color: var(--accent-strong);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1;
  transition:
    transform var(--motion-state-dur) var(--motion-ease-out);
}
.detail-more[open] summary {
  color: var(--text);
}
.detail-more[open] summary::before {
  transform: rotate(45deg);
}
.detail-more summary:active { transform: scale(0.98); }
.detail-more__content {
  padding-top: 14px;
}
.detail-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: 1px solid oklch(1 0 0 / 0.07);
}
.detail-stat {
  min-width: 0;
  padding: 8px 0;
  border-bottom: 1px solid oklch(1 0 0 / 0.07);
  transition:
    color var(--motion-state-dur) var(--motion-ease-out);
}
.detail-stat__value {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 650;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
}
.detail-stat__label {
  font-size: 10px;
  color: var(--text-dim);
  text-transform: uppercase;
}
.detail-list {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0 12px;
  margin: 0;
  border-top: 1px solid oklch(1 0 0 / 0.07);
}
.detail-list dt,
.detail-list dd {
  margin: 0;
  padding: 7px 0;
  border-bottom: 1px solid oklch(1 0 0 / 0.07);
  font-size: 12px;
  line-height: 1.35;
}
.detail-list dt {
  min-width: 0;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.detail-list dd {
  color: var(--text);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
  text-align: right;
}
.detail-reveal {
  opacity: 1;
  transform: translateY(0);
  filter: blur(0);
  transition:
    opacity 220ms var(--motion-ease-out),
    transform 220ms var(--motion-ease-out),
    filter 220ms var(--motion-ease-out);
  will-change: opacity, transform, filter;
}
.detail-reveal.is-new {
  opacity: 0;
  transform: translateY(8px);
  filter: blur(2px);
}

/* ===================================================================
   Hidden-state reset
   =================================================================== */
/* Component display rules (e.g. `.loading-state { display: flex }`,
   `.selection-dock`, `.sheet`) have the same specificity as the UA default
   `[hidden] { display: none }` and appear later in source order, so they
   win the cascade and the native hidden attribute stops hiding elements.
   This was observed in the wild: the viewer kept showing "Loading skill
   map..." after graph load because JS set `el.hidden = true` but the
   flex rule overrode it. `!important` restores the native contract for
   loading-state and all shared overlays/panels (selection dock, sheet,
   legend, empty-state) without affecting their visible-state display behavior. */
[hidden] { display: none !important; }

/* ===================================================================
   Empty / loading states
   =================================================================== */
.empty-state, .loading-state {
  position: absolute; inset: 0;
  z-index: 45;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-ui);
  color: var(--text-dim); font-size: 14px;
  pointer-events: none;
}
.loading-state {
  flex-direction: column;
  gap: 18px;
  background: var(--bg);
  opacity: 1;
  transition: opacity 240ms var(--motion-ease-out);
  will-change: opacity;
}
.loading-state[data-closing="true"] {
  opacity: 0;
}
.loading-state__loaders {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
}
.loading-state__text {
  margin: 0;
}
.spiral-loader {
  --spiral-size: 24px;
  position: relative;
  display: block;
  width: var(--spiral-size);
  height: var(--spiral-size);
  flex: 0 0 auto;
  color: oklch(0.934 0.012 91.522);
}
.spiral-loader__phase {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  opacity: 0;
}
.spiral-loader__phase--fast {
  animation: spiral-loader-fast-phase 4000ms steps(1, end) infinite;
}
.spiral-loader__phase--slow {
  animation: spiral-loader-slow-phase 4000ms steps(1, end) infinite;
}
.spiral-loader__motion {
  transform: translate(-0.5px, 1.5px);
}
.spiral-loader__phase--fast .spiral-loader__motion {
  animation: spiral-loader-slide 500ms cubic-bezier(0.167, 0.167, 0.833, 0.833) infinite;
}
.spiral-loader__phase--slow .spiral-loader__motion {
  animation: spiral-loader-slide 1000ms cubic-bezier(0.167, 0.167, 0.833, 0.833) infinite;
}
.spiral-loader__path {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.24;
  stroke-dasharray: 21 100;
  stroke-dashoffset: -23;
}
.spiral-loader__phase--fast .spiral-loader__path {
  animation: spiral-loader-trim 500ms cubic-bezier(0.32, 0.154, 0.826, 0.579) infinite;
}
.spiral-loader__phase--slow .spiral-loader__path {
  animation: spiral-loader-trim 1000ms cubic-bezier(0.32, 0.313, 0.826, 0.143) infinite;
}
@keyframes spiral-loader-fast-phase {
  0%, 49.999% { opacity: 1; }
  50%, 100% { opacity: 0; }
}
@keyframes spiral-loader-slow-phase {
  0%, 49.999% { opacity: 0; }
  50%, 100% { opacity: 1; }
}
@keyframes spiral-loader-slide {
  from { transform: translate(-0.5px, 1.5px); }
  to { transform: translate(-8.5px, 1.5px); }
}
@keyframes spiral-loader-trim {
  from { stroke-dashoffset: -23; }
  to { stroke-dashoffset: -57; }
}

@media (hover: hover) and (pointer: fine) {
  .search-field__clear:hover { color: var(--text); background: oklch(1 0 0 / 0.045); }
  .hud-btn:hover { color: var(--text); background: transparent; }
  .filterbar__clear:hover { color: var(--text); box-shadow: var(--shadow-border-hover); }
  .domain-label:hover { opacity: 0.94; }
  .legend__close:hover { color: var(--text); background: oklch(1 0 0 / 0.04); }
  .selection-dock__close:hover,
  .sheet__close:hover { color: var(--text); background: oklch(1 0 0 / 0.04); }
  .filterbar__select:hover,
  .filterbar__range:hover { box-shadow: var(--shadow-border-hover); }
  .detail-more summary:hover {
    color: var(--text);
  }
}

/* ===================================================================
   Responsive
   =================================================================== */
@media (max-width: 768px) {
  .hud-search {
    bottom: 58px;
    width: calc(100vw - 28px);
    left: 14px;
    transform: translateY(8px) scale(0.97);
  }
  .hud-search[data-open="true"] {
    transform: translateY(0) scale(1);
  }
  .hud-actions { bottom: 10px; gap: 0; padding: 3px; }
  .hud-btn { width: 34px; height: 34px; }
  .filter-panel,
  .settings-panel,
  .legend {
    bottom: 58px;
    left: 14px;
    right: 14px;
    width: auto;
    transform-origin: bottom center;
    transform: translateY(var(--panel-translate-y)) scale(0.97);
  }
  .filter-panel[data-open="true"],
  .settings-panel[data-open="true"],
  .legend[data-open="true"] {
    transform: translateY(0) scale(1);
  }
  .filter-panel__body { max-width: none; overflow-x: auto; flex-wrap: nowrap; }
  .filterbar__group { flex-shrink: 0; }
  .filterbar__clear { flex-shrink: 0; }
  .minimap { width: 120px; height: 80px; bottom: 10px; right: 10px; }
  .legend { max-height: 60vh; }
  .selection-dock { display: none; }
}
@media (min-width: 769px) {
  .sheet { display: none; }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
  .t-shimmer::before {
    animation: none !important;
  }
  .spiral-loader__phase,
  .spiral-loader__motion,
  .spiral-loader__path {
    animation: none !important;
  }
  .spiral-loader__phase--fast { opacity: 1; }
  .spiral-loader__phase--slow { opacity: 0; }
  .spiral-loader__motion { transform: translate(-4.5px, 1.5px); }
  .spiral-loader__path { stroke-dashoffset: -40; }
  .t-icon-swap .t-icon,
  .t-panel-slide,
  .filter-panel,
  .filter-panel .filterbar__group,
  .filter-panel .filterbar__clear,
  .legend,
  .legend__section,
  .selection-dock,
  .sheet,
  .search-field,
  .search-field__clear,
  .hud-toolbar__indicator,
  .hud-btn,
  .filterbar__select,
  .filterbar__range,
  .settings-range,
  .filterbar__clear,
  .minimap,
  .domain-label,
  .detail-reveal,
  .detail-more summary,
  .graph-node__focus-ring {
    transition: none !important;
    filter: none !important;
    transform: none !important;
  }
}
"""

VIEWER_SFX_JS = """\
/**
 * Minimal procedural Web Audio SFX engine for the Phase 1 skill map viewer.
 *
 * Design contract (decisions 54-62):
 * - SFX are original, generated procedurally via Web Audio (no asset files).
 * - No sound before first user gesture. AudioContext is created lazily.
 * - Visible mute toggle; preference remembered in localStorage.
 * - Reduced motion preference keeps SFX minimal.
 * - Sound vocabulary: node select, drawer open/close, domain collapse/expand,
 *   filter apply/clear. No ambient loops, no hover sounds, no music.
 * - Rate-limited so rapid navigation does not smear into noise.
 * - Palette: soft glass/graphite ticks, muted tonal blooms, short filtered
 *   noise transients. No arcade/fantasy/aggressive sounds.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "traccia-viewer-sound-enabled-v2";
  const RATE_LIMIT_MS = 60; // prevent overlapping one-shots for the same event
  const SLIDER_TICK_VOLUME = 0.42;
  const SLIDER_TICK_FREQ = 5500;
  const SLIDER_TICK_DECAY_SEC = 0.006;
  const SLIDER_NOISE_DURATION_SEC = 0.002;
  const SLIDER_NOISE_LEVEL = 0.85;
  const SLIDER_NOISE_Q = 18;
  const SLIDER_TICK_MIN_GAP_SEC = 0.04;
  const SLIDER_MAX_QUEUE_AHEAD_SEC = 0.04;

  class SfxEngine {
    constructor() {
      this._ctx = null;
      this._master = null;
      this._enabled = this._readStoredPreference();
      this._lastPlayed = {};
      this._reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
      ).matches;
      this._noiseBuffer = null;
      this._nextSliderTickTime = 0;
      this._pendingSliderTicks = [];
    }

    _readStoredPreference() {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored === null) return null; // null = use config default
        return stored === "true";
      } catch (_e) {
        return null;
      }
    }

    _writeStoredPreference(value) {
      try {
        localStorage.setItem(STORAGE_KEY, String(value));
      } catch (_e) {
        /* ignore quota errors */
      }
    }

    /** Resolve whether sound should play given stored pref + config default. */
    shouldBeOn(configDefault) {
      const stored = this._readStoredPreference();
      return stored === null ? !!configDefault : stored;
    }

    isEnabled() {
      return !!this._enabled;
    }

    /** Enable or disable sound. Must be called from a user gesture. */
    setEnabled(enabled) {
      this._enabled = !!enabled;
      this._writeStoredPreference(this._enabled);
      if (this._enabled) {
        this._ensureContext();
      }
    }

    _ensureContext() {
      if (this._ctx) return;
      try {
        const Ctor = window.AudioContext || window.webkitAudioContext;
        if (!Ctor) return;
        this._ctx = new Ctor();
        this._master = this._ctx.createGain();
        this._master.gain.value = 0.15; // very low master gain
        this._master.connect(this._ctx.destination);
      } catch (_e) {
        this._ctx = null;
      }
    }

    /** Resume the audio context after a user gesture (browsers suspend it). */
    unlock() {
      this._ensureContext();
      if (this._ctx && this._ctx.state === "suspended") {
        this._ctx.resume().catch(function () {});
      }
    }

    _rateLimited(key) {
      const now = this._ctx ? this._ctx.currentTime * 1000 : Date.now();
      const last = this._lastPlayed[key] || 0;
      if (now - last < RATE_LIMIT_MS) return false;
      this._lastPlayed[key] = now;
      return true;
    }

    _play(oscConfig, gainConfig, filterConfig) {
      if (!this._enabled || this._reducedMotion) return;
      this._ensureContext();
      if (!this._ctx || !this._master) return;

      const now = this._ctx.currentTime;
      const osc = this._ctx.createOscillator();
      const gain = this._ctx.createGain();
      let node = osc;

      if (filterConfig) {
        const filter = this._ctx.createBiquadFilter();
        filter.type = filterConfig.type || "lowpass";
        filter.frequency.value = filterConfig.frequency || 2000;
        filter.Q.value = filterConfig.Q || 0.7;
        node.connect(filter);
        node = filter;
      }

      node.connect(gain);
      gain.connect(this._master);

      osc.type = oscConfig.type || "sine";
      osc.frequency.setValueAtTime(oscConfig.frequency, now);
      if (oscConfig.frequencyEnd) {
        osc.frequency.exponentialRampToValueAtTime(
          oscConfig.frequencyEnd,
          now + oscConfig.duration
        );
      }

      const peak = gainConfig.peak || 0.3;
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(peak, now + (gainConfig.attack || 0.005));
      gain.gain.exponentialRampToValueAtTime(0.0001, now + oscConfig.duration);

      osc.start(now);
      osc.stop(now + oscConfig.duration + 0.02);
    }

    _getNoiseBuffer() {
      if (this._noiseBuffer || !this._ctx) return this._noiseBuffer;
      const samples = Math.floor(this._ctx.sampleRate * 0.5);
      this._noiseBuffer = this._ctx.createBuffer(1, samples, this._ctx.sampleRate);
      const data = this._noiseBuffer.getChannelData(0);
      for (let i = 0; i < samples; i += 1) {
        data[i] = Math.random() * 2 - 1;
      }
      return this._noiseBuffer;
    }

    _scheduleSliderTick(when) {
      if (!this._ctx || !this._master) return;

      const tickGain = this._ctx.createGain();
      tickGain.gain.value = SLIDER_TICK_VOLUME;
      tickGain.connect(this._master);

      const osc = this._ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = SLIDER_TICK_FREQ;
      const oscEnv = this._ctx.createGain();
      oscEnv.gain.setValueAtTime(1, when);
      oscEnv.gain.exponentialRampToValueAtTime(0.0005, when + SLIDER_TICK_DECAY_SEC);
      osc.connect(oscEnv).connect(tickGain);
      osc.start(when);
      osc.stop(when + SLIDER_TICK_DECAY_SEC + 0.02);

      const noise = this._ctx.createBufferSource();
      noise.buffer = this._getNoiseBuffer();
      const noiseGain = this._ctx.createGain();
      noiseGain.gain.setValueAtTime(SLIDER_NOISE_LEVEL, when);
      noiseGain.gain.exponentialRampToValueAtTime(0.0005, when + SLIDER_NOISE_DURATION_SEC);
      const filter = this._ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.value = SLIDER_TICK_FREQ;
      filter.Q.value = SLIDER_NOISE_Q;
      noise.connect(noiseGain).connect(filter).connect(tickGain);
      noise.start(when);
      noise.stop(when + SLIDER_NOISE_DURATION_SEC + 0.01);

      this._pendingSliderTicks.push({ when, osc, noise });
    }

    cancelSliderTicks() {
      if (!this._ctx) return;
      const now = this._ctx.currentTime;
      this._pendingSliderTicks.forEach(function (tick) {
        if (tick.when <= now) return;
        try { tick.osc.stop(); } catch (_e) {}
        try { tick.noise.stop(); } catch (_e) {}
      });
      this._pendingSliderTicks = [];
      this._nextSliderTickTime = now;
    }

    /** Lisse-inspired slider detent: 5.5kHz partial + tiny filtered-noise tick. */
    sliderTick() {
      if (!this._enabled || this._reducedMotion) return;
      this._ensureContext();
      if (!this._ctx || !this._master) return;
      const now = this._ctx.currentTime;
      const when = Math.max(now, this._nextSliderTickTime);
      if (when - now > SLIDER_MAX_QUEUE_AHEAD_SEC) return;
      this._scheduleSliderTick(when);
      this._nextSliderTickTime = when + SLIDER_TICK_MIN_GAP_SEC;
    }

    /** Soft two-layer tick for node select / deep-link focus (~60-110ms). */
    nodeSelect() {
      if (!this._rateLimited("select")) return;
      // Layer 1: quick high tick
      this._play(
        { type: "sine", frequency: 880, frequencyEnd: 660, duration: 0.06 },
        { peak: 0.18, attack: 0.002 },
        { type: "lowpass", frequency: 3000, Q: 1 }
      );
      // Layer 2: softer lower bloom slightly delayed
      const self = this;
      setTimeout(function () {
        self._play(
          { type: "triangle", frequency: 330, duration: 0.09 },
          { peak: 0.1, attack: 0.004 },
          { type: "lowpass", frequency: 1200, Q: 0.7 }
        );
      }, 30);
    }

    /** Very quiet slide/bloom for drawer open (~100-160ms). */
    drawerOpen() {
      this._play(
        { type: "sine", frequency: 200, frequencyEnd: 400, duration: 0.14 },
        { peak: 0.08, attack: 0.01 },
        { type: "lowpass", frequency: 1500, Q: 0.5 }
      );
    }

    /** Very quiet close cue (~100-160ms). */
    drawerClose() {
      this._play(
        { type: "sine", frequency: 400, frequencyEnd: 200, duration: 0.12 },
        { peak: 0.06, attack: 0.008 },
        { type: "lowpass", frequency: 1500, Q: 0.5 }
      );
    }

    /** Compact fold/unfold for domain collapse/expand (~80-140ms). */
    domainToggle(expanding) {
      if (!this._rateLimited("domain")) return;
      if (expanding) {
        this._play(
          { type: "triangle", frequency: 300, frequencyEnd: 500, duration: 0.1 },
          { peak: 0.07, attack: 0.005 },
          { type: "lowpass", frequency: 2000, Q: 0.7 }
        );
      } else {
        this._play(
          { type: "triangle", frequency: 500, frequencyEnd: 300, duration: 0.08 },
          { peak: 0.06, attack: 0.004 },
          { type: "lowpass", frequency: 2000, Q: 0.7 }
        );
      }
    }

    /** Dry switch cue for filter apply/clear (~35-70ms). */
    filterSwitch() {
      if (!this._rateLimited("filter")) return;
      this._play(
        { type: "square", frequency: 1200, duration: 0.03 },
        { peak: 0.04, attack: 0.001 },
        { type: "lowpass", frequency: 4000, Q: 2 }
      );
    }

    /** Small tactile tap for bottom dock buttons (~35-55ms). */
    dockButton() {
      if (!this._rateLimited("dock")) return;
      this._play(
        { type: "triangle", frequency: 760, frequencyEnd: 980, duration: 0.045 },
        { peak: 0.045, attack: 0.0015 },
        { type: "lowpass", frequency: 2600, Q: 1.2 }
      );
    }
  }

  window.SfxEngine = SfxEngine;
})();
"""

VIEWER_JS = """\
/**
 * Phase 1 public skill map viewer.
 *
 * Hybrid canvas + SVG renderer for high-performance 12k+ node graphs.
 *
 * Architecture:
 * - Canvas raster layer draws ALL visible node glyphs and bulk edges as pixels.
 *   This is the performance layer: no DOM elements per node/edge.
 * - SVG overlay layer keeps only domain labels, the capped accessible
 *   node set (for keyboard/AT interaction), and focus-path highlighted
 *   edges in the DOM.
 * - Canvas hit-testing handles clicks on nodes that are only drawn as
 *   pixels (not in the SVG accessible set).
 * - Pan/zoom transforms are applied to both layers in sync, batched
 *   via requestAnimationFrame.
 *
 * Features (per docs/finished-run-viewer-decisions.md):
 * - Deterministic constellation layout (decision 18)
 * - Pan/zoom with mouse, touch, and keyboard
 * - Search across names, domains, descriptions (decision 35)
 * - Compact filter panel: domain, status, freshness, confidence, evidence
 * - Focus path highlighting on selection (decision 8)
 * - Node detail drawer (desktop) / bottom sheet (mobile) (decisions 9, 42)
 * - Collapsible minimap (decision 37)
 * - Collapsible legend (decision 43)
 * - Hash deep links: #node=<id> (decision 52)
 * - Keyboard navigation (decision 39)
 * - Minimal procedural SFX with gesture-gated unlock (decisions 54-62)
 * - Public-safe fields only (decision 50)
 */
(function () {
  "use strict";

  // --- State ---
  let graphData = null;
  let viewerConfig = { enableSound: true, version: 1 };
  let nodes = [];
  let edges = [];
  let domains = [];
  let visualGroups = [];
  let domainColorMap = {};
  let resolvedDomainColors = {};
  let resolvedVisualGroupColors = {};
  let nodeById = new Map();
  let adjacencyByNode = new Map();
  let nodesByVisualGroup = new Map();
  let layoutCache = null;
  let selectedNodeId = null;
  let focusedNodeIds = new Set();
  let activeFocus = null;
  let focusDisplay = null;
  let focusDisplayFrom = null;
  let focusDisplayTo = null;
  let focusAnimationFrame = null;
  let focusAnimationToken = 0;
  let focusAnimationStart = 0;
  let focusAnimationDuration = 0;
  let focusQuietClassesSynced = false;
  let focusQuietClassFrame = null;
  let focusLabelRefreshTimer = null;
  let focusDockHydrationTimer = null;
  let viewFrame = null;
  let canvasRedrawPending = false;
  let canvasCtx = null;
  let canvasBitmap = null;
  let canvasBitmapCtx = null;
  let canvasDpr = 1;
  let canvasCachePad = 0;
  let canvasViewportPad = 0;
  let renderedCanvasViewState = { x: 0, y: 0, scale: 1 };
  let blittedCanvasViewState = { x: 0, y: 0, scale: 1 };
  let cachedVisibleNodeIds = null;
  let cachedCanvasNodeIds = null;
  let cachedCanvasNodes = null;
  let domainLabelElements = new Map();
  let svgNodeElements = new Map();
  let svgEdgeElements = [];
  let hoverNodeId = null;
  let hoverNodeEl = null;
  let lastCanvasPointer = null;
  let wheelZoomAnchor = null;
  let renderedSyntheticLabelBoxes = [];
  let canvasSettleTimer = null;
  let resizeFitTimer = null;
  const panelHideTimers = new WeakMap();
  // Deferred canvas label redraws: zoom and focus changes can request label
  // updates, but the all-node canvas pass is throttled until interaction settles.
  let zoomLabelTimer = null;
  let viewTweenFrame = null;
  let viewTweenToken = 0;
  let panInertiaFrame = null;
  let panSamples = [];
  let cameraGestureActive = false;
  let wheelCameraActive = false;
  let wheelCameraTimer = null;
  let suppressNextGraphClick = false;
  // Session-level domain collapse state (decision 34): public collapse is
  // temporary per browser session, not persisted to curation.json.
  let collapsedDomains = {};
  const DEFAULT_FILTERS = Object.freeze({
    search: "",
    domain: "",
    status: "",
    freshness: "current",
    minConfidence: 0.75,
    maxSkills: 1000,
    evidenceType: "",
  });
  let filters = defaultFilters();
  const VIEW_SETTINGS_STORAGE_KEY = "traccia.viewer.renderSettings.v1";
  const DEFAULT_VIEW_SETTINGS = Object.freeze({
    contextDimming: 0.25,
    nodeScale: 1,
    lineStrength: 1,
    labelDensity: 1,
    separation: 1,
    showLines: true,
    showCategories: true,
    showCategoryLabels: true,
    showSkillLabels: true,
    showLevelBadges: true,
    showBackgroundDots: true,
  });
  // Dormant constellation experiment: keep this off for ordinary skill clicks.
  // If a future request mentions "constellation", revive this flag or attach
  // the pocket behavior to a deliberate mode instead of default node selection.
  const ENABLE_NODE_CONSTELLATION_FOCUS = false;
  let viewSettings = defaultViewSettings();

  // View transform
  let viewState = { x: 0, y: 0, scale: 1 };
  let targetViewState = { x: 0, y: 0, scale: 1 };
  const VIEW = {
    minScale: 0.025,
    maxScale: 4,
    nodeBaseRadius: 4.9,
    nodeLevelStep: 2.05,
    treeAreaRadius: 430,
    treeTopicRadius: 820,
    treeSkillRadius: 1080,
    treeSkillRowSpacing: 132,
    treeTopicMinSpan: 0.16,
    treeSkillLaneMinPx: 118,
    treeSkillMaxLanes: 24,
    treeBreathingMax: 2.05,
    treeAreaBreathingMax: 1.74,
    treeAreaGapPx: 240,
    treeTopicGapPx: 280,
    treeTopicInnerFill: 0.62,
    treeTopicRadialLaneGap: 92,
    treeTopicTerritoryLaneGap: 190,
    treeTopicSkillGap: 560,
    treeTopicLabelGap: 46,
    treeTopicLabelLaneGap: 34,
    topicLabelScale: 0.42,
    labelScale: 0.45,
    maxNodeLabels: 1000,
    maxMobileNodeLabels: 180,
    mobileLabelViewportWidth: 700,
    canvasLabelMinGraphPx: 8.4,
    canvasLabelMaxGraphPx: 10.8,
    canvasLabelGutterGraphPx: 6,
    canvasLabelRadialGapGraphPx: 14,
    canvasLabelSlotStepGraphPx: 13,
    canvasLabelSlotCount: 7,
    maxAccessibleNodes: 260,
    maxMinimapDots: 1500,
    maxFocusLabels: 52,
    labelMovementPad: 1600,
    maxFocusShelfRows: 72,
    focusQuietAlpha: 0.5,
    focusContextAlpha: 0.25,
    focusQuietScale: 1,
    focusContextScale: 0.78,
    focusPocketAncestorGap: 128,
    focusPocketAncestorTangentGap: 46,
    focusPocketSiblingRadius: 175,
    focusPocketSuggestionRadius: 300,
    focusPocketSpiralStep: 54,
    focusClearanceMaxMove: 118,
    focusClearanceRadii: [34, 56, 82, 112],
    // Canvas edge culling: skip edges whose midpoint is far outside viewport.
    // Node glyphs are intentionally not culled by zoom or viewport: the public
    // map contract is that every in-filter node remains visually represented.
    canvasEdgeCullPad: 200,
    canvasCachePadMin: 1800,
    canvasCachePadMax: 2200,
    canvasViewportPad: 1280,
    canvasMaxDpr: 1.35,
    cameraPanSettleMs: 360,
    cameraZoomLabelSettleMs: 180,
    cameraZoomCanvasSettleMs: 260,
    detailZoomLow: 0.3,
    detailZoomMedium: 0.5,
  };
  const FOCUS_ANIMATION_MS = 260;
  const PAN_INERTIA = {
    sampleWindowMs: 130,
    minVelocity: 0.045,
    maxVelocity: 0.84,
    friction: 0.9,
    stopVelocity: 0.014,
    maxDurationMs: 560,
  };
  const WHEEL_ZOOM = {
    mouseRate: 1 / 540,
    trackpadRate: 1 / 170,
    lineHeightPx: 40,
    pageHeightPx: 800,
  };

  function bumpViewerMetric(name) {
    if (!window.__tracciaViewerMetrics) return;
    window.__tracciaViewerMetrics[name] = (window.__tracciaViewerMetrics[name] || 0) + 1;
  }

  // Quiet area glows and branch strokes for the canvas pass. These colors are
  // accents on the branch structure, not filled overlap-prone region bubbles.
  const DOMAIN_BACKDROP_PALETTE = [
    { fill: "rgba(56, 121, 108, 0.045)", stroke: "rgba(56, 121, 108, 0.13)" },
    { fill: "rgba(111, 143, 125, 0.036)", stroke: "rgba(111, 143, 125, 0.11)" },
    { fill: "rgba(191, 118, 91, 0.035)", stroke: "rgba(191, 118, 91, 0.10)" },
    { fill: "rgba(211, 205, 187, 0.028)", stroke: "rgba(211, 205, 187, 0.09)" },
    { fill: "rgba(79, 155, 134, 0.036)", stroke: "rgba(79, 155, 134, 0.11)" },
    { fill: "rgba(115, 144, 106, 0.035)", stroke: "rgba(115, 144, 106, 0.10)" },
    { fill: "rgba(197, 139, 105, 0.035)", stroke: "rgba(197, 139, 105, 0.10)" },
    { fill: "rgba(159, 150, 127, 0.028)", stroke: "rgba(159, 150, 127, 0.09)" },
  ];

  const VISUAL_GROUP_COLORS = [
    "#38796c", "#4f9b86", "#6f8f7d", "#bf765b",
    "#d3cdbb", "#73906a", "#9f967f", "#c58b69",
  ];

  const AREA_LAYOUT_ORDER = [
    "AI & Automation", "Code & Tooling", "Systems & Operations", "Data & Analysis",
    "Web & Interface", "Media & Creative", "Docs & Knowledge", "Product & Planning",
    "Security & Privacy", "Communication", "General Craft",
  ];

  const SKILL_CONSTELLATIONS = [
    { name: "AI & Automation", pattern: /\\b(ai|llm|model|prompt|agent|automation|workflow|bot|chatgpt|glm|gemini|openai|claude|droid)\\b/i },
    { name: "Web & Interface", pattern: /\\b(ui|ux|css|html|frontend|react|component|browser|dom|canvas|svg|web|website|design|layout|animation|viewer)\\b/i },
    { name: "Data & Analysis", pattern: /\\b(data|json|sql|database|graph|analysis|analytics|metric|schema|query|dataset|csv|parsing|statistics)\\b/i },
    { name: "Systems & Operations", pattern: /\\b(linux|shell|bash|server|ssh|docker|container|vm|network|dns|nginx|system|process|service|deploy|hosting|cloud)\\b/i },
    { name: "Code & Tooling", pattern: /\\b(code|git|github|test|typescript|python|javascript|api|cli|package|build|lint|debug|refactor|repository)\\b/i },
    { name: "Docs & Knowledge", pattern: /\\b(doc|docs|documentation|markdown|writing|note|obsidian|knowledge|research|readme|content)\\b/i },
    { name: "Media & Creative", pattern: /\\b(image|video|audio|sfx|visual|graphic|photo|color|palette|asset|media)\\b/i },
    { name: "Product & Planning", pattern: /\\b(product|plan|roadmap|decision|strategy|requirement|spec|review|feedback|user|workflow)\\b/i },
    { name: "Security & Privacy", pattern: /\\b(security|privacy|auth|token|credential|secret|permission|redact|sensitive|safe)\\b/i },
    { name: "Communication", pattern: /\\b(email|slack|discord|message|chat|collaboration|meeting|social)\\b/i },
  ];

  const BRANCH_TOPIC_RULES = {
    "AI & Automation": [
      { name: "Agents & Workflows", pattern: /\\b(agent|workflow|automation|orchestration|bot|retry|loop)\\b/i },
      { name: "LLM Operations", pattern: /\\b(llm|model|glm|gemini|openai|claude|chatgpt|inference|provider)\\b/i },
      { name: "Prompting & Evaluation", pattern: /\\b(prompt|evaluation|eval|fact[- ]?check|classification|reasoning)\\b/i },
      { name: "AI Media", pattern: /\\b(image|audio|video|vision|ocr|generation|generated|multimodal)\\b/i },
    ],
    "Web & Interface": [
      { name: "Frontend UI", pattern: /\\b(ui|ux|frontend|react|component|button|form|toolbar|panel)\\b/i },
      { name: "CSS & Styling", pattern: /\\b(css|style|font|color|palette|layout|grid|flex|z-index|mask|clip|animation)\\b/i },
      { name: "Browser & DOM", pattern: /\\b(browser|dom|html|chrome|safari|extension|devtools|cookie|localstorage)\\b/i },
      { name: "Canvas & Graphics", pattern: /\\b(canvas|svg|webgl|three|3d|render|visual|graph|map)\\b/i },
      { name: "Accessibility", pattern: /\\b(accessibility|aria|keyboard|focus|screen reader|reduced motion)\\b/i },
    ],
    "Data & Analysis": [
      { name: "Databases & Storage", pattern: /\\b(sql|sqlite|postgres|database|storage|cache|index|schema)\\b/i },
      { name: "Parsing & Formats", pattern: /\\b(json|yaml|csv|xml|parser|parsing|schema|format|metadata)\\b/i },
      { name: "Metrics & Analytics", pattern: /\\b(metric|analytics|statistics|analysis|ranking|score|count)\\b/i },
      { name: "Graphs & Queries", pattern: /\\b(graph|query|cypher|tree|node|edge|dataset)\\b/i },
    ],
    "Systems & Operations": [
      { name: "Linux & Shell", pattern: /\\b(linux|shell|bash|cli|terminal|process|systemd|cron|chmod)\\b/i },
      { name: "Cloud & Deploy", pattern: /\\b(cloud|deploy|hosting|server|service|vercel|aws|gcp|oci|worker)\\b/i },
      { name: "Networking & DNS", pattern: /\\b(network|dns|http|ssh|proxy|nginx|port|tls|tcp|ip)\\b/i },
      { name: "Containers & VMs", pattern: /\\b(docker|container|vm|qemu|virtual|podman|kubernetes)\\b/i },
      { name: "Monitoring & Debugging", pattern: /\\b(debug|troubleshoot|log|monitor|profile|trace|diagnostic|crash)\\b/i },
      { name: "Windows & Admin", pattern: /\\b(windows|powershell|active directory|registry|wsl|admin)\\b/i },
    ],
    "Code & Tooling": [
      { name: "APIs & SDKs", pattern: /\\b(api|sdk|endpoint|client|server|request|response|integration)\\b/i },
      { name: "Testing & QA", pattern: /\\b(test|qa|assert|snapshot|fixture|coverage|verification|typecheck)\\b/i },
      { name: "Git & Repositories", pattern: /\\b(git|github|repo|repository|commit|branch|pull request|pr|jj)\\b/i },
      { name: "Build & Packaging", pattern: /\\b(build|package|bundle|npm|bun|uv|python|typescript|javascript|compile)\\b/i },
      { name: "CLI & Scripts", pattern: /\\b(cli|script|command|argparse|flag|config|tooling)\\b/i },
      { name: "Debugging & Refactors", pattern: /\\b(debug|refactor|lint|ruff|error|exception|traceback|fix)\\b/i },
    ],
    "Docs & Knowledge": [
      { name: "Documentation", pattern: /\\b(doc|docs|documentation|readme|manual|guide|spec)\\b/i },
      { name: "Markdown & Notes", pattern: /\\b(markdown|md|note|obsidian|knowledge|wiki|frontmatter)\\b/i },
      { name: "Research & Writing", pattern: /\\b(research|writing|paper|citation|summary|article|content)\\b/i },
    ],
    "Media & Creative": [
      { name: "Audio & Video", pattern: /\\b(audio|video|sfx|sound|music|mux|sync|ffmpeg)\\b/i },
      { name: "Image & Graphics", pattern: /\\b(image|photo|graphic|visual|sprite|pixel|color|palette|asset)\\b/i },
      { name: "3D & Blender", pattern: /\\b(3d|three|blender|modeling|mesh|shader|render)\\b/i },
      { name: "Game & Level Design", pattern: /\\b(game|level|minecraft|roblox|mechanic|play|economy)\\b/i },
    ],
    "Product & Planning": [
      { name: "Strategy & Requirements", pattern: /\\b(strategy|requirement|spec|scope|planning|roadmap|decision)\\b/i },
      { name: "Reviews & Feedback", pattern: /\\b(review|feedback|critique|audit|rubric|quality)\\b/i },
      { name: "User Workflows", pattern: /\\b(user|workflow|journey|persona|product|experience|onboarding)\\b/i },
    ],
    "Security & Privacy": [
      { name: "Auth & Permissions", pattern: /\\b(auth|oauth|token|permission|session|credential|login)\\b/i },
      { name: "Secrets & Redaction", pattern: /\\b(secret|redact|privacy|sensitive|private|leak|safe)\\b/i },
      { name: "Abuse & Detection", pattern: /\\b(anti|bot|scraping|captcha|detection|evasion|abuse|spam|threat)\\b/i },
      { name: "Security Analysis", pattern: /\\b(security|encryption|malware|exploit|vulnerability|proxy|mitm)\\b/i },
    ],
    "Communication": [
      { name: "Chat & Messaging", pattern: /\\b(chat|message|discord|slack|conversation|thread)\\b/i },
      { name: "Social Platforms", pattern: /\\b(social|twitter|x.com|reddit|instagram|platform)\\b/i },
      { name: "Email & Outreach", pattern: /\\b(email|outreach|newsletter|contact|inbox)\\b/i },
      { name: "Collaboration", pattern: /\\b(collaboration|meeting|team|handoff|review)\\b/i },
    ],
    "General Craft": [
      { name: "Architecture & Patterns", pattern: /\\b(architecture|pattern|design|system|structure|abstraction|modeling)\\b/i },
      { name: "Debugging & Troubleshooting", pattern: /\\b(debug|troubleshoot|diagnostic|error|failure|fix|issue)\\b/i },
      { name: "File & Content Ops", pattern: /\\b(file|folder|path|export|import|content|metadata|document)\\b/i },
      { name: "Platform Knowledge", pattern: /\\b(platform|environment|setup|configuration|hardware|device|local)\\b/i },
      { name: "Languages & Tools", pattern: /\\b(python|javascript|typescript|go|rust|package|library|framework)\\b/i },
      { name: "Research & Review", pattern: /\\b(research|review|analysis|comparison|selection|evaluation)\\b/i },
    ],
  };

  const DISPLAY_TOKEN_CASE = {
    ai: "AI", api: "API", css: "CSS", csv: "CSV", dns: "DNS", dom: "DOM",
    gcp: "GCP", git: "Git", github: "GitHub", glm: "GLM", gpt: "GPT",
    html: "HTML", http: "HTTP", https: "HTTPS", ios: "iOS", ip: "IP",
    json: "JSON", jwt: "JWT", llm: "LLM", mcp: "MCP", ocr: "OCR",
    pdf: "PDF", pr: "PR", qa: "QA", qemu: "QEMU", rtk: "RTK", sdk: "SDK",
    sfx: "SFX", sql: "SQL", sqlite: "SQLite", ssh: "SSH", svg: "SVG",
    tls: "TLS", ui: "UI", uri: "URI", url: "URL", ux: "UX", vm: "VM",
    webgl: "WebGL", webgpu: "WebGPU", xml: "XML", yaml: "YAML",
  };

  // --- SFX ---
  const sfx = new window.SfxEngine();
  const DATA_VERSION = "20260629-anchor-lock-1";
  const LOADING_EXIT_MS = 260;
  const DRAG_SELECT_THRESHOLD = 5;

  // --- DOM refs ---
  const $ = (id) => document.getElementById(id);
  const dom = {};

  function cacheDom() {
    [
      "viewport", "canvas", "graph-camera", "graph-canvas", "graph-svg", "graph-zoom", "graph-domain-labels",
      "graph-edges", "graph-nodes", "search-toggle", "search-panel",
      "search-input", "search-clear",
      "filter-domain", "filter-status", "filter-freshness", "filter-scope",
      "filter-confidence", "filter-confidence-value", "filter-evidence", "filter-clear", "filter-toggle",
      "settings-toggle", "settings-panel", "setting-dim", "setting-dim-value",
      "setting-node-size", "setting-node-size-value", "setting-line-strength",
      "setting-line-strength-value", "setting-label-density", "setting-label-density-value",
      "setting-separation", "setting-separation-value", "setting-show-lines",
      "setting-show-categories", "setting-show-category-labels", "setting-show-skill-labels",
      "setting-show-level-badges", "setting-show-background-dots", "settings-reset",
      "minimap", "minimap-svg", "legend", "legend-stats", "legend-toggle", "legend-close",
      "action-dock", "toolbar-indicator", "minimap-toggle", "sound-toggle", "reset-view",
      "drawer", "drawer-title", "drawer-body", "drawer-close",
      "sheet", "sheet-title", "sheet-body", "sheet-close",
      "empty-state", "loading-state", "loading-message", "filter-bar",
    ].forEach(function (id) {
      dom[id.replace(/-/g, "_")] = $(id);
    });
  }

  // --- Init ---
  async function init() {
    cacheDom();
    viewSettings = loadViewSettings();
    syncSettingsControls();
    initCanvas();
    bindEvents();

    var loadStage = "loading graph data";
    try {
      const [graphRes, configRes] = await Promise.all([
        fetch("graph.json?v=" + DATA_VERSION),
        fetch("config.json?v=" + DATA_VERSION).catch(function () { return null; }),
      ]);
      if (!graphRes.ok) {
        throw new Error("graph.json returned HTTP " + graphRes.status);
      }
      graphData = await graphRes.json();
      if (configRes && configRes.ok) {
        viewerConfig = await configRes.json();
      }

      loadStage = "initializing controls";
      initSoundToggle();
      loadStage = "processing graph data";
      processData();
      loadStage = "rendering filters";
      renderFilters();
      renderLegend();
      loadStage = "laying out skill map";
      layoutAndRender();
      resetView();
      handleDeepLink();

      finishLoading();
      updateEmptyState();
    } catch (err) {
      console.error("Skill map initialization failed during " + loadStage + ".", err);
      showError("Failed to initialize skill map. Check the browser console for details.");
    }
  }

  function showError(msg) {
    if (dom.loading_state) {
      delete dom.loading_state.dataset.closing;
    }
    setLoadingMessage(msg);
    dom.loading_state.hidden = false;
  }

  function finishLoading() {
    document.body.classList.remove("viewer-loading");
    if (!dom.loading_state) return;
    dom.loading_state.dataset.closing = "true";
    var delay = prefersReducedMotion() ? 0 : LOADING_EXIT_MS;
    window.setTimeout(function () {
      dom.loading_state.hidden = true;
      delete dom.loading_state.dataset.closing;
    }, delay);
  }

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function setLoadingMessage(msg) {
    if (!dom.loading_message) {
      dom.loading_state.textContent = msg;
      return;
    }
    dom.loading_message.textContent = msg;
    dom.loading_message.dataset.text = msg;
  }

  // --- Canvas setup ---
  function initCanvas() {
    if (!dom.graph_canvas) return;
    canvasCtx = dom.graph_canvas.getContext("2d");
    canvasBitmap = document.createElement("canvas");
    canvasBitmapCtx = canvasBitmap.getContext("2d");
    resizeCanvas();
  }

  function resizeCanvas() {
    if (!dom.graph_canvas || !canvasCtx) return;
    var rect = dom.canvas.getBoundingClientRect();
    canvasDpr = Math.min(window.devicePixelRatio || 1, VIEW.canvasMaxDpr);
    canvasCachePad = canvasCachePadForRect(rect);
    canvasViewportPad = Math.min(canvasCachePad, VIEW.canvasViewportPad);
    var cacheWidth = Math.max(1, Math.floor((rect.width + canvasCachePad * 2) * canvasDpr));
    var cacheHeight = Math.max(1, Math.floor((rect.height + canvasCachePad * 2) * canvasDpr));
    dom.graph_canvas.width = Math.max(1, Math.floor((rect.width + canvasViewportPad * 2) * canvasDpr));
    dom.graph_canvas.height = Math.max(1, Math.floor((rect.height + canvasViewportPad * 2) * canvasDpr));
    dom.graph_canvas.style.width = (rect.width + canvasViewportPad * 2) + "px";
    dom.graph_canvas.style.height = (rect.height + canvasViewportPad * 2) + "px";
    dom.graph_canvas.style.left = (-canvasViewportPad) + "px";
    dom.graph_canvas.style.top = (-canvasViewportPad) + "px";
    dom.graph_canvas.style.right = "auto";
    dom.graph_canvas.style.bottom = "auto";
    // The canvas DOM box is larger than the visible viewport and starts at
    // -canvasViewportPad. Its graph pixels are drawn with the real viewport
    // origin at (canvasViewportPad, canvasViewportPad), so zoom transforms must
    // pivot around that point. Otherwise the canvas nodes drift away from the
    // SVG text overlay whenever the active camera scale ratio is not 1.
    dom.graph_canvas.style.transformOrigin = canvasViewportPad + "px " + canvasViewportPad + "px";
    if (canvasBitmap && canvasBitmapCtx) {
      canvasBitmap.width = cacheWidth;
      canvasBitmap.height = cacheHeight;
    }
  }

  function canvasCachePadForRect(rect) {
    // The backing bitmap needs to cover likely drag distance, not just the
    // visible viewport. If this pad is too small the interaction path outruns
    // the cached pixels and the page exposes checkerboard-like empty chunks.
    var dynamicPad = Math.max(rect.width || 0, rect.height || 0) * 1.35;
    return Math.round(Math.max(VIEW.canvasCachePadMin, Math.min(VIEW.canvasCachePadMax, dynamicPad)));
  }

  // --- Data processing ---
  function processData() {
    nodes = (graphData.nodes || []).filter(function (n) {
      return n && n.id;
    });
    nodeById = new Map();
    adjacencyByNode = new Map();
    nodes.forEach(function (n) {
      nodeById.set(n.id, n);
      adjacencyByNode.set(n.id, []);
      n._displayName = displayNameForText(n.name || n.id);
    });
    edges = (graphData.edges || []).filter(function (e) {
      return e && e.fromId && e.toId && nodeById.has(e.fromId) && nodeById.has(e.toId);
    });
    edges.forEach(function (e) {
      adjacencyByNode.get(e.fromId).push(e);
      adjacencyByNode.get(e.toId).push(e);
    });

    assignDomainAndVisualGroups();
    buildVisualGroupNodeIndex();

    // Build skill-area list and color mapping. Raw graph domains remain on
    // node.domain, but the public map groups skill nodes into top-level areas
    // so users do not read every branch as a subfolder of Programming.
    var domainSet = {};
    nodes.forEach(function (n) {
      if (n.kind === "domain") return;
      var d = n._skillArea || n._visualGroup || n.domain || "Uncategorized";
      domainSet[d] = true;
    });
    domains = Object.keys(domainSet).sort(function (a, b) {
      return areaLayoutIndex(a) - areaLayoutIndex(b) || a.localeCompare(b);
    });
    var palette = [
      "--domain-1", "--domain-2", "--domain-3", "--domain-4",
      "--domain-5", "--domain-6", "--domain-7", "--domain-8",
    ];
    domainColorMap = {};
    domains.forEach(function (d, i) {
      var varName = palette[i % palette.length];
      domainColorMap[d] = "var(" + varName + ")";
    });

    // Resolve CSS custom property colors to concrete hex for canvas.
    // Canvas cannot use var(--domain-N), so we read computed styles once.
    resolveDomainColors();
  }

  function assignDomainAndVisualGroups() {
    var domainNamesById = new Map();
    nodes.forEach(function (node) {
      if (node.kind === "domain") {
        domainNamesById.set(node.id, node.name || node.domain || "Uncategorized");
        if (!node.domain) node.domain = node.name || "Uncategorized";
      }
    });

    // Public graph data normally carries node.domain, but older/debug graph
    // contracts may only expose taxonomy edges. Recover the same domain model
    // from parent_of domain edges so the viewer never collapses into one
    // accidental "Uncategorized" mass.
    edges.forEach(function (edge) {
      if ((edge.edgeType || "").toLowerCase() !== "parent_of") return;
      if (!domainNamesById.has(edge.fromId)) return;
      var child = nodeById.get(edge.toId);
      if (child && !child.domain) child.domain = domainNamesById.get(edge.fromId);
    });

    var groupCounts = {};
    nodes.forEach(function (node) {
      var group = visualGroupForNode(node);
      node._skillArea = group;
      node._visualGroup = group;
      node._displayName = displayNameForText(node.name || node.id);
      if (node.kind === "domain") return;
      groupCounts[group] = (groupCounts[group] || 0) + 1;
    });

    visualGroups = Object.keys(groupCounts).sort(function (a, b) {
      return areaLayoutIndex(a) - areaLayoutIndex(b) ||
        groupCounts[b] - groupCounts[a] ||
        a.localeCompare(b);
    });
  }

  function buildVisualGroupNodeIndex() {
    nodesByVisualGroup = new Map();
    nodes.forEach(function (node) {
      if (node.kind === "domain") return;
      var group = node._visualGroup || "General Craft";
      if (!nodesByVisualGroup.has(group)) nodesByVisualGroup.set(group, []);
      nodesByVisualGroup.get(group).push(node);
    });
    nodesByVisualGroup.forEach(function (groupNodes) {
      groupNodes.sort(compareTreeRank);
    });
  }

  function visualGroupForNode(node) {
    if (node.kind === "domain") return "Source Domains";
    var constellation = classifySkillConstellation(node);
    return constellation;
  }

  function classifySkillConstellation(node) {
    var text = ((node.name || "") + " " + (node.description || "") + " " + (node.domain || "")).toLowerCase();
    for (var i = 0; i < SKILL_CONSTELLATIONS.length; i += 1) {
      if (SKILL_CONSTELLATIONS[i].pattern.test(text)) return SKILL_CONSTELLATIONS[i].name;
    }
    return "General Craft";
  }

  function fallbackTopicShard(node, area) {
    var shardNames = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"];
    var shardCount = area === "General Craft" ? 6 : 3;
    var shard = Math.floor(seededUnit(node.id, 17) * shardCount);
    return shardNames[Math.min(shardNames.length - 1, shard)];
  }

  function areaLayoutIndex(area) {
    var idx = AREA_LAYOUT_ORDER.indexOf(area);
    return idx === -1 ? AREA_LAYOUT_ORDER.length : idx;
  }

  function branchTopicForNode(node) {
    if (node._branchTopic) return node._branchTopic;
    var area = node._visualGroup || node._skillArea || "General Craft";
    var baseArea = visualGroupDisplayName(area);
    var rules = BRANCH_TOPIC_RULES[baseArea] || BRANCH_TOPIC_RULES["General Craft"];
    var text = ((node.name || "") + " " + (node.description || "") + " " + (node.domain || "")).toLowerCase();
    for (var i = 0; i < rules.length; i += 1) {
      if (rules[i].pattern.test(text)) {
        node._branchTopic = rules[i].name;
        return node._branchTopic;
      }
    }
    node._branchTopic = baseArea === "General Craft" ?
      "Craft Foundations " + fallbackTopicShard(node, baseArea) :
      baseArea + " Practice " + fallbackTopicShard(node, baseArea);
    return node._branchTopic;
  }

  function displayNameForNode(node) {
    return node && (node._displayName || displayNameForText(node.name || node.id));
  }

  function displayNameForText(raw) {
    var text = String(raw || "").trim();
    if (!text) return "";
    if (shouldPreserveTechnicalLabel(text)) return text;
    var normalized = text
      .replace(/[_]+/g, " ")
      .replace(/([A-Za-z0-9])[-]+([A-Za-z0-9])/g, "$1 $2")
      .replace(/\\s+/g, " ")
      .trim();
    if (!normalized) return text;
    return normalized.split(" ").map(formatDisplayToken).join(" ");
  }

  function shouldPreserveTechnicalLabel(text) {
    if (/^@/.test(text)) return true;
    if (/^\\.[A-Za-z0-9]/.test(text)) return true;
    if (text.indexOf("/") !== -1) return true;
    if (/^GM_/.test(text)) return true;
    if (/^[a-z]\\d[-_]/.test(text)) return true;
    if (/^[a-z0-9]+(\\.[a-z0-9]+)+$/i.test(text)) return true;
    return false;
  }

  function formatDisplayToken(token) {
    if (!token) return token;
    var prefix = "";
    var suffix = "";
    var core = token;
    while (core && /^[([{]/.test(core.charAt(0))) {
      prefix += core.charAt(0);
      core = core.slice(1);
    }
    while (core && /[)\\]},.:;]$/.test(core)) {
      suffix = core.charAt(core.length - 1) + suffix;
      core = core.slice(0, -1);
    }
    if (!core) return prefix + suffix;
    var lower = core.toLowerCase();
    if (DISPLAY_TOKEN_CASE[lower]) return prefix + DISPLAY_TOKEN_CASE[lower] + suffix;
    if (/^[A-Z]{2,}$/.test(core)) return prefix + core + suffix;
    if (/^\\d/.test(core)) return prefix + core + suffix;
    return prefix + core.charAt(0).toUpperCase() + core.slice(1).toLowerCase() + suffix;
  }

  function resolveDomainColors() {
    if (!dom.graph_svg) return;
    var computed = getComputedStyle(document.documentElement);
    var palette = [
      "--domain-1", "--domain-2", "--domain-3", "--domain-4",
      "--domain-5", "--domain-6", "--domain-7", "--domain-8",
    ];
    var hexPalette = palette.map(function (v) {
      return computed.getPropertyValue(v).trim() || "#38796c";
    });
    resolvedDomainColors = {};
    domains.forEach(function (d, i) {
      resolvedDomainColors[d] = hexPalette[i % hexPalette.length];
    });
    resolvedVisualGroupColors = {};
    visualGroups.forEach(function (group, i) {
      resolvedVisualGroupColors[group] = VISUAL_GROUP_COLORS[i % VISUAL_GROUP_COLORS.length];
    });
  }

  // --- Layout (generated radial skill tree) ---
  function computeLayout() {
    var layoutNodes = getVisibleNodes();
    nodes.forEach(function (node) {
      node._isVisualKeystone = false;
    });

    var positions = {};
    var branchParents = {};
    var childrenByParent = {};
    var domainBBoxes = {};
    var treeNodes = [];
    var treeLinks = [];
    var bounds = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };

    var root = buildPresentationTree(layoutNodes);
    var totalNodes = Math.max(root._leafCount, 1);
    var densityExpansion = Math.max(0, Math.sqrt(totalNodes) - 22);
    var separation = viewSettings.separation;
    var areaRadius = (VIEW.treeAreaRadius + Math.min(230, Math.sqrt(totalNodes) * 4.8)) * separation;
    var topicRadius = areaRadius + (370 + Math.min(90, densityExpansion * 4.5)) * separation;
    var skillRadius = topicRadius + (300 + Math.min(150, densityExpansion * 7.5)) * separation;
    var totalWeight = root.children.reduce(function (sum, area) {
      return sum + area._layoutWeight;
    }, 0) || 1;
    var areaGap = angularGapForRadius(VIEW.treeAreaGapPx, skillRadius, root.children.length, Math.PI * 2);
    var availableAreaSpan = Math.max(Math.PI * 2 * 0.58, Math.PI * 2 - areaGap * root.children.length);
    var cursor = -Math.PI / 2 - Math.PI + areaGap / 2;

    placeTreeNode(root, { x: 0, y: 0, angle: -Math.PI / 2, radius: 0 });
    root.children.forEach(function (area) {
      var areaSpan = availableAreaSpan * area._layoutWeight / totalWeight;
      var areaStart = cursor;
      var areaEnd = cursor + areaSpan;
      var areaAngle = (areaStart + areaEnd) / 2;
      cursor = areaEnd + areaGap;
      layoutAreaBranch(area, areaStart, areaEnd, areaAngle, areaRadius, topicRadius, skillRadius);
    });

    if (!isFinite(bounds.minX)) {
      bounds = { minX: -100, minY: -100, maxX: 100, maxY: 100 };
    }
    layoutCache = {
      positions: positions,
      branchParents: branchParents,
      childrenByParent: childrenByParent,
      domainBBoxes: domainBBoxes,
      treeNodes: treeNodes,
      treeLinks: treeLinks,
      bounds: bounds,
      totalHeight: bounds.maxY - bounds.minY,
      totalWidth: bounds.maxX - bounds.minX,
      centerX: (bounds.minX + bounds.maxX) / 2,
      centerY: (bounds.minY + bounds.maxY) / 2,
    };
    return layoutCache;

    function placeTreeNode(node, point) {
      positions[node.id] = point;
      treeNodes.push(node);
      updateBoundsWithNode(bounds, point, node);
    }

    function connect(parent, child, area, depth) {
      branchParents[child.id] = parent.id;
      if (!childrenByParent[parent.id]) childrenByParent[parent.id] = [];
      childrenByParent[parent.id].push(child.id);
      treeLinks.push({
        fromId: parent.id,
        toId: child.id,
        area: area,
        depth: depth,
      });
    }

    function layoutAreaBranch(area, areaStart, areaEnd, areaAngle, areaRadius, topicRadius, skillRadius) {
      var areaPoint = {
        x: Math.cos(areaAngle) * areaRadius,
        y: Math.sin(areaAngle) * areaRadius * 0.92,
        angle: areaAngle,
        radius: areaRadius,
      };
      placeTreeNode(area, areaPoint);
      connect(root, area, area._visualGroup, 1);

      var groupBounds = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
      updateBoundsWithNode(groupBounds, areaPoint, area);
      var topics = area.children;
      var topicCount = Math.max(topics.length, 1);
      var topicSpan = Math.max(VIEW.treeTopicMinSpan * topicCount, (areaEnd - areaStart) * 0.94);
      topicSpan = Math.min(topicSpan, areaEnd - areaStart);
      var topicGap = angularGapForRadius(VIEW.treeTopicGapPx, skillRadius, topicCount, topicSpan);
      var topicSlices = weightedTopicSlices(topics, areaAngle, topicSpan, topicGap);
      topics.forEach(function (topic, topicIndex) {
        var topicSlice = topicSlices[topicIndex];
        var topicAngle = topicSlice.angle;
        topic._labelLane = topicLabelLane(topic, topicIndex, topicCount);
        topic._territoryLane = topicTerritoryLane(topicIndex, topicCount);
        var topicR = topicRadius +
          (topicIndex % 2 ? 28 : -18) * separation +
          (topic._territoryLane || 0) * VIEW.treeTopicTerritoryLaneGap * separation +
          (topic._breathing - 1) * 120 * separation +
          (topic._labelLane || 0) * VIEW.treeTopicRadialLaneGap * separation;
        var topicPoint = {
          x: Math.cos(topicAngle) * topicR,
          y: Math.sin(topicAngle) * topicR * 0.92,
          angle: topicAngle,
          radius: topicR,
        };
        placeTreeNode(topic, topicPoint);
        updateBoundsWithNode(groupBounds, topicPoint, topic);
        connect(area, topic, area._visualGroup, 2);
        layoutTopicLeaves(topic, topicAngle, topicSlice.span, skillRadius, topicR, groupBounds);
      });

      var pad = 110 * separation;
      if (!isFinite(groupBounds.minX)) {
        groupBounds = {
          minX: areaPoint.x - pad,
          minY: areaPoint.y - pad,
          maxX: areaPoint.x + pad,
          maxY: areaPoint.y + pad,
        };
      }
      domainBBoxes[area._visualGroup] = {
        x: groupBounds.minX - pad,
        y: groupBounds.minY - pad,
        width: Math.max(220, groupBounds.maxX - groupBounds.minX + pad * 2),
        height: Math.max(180, groupBounds.maxY - groupBounds.minY + pad * 2),
        centerX: areaPoint.x,
        centerY: areaPoint.y,
        originX: 0,
        originY: 0,
        labelY: areaPoint.y - treeNodeRadius(area) - 24,
        areaNodeId: area.id,
        baseDomain: area._visualGroup,
      };
    }

    function layoutTopicLeaves(topic, topicAngle, topicSpan, skillRadius, topicRadius, groupBounds) {
      var skills = topic.children;
      if (!skills.length) return;
      var breathing = topic._breathing || 1;
      var desiredLeafSpan = Math.max(
        topicSpan * VIEW.treeTopicInnerFill,
        VIEW.treeTopicMinSpan * Math.min(breathing, 1.35)
      );
      var leafSpan = Math.min(topicSpan * 0.82, desiredLeafSpan);
      var skillR = Math.max(
        skillRadius + (breathing - 1) * 96 * separation,
        topicRadius + VIEW.treeTopicSkillGap * separation
      );
      var laneMinPx = VIEW.treeSkillLaneMinPx * (1 + (breathing - 1) * 0.46);
      var laneCapacity = Math.max(
        4,
        Math.min(VIEW.treeSkillMaxLanes, Math.floor((leafSpan * skillR) / (laneMinPx * separation)))
      );
      var laneCount = Math.max(1, Math.min(laneCapacity, skills.length));
      var rowSpacing = VIEW.treeSkillRowSpacing * (1 + (breathing - 1) * 0.9);
      skills.forEach(function (skill, index) {
        var row = Math.floor(index / laneCount);
        var lane = index % laneCount;
        var angle = topicAngle - leafSpan / 2 + leafSpan * (lane + 0.5) / laneCount;
        angle += seededJitter(skill.id, 11) * Math.min(0.022, leafSpan / Math.max(laneCount, 1) * 0.18);
        var radius = skillR + row * rowSpacing * separation + (skill.level || 0) * 4 * separation;
        var point = {
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius * 0.92,
          angle: angle,
          radius: radius,
        };
        positions[skill.id] = point;
        updateBoundsWithNode(bounds, point, skill);
        updateBoundsWithNode(groupBounds, point, skill);
        connect(topic, skill, topic._visualGroup, 3);
      });
    }
  }

  function buildPresentationTree(layoutNodes) {
    var root = syntheticTreeNode("__tree_root__", "Microck", "tree-root", "", "");
    var byArea = {};
    layoutNodes.forEach(function (node) {
      if (node.kind === "domain") return;
      var areaName = node._visualGroup || "General Craft";
      if (!byArea[areaName]) {
        byArea[areaName] = syntheticTreeNode(
          "__tree_area__" + slugifySyntheticId(areaName),
          visualGroupDisplayName(areaName),
          "skill-area",
          areaName,
          ""
        );
        byArea[areaName]._topics = {};
      }
      var topicName = branchTopicForNode(node);
      node._branchTopic = topicName;
      var topicKey = topicName;
      if (!byArea[areaName]._topics[topicKey]) {
        byArea[areaName]._topics[topicKey] = syntheticTreeNode(
          "__tree_topic__" + slugifySyntheticId(areaName + "__" + topicName),
          topicName,
          "branch-topic",
          areaName,
          topicName
        );
      }
      byArea[areaName]._topics[topicKey].children.push(node);
    });

    root.children = Object.keys(byArea).map(function (areaName) {
      var area = byArea[areaName];
      area.children = Object.keys(area._topics).map(function (topicName) {
        var topic = area._topics[topicName];
        topic.children.sort(compareTreeRank);
        topic._leafCount = topic.children.length;
        if (topic.children[0]) topic.children[0]._isVisualKeystone = true;
        return topic;
      }).sort(compareTopicNodes);
      area._leafCount = area.children.reduce(function (sum, topic) {
        return sum + topic._leafCount;
      }, 0);
      area.children.forEach(function (topic) {
        topic._breathing = topicBreathingFactor(topic._leafCount);
        topic._labelWeight = topicLabelWeight(topic);
        topic._layoutWeight = topicLayoutWeight(topic);
      });
      area._breathing = areaBreathingFactor(area);
      area._weight = Math.max(3, Math.sqrt(area._leafCount) + area.children.length * 1.95);
      area._layoutWeight = area._weight * area._breathing;
      var firstTopic = area.children[0];
      if (firstTopic && firstTopic.children[0]) firstTopic.children[0]._isVisualKeystone = true;
      delete area._topics;
      return area;
    }).sort(compareAreaNodes);
    root._leafCount = root.children.reduce(function (sum, area) {
      return sum + area._leafCount;
    }, 0);
    return root;
  }

  function topicBreathingFactor(leafCount) {
    // Dense topics need actual geometric room, not just fewer labels. This
    // factor is computed once with the layout so pan/zoom stays a pure camera
    // transform and the user's mental map does not wobble.
    var crowding = Math.max(0, Math.sqrt(Math.max(leafCount || 0, 1)) - 3);
    return Math.min(VIEW.treeBreathingMax, 1 + crowding * 0.2);
  }

  function topicLabelWeight(topic) {
    var label = topic && (topic._displayName || topic.name) || "";
    var extra = Math.max(0, label.length - 14);
    return 1 + Math.min(0.9, extra * 0.035);
  }

  function topicLayoutWeight(topic) {
    return Math.max(1, Math.sqrt(topic._leafCount || 1)) *
      (topic._breathing || 1) *
      (topic._labelWeight || 1);
  }

  function areaBreathingFactor(area) {
    var topics = area.children || [];
    if (!topics.length) return 1;
    var maxTopicBreathing = topics.reduce(function (maxValue, topic) {
      return Math.max(maxValue, topic._breathing || 1);
    }, 1);
    var areaCrowding = Math.max(0, Math.sqrt(Math.max(area._leafCount || 0, 1)) - 8) * 0.046;
    return Math.min(
      VIEW.treeAreaBreathingMax,
      1 + (maxTopicBreathing - 1) * 0.76 + areaCrowding
    );
  }

  function topicLabelLane(topic, topicIndex, topicCount) {
    var label = topic && (topic._displayName || topic.name) || "";
    var needsLabelRoom = topicCount > 4 || label.length > 18 || (topic._breathing || 1) > 1.16;
    if (!needsLabelRoom) return 0;
    var lanes = [0, 1.1, 2.2, 3.25];
    return lanes[topicIndex % lanes.length];
  }

  function topicTerritoryLane(topicIndex, topicCount) {
    if (topicCount <= 1) return 0;
    var lanes = [0, 2, 4, 1, 3, 5];
    return lanes[topicIndex % lanes.length];
  }

  function angularGapForRadius(gapPx, radius, count, totalSpan) {
    if (count <= 1) return 0;
    var rawGap = gapPx / Math.max(radius, 1);
    var maxGap = totalSpan / Math.max(count * 2.6, 1);
    return Math.max(0, Math.min(rawGap, maxGap));
  }

  function weightedTopicSlices(topics, centerAngle, totalSpan, gap) {
    if (!topics.length) return [];
    var topicGap = gap || 0;
    var gapTotal = topicGap * Math.max(0, topics.length - 1);
    var usableSpan = Math.max(totalSpan * 0.42, totalSpan - gapTotal);
    var minSpan = Math.min(VIEW.treeTopicMinSpan, usableSpan / topics.length * 0.55);
    var reservedSpan = minSpan * topics.length;
    if (reservedSpan > usableSpan * 0.92) {
      minSpan = usableSpan * 0.92 / topics.length;
      reservedSpan = minSpan * topics.length;
    }
    var flexibleSpan = Math.max(0, usableSpan - reservedSpan);
    var totalWeight = topics.reduce(function (sum, topic) {
      return sum + (topic._layoutWeight || topicLayoutWeight(topic));
    }, 0) || topics.length;
    var coveredSpan = usableSpan + gapTotal;
    var cursor = centerAngle - coveredSpan / 2;
    return topics.map(function (topic) {
      var weight = topic._layoutWeight || topicLayoutWeight(topic);
      var span = minSpan + flexibleSpan * weight / totalWeight;
      var slice = {
        start: cursor,
        end: cursor + span,
        angle: cursor + span / 2,
        span: span,
      };
      cursor += span + topicGap;
      return slice;
    });
  }

  function syntheticTreeNode(id, name, kind, area, topic) {
    return {
      id: id,
      name: name,
      _displayName: name,
      kind: kind,
      _synthetic: true,
      _visualGroup: area,
      _skillArea: area,
      _branchTopic: topic,
      children: [],
      level: kind === "tree-root" ? 5 : kind === "skill-area" ? 4 : 3,
      confidence: 1,
      freshness: "active",
    };
  }

  function compareAreaNodes(a, b) {
    return areaLayoutIndex(a._visualGroup) - areaLayoutIndex(b._visualGroup) ||
      b._leafCount - a._leafCount ||
      a.name.localeCompare(b.name);
  }

  function compareTopicNodes(a, b) {
    return b._leafCount - a._leafCount ||
      a.name.localeCompare(b.name);
  }

  function slugifySyntheticId(text) {
    return String(text || "node").toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "node";
  }

  function updateBoundsWithNode(bounds, point, node) {
    var nodeExtent = (node._synthetic ? treeNodeRadius(node) : nodeRadius(node)) + 48;
    bounds.minX = Math.min(bounds.minX, point.x - nodeExtent);
    bounds.maxX = Math.max(bounds.maxX, point.x + nodeExtent);
    bounds.minY = Math.min(bounds.minY, point.y - nodeExtent);
    bounds.maxY = Math.max(bounds.maxY, point.y + nodeExtent);
  }

  function nodeImportance(node) {
    var evidenceCount = ((node.provenanceSummary || {}).evidenceCount || 0);
    var centrality = node.coreSelfCentrality || 0;
    return (node.featured ? 120 : 0) +
      (node.level || 0) * 14 +
      (node.confidence || 0) * 22 +
      centrality * 18 +
      Math.min(evidenceCount, 10);
  }

  function seededJitter(seed, salt) {
    return seededUnit(seed, salt) - 0.5;
  }

  function seededUnit(seed, salt) {
    var text = String(seed || "") + ":" + salt;
    var hash = 2166136261;
    for (var i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0) / 4294967295;
  }

  // --- Canvas node set ---
  // Obsidian-style canvas performance comes from keeping the bulk graph out of
  // the DOM and degrading detail, not from hiding graph glyphs. This set is the
  // canonical "drawn node" set: every filtered, uncollapsed node is included at
  // every zoom level. Labels and accessibility nodes are still capped elsewhere.
  function buildCanvasNodeSet(visibleNodeIds) {
    var drawable = new Set();
    visibleNodeIds.forEach(function (id) {
      var node = nodeById.get(id);
      if (!node) return;
      if (isNodeCollapsed(node)) return;
      drawable.add(id);
    });
    return drawable;
  }

  function edgeVisibleOnCanvas(edge, canvasNodeIds) {
    if (!canvasNodeIds.has(edge.fromId) || !canvasNodeIds.has(edge.toId)) return false;
    var fromNode = nodeById.get(edge.fromId);
    var toNode = nodeById.get(edge.toId);
    if (fromNode && isNodeCollapsed(fromNode)) return false;
    if (toNode && isNodeCollapsed(toNode)) return false;
    return true;
  }

  // --- Rendering ---
  function layoutAndRender() {
    computeLayout();
    refreshActiveFocusAfterLayout();
    renderGraph();
    renderMinimap();
    updateEmptyState();
  }

  function treeNodeRadius(node) {
    if (node.kind === "tree-root") return 32 * viewSettings.nodeScale;
    if (node.kind === "skill-area") return 22 * viewSettings.nodeScale;
    if (node.kind === "branch-topic") return 14 * viewSettings.nodeScale;
    return nodeRadius(node);
  }

  function nodeRadius(node) {
    // Level is the primary size signal. Keystone/featured status is shown with
    // rings and glow so lower-level notable nodes do not visually outrank L4/L5
    // mastery nodes by physical radius.
    var level = node.level || 0;
    return (VIEW.nodeBaseRadius + Math.max(0, Math.min(level, 5)) * VIEW.nodeLevelStep) * viewSettings.nodeScale;
  }

  function nodeDrawDetailState(node) {
    var isSelected = selectedNodeId === node.id;
    var isFocused = focusedNodeIds.has(node.id);
    var isLandmark = isSelected || isFocused || isKeystoneNode(node) || !!node.featured ||
      !!(filters.search && nodeMatchesSearch(node, filters.search));
    var viewScale = safeViewScale();
    return {
      isSelected: isSelected,
      isFocused: isFocused,
      isLandmark: isLandmark,
      lowDetail: viewScale < VIEW.detailZoomLow && !isLandmark,
      mediumDetail: viewScale < VIEW.detailZoomMedium && !isLandmark,
      viewScale: viewScale,
    };
  }

  function nodeVisualRadius(node) {
    var detail = nodeDrawDetailState(node);
    var viewScale = detail.viewScale;
    var drawR = Math.max(
      0.6 / Math.max(viewScale, 0.025),
      nodeRadius(node) * getDisplayScale(node.id)
    );
    var level = Math.max(0, Math.min(5, node.level || 0));
    if (detail.lowDetail) {
      return Math.max(
        (1.05 + level * 0.24) / viewScale,
        Math.min(drawR, (2.1 + level * 0.34) / viewScale)
      );
    }
    if (detail.mediumDetail) {
      return Math.max((2.2 + level * 0.3) / viewScale, drawR * 0.6);
    }
    return drawR;
  }

  function nodeColor(node) {
    return nodeColorHex(node);
  }

  function nodeColorHex(node) {
    if (node._visualGroup && resolvedVisualGroupColors[node._visualGroup]) {
      return resolvedVisualGroupColors[node._visualGroup];
    }
    return resolvedDomainColors[node.domain || "Uncategorized"] || "#38796c";
  }

  function confidenceRingClass(node) {
    var c = node.confidence || 0;
    if (c >= 0.75) return "ring--high";
    if (c >= 0.45) return "ring--medium";
    return "ring--low";
  }

  function isStale(node) {
    var f = (node.freshness || "").toLowerCase();
    return f === "stale" || f === "historical";
  }

  function isHistorical(node) {
    return (node.freshness || "").toLowerCase() === "historical";
  }

  function edgeStyle(edgeType) {
    var t = (edgeType || "related_to").toLowerCase();
    if (t === "parent_of" || t === "part_of") return "";
    if (t === "uses_tool" || t === "produces_artifact") return "3 3";
    if (t === "prerequisite_of") return "8 4";
    return "5 5"; // related_to, specializes, demonstrated_by
  }

  // renderGraph is the master render pass. It draws every filtered node glyph
  // plus bulk edges and skill labels to the canvas raster layer, then creates
  // SVG overlay elements only for domain labels, the capped accessible node set,
  // and focus-path highlighted edges.
  function renderGraph() {
    if (!layoutCache) return;
    focusDisplay = resolveFocusDisplay();
    var nodeSets = refreshVisibleNodeCaches();
    var canvasNodeIds = nodeSets.canvasNodeIds;
    var accessibleNodeIds = getAccessibleNodeIds(canvasNodeIds);

    renderDomainLabels();
    renderSvgEdges(canvasNodeIds);
    renderSvgNodes(canvasNodeIds, accessibleNodeIds);
    scheduleCanvasRedraw();
    applyViewTransform();
  }

  function refreshVisibleNodeCaches() {
    cachedVisibleNodeIds = getVisibleNodeIds();
    cachedCanvasNodeIds = buildCanvasNodeSet(cachedVisibleNodeIds);
    cachedCanvasNodes = Array.from(cachedCanvasNodeIds)
      .map(function (id) { return nodeById.get(id); })
      .filter(Boolean)
      .sort(function (a, b) {
        return (a.name || a.id || "").localeCompare(b.name || b.id || "");
      });
    return {
      visibleNodeIds: cachedVisibleNodeIds,
      canvasNodeIds: cachedCanvasNodeIds,
      canvasNodes: cachedCanvasNodes,
    };
  }

  function getCachedVisibleNodeIds() {
    if (!cachedVisibleNodeIds) refreshVisibleNodeCaches();
    return cachedVisibleNodeIds;
  }

  function getCachedCanvasNodeIds() {
    if (!cachedCanvasNodeIds) refreshVisibleNodeCaches();
    return cachedCanvasNodeIds;
  }

  function getCachedCanvasNodes() {
    if (!cachedCanvasNodes) refreshVisibleNodeCaches();
    return cachedCanvasNodes;
  }

  function emptyFocusDisplay() {
    return {
      active: false,
      points: new Map(),
      alphas: new Map(),
      scales: new Map(),
      hitPriority: new Map(),
      z: new Map(),
      focusIds: new Set(),
      quietIds: new Set(),
      labelIds: new Set(),
    };
  }

  function refreshActiveFocusAfterLayout() {
    if (!layoutCache || !activeFocus) return;
    if (activeFocus.kind === "domain") {
      activeFocus = buildDomainFocus(activeFocus.domain);
    } else if (activeFocus.kind === "node") {
      activeFocus = buildNodeFocus(activeFocus.targetId);
    } else if (activeFocus.kind === "tree") {
      activeFocus = buildTreeFocus(activeFocus.targetId);
    }
    focusDisplayTo = buildFocusDisplayState(activeFocus);
    focusDisplay = focusDisplayTo;
  }

  function startFocusTransition(nextDisplay, animated) {
    focusAnimationToken += 1;
    if (focusAnimationFrame) {
      cancelAnimationFrame(focusAnimationFrame);
      focusAnimationFrame = null;
    }
    if (focusQuietClassFrame) {
      cancelAnimationFrame(focusQuietClassFrame);
      focusQuietClassFrame = null;
    }
    if (focusLabelRefreshTimer) {
      clearTimeout(focusLabelRefreshTimer);
      focusLabelRefreshTimer = null;
    }
    focusDisplayFrom = focusDisplay || focusDisplayTo || emptyFocusDisplay();
    focusDisplayTo = nextDisplay || emptyFocusDisplay();
    if (!animated || prefersReducedMotion()) {
      focusDisplay = focusDisplayTo;
      renderGraph();
      return;
    }

    // Commit focus state to both layers before any camera tween can reuse the
    // retained canvas bitmap. If SVG hit targets move to the new focus display
    // while canvas pixels remain at the old positions, hover appears correct
    // but the visible graph looks offset during zoom/pan.
    focusDisplay = focusDisplayTo;
    renderFocusFrame(true);
    scheduleSettledFocusLabels();
  }

  function resolveFocusDisplay() {
    if (focusAnimationFrame) return focusDisplay || focusDisplayFrom || emptyFocusDisplay();
    return focusDisplayTo || emptyFocusDisplay();
  }

  function interpolateFocusDisplay(fromState, toState, t) {
    var state = emptyFocusDisplay();
    state.active = !!(toState && toState.active);
    state.focusIds = new Set((toState && toState.focusIds) || []);
    state.quietIds = new Set((toState && toState.quietIds) || []);
    state.labelIds = new Set((toState && toState.labelIds) || []);
    var ids = new Set();
    collectFocusDisplayIds(ids, fromState);
    collectFocusDisplayIds(ids, toState);
    ids.forEach(function (id) {
      var fromPoint = pointInFocusState(fromState, id);
      var toPoint = pointInFocusState(toState, id);
      if (fromPoint && toPoint) {
        state.points.set(id, {
          x: lerp(fromPoint.x, toPoint.x, t),
          y: lerp(fromPoint.y, toPoint.y, t),
        });
      }
      state.alphas.set(id, lerp(alphaInFocusState(fromState, id), alphaInFocusState(toState, id), t));
      state.scales.set(id, lerp(scaleInFocusState(fromState, id), scaleInFocusState(toState, id), t));
      state.hitPriority.set(id, lerp(hitPriorityInFocusState(fromState, id), hitPriorityInFocusState(toState, id), t));
      state.z.set(id, lerp(zInFocusState(fromState, id), zInFocusState(toState, id), t));
    });
    return state;
  }

  function collectFocusDisplayIds(ids, state) {
    if (!state) return;
    [state.points, state.alphas, state.scales, state.hitPriority, state.z].forEach(function (map) {
      if (!map) return;
      map.forEach(function (_value, id) { ids.add(id); });
    });
    if (state.focusIds) state.focusIds.forEach(function (id) { ids.add(id); });
  }

  function pointInFocusState(state, id) {
    if (state && state.points && state.points.has(id)) return state.points.get(id);
    return layoutCache && layoutCache.positions ? layoutCache.positions[id] : null;
  }

  function alphaInFocusState(state, id) {
    return state && state.alphas && state.alphas.has(id) ? state.alphas.get(id) : 1;
  }

  function scaleInFocusState(state, id) {
    return state && state.scales && state.scales.has(id) ? state.scales.get(id) : 1;
  }

  function hitPriorityInFocusState(state, id) {
    return state && state.hitPriority && state.hitPriority.has(id) ? state.hitPriority.get(id) : 1;
  }

  function zInFocusState(state, id) {
    return state && state.z && state.z.has(id) ? state.z.get(id) : 0;
  }

  function getDisplayPoint(id) {
    var state = focusDisplay || emptyFocusDisplay();
    if (state.points && state.points.has(id)) return state.points.get(id);
    return layoutCache && layoutCache.positions ? layoutCache.positions[id] : null;
  }

  function getDisplayAlpha(id) {
    var state = focusDisplay || emptyFocusDisplay();
    var value = state.alphas && state.alphas.has(id) ? state.alphas.get(id) : 1;
    if (value === 1 && state.active && !(state.focusIds && state.focusIds.has(id))) {
      value = viewSettings.contextDimming;
    }
    return Math.max(0, Math.min(1, value));
  }

  function getDisplayScale(id) {
    var state = focusDisplay || emptyFocusDisplay();
    var value = state.scales && state.scales.has(id) ? state.scales.get(id) : 1;
    return Math.max(0.12, Math.min(1.4, value));
  }

  function getHitPriority(id) {
    var state = focusDisplay || emptyFocusDisplay();
    var value = state.hitPriority && state.hitPriority.has(id) ? state.hitPriority.get(id) : 1;
    if (value === 1 && state.active && !(state.focusIds && state.focusIds.has(id))) {
      value = 0.62;
    }
    return Math.max(0.08, value);
  }

  function getDisplayZ(id) {
    var state = focusDisplay || emptyFocusDisplay();
    return state.z && state.z.has(id) ? state.z.get(id) : 0;
  }

  function isFocusQuieted(id) {
    var state = focusDisplay || emptyFocusDisplay();
    return !!(state.active && !(state.focusIds && state.focusIds.has(id)));
  }

  function renderFocusFrame(redrawCanvas) {
    applyFocusDisplayToSvg();
    if (redrawCanvas !== false) renderCanvas();
    renderMinimapViewport();
  }

  function applyFocusDisplayToSvg() {
    if (!layoutCache) return;
    domainLabelElements.forEach(function (el, domain) {
      var selected = !!(activeFocus && activeFocus.kind === "domain" && activeFocus.domain === domain);
      el.classList.toggle("selected", selected);
      el.setAttribute("aria-pressed", String(selected));
    });
    focusSvgUpdateIds().forEach(function (id) {
      var el = svgNodeElements.get(id);
      if (!el) return;
      updateFocusNodeElement(el, id);
    });
    svgEdgeElements.forEach(function (edge) {
      var el = edge.el;
      var fromId = edge.fromId;
      var toId = edge.toId;
      var from = getDisplayPoint(fromId);
      var to = getDisplayPoint(toId);
      if (!from || !to) return;
      el.setAttribute("d", straightPath(from, to));
      el.style.opacity = String(0.96 * Math.min(getDisplayAlpha(fromId), getDisplayAlpha(toId)));
    });
  }

  function focusSvgUpdateIds() {
    var state = focusDisplay || emptyFocusDisplay();
    if (!state.active) return new Set(svgNodeElements.keys());
    var ids = new Set();
    [state.points, state.alphas, state.scales, state.z].forEach(function (map) {
      if (!map) return;
      map.forEach(function (_value, id) { ids.add(id); });
    });
    if (state.focusIds) state.focusIds.forEach(function (id) { ids.add(id); });
    if (state.labelIds) state.labelIds.forEach(function (id) { ids.add(id); });
    focusedNodeIds.forEach(function (id) { ids.add(id); });
    if (selectedNodeId) ids.add(selectedNodeId);
    return ids;
  }

  function updateFocusNodeElement(el, id) {
    var point = getDisplayPoint(id);
    if (!point) return;
    var scale = getDisplayScale(id);
    el.setAttribute("transform", "translate(" + point.x + "," + point.y + ") scale(" + scale + ")");
    el.style.opacity = String(getDisplayAlpha(id));
    updateNodeOverlayRadii(el, id);
    el.classList.toggle("selected", selectedNodeId === id);
    el.classList.toggle("focused", focusedNodeIds.has(id));
    el.classList.toggle("quieted", isFocusQuieted(id));
  }

  function syncFocusQuietClasses() {
    var entries = Array.from(svgNodeElements.entries());
    var index = 0;
    var token = focusAnimationToken;

    function step() {
      if (token !== focusAnimationToken) return;
      var end = Math.min(entries.length, index + 56);
      for (; index < end; index += 1) {
        var id = entries[index][0];
        var el = entries[index][1];
        el.classList.toggle("quieted", isFocusQuieted(id));
      }
      if (index < entries.length) {
        focusQuietClassFrame = requestAnimationFrame(step);
        return;
      }
      focusQuietClassFrame = null;
    }

    focusQuietClassFrame = requestAnimationFrame(step);
  }

  function scheduleSettledFocusLabels() {
    if (focusLabelRefreshTimer) clearTimeout(focusLabelRefreshTimer);
    focusLabelRefreshTimer = setTimeout(function () {
      focusLabelRefreshTimer = null;
      scheduleSettledCanvasRedraw(0);
    }, 120);
  }

  function setFocusCanvasPreview(active) {
    if (!dom.graph_canvas) return;
    dom.graph_canvas.style.opacity = "";
  }

  function buildNodeFocus(id) {
    var node = nodeById.get(id);
    if (!node) return null;
    var ids = computeFocusPath(id);
    connectedNodeSuggestions(node, 10).forEach(function (item) {
      ids.add(item.node.id);
    });
    ids.add(id);
    var labelIds = new Set();
    Array.from(ids)
      .filter(function (nodeId) { return !!(layoutCache && layoutCache.positions[nodeId]); })
      .slice(0, VIEW.maxFocusLabels)
      .forEach(function (nodeId) { labelIds.add(nodeId); });
    return {
      kind: "node",
      targetId: id,
      title: displayNameForNode(node),
      nodeIds: ids,
      labelIds: labelIds,
      allCount: ids.size,
      shownCount: labelIds.size,
      shelfRows: [],
    };
  }

  function buildDomainFocus(domain) {
    var matching = (nodesByVisualGroup.get(domain) || []).filter(function (node) {
      return !isNodeCollapsed(node);
    });
    var visibleNodeIds = getCachedVisibleNodeIds();
    var displayable = matching.filter(function (node) {
      return visibleNodeIds.has(node.id) && !!(layoutCache && layoutCache.positions[node.id]);
    });
    var focusIds = new Set(displayable.map(function (node) { return node.id; }));
    var labelIds = new Set();
    displayable.slice(0, VIEW.maxFocusLabels).forEach(function (node) {
      labelIds.add(node.id);
    });
    return {
      kind: "domain",
      domain: domain,
      title: visualGroupDisplayName(domain),
      nodeIds: focusIds,
      labelIds: labelIds,
      allCount: matching.length,
      shownCount: displayable.length,
      shelfRows: displayable.slice(0, VIEW.maxFocusShelfRows),
    };
  }

  function buildTreeFocus(id) {
    var treeNode = getSyntheticTreeNode(id);
    if (!treeNode) return null;
    if (treeNode.kind === "skill-area" && treeNode._visualGroup) {
      var areaFocus = buildDomainFocus(treeNode._visualGroup);
      areaFocus.kind = "tree";
      areaFocus.targetId = id;
      areaFocus.title = treeNode._displayName || treeNode.name || areaFocus.title;
      areaFocus.nodeIds.add(id);
      return areaFocus;
    }
    var matching = collectTreeFocusNodes(treeNode).filter(function (node) {
      return !isNodeCollapsed(node);
    });
    var visibleNodeIds = getCachedVisibleNodeIds();
    var displayable = matching.filter(function (node) {
      return visibleNodeIds.has(node.id) && !!(layoutCache && layoutCache.positions[node.id]);
    });
    var focusIds = new Set(displayable.map(function (node) { return node.id; }));
    focusIds.add(id);
    var labelIds = new Set();
    displayable.slice(0, VIEW.maxFocusLabels).forEach(function (node) {
      labelIds.add(node.id);
    });
    return {
      kind: "tree",
      targetId: id,
      title: treeNode._displayName || treeNode.name || "Selection",
      nodeIds: focusIds,
      labelIds: labelIds,
      allCount: matching.length,
      shownCount: displayable.length,
      shelfRows: displayable.slice(0, VIEW.maxFocusShelfRows),
    };
  }

  function getSyntheticTreeNode(id) {
    if (!layoutCache || !id) return null;
    return (layoutCache.treeNodes || []).find(function (node) {
      return node && node._synthetic && node.id === id;
    }) || null;
  }

  function collectTreeFocusNodes(treeNode) {
    var collected = [];
    function visit(node) {
      if (!node) return;
      if (node._synthetic) {
        (node.children || []).forEach(visit);
        return;
      }
      if (nodeById.has(node.id)) collected.push(node);
    }
    visit(treeNode);
    return collected.sort(compareTreeRank);
  }

  function buildFocusDisplayState(focus) {
    var state = emptyFocusDisplay();
    if (!focus || !layoutCache) return state;
    state.active = true;
    state.focusIds = new Set(focus.nodeIds || []);
    state.labelIds = new Set(focus.labelIds || []);
    if (focus.kind === "node" && ENABLE_NODE_CONSTELLATION_FOCUS) {
      var pocketPoints = buildNodeFocusPocketPoints(focus);
      pocketPoints.forEach(function (point, id) {
        state.points.set(id, point);
      });
    }
    state.focusIds.forEach(function (id) {
      state.alphas.set(id, 1);
      state.scales.set(id, 1);
      state.hitPriority.set(id, 1.8);
      state.z.set(id, 20);
    });
    if (focus.kind === "node" && focus.targetId) {
      state.scales.set(focus.targetId, 1.18);
      state.hitPriority.set(focus.targetId, 2.4);
      state.z.set(focus.targetId, 42);
    }
    return state;
  }

  function buildNodeFocusPocketPoints(focus) {
    var points = new Map();
    if (!focus || !focus.targetId || !layoutCache || !layoutCache.positions) return points;
    var targetPoint = layoutCache.positions[focus.targetId];
    if (!targetPoint) return points;

    var focusIds = new Set(focus.nodeIds || []);
    var basis = focusPocketBasis(targetPoint);
    points.set(focus.targetId, focusPocketDisplayPoint(targetPoint.x, targetPoint.y));

    var topicId = layoutCache.branchParents[focus.targetId];
    if (topicId && focusIds.has(topicId)) {
      points.set(topicId, focusPocketOffsetPoint(
        targetPoint,
        basis.inward,
        basis.tangent,
        VIEW.focusPocketAncestorGap,
        -VIEW.focusPocketAncestorTangentGap * 0.35
      ));
    }

    var siblingIds = (layoutCache.childrenByParent[topicId] || []).filter(function (id) {
      return id !== focus.targetId && focusIds.has(id) && nodeById.has(id);
    });
    var siblingSet = new Set(siblingIds);
    var suggestionIds = Array.from(focusIds).filter(function (id) {
      return id !== focus.targetId &&
        nodeById.has(id) &&
        !siblingSet.has(id);
    });

    placeFocusPocketNodes(
      points,
      siblingIds,
      targetPoint,
      basis,
      VIEW.focusPocketSiblingRadius,
      VIEW.focusPocketSpiralStep,
      0.35
    );
    placeFocusPocketNodes(
      points,
      suggestionIds,
      targetPoint,
      basis,
      VIEW.focusPocketSuggestionRadius,
      VIEW.focusPocketSpiralStep * 1.12,
      1.55
    );
    return points;
  }

  function focusPocketBasis(point) {
    var outward = normalizeVector(point.x, point.y);
    if (Math.abs(outward.x) + Math.abs(outward.y) < 0.001) {
      outward = { x: 0, y: -1 };
    }
    return {
      outward: outward,
      inward: { x: -outward.x, y: -outward.y },
      tangent: { x: -outward.y, y: outward.x },
    };
  }

  function focusPocketOffsetPoint(origin, radial, tangent, radialOffset, tangentOffset) {
    return focusPocketDisplayPoint(
      origin.x + radial.x * radialOffset + tangent.x * tangentOffset,
      origin.y + radial.y * radialOffset + tangent.y * tangentOffset
    );
  }

  function placeFocusPocketNodes(points, ids, origin, basis, baseRadius, radiusStep, angleOffset) {
    ids.forEach(function (id, index) {
      if (points.has(id)) return;
      var radius = baseRadius + Math.sqrt(index) * radiusStep;
      var angle = angleOffset + index * 2.399963229728653 + seededJitter(id, 71) * 0.18;
      var radialOffset = Math.cos(angle) * radius;
      var tangentOffset = Math.sin(angle) * radius;
      points.set(id, focusPocketOffsetPoint(origin, basis.outward, basis.tangent, radialOffset, tangentOffset));
    });
  }

  function focusPocketDisplayPoint(x, y) {
    return {
      x: x,
      y: y,
      angle: Math.atan2(y / 0.92, x),
      radius: Math.hypot(x, y / 0.92),
    };
  }

  function normalizeVector(x, y) {
    var length = Math.hypot(x, y);
    if (!Number.isFinite(length) || length <= 0.0001) return { x: 0, y: 0 };
    return { x: x / length, y: y / length };
  }

  function buildFocusProtectedBoxes(focus) {
    var boxes = [];
    var ids = focus.labelIds && focus.labelIds.size ? focus.labelIds : focus.nodeIds;
    ids.forEach(function (id) {
      var node = nodeById.get(id);
      var p = layoutCache.positions[id];
      if (!node || !p) return;
      boxes.push(nodeLabelProtectionBox(node, p));
    });
    return boxes;
  }

  function nodeLabelProtectionBox(node, p) {
    var r = nodeRadius(node);
    var label = displayNameForNode(node);
    var labelWidth = Math.min(220, Math.max(58, label.length * 6.4)) + 28;
    var halfWidth = Math.max(labelWidth / 2, r + 16);
    var top = p.y - r - 16;
    var bottom = p.y + r + 38;
    return {
      minX: p.x - halfWidth,
      maxX: p.x + halfWidth,
      minY: top,
      maxY: bottom,
      cx: p.x,
      cy: (top + bottom) / 2,
    };
  }

  function nodeClearanceBox(node, p, scale) {
    var r = nodeRadius(node) * (scale || 1) + 8;
    return {
      minX: p.x - r,
      maxX: p.x + r,
      minY: p.y - r,
      maxY: p.y + r,
      cx: p.x,
      cy: p.y,
    };
  }

  function nearestClearance(point, boxes) {
    var best = null;
    boxes.forEach(function (box) {
      var margin = 24;
      if (point.x < box.minX - margin || point.x > box.maxX + margin ||
          point.y < box.minY - margin || point.y > box.maxY + margin) {
        return;
      }
      var dx = point.x - box.cx;
      var dy = point.y - box.cy;
      var dist = Math.max(1, Math.hypot(dx, dy));
      var overlapX = Math.max(0, Math.min(point.x - (box.minX - margin), (box.maxX + margin) - point.x));
      var overlapY = Math.max(0, Math.min(point.y - (box.minY - margin), (box.maxY + margin) - point.y));
      var overlap = Math.min(overlapX, overlapY);
      var score = overlap + 80 / dist;
      if (!best || score > best.score) {
        best = { box: box, dx: dx / dist, dy: dy / dist, score: score };
      }
    });
    return best;
  }

  function clearanceSlotPoint(node, point, clearance, occupied) {
    var baseAngle = Math.atan2(clearance.dy, clearance.dx);
    if (!Number.isFinite(baseAngle)) {
      baseAngle = seededUnit(node.id, 29) * Math.PI * 2;
    }
    var step = Math.PI / 6;
    for (var rIndex = 0; rIndex < VIEW.focusClearanceRadii.length; rIndex += 1) {
      var radius = Math.min(VIEW.focusClearanceMaxMove, VIEW.focusClearanceRadii[rIndex]);
      for (var slot = 0; slot < 12; slot += 1) {
        var side = slot % 2 === 0 ? 1 : -1;
        var turns = Math.ceil(slot / 2);
        var angle = baseAngle + side * turns * step + seededJitter(node.id, slot + 31) * 0.1;
        var candidate = {
          x: point.x + Math.cos(angle) * radius,
          y: point.y + Math.sin(angle) * radius,
        };
        if (!boxIntersectsAny(nodeClearanceBox(node, candidate, VIEW.focusQuietScale), occupied)) {
          return candidate;
        }
      }
    }
    return {
      x: point.x + clearance.dx * VIEW.focusClearanceMaxMove,
      y: point.y + clearance.dy * VIEW.focusClearanceMaxMove,
    };
  }

  function boxIntersectsAny(box, boxes) {
    return boxes.some(function (other) {
      return box.minX <= other.maxX &&
        box.maxX >= other.minX &&
        box.minY <= other.maxY &&
        box.maxY >= other.minY;
    });
  }

  // --- Canvas raster rendering (the performance layer) ---
  function renderCanvas() {
    if (!canvasCtx || !layoutCache) return;
    bumpViewerMetric("renderCanvas");
    sanitizeViewState();
    var ctx = canvasBitmapCtx || canvasCtx;
    var pos = layoutCache.positions;
    var w = canvasBitmap ? canvasBitmap.width : dom.graph_canvas.width;
    var h = canvasBitmap ? canvasBitmap.height : dom.graph_canvas.height;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    // Apply DPR + view transform so graph coords map directly to canvas pixels.
    ctx.setTransform(
      safeViewScale() * canvasDpr, 0, 0,
      safeViewScale() * canvasDpr,
      (viewState.x + canvasCachePad) * canvasDpr,
      (viewState.y + canvasCachePad) * canvasDpr
    );

    var bounds = getGraphViewportBounds(VIEW.canvasEdgeCullPad + canvasCachePad);
    var canvasNodeIds = getCachedCanvasNodeIds();
    renderedSyntheticLabelBoxes = [];

    // --- Presentation tree scaffold (before skill nodes) ---
    // Keep the surrounding constellation visible during focus. Performance
    // optimizations must come from caching/deferred work, not hiding context.
    if (viewSettings.showCategories) {
      renderTreeAreaGlows(ctx, bounds);
    }
    if (viewSettings.showLines) {
      renderZoomBranchLinks(ctx, bounds, canvasNodeIds);
    }
    if (viewSettings.showCategories) {
      renderSyntheticTreeNodes(ctx, bounds);
    }

    // --- Draw edges ---
    ctx.lineWidth = 1 / safeViewScale();
    ctx.lineCap = "round";

    if (viewSettings.showLines && selectedNodeId) {
      edges.forEach(function (edge) {
        if (!edgeVisibleOnCanvas(edge, canvasNodeIds)) return;
        if (!selectedEdgeVisibleInFocusPocket(edge)) return;

        var from = getDisplayPoint(edge.fromId);
        var to = getDisplayPoint(edge.toId);
        if (!from || !to) return;

        if (edge.fromId !== selectedNodeId && edge.toId !== selectedNodeId) return;

        // Viewport cull: skip edges whose midpoint is far outside view.
        var midX = (from.x + to.x) / 2;
        var midY = (from.y + to.y) / 2;
        if (midX < bounds.minX || midX > bounds.maxX ||
            midY < bounds.minY || midY > bounds.maxY) {
          // Still draw if one endpoint is in view (long edges spanning viewport).
          if (!pointInBounds(from, bounds) && !pointInBounds(to, bounds)) return;
        }

        ctx.strokeStyle = "#4fb39e";
        ctx.lineWidth = (2.2 * Math.sqrt(viewSettings.lineStrength)) / safeViewScale();
        ctx.globalAlpha = Math.min(
          1,
          0.96 * viewSettings.lineStrength * Math.min(getDisplayAlpha(edge.fromId), getDisplayAlpha(edge.toId))
        );

        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();
      });
    }

    ctx.globalAlpha = 1;

    // --- Draw nodes ---
    getCanvasDrawNodes().forEach(function (node) {
      var p = getDisplayPoint(node.id);
      if (!p) return;
      if (!canvasNodeIds.has(node.id)) return;
      if (isNodeCollapsed(node)) return;

      var color = nodeColorHex(node);
      var detail = nodeDrawDetailState(node);
      var isSelected = detail.isSelected;
      var isFocused = detail.isFocused;
      var viewScale = detail.viewScale;
      var lowDetail = detail.lowDetail;
      var mediumDetail = detail.mediumDetail;
      var stale = isStale(node);
      var displayAlpha = getDisplayAlpha(node.id);
      var drawR = nodeVisualRadius(node);

      // Glow for selected/focused nodes.
      if (isSelected || isFocused) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, drawR + 12, 0, Math.PI * 2);
        var grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, drawR + 12);
        grad.addColorStop(0, "rgba(56, 121, 108, 0.32)");
        grad.addColorStop(1, "rgba(56, 121, 108, 0)");
        ctx.fillStyle = grad;
        ctx.fill();
      }

      // Node fill.
      ctx.globalAlpha = displayAlpha * (lowDetail ? (stale ? 0.24 : 0.68) : (stale ? 0.5 : 1));
      ctx.beginPath();
      ctx.arc(p.x, p.y, drawR, 0, Math.PI * 2);
      ctx.fillStyle = lowDetail ? color : "#141416";
      ctx.fill();

      if (lowDetail) {
        ctx.globalAlpha = 1;
        return;
      }

      // Confidence ring stroke (domain color).
      ctx.lineWidth = (isSelected ? 2.6 : 1.7) / viewState.scale;
      ctx.strokeStyle = color;
      ctx.stroke();

      // Inner dot.
      if (!lowDetail) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(5 / viewScale, drawR * 0.42), 0, Math.PI * 2);
        ctx.fillStyle = "rgba(56, 121, 108, 0.14)";
        ctx.fill();
      }

      ctx.globalAlpha = 1;

      // Level text (only when zoomed in enough).
      if (viewSettings.showLevelBadges && !mediumDetail && viewScale >= VIEW.detailZoomMedium) {
        ctx.fillStyle = "#ece9e0";
        ctx.globalAlpha = displayAlpha * (stale ? 0.5 : 0.9);
        ctx.font = "650 " + canvasLevelTextFontSize(drawR) + "px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("L" + (node.level || 0), p.x, p.y);
        ctx.globalAlpha = 1;
      }

      // Keystone/featured ring. This is emphasis only; radius remains level-driven.
      if ((isKeystoneNode(node) || node.featured) && !lowDetail) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, drawR + 9, 0, Math.PI * 2);
        ctx.strokeStyle = "#38796c";
        ctx.lineWidth = 1.2 / viewScale;
        ctx.setLineDash([2 / viewScale, 5 / viewScale]);
        ctx.globalAlpha = 0.75 * displayAlpha;
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      }

      // Search match highlight.
      if (filters.search && nodeMatchesSearch(node, filters.search)) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, drawR, 0, Math.PI * 2);
        ctx.strokeStyle = "#4fb39e";
        ctx.lineWidth = 3 / viewScale;
        ctx.stroke();
      }
    });

    renderCanvasSkillLabels(ctx, canvasNodeIds);

    ctx.globalAlpha = 1;
    renderedCanvasViewState = {
      x: viewState.x,
      y: viewState.y,
      scale: viewState.scale,
    };
    blitCanvasBitmapCache();
    if (dom.graph_canvas) dom.graph_canvas.style.opacity = "";
    resetCanvasBitmapTransform();
    updateSvgNodeOverlayGeometry();
  }

  function getCanvasDrawNodes() {
    var nodesForCanvas = getCachedCanvasNodes();
    var state = focusDisplay || emptyFocusDisplay();
    if (!(state.active && state.focusIds && state.focusIds.size)) return nodesForCanvas;
    var contextNodes = [];
    var focusNodes = [];
    nodesForCanvas.forEach(function (node) {
      if (state.focusIds.has(node.id)) {
        focusNodes.push(node);
      } else {
        contextNodes.push(node);
      }
    });
    return contextNodes.concat(focusNodes);
  }

  function renderCanvasSkillLabels(ctx, canvasNodeIds) {
    if (!layoutCache || !viewSettings.showSkillLabels) return;
    var candidates = [];
    canvasNodeIds.forEach(function (id) {
      var node = nodeById.get(id);
      if (!node) return;
      if (!skillLabelVisibleAtCurrentScale(node)) return;
      var p = getDisplayPoint(node.id);
      if (!p) return;
      if (isNodeCollapsed(node)) return;
      candidates.push({ node: node, point: p, score: persistentLabelPriority(node) });
    });

    candidates.sort(function (a, b) {
      return b.score - a.score || displayNameForNode(a.node).localeCompare(displayNameForNode(b.node));
    });

    var activeLabelCap = focusDisplay && focusDisplay.active ?
      Math.max(VIEW.maxFocusLabels, (focusDisplay.labelIds && focusDisplay.labelIds.size) || 0) :
      VIEW.maxNodeLabels;
    var maxLabels = maxRenderedNodeLabels(activeLabelCap);
    var occupied = canvasReservedLabelBoxes();
    ctx.save();
    candidates.some(function (item, index) {
      if (index >= maxLabels && !labelMustRender(item.node)) return true;
      var placement = canvasSkillLabelPlacement(ctx, item.node, item.point, occupied);
      if (!placement) return false;
      drawCanvasSkillLabel(ctx, placement);
      occupied.push(placement.box);
      return false;
    });
    ctx.restore();
  }

  function canvasReservedLabelBoxes() {
    if (!layoutCache || !viewSettings.showCategories || !viewSettings.showCategoryLabels) return [];
    return renderedSyntheticLabelBoxes.slice();
  }

  function canvasSkillLabelPlacement(ctx, node, point, occupied) {
    var descriptor = canvasSkillLabelDescriptor(ctx, node, point);
    var candidates = canvasSkillLabelCandidates(node, point, descriptor);
    for (var i = 0; i < candidates.length; i += 1) {
      if (!boxIntersectsAny(candidates[i].box, occupied)) {
        return candidates[i];
      }
    }
    if (labelCanForceRender(node) && candidates.length) {
      candidates[0].forced = true;
      return candidates[0];
    }
    return null;
  }

  function canvasSkillLabelDescriptor(ctx, node, point) {
    var r = nodeRadius(node) * getDisplayScale(node.id);
    var displayAlpha = Math.max(0.2, getDisplayAlpha(node.id));
    var isMuted = !labelMustRender(node) && !isKeystoneNode(node);
    var fontPx = canvasSkillLabelGraphPx(node);
    var text = truncate(displayNameForNode(node), 24);
    var font = "550 " + fontPx + "px " + canvasLabelFontFamily();
    ctx.font = font;
    var measuredWidth = ctx.measureText(text).width;
    return {
      node: node,
      point: point,
      text: text,
      font: font,
      fontPx: fontPx,
      width: measuredWidth,
      height: fontPx * 1.15,
      radius: r,
      displayAlpha: displayAlpha,
      isMuted: isMuted,
    };
  }

  function canvasSkillLabelCandidates(node, point, descriptor) {
    var angle = Number.isFinite(point.angle) ? point.angle : Math.atan2(point.y / 0.92, point.x);
    var radial = normalizedLabelVector(Math.cos(angle), Math.sin(angle) * 0.92);
    var tangent = normalizedLabelVector(-radial.y, radial.x);
    var align = Math.abs(radial.x) > 0.38 ? (radial.x > 0 ? "left" : "right") : "center";
    var baseDistance = descriptor.radius +
      VIEW.canvasLabelRadialGapGraphPx + VIEW.canvasLabelGutterGraphPx;
    var slotStep = VIEW.canvasLabelSlotStepGraphPx;
    var offsets = [0, -1, 1, -2, 2, -3, 3];
    var candidates = [];
    for (var distanceIndex = 0; distanceIndex < 3; distanceIndex += 1) {
      var distance = baseDistance + distanceIndex * slotStep * 1.35;
      for (var offsetIndex = 0; offsetIndex < offsets.length; offsetIndex += 1) {
        if (candidates.length >= VIEW.canvasLabelSlotCount * 3) return candidates;
        var offset = offsets[offsetIndex] * slotStep;
        var x = point.x + radial.x * distance + tangent.x * offset;
        var y = point.y + radial.y * distance + tangent.y * offset;
        candidates.push(canvasSkillLabelCandidate(descriptor, x, y, align));
      }
    }
    return candidates;
  }

  function normalizedLabelVector(x, y) {
    var length = Math.hypot(x, y) || 1;
    return { x: x / length, y: y / length };
  }

  function canvasSkillLabelCandidate(descriptor, x, y, align) {
    var gutter = VIEW.canvasLabelGutterGraphPx;
    var minX = x - descriptor.width / 2;
    var maxX = x + descriptor.width / 2;
    if (align === "left") {
      minX = x;
      maxX = x + descriptor.width;
    } else if (align === "right") {
      minX = x - descriptor.width;
      maxX = x;
    }
    var halfHeight = descriptor.height / 2;
    return {
      node: descriptor.node,
      text: descriptor.text,
      font: descriptor.font,
      fontPx: descriptor.fontPx,
      x: x,
      y: y,
      align: align,
      displayAlpha: descriptor.displayAlpha,
      isMuted: descriptor.isMuted,
      box: {
        minX: minX - gutter,
        maxX: maxX + gutter,
        minY: y - halfHeight - gutter,
        maxY: y + halfHeight + gutter,
        cx: x,
        cy: y,
      },
    };
  }

  function labelCanForceRender(node) {
    return selectedNodeId === node.id ||
      !!(filters.search && nodeMatchesSearch(node, filters.search));
  }

  function drawCanvasSkillLabel(ctx, placement) {
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    ctx.font = placement.font;
    ctx.textAlign = placement.align;
    ctx.globalAlpha = placement.displayAlpha * (placement.isMuted ? 0.72 : 0.95);
    ctx.lineWidth = Math.max(1.4, placement.fontPx * 0.24);
    ctx.strokeStyle = "rgba(20, 20, 22, 0.92)";
    ctx.strokeText(placement.text, placement.x, placement.y);
    ctx.fillStyle = placement.isMuted ? "rgba(184, 179, 166, 0.88)" : "rgba(236, 233, 224, 0.96)";
    ctx.fillText(placement.text, placement.x, placement.y);
    ctx.globalAlpha = 1;
  }

  function canvasLabelFontFamily() {
    var family = getComputedStyle(document.documentElement).getPropertyValue("--font-label").trim();
    return family || "Inter, system-ui, sans-serif";
  }

  function canvasSkillLabelGraphPx(node) {
    var level = Math.max(0, Math.min(5, node.level || 0));
    var focusBoost = labelMustRender(node) || isKeystoneNode(node) ? 0.55 : 0;
    return Math.max(
      VIEW.canvasLabelMinGraphPx,
      Math.min(VIEW.canvasLabelMaxGraphPx, 8.6 + level * 0.32 + focusBoost)
    );
  }

  function scheduleCanvasRedraw() {
    if (canvasSettleTimer) {
      clearTimeout(canvasSettleTimer);
      canvasSettleTimer = null;
    }
    canvasRedrawPending = true;
    scheduleViewUpdate(false, true);
  }

  function scheduleSettledCanvasRedraw(delay) {
    if (canvasSettleTimer) clearTimeout(canvasSettleTimer);
    canvasSettleTimer = setTimeout(function () {
      canvasSettleTimer = null;
      if (isCameraAnimating()) {
        scheduleSettledCanvasRedraw(Math.max(80, delay || 0));
        return;
      }
      canvasRedrawPending = true;
      scheduleViewUpdate(true, true);
    }, delay);
  }

  function resetCanvasBitmapTransform() {
    if (!dom.graph_canvas) return;
    dom.graph_canvas.style.transform = "translate3d(0, 0, 0) scale(1)";
  }

  function resetCameraCompositorTransform() {
    if (!dom.graph_camera) return;
    dom.graph_camera.style.transform = "translate3d(0, 0, 0) scale(1)";
  }

  function activeCameraBaseViewState() {
    return {
      x: Number.isFinite(blittedCanvasViewState.x) ? blittedCanvasViewState.x : viewState.x,
      y: Number.isFinite(blittedCanvasViewState.y) ? blittedCanvasViewState.y : viewState.y,
      scale: safeScaleValue(blittedCanvasViewState.scale || safeViewScale()),
    };
  }

  function applyCameraCompositorTransform() {
    if (!dom.graph_camera) return false;
    var base = activeCameraBaseViewState();
    var ratio = safeViewScale() / safeScaleValue(base.scale);
    if (!Number.isFinite(ratio) || ratio <= 0) {
      resetCameraCompositorTransform();
      return false;
    }
    var x = viewState.x - base.x * ratio;
    var y = viewState.y - base.y * ratio;
    dom.graph_camera.style.transform = "translate3d(" + x + "px, " + y + "px, 0) scale(" + ratio + ")";
    return true;
  }

  function applyCanvasBitmapFallbackTransform() {
    if (!dom.graph_canvas) return;
    var renderedScale = safeScaleValue(renderedCanvasViewState.scale || safeViewScale());
    var ratio = safeViewScale() / renderedScale;
    if (!Number.isFinite(ratio) || ratio <= 0) {
      resetCanvasBitmapTransform();
      return;
    }
    var x = viewState.x - renderedCanvasViewState.x * ratio;
    var y = viewState.y - renderedCanvasViewState.y * ratio;
    dom.graph_canvas.style.transform = "translate3d(" + x + "px, " + y + "px, 0) scale(" + ratio + ")";
  }

  function visibleCanvasTransform() {
    var renderedScale = safeScaleValue(blittedCanvasViewState.scale || safeViewScale());
    var ratio = safeViewScale() / renderedScale;
    if (!Number.isFinite(ratio) || ratio <= 0) {
      return { x: 0, y: 0, ratio: 1, valid: false };
    }
    return {
      x: viewState.x - blittedCanvasViewState.x * ratio,
      y: viewState.y - blittedCanvasViewState.y * ratio,
      ratio: ratio,
      valid: true,
    };
  }

  function resetVisibleCanvasTransform() {
    blittedCanvasViewState = {
      x: viewState.x,
      y: viewState.y,
      scale: viewState.scale,
    };
    resetCanvasBitmapTransform();
  }

  function applyVisibleCanvasTransform() {
    if (!dom.graph_canvas) return false;
    var t = visibleCanvasTransform();
    if (!t.valid) {
      resetCanvasBitmapTransform();
      return false;
    }
    dom.graph_canvas.style.transform = "translate3d(" + t.x + "px, " + t.y + "px, 0) scale(" + t.ratio + ")";
    return true;
  }

  function visibleCanvasViewportMissPx() {
    if (!dom.canvas || !dom.graph_canvas) return Infinity;
    var rect = dom.canvas.getBoundingClientRect();
    var t = visibleCanvasTransform();
    if (!t.valid) return Infinity;
    var canvasWidth = rect.width + canvasViewportPad * 2;
    var canvasHeight = rect.height + canvasViewportPad * 2;
    var left = t.x - t.ratio * canvasViewportPad;
    var top = t.y - t.ratio * canvasViewportPad;
    var right = t.x + t.ratio * (canvasWidth - canvasViewportPad);
    var bottom = t.y + t.ratio * (canvasHeight - canvasViewportPad);
    return Math.max(
      Math.max(0, left),
      Math.max(0, top),
      Math.max(0, rect.width - right),
      Math.max(0, rect.height - bottom)
    );
  }

  function visibleCanvasCoversViewport(marginPx) {
    var missPx = visibleCanvasViewportMissPx();
    return Number.isFinite(missPx) && missPx <= (marginPx || 1);
  }

  function visibleCanvasTransformFitsPad() {
    var t = visibleCanvasTransform();
    if (!t.valid) return false;
    if (Math.abs(t.ratio - 1) > 0.001) return false;
    return visibleCanvasCoversViewport(canvasViewportPad * 0.18);
  }

  function visibleCanvasTransformWithinPad() {
    return visibleCanvasCoversViewport(1);
  }

  function blitCanvasBitmapCache() {
    if (!canvasBitmap || !canvasCtx) return;
    var source = canvasCacheSourceRect();
    if (!source) return;
    bumpViewerMetric("blitCanvasBitmapCache");
    canvasCtx.setTransform(1, 0, 0, 1, 0, 0);
    canvasCtx.clearRect(0, 0, dom.graph_canvas.width, dom.graph_canvas.height);
    canvasCtx.drawImage(
      canvasBitmap,
      source.sx, source.sy, source.sw, source.sh,
      0, 0, dom.graph_canvas.width, dom.graph_canvas.height
    );
    resetVisibleCanvasTransform();
  }

  function canvasCacheSourceRect() {
    if (!canvasBitmap || !dom.graph_canvas) return null;
    var rect = dom.canvas.getBoundingClientRect();
    var renderedScale = safeScaleValue(renderedCanvasViewState.scale || safeViewScale());
    var ratio = safeViewScale() / renderedScale;
    if (!Number.isFinite(ratio) || ratio <= 0) return null;
    var sxCss = canvasCachePad + renderedCanvasViewState.x - (viewState.x / ratio) - canvasViewportPad;
    var syCss = canvasCachePad + renderedCanvasViewState.y - (viewState.y / ratio) - canvasViewportPad;
    return {
      sx: Math.round(sxCss * canvasDpr),
      sy: Math.round(syCss * canvasDpr),
      sw: Math.max(1, Math.round(((rect.width + canvasViewportPad * 2) / ratio) * canvasDpr)),
      sh: Math.max(1, Math.round(((rect.height + canvasViewportPad * 2) / ratio) * canvasDpr)),
    };
  }

  function canvasCacheCoversCurrentView() {
    var source = canvasCacheSourceRect();
    if (!source || !canvasBitmap) return false;
    return source.sx >= 0 &&
      source.sy >= 0 &&
      source.sx + source.sw <= canvasBitmap.width &&
      source.sy + source.sh <= canvasBitmap.height;
  }

  function canvasRenderedAtCurrentScale() {
    var renderedScale = safeScaleValue(renderedCanvasViewState.scale || safeViewScale());
    return Math.abs(renderedScale - safeViewScale()) <= 0.001;
  }

  function canvasReadyForInteractiveOverlays() {
    if (canvasRenderedAtCurrentScale()) return true;
    // During wheel/pan movement, the retained canvas pixels and SVG overlay
    // share the graph-camera compositor transform. Hover/selection overlays can
    // stay live without waiting for the expensive settled canvas repaint.
    return isCameraAnimating() && !!canvasBitmap && !!canvasCtx;
  }

  function applyCanvasBitmapTransform() {
    if (!dom.graph_canvas) return;
    bumpViewerMetric("applyCanvasBitmapTransform");
    if (!canvasBitmap || !canvasCtx) {
      applyCanvasBitmapFallbackTransform();
      return;
    }
    if (isCameraAnimating()) {
      if (visibleCanvasTransformWithinPad()) {
        // During active camera movement, canvas and SVG move together through
        // #graph-camera. The SVG overlay is pinned to the retained bitmap's base
        // view, and the shared compositor transform projects both layers to the
        // live viewState. Pointer math uses viewState directly, so hit testing
        // does not depend on browser DOMMatrix behavior through CSS transforms.
        bumpViewerMetric("cameraSharedTransform");
        resetCanvasBitmapTransform();
      } else {
        // Do not recenter or redraw the bitmap while the camera is active.
        // Both operations mutate the retained base view; changing that base
        // mid-wheel/mid-drag makes the visible graph jump a few pixels even
        // though hover math still uses the correct world coordinates. The
        // larger visible guard band absorbs normal gestures, and the settled
        // redraw below refreshes the bitmap from the final camera state.
        bumpViewerMetric("cameraCacheDeferredMiss");
        resetCanvasBitmapTransform();
      }
      scheduleSettledCanvasRedraw(VIEW.cameraPanSettleMs);
      return;
    }
    resetCameraCompositorTransform();
    dom.graph_canvas.style.transform = "translate3d(0, 0, 0) scale(1)";
    if (!canvasRenderedAtCurrentScale()) {
      // Reblitting a bitmap rendered at the old zoom keeps node centers in
      // roughly the right place, but node glyph sizes and LOD-dependent labels
      // no longer match the SVG hit/hover/selection overlays. A zoom settle is
      // therefore a hard redraw boundary; pan-only movement can still use the
      // retained bitmap cache below.
      bumpViewerMetric("idleScaleMismatchRedraw");
      canvasRedrawPending = false;
      renderCanvas();
      return;
    }
    if (!canvasCacheCoversCurrentView()) {
      bumpViewerMetric("idleCacheMissRedraw");
      canvasRedrawPending = false;
      renderCanvas();
      return;
    }
    if (visibleCanvasTransformFitsPad()) {
      bumpViewerMetric("idleCacheTransform");
      applyVisibleCanvasTransform();
      return;
    }
    bumpViewerMetric("idleCacheBlit");
    blitCanvasBitmapCache();
  }

  // --- Presentation tree scaffold ---
  function domainBackdropColor(domain) {
    var idx = visualGroups.indexOf(domain);
    if (idx < 0) idx = 0;
    return DOMAIN_BACKDROP_PALETTE[idx % DOMAIN_BACKDROP_PALETTE.length];
  }

  function renderTreeAreaGlows(ctx, bounds) {
    if (!layoutCache) return;
    var bboxes = layoutCache.domainBBoxes;
    Object.keys(bboxes).forEach(function (domain) {
      if (isDomainCollapsed(domain)) return;
      var bbox = bboxes[domain];
      if (!pointInBounds({ x: bbox.centerX, y: bbox.centerY }, bounds)) return;
      var color = domainBackdropColor(domain);
      var viewScale = safeViewScale();
      var r = 52 / Math.max(viewScale, 0.24);
      var grad = ctx.createRadialGradient(bbox.centerX, bbox.centerY, 0, bbox.centerX, bbox.centerY, r);
      grad.addColorStop(0, color.fill);
      grad.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = grad;
      ctx.globalAlpha = 0.85;
      ctx.beginPath();
      ctx.arc(bbox.centerX, bbox.centerY, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.lineWidth = 1 / viewScale;
      ctx.strokeStyle = color.stroke;
      ctx.beginPath();
      ctx.arc(bbox.centerX, bbox.centerY, 28 / Math.max(viewScale, 0.35), 0, Math.PI * 2);
      ctx.stroke();
    });
  }

  function renderSyntheticTreeNodes(ctx, bounds) {
    if (!layoutCache) return;
    ctx.save();
    var labelReservedBoxes = syntheticTreeLabelReservedBoxes(bounds);
    (layoutCache.treeNodes || []).forEach(function (node) {
      if (!node._synthetic) return;
      if (node.kind !== "tree-root" && isDomainCollapsed(node._visualGroup)) {
        if (node.kind !== "skill-area") return;
      }
      var p = getDisplayPoint(node.id);
      if (!p) return;
      if (!pointInBounds(p, bounds) && node.kind !== "tree-root") return;
      var r = treeNodeRadius(node);
      var color = node.kind === "tree-root" ? "#4f9b86" : nodeColorHex(node);
      ctx.globalAlpha = getDisplayAlpha(node.id) * (node.kind === "branch-topic" && viewState.scale < 0.16 ? 0.72 : 1);
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = node.kind === "tree-root" ? "#111d1a" : "#111315";
      ctx.fill();
      var viewScale = safeViewScale();
      ctx.lineWidth = (node.kind === "tree-root" ? 2.2 : 1.6) / viewScale;
      ctx.strokeStyle = color;
      ctx.stroke();
      if (node.kind === "tree-root" || node.kind === "skill-area") {
        ctx.beginPath();
        ctx.arc(p.x, p.y, r + (node.kind === "tree-root" ? 9 : 6), 0, Math.PI * 2);
        ctx.globalAlpha = 0.38 * getDisplayAlpha(node.id);
        ctx.stroke();
        ctx.globalAlpha = 1;
      }
      if (shouldRenderSyntheticTreeLabel(node)) {
        ctx.fillStyle = "#ece9e0";
        ctx.globalAlpha = getDisplayAlpha(node.id) * (node.kind === "branch-topic" ? 0.7 : 0.88);
        var labelSize = node.kind === "tree-root" ? 18 : node.kind === "branch-topic" ? 12 : 14;
        var labelPoint = syntheticTreeLabelPoint(node, p, r);
        var labelBox = syntheticTreeLabelBox(node, p, r);
        if (!syntheticTreeLabelCanRender(node, labelBox, labelReservedBoxes)) {
          ctx.globalAlpha = 1;
          return;
        }
        ctx.font = (node.kind === "tree-root" ? "700 " : "650 ") +
          labelSize + "px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(node._displayName, labelPoint.x, labelPoint.y);
        labelReservedBoxes.push(labelBox);
        renderedSyntheticLabelBoxes.push(labelBox);
        ctx.globalAlpha = 1;
      }
    });
    ctx.restore();
  }

  function shouldRenderSyntheticTreeLabel(node) {
    if (!viewSettings.showCategories || !viewSettings.showCategoryLabels) return false;
    if (node.kind === "tree-root") return true;
    if (node.kind === "skill-area") return false;
    if (node.kind !== "branch-topic") return false;
    if (!syntheticTreeLabelRelevantInFocus(node)) return false;
    return focusedNodeIds.has(node.id) || safeViewScale() >= VIEW.topicLabelScale;
  }

  function syntheticTreeLabelRelevantInFocus(node) {
    if (!activeFocus || !(focusDisplay && focusDisplay.active)) return true;
    if (activeFocus.kind === "domain" && activeFocus.domain) {
      return node._visualGroup === activeFocus.domain;
    }
    if (activeFocus.kind === "tree") {
      var targetTreeNode = getSyntheticTreeNode(activeFocus.targetId);
      if (!targetTreeNode) return false;
      if (targetTreeNode.kind === "branch-topic") return node.id === targetTreeNode.id;
      if (targetTreeNode.kind === "skill-area") return node._visualGroup === targetTreeNode._visualGroup;
      return false;
    }
    if (activeFocus.kind === "node") {
      var targetNode = nodeById.get(activeFocus.targetId);
      if (!targetNode) return false;
      return node._visualGroup === targetNode._visualGroup &&
        node._branchTopic === targetNode._branchTopic;
    }
    return false;
  }

  function syntheticTreeLabelReservedBoxes(bounds) {
    var boxes = [];
    if (!layoutCache) return boxes;
    var state = focusDisplay || emptyFocusDisplay();
    var ids = new Set();
    if (state.active) {
      if (state.focusIds) state.focusIds.forEach(function (id) { ids.add(id); });
      if (state.labelIds) state.labelIds.forEach(function (id) { ids.add(id); });
      if (selectedNodeId) ids.add(selectedNodeId);
    } else if (safeViewScale() >= VIEW.topicLabelScale) {
      getCachedCanvasNodeIds().forEach(function (id) { ids.add(id); });
    }

    ids.forEach(function (id) {
      var node = nodeById.get(id);
      var point = getDisplayPoint(id);
      if (!node || !point) return;
      if (isNodeCollapsed(node)) return;
      if (bounds && !pointInBounds(point, bounds)) return;
      if (state.labelIds && state.labelIds.has(id)) {
        boxes.push(nodeLabelProtectionBox(node, point));
        return;
      }
      boxes.push(nodeClearanceBox(node, point, getDisplayScale(id)));
    });
    return boxes;
  }

  function syntheticTreeLabelCanRender(node, labelBox, reservedBoxes) {
    if (node.kind === "tree-root") return true;
    if (!boxIntersectsAny(labelBox, reservedBoxes)) return true;
    return !!(activeFocus && activeFocus.kind === "tree" && activeFocus.targetId === node.id);
  }

  function syntheticTreeLabelPoint(node, point, radius) {
    if (node.kind !== "branch-topic") {
      return {
        x: point.x,
        y: point.y + radius + (node.kind === "tree-root" ? 22 : 18),
      };
    }
    var angle = Number.isFinite(point.angle) ? point.angle : Math.atan2(point.y / 0.92, point.x);
    var distance = radius +
      VIEW.treeTopicLabelGap +
      ((node._labelLane || 0) * VIEW.treeTopicLabelLaneGap);
    return {
      x: point.x + Math.cos(angle) * distance,
      y: point.y + Math.sin(angle) * distance * 0.92,
    };
  }

  function syntheticTreeLabelBox(node, point, radius) {
    var text = node._displayName || node.name || "";
    var halfWidth = Math.min(180, Math.max(42, text.length * 4.4));
    var labelPoint = syntheticTreeLabelPoint(node, point, radius);
    return {
      minX: labelPoint.x - halfWidth,
      maxX: labelPoint.x + halfWidth,
      minY: labelPoint.y - 14,
      maxY: labelPoint.y + 12,
      cx: labelPoint.x,
      cy: labelPoint.y,
    };
  }

  function renderZoomBranchLinks(ctx, bounds, canvasNodeIds) {
    if (!layoutCache) return;
    var pos = layoutCache.positions;
    var localBounds = bounds || getGraphViewportBounds(VIEW.canvasEdgeCullPad);
    ctx.save();
    ctx.lineCap = "round";
    (layoutCache.treeLinks || []).forEach(function (link) {
      if (!treeLinkVisible(link, canvasNodeIds)) return;
      var from = getDisplayPoint(link.fromId);
      var to = getDisplayPoint(link.toId);
      if (!from || !to) return;
      if (!segmentIntersectsBounds(from, to, localBounds)) return;

      ctx.strokeStyle = resolvedVisualGroupColors[link.area] || "#38796c";
      var viewScale = safeViewScale();
      ctx.lineWidth = ((link.depth === 1 ? 1.55 : link.depth === 2 ? 1.16 : 0.82) * Math.sqrt(viewSettings.lineStrength)) / viewScale;
      ctx.globalAlpha = Math.min(1, viewSettings.lineStrength * Math.min(getDisplayAlpha(link.fromId), getDisplayAlpha(link.toId)) * (viewScale < VIEW.detailZoomMedium ?
        (link.depth === 3 ? 0.2 : 0.36) :
        (link.depth === 3 ? 0.28 : 0.46)));
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    });

    ctx.restore();
  }

  function treeLinkVisible(link, canvasNodeIds) {
    if (!link) return false;
    if (isDomainCollapsed(link.area) && link.depth > 1) return false;
    if (!treeLinkVisibleInFocusPocket(link)) return false;
    if (link.depth === 3) return canvasNodeIds.has(link.toId);
    return true;
  }

  function treeLinkVisibleInFocusPocket(link) {
    var state = focusDisplay || emptyFocusDisplay();
    if (!(state.active && state.points && state.points.size)) return true;
    var fromMoved = state.points.has(link.fromId);
    var toMoved = state.points.has(link.toId);
    if (fromMoved !== toMoved) return false;
    if (!fromMoved && !toMoved) return true;
    return !!(state.focusIds && state.focusIds.has(link.fromId) && state.focusIds.has(link.toId));
  }

  function selectedEdgeVisibleInFocusPocket(edge) {
    var state = focusDisplay || emptyFocusDisplay();
    if (!(state.active && state.points && state.points.size)) return true;
    return state.points.has(edge.fromId) &&
      state.points.has(edge.toId) &&
      !!(state.focusIds && state.focusIds.has(edge.fromId) && state.focusIds.has(edge.toId));
  }

  // --- SVG overlay: domain labels ---
  function renderDomainLabels() {
    var ns = "http://www.w3.org/2000/svg";
    var fragment = document.createDocumentFragment();
    domainLabelElements = new Map();
    if (!viewSettings.showCategories || !viewSettings.showCategoryLabels) {
      dom.graph_domain_labels.replaceChildren(fragment);
      return;
    }
    Object.keys(layoutCache.domainBBoxes).forEach(function (domain) {
      var label = createDomainLabel(domain, ns);
      domainLabelElements.set(domain, label);
      fragment.appendChild(label);
    });
    dom.graph_domain_labels.replaceChildren(fragment);
  }

  // --- SVG overlay: edges (only focus-path highlighted edges get DOM elements) ---
  function renderSvgEdges(visibleNodeIds) {
    var pos = layoutCache.positions;
    var ns = "http://www.w3.org/2000/svg";
    var fragment = document.createDocumentFragment();

    // Only create SVG edge elements for the selected/focus path.
    // All other edges are drawn on canvas.
    if (!selectedNodeId) {
      svgEdgeElements = [];
      dom.graph_edges.replaceChildren(fragment);
      return;
    }
    if (!viewSettings.showLines) {
      svgEdgeElements = [];
      dom.graph_edges.replaceChildren(fragment);
      return;
    }

    svgEdgeElements = [];
    var selectedPathIds = presentationPathIds(selectedNodeId);
    (layoutCache.treeLinks || []).forEach(function (link) {
      if (!selectedPathIds.has(link.fromId) || !selectedPathIds.has(link.toId)) return;
      if (!treeLinkVisible(link, visibleNodeIds)) return;
      var from = getDisplayPoint(link.fromId);
      var to = getDisplayPoint(link.toId);
      if (!from || !to) return;

      var path = document.createElementNS(ns, "path");
      path.setAttribute("class", "graph-edge highlighted");
      path.setAttribute("data-from", link.fromId);
      path.setAttribute("data-to", link.toId);
      path.setAttribute("d", straightPath(from, to));
      path.style.opacity = String(0.96 * Math.min(getDisplayAlpha(link.fromId), getDisplayAlpha(link.toId)));
      svgEdgeElements.push({ el: path, fromId: link.fromId, toId: link.toId });
      fragment.appendChild(path);
    });

    dom.graph_edges.replaceChildren(fragment);
  }

  function presentationPathIds(nodeId) {
    var ids = new Set();
    var current = nodeId;
    while (current) {
      ids.add(current);
      current = layoutCache.branchParents[current];
    }
    return ids;
  }

  // --- SVG overlay: nodes (only the capped accessible set gets DOM elements) ---
  function renderSvgNodes(visibleNodeIds, accessibleNodeIds) {
    var pos = layoutCache.positions;
    var ns = "http://www.w3.org/2000/svg";
    var fragment = document.createDocumentFragment();
    svgNodeElements = new Map();

    Array.from(accessibleNodeIds)
      .map(function (id) { return nodeById.get(id); })
      .filter(Boolean)
      .sort(function (a, b) {
        return getDisplayZ(a.id) - getDisplayZ(b.id) ||
          (a.name || a.id || "").localeCompare(b.name || b.id || "");
      })
      .forEach(function (node) {
      var p = getDisplayPoint(node.id);
      if (!p) return;
      if (!visibleNodeIds.has(node.id)) return;
      if (isNodeCollapsed(node)) return;

      // Only create SVG node elements for the accessible set.
      // All other nodes are drawn on canvas.
      if (!accessibleNodeIds.has(node.id)) return;

      var r = nodeRadius(node);
      var g = document.createElementNS(ns, "g");
      g.setAttribute("class", "graph-node");
      g.setAttribute("data-id", node.id);
      var displayScale = getDisplayScale(node.id);
      g.setAttribute("transform", "translate(" + p.x + "," + p.y + ") scale(" + displayScale + ")");
      g.style.opacity = String(getDisplayAlpha(node.id));
      applyNodeAccessibility(g, node, accessibleNodeIds);
      if (selectedNodeId === node.id) g.classList.add("selected");
      if (focusedNodeIds.has(node.id)) g.classList.add("focused");
      if (isFocusQuieted(node.id)) g.classList.add("quieted");
      if (isStale(node)) g.classList.add("dimmed");
      if (isKeystoneNode(node) || node.featured) g.classList.add("keystone");

      if (filters.search && nodeMatchesSearch(node, filters.search)) {
        g.classList.add("matched");
      }

      // SVG nodes are interaction handles and state overlays only. The canvas
      // layer is the single visible source for node bodies, which prevents
      // canvas/SVG duplicate glyphs from drifting apart during camera motion.
      var hit = document.createElementNS(ns, "circle");
      hit.setAttribute("class", "graph-node__hit");
      g.appendChild(hit);

      // Glow
      var glow = document.createElementNS(ns, "circle");
      glow.setAttribute("class", "graph-node__glow");
      g.appendChild(glow);

      var focusRing = document.createElementNS(ns, "circle");
      focusRing.setAttribute("class", "graph-node__focus-ring");
      g.appendChild(focusRing);
      updateNodeOverlayRadii(g, node.id);

      fragment.appendChild(g);
      svgNodeElements.set(node.id, g);
    });

    dom.graph_nodes.replaceChildren(fragment);
    syncHoverOverlay();
  }

  function createDomainLabel(domain, ns) {
    var bbox = layoutCache.domainBBoxes[domain];
    var isCollapsed = !!collapsedDomains[domain];
    var isSelected = filters.domain === domain ||
      !!(activeFocus && activeFocus.kind === "domain" && activeFocus.domain === domain);
    var labelName = visualGroupDisplayName(domain);
    var label = document.createElementNS(ns, "text");
    label.setAttribute(
      "class",
      "domain-label" +
        (isCollapsed ? " collapsed" : "") +
        (isSelected ? " selected" : "")
    );
    label.setAttribute("x", bbox.centerX);
    label.setAttribute("y", bbox.labelY);
    label.setAttribute("data-domain", domain);
    label.setAttribute("role", "button");
    label.setAttribute("tabindex", "0");
    label.setAttribute(
      "aria-label",
      "Focus skill area " + labelName + ". Hold Shift or Alt to " +
        (isCollapsed ? "expand" : "collapse") + " this area."
    );
    label.setAttribute("aria-pressed", String(isSelected));
    label.setAttribute("aria-expanded", String(!isCollapsed));
    label.textContent = labelName + (isCollapsed ? " [+]" : "");
    label.addEventListener("click", function (e) {
      if (e.shiftKey || e.altKey) {
        toggleDomain(domain);
        return;
      }
      focusDomain(domain, true);
    });
    label.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (e.shiftKey || e.altKey) {
          toggleDomain(domain);
          return;
        }
        focusDomain(domain, true);
      }
    });
    return label;
  }

  function visualGroupDisplayName(group) {
    var slash = group.indexOf(" / ");
    var name = slash !== -1 ? group.slice(slash + 3) : group;
    return name;
  }

  function getAccessibleNodeIds(visibleNodeIds) {
    var accessible = new Set();
    var candidates = [];

    visibleNodeIds.forEach(function (id) {
      var node = nodeById.get(id);
      if (!node) return;
      var p = getDisplayPoint(node.id);
      if (!p) return;
      if (isNodeCollapsed(node)) return;

      if (nodeMustEnterAccessibilityTree(node)) {
        accessible.add(node.id);
      } else {
        candidates.push(node);
      }
    });

    candidates.sort(function (a, b) {
      return nodeAccessibilityPriority(b) - nodeAccessibilityPriority(a) ||
        (a.name || a.id || "").localeCompare(b.name || b.id || "");
    });

    candidates.some(function (node) {
      if (accessible.size >= VIEW.maxAccessibleNodes) return true;
      if (!nodeShouldEnterAccessibilityTree(node)) return false;
      accessible.add(node.id);
      return false;
    });

    return accessible;
  }

  function nodeMustEnterAccessibilityTree(node) {
    return selectedNodeId === node.id ||
      focusedNodeIds.has(node.id) ||
      !!node.featured ||
      isKeystoneNode(node) ||
      !!(filters.search && nodeMatchesSearch(node, filters.search));
  }

  function nodeShouldEnterAccessibilityTree(node) {
    return nodeAccessibilityPriority(node) >= 42;
  }

  function nodeAccessibilityPriority(node) {
    var score = nodeImportance(node);
    if (isKeystoneNode(node)) score += 800;
    if (node.featured) score += 500;
    if (selectedNodeId === node.id) score += 1000;
    if (focusedNodeIds.has(node.id)) score += 700;
    if (focusDisplay && focusDisplay.focusIds && focusDisplay.focusIds.has(node.id)) score += 450;
    return score;
  }

  function applyNodeAccessibility(g, node, accessibleNodeIds) {
    if (!accessibleNodeIds.has(node.id)) {
      g.setAttribute("aria-hidden", "true");
      return;
    }

    g.setAttribute("tabindex", "0");
    g.setAttribute("role", "button");
    g.setAttribute("aria-label", nodeAriaLabel(node));
  }

  function nodeAriaLabel(node) {
    return displayNameForNode(node) +
      ", L" + (node.level || 0) +
      ", area " + nodeAreaName(node) +
      ", " + Math.round((node.confidence || 0) * 100) + "% confidence";
  }

  function nodeAreaName(node) {
    if (node.kind === "domain") return node.name || node.domain || "Uncategorized";
    return visualGroupDisplayName(node._skillArea || node._visualGroup || node.domain || "Uncategorized");
  }

  function maxRenderedNodeLabels(activeLabelCap) {
    var densityCap = Math.max(24, Math.round(activeLabelCap * viewSettings.labelDensity));
    if (!isConstrainedLabelViewport()) return densityCap;

    // Canvas labels are painted into the retained bitmap. Small touch
    // viewports still cap label count so redraws after pinch gestures settle
    // quickly while desktop keeps the full 1000-label budget.
    var mobileDensity = Math.min(1, viewSettings.labelDensity);
    var mobileCap = Math.max(24, Math.round(VIEW.maxMobileNodeLabels * mobileDensity));
    return Math.min(densityCap, mobileCap);
  }

  function isConstrainedLabelViewport() {
    if (!dom.canvas) return false;
    var rect = dom.canvas.getBoundingClientRect();
    var shortestSide = Math.min(rect.width || window.innerWidth || 0, rect.height || window.innerHeight || 0);
    var coarsePointer = !!(window.matchMedia && window.matchMedia("(pointer: coarse)").matches);
    return shortestSide <= VIEW.mobileLabelViewportWidth || (coarsePointer && shortestSide <= 900);
  }

  function labelMustRender(node) {
    return selectedNodeId === node.id ||
      focusedNodeIds.has(node.id) ||
      !!(focusDisplay && focusDisplay.labelIds && focusDisplay.labelIds.has(node.id)) ||
      !!node.featured ||
      !!(filters.search && nodeMatchesSearch(node, filters.search));
  }

  function persistentLabelPriority(node) {
    var score = nodeImportance(node);
    if (labelMustRender(node)) score += 10000;
    if (focusDisplay && focusDisplay.focusIds && focusDisplay.focusIds.has(node.id)) score += 3000;
    if (isKeystoneNode(node)) score += 700;
    return score;
  }

  function skillLabelVisibleAtCurrentScale(node) {
    return safeViewScale() >= VIEW.labelScale || labelMustRender(node);
  }

  function isKeystoneNode(node) {
    return !!node._isVisualKeystone;
  }

  function getGraphViewportBounds(pad) {
    sanitizeViewState();
    var rect = dom.canvas.getBoundingClientRect();
    var padding = pad || 0;
    var viewScale = safeViewScale();
    return {
      minX: (-viewState.x - padding) / viewScale,
      minY: (-viewState.y - padding) / viewScale,
      maxX: (-viewState.x + rect.width + padding) / viewScale,
      maxY: (-viewState.y + rect.height + padding) / viewScale,
    };
  }

  function pointInBounds(point, bounds) {
    return point.x >= bounds.minX &&
      point.x <= bounds.maxX &&
      point.y >= bounds.minY &&
      point.y <= bounds.maxY;
  }

  function segmentIntersectsBounds(a, b, bounds) {
    if (pointInBounds(a, bounds) || pointInBounds(b, bounds)) return true;
    var minX = Math.min(a.x, b.x);
    var maxX = Math.max(a.x, b.x);
    var minY = Math.min(a.y, b.y);
    var maxY = Math.max(a.y, b.y);
    return maxX >= bounds.minX &&
      minX <= bounds.maxX &&
      maxY >= bounds.minY &&
      minY <= bounds.maxY;
  }

  function straightPath(from, to) {
    return "M" + from.x + "," + from.y + " L" + to.x + "," + to.y;
  }

  function clientPointToGraphPoint(clientX, clientY) {
    if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return null;
    if (!dom.canvas) return null;
    sanitizeViewState();
    var rect = dom.canvas.getBoundingClientRect();
    var scale = safeViewScale();
    return {
      x: (clientX - rect.left - viewState.x) / scale,
      y: (clientY - rect.top - viewState.y) / scale,
    };
  }

  function graphPointToClientPoint(graphX, graphY) {
    if (!Number.isFinite(graphX) || !Number.isFinite(graphY)) return null;
    if (!dom.canvas) return null;
    sanitizeViewState();
    var rect = dom.canvas.getBoundingClientRect();
    var scale = safeViewScale();
    return {
      x: rect.left + viewState.x + graphX * scale,
      y: rect.top + viewState.y + graphY * scale,
    };
  }

  function graphScreenScale() {
    return safeViewScale();
  }

  function truncate(s, n) {
    if (!s) return "";
    return s.length > n ? s.slice(0, n - 3) + "..." : s;
  }

  // --- Canvas hit-testing ---
  // Finds the nearest visible node to a screen-space point.
  // Used for clicks that pass through the SVG overlay (nodes only in canvas).
  function hitTestNode(screenX, screenY) {
    if (!layoutCache) return null;
    sanitizeViewState();
    var graphPoint = clientPointToGraphPoint(screenX, screenY);
    var viewScale = graphScreenScale();
    if (!graphPoint) {
      var rect = dom.canvas.getBoundingClientRect();
      graphPoint = {
        x: (screenX - rect.left - viewState.x) / safeViewScale(),
        y: (screenY - rect.top - viewState.y) / safeViewScale(),
      };
      viewScale = safeViewScale();
    }
    var gx = graphPoint.x;
    var gy = graphPoint.y;
    var best = null;
    var bestDist = Infinity;
    var bestPriority = -Infinity;
    var hitRadius = 22 / viewScale + 6;
    var canvasNodeIds = getCachedCanvasNodeIds();

    canvasNodeIds.forEach(function (id) {
      var node = nodeById.get(id);
      if (!node) return;
      var p = getDisplayPoint(node.id);
      if (!p) return;
      if (isNodeCollapsed(node)) return;
      var dx = p.x - gx;
      var dy = p.y - gy;
      var dist = Math.hypot(dx, dy);
      var r = nodeVisualRadius(node);
      var hitPriority = Math.max(0.08, getHitPriority(node.id));
      var withinHit = dist < r + hitRadius;
      var priorityTieBreak = Math.abs(dist - bestDist) <= (0.8 / Math.max(viewScale, 0.05)) &&
        hitPriority > bestPriority;
      if (withinHit && (dist < bestDist || priorityTieBreak)) {
        bestDist = dist;
        bestPriority = hitPriority;
        best = node.id;
      }
    });

    if (viewSettings.showCategories) {
      (layoutCache.treeNodes || []).forEach(function (node) {
        if (!node || !node._synthetic) return;
        if (node.kind !== "tree-root" && isDomainCollapsed(node._visualGroup)) return;
        var p = layoutCache.positions[node.id];
        p = getDisplayPoint(node.id) || p;
        if (!p) return;
        var dx = p.x - gx;
        var dy = p.y - gy;
        var dist = Math.hypot(dx, dy);
        var r = treeNodeRadius(node);
        var labelHit = syntheticTreeLabelHit(node, p, gx, gy);
        var insideNode = dist < r + hitRadius;
        if (!insideNode && !labelHit) return;
        var priority = node.kind === "branch-topic" ? 2.2 : node.kind === "skill-area" ? 2 : 1.7;
        var candidateDist = labelHit ? 0 : dist;
        var priorityTieBreak = Math.abs(candidateDist - bestDist) <= (0.8 / Math.max(viewScale, 0.05)) &&
          priority > bestPriority;
        if (candidateDist < bestDist || priorityTieBreak) {
          bestDist = candidateDist;
          bestPriority = priority;
          best = node.id;
        }
      });
    }

    return best;
  }

  function syntheticTreeLabelHit(node, point, gx, gy) {
    if (!shouldRenderSyntheticTreeLabel(node)) return false;
    var r = treeNodeRadius(node);
    var box = syntheticTreeLabelBox(node, point, r);
    return gx >= box.minX &&
      gx <= box.maxX &&
      gy >= box.minY &&
      gy <= box.maxY;
  }

  function activateGraphId(id, fromInteraction) {
    if (!id) return;
    if (nodeById.has(id)) {
      selectNode(id, fromInteraction);
      return;
    }
    focusTreeNode(id, fromInteraction);
  }

  function pointerActivationId(event, fallbackId) {
    if (!event || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) {
      return fallbackId;
    }
    return graphNodeIdAtClientPoint(event.clientX, event.clientY) ||
      hitTestNode(event.clientX, event.clientY) ||
      fallbackId;
  }

  function ensureHoverOverlay() {
    if (hoverNodeEl && hoverNodeEl.isConnected) return hoverNodeEl;
    var ns = "http://www.w3.org/2000/svg";
    hoverNodeEl = document.createElementNS(ns, "circle");
    hoverNodeEl.setAttribute("class", "graph-node-hover-ring");
    hoverNodeEl.setAttribute("aria-hidden", "true");
    hoverNodeEl.dataset.visible = "false";
    dom.graph_nodes.appendChild(hoverNodeEl);
    return hoverNodeEl;
  }

  function setHoverNode(id) {
    if (hoverNodeId === id) return;
    hoverNodeId = id || null;
    syncHoverOverlay();
  }

  function clearHoverNode() {
    setHoverNode(null);
  }

  function syncHoverOverlay() {
    if (!dom.graph_nodes) return;
    var el = ensureHoverOverlay();
    if (!hoverNodeId || !canvasReadyForInteractiveOverlays()) {
      el.dataset.visible = "false";
      return;
    }
    var point = getDisplayPoint(hoverNodeId);
    var radius = hoverOverlayRadius(hoverNodeId);
    if (!point || !Number.isFinite(radius)) {
      el.dataset.visible = "false";
      return;
    }
    el.setAttribute("cx", point.x);
    el.setAttribute("cy", point.y);
    el.setAttribute("r", radius);
    el.dataset.visible = "true";
  }

  function updateSvgNodeOverlayGeometry() {
    if (!svgNodeElements || !svgNodeElements.size) {
      syncHoverOverlay();
      return;
    }
    svgNodeElements.forEach(function (el, id) {
      updateNodeOverlayRadii(el, id);
    });
    syncHoverOverlay();
  }

  function updateNodeOverlayRadii(el, id) {
    var node = nodeById.get(id);
    if (!el || !node) return;
    var displayScale = Math.max(0.12, getDisplayScale(id));
    var localVisualR = nodeVisualRadius(node) / displayScale;
    var hit = el.querySelector(".graph-node__hit");
    var glow = el.querySelector(".graph-node__glow");
    var focusRing = el.querySelector(".graph-node__focus-ring");
    if (hit) hit.setAttribute("r", Math.max(localVisualR + 10, 20));
    if (glow) glow.setAttribute("r", localVisualR + 12);
    if (focusRing) focusRing.setAttribute("r", localVisualR + 5);
  }

  function hoverOverlayRadius(id) {
    var node = nodeById.get(id);
    if (node) return nodeVisualRadius(node) + 5;
    var treeNode = getSyntheticTreeNode(id);
    if (treeNode) return treeNodeRadius(treeNode) + 6;
    return NaN;
  }

  // --- Filters ---
  function getVisibleNodeIds() {
    var visible = new Set();
    getVisibleNodes().forEach(function (node) {
      visible.add(node.id);
    });
    return visible;
  }

  function getDisplayedNodeIds() {
    var displayed = new Set();
    getVisibleNodes().forEach(function (node) {
      if (isNodeCollapsed(node)) return;
      displayed.add(node.id);
    });
    return displayed;
  }

  function getVisibleNodes() {
    var baseNodes = nodes.filter(function (node) {
      if (node.kind === "domain") return false;
      return matchesFilters(node);
    });
    return applyScopeLimit(baseNodes);
  }

  function defaultFilters() {
    return Object.assign({}, DEFAULT_FILTERS);
  }

  function defaultViewSettings() {
    return Object.assign({}, DEFAULT_VIEW_SETTINGS);
  }

  function clampNumber(value, min, max, fallback) {
    var parsed = Number(value);
    if (!Number.isFinite(parsed)) return fallback;
    return Math.max(min, Math.min(max, parsed));
  }

  function normalizeViewSettings(raw) {
    var source = raw && typeof raw === "object" ? raw : {};
    return {
      contextDimming: clampNumber(source.contextDimming, 0.25, 1, DEFAULT_VIEW_SETTINGS.contextDimming),
      nodeScale: clampNumber(source.nodeScale, 0.75, 1.45, DEFAULT_VIEW_SETTINGS.nodeScale),
      lineStrength: clampNumber(source.lineStrength, 0.45, 1.6, DEFAULT_VIEW_SETTINGS.lineStrength),
      labelDensity: clampNumber(source.labelDensity, 0.4, 1.6, DEFAULT_VIEW_SETTINGS.labelDensity),
      separation: clampNumber(source.separation, 0.75, 1.35, DEFAULT_VIEW_SETTINGS.separation),
      showLines: source.showLines !== false,
      showCategories: source.showCategories !== false,
      showCategoryLabels: source.showCategoryLabels !== false,
      showSkillLabels: source.showSkillLabels !== false,
      showLevelBadges: source.showLevelBadges !== false,
      showBackgroundDots: source.showBackgroundDots !== false,
    };
  }

  function loadViewSettings() {
    try {
      var raw = window.localStorage.getItem(VIEW_SETTINGS_STORAGE_KEY);
      if (!raw) return defaultViewSettings();
      return normalizeViewSettings(JSON.parse(raw));
    } catch (_err) {
      return defaultViewSettings();
    }
  }

  function saveViewSettings() {
    try {
      window.localStorage.setItem(VIEW_SETTINGS_STORAGE_KEY, JSON.stringify(viewSettings));
    } catch (_err) {
      // Local storage is a preference cache. Rendering should keep working
      // when a privacy setting or quota prevents writes.
    }
  }

  function percentText(value) {
    return Math.round(value * 100) + "%";
  }

  function syncRangeProgress(el) {
    if (!el) return;
    var min = Number(el.min || 0);
    var max = Number(el.max || 100);
    var value = Number(el.value || 0);
    var span = max - min;
    var pct = span === 0 ? 0 : ((value - min) / span) * 100;
    el.style.setProperty("--range-progress", Math.max(0, Math.min(100, pct)) + "%");
  }

  var NUMERIC_TEXT_READOUT_TRANSITION = { duration: 300 };
  var NUMERIC_TEXT_DEFAULT_TRANSITION = {
    duration: 550,
    easing: "linear(0,.1052,.3155,.532,.7112,.8414,.9265,.9765,1.0023,1.013,1.0151,1.0133,1.01,1.0068,1.0041,1.0022,1.001,1)",
  };
  var NUMERIC_TEXT_MOTION = {
    y: 0.35,
    scale: 0.6,
    blur: 0.1,
    rotate: 2,
    stagger: 0.3,
  };
  var NUMERIC_TEXT_SHADOW_CSS = [
    ":host{position:relative;display:inline-flex;white-space:nowrap!important;isolation:isolate;}",
    "span{margin:0!important;padding:0!important;transform-origin:center;}",
    "[inert]{position:absolute!important;display:inline-flex!important;will-change:transform;z-index:0;}",
    ".section{position:relative!important;display:inline-flex!important;will-change:transform;z-index:1;}",
    ".char{display:inline-block!important;white-space:pre!important;}",
  ].join("");

  function numericTextCreate(tagName, className, text) {
    var el = document.createElement(tagName);
    el.setAttribute("aria-hidden", "true");
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function numericTextRect(el) {
    return el.getBoundingClientRect();
  }

  function numericTextCancel(el) {
    Array.from(el.getAnimations()).forEach(function (animation) {
      animation.cancel();
    });
  }

  function numericTextSlideSection(el, dx, transition) {
    if (!dx || typeof el.animate !== "function") return;
    numericTextCancel(el);
    el.animate({ transform: ["translateX(" + dx + "px)", ""] }, {
      duration: transition.duration,
      easing: transition.easing,
      fill: "both",
    });
  }

  var numericTextSegmenter = window.Intl && Intl.Segmenter ?
    new Intl.Segmenter(undefined, { granularity: "grapheme" }) :
    null;

  function numericTextSegments(value) {
    var text = String(value);
    if (numericTextSegmenter) {
      return Array.from(numericTextSegmenter.segment(text), function (part) {
        return part.segment === " " ? "\\u00a0" : part.segment;
      });
    }
    return Array.from(text, function (char) {
      return char === " " ? "\\u00a0" : char;
    });
  }

  function numericTextDiff(currentChars, nextValue) {
    var nextChars = numericTextSegments(nextValue);
    var currentLength = currentChars.length;
    var nextLength = nextChars.length;
    var prefixCount = 0;
    while (
      prefixCount < currentLength &&
      prefixCount < nextLength &&
      currentChars[prefixCount].textContent === nextChars[prefixCount]
    ) {
      prefixCount += 1;
    }

    var suffixCount = 0;
    var maxSuffix = Math.min(currentLength - prefixCount, nextLength - prefixCount);
    while (
      suffixCount < maxSuffix &&
      currentChars[currentLength - 1 - suffixCount].textContent ===
        nextChars[nextLength - 1 - suffixCount]
    ) {
      suffixCount += 1;
    }

    return {
      prefixCount: prefixCount,
      suffixCount: suffixCount,
      middleLabels: nextChars.slice(prefixCount, nextLength - suffixCount),
    };
  }

  class TracciaNumericText extends HTMLElement {
    constructor() {
      super();
      this._prefix = numericTextCreate("span", "section");
      this._middle = numericTextCreate("span", "section");
      this._suffix = numericTextCreate("span", "section");
      this._chars = [];
      this._exitingChars = [];
      this._isRTL = false;
      this._value = "";
      this._prevValue = "";
      this.transition = Object.assign({}, NUMERIC_TEXT_DEFAULT_TRANSITION);
      this.trend = 0;
      this.respectMotionPreference = true;

      var shadow = this.attachShadow({ mode: "open" });
      var style = document.createElement("style");
      style.textContent = NUMERIC_TEXT_SHADOW_CSS;
      shadow.append(style, this._prefix, this._middle, this._suffix);
    }

    connectedCallback() {
      this._isRTL = getComputedStyle(this).direction === "rtl";
      this._render(false);
    }

    get value() {
      return this._value;
    }

    set value(next) {
      this.update(next, false);
    }

    setOptions(options) {
      if (options.transition) {
        this.transition = Object.assign({}, NUMERIC_TEXT_DEFAULT_TRANSITION, options.transition);
      }
      if (typeof options.trend === "number") this.trend = options.trend;
      if (typeof options.respectMotionPreference === "boolean") {
        this.respectMotionPreference = options.respectMotionPreference;
      }
    }

    update(next, animated) {
      next = String(next);
      if (next === this._value) return;
      this._prevValue = this._value;
      this._value = next;
      var shouldAnimate = animated !== false &&
        !(this.respectMotionPreference && prefersReducedMotion());
      this._render(shouldAnimate);
    }

    _render(animated) {
      var diff = numericTextDiff(this._chars, this._value);
      var prefixCount = diff.prefixCount;
      var suffixCount = diff.suffixCount;
      var middleLabels = diff.middleLabels;
      var middleLength = middleLabels.length;
      var oldMiddleEnd = this._chars.length - suffixCount;
      var nextLength = prefixCount + middleLength + suffixCount;

      if (!animated) {
        var nextChars = new Array(nextLength);
        var nextMiddleEnd = prefixCount + middleLength;
        for (var i = 0; i < prefixCount; i += 1) nextChars[i] = this._chars[i];
        for (var j = 0; j < middleLength; j += 1) {
          nextChars[prefixCount + j] = numericTextCreate("span", "char", middleLabels[j]);
        }
        for (var k = 0; k < suffixCount; k += 1) {
          nextChars[nextMiddleEnd + k] = this._chars[oldMiddleEnd + k];
        }
        for (var removeIndex = prefixCount; removeIndex < oldMiddleEnd; removeIndex += 1) {
          this._chars[removeIndex].remove();
        }
        this._prefix.replaceChildren.apply(this._prefix, nextChars.slice(0, prefixCount));
        this._middle.replaceChildren.apply(this._middle, nextChars.slice(prefixCount, nextMiddleEnd));
        this._suffix.replaceChildren.apply(this._suffix, nextChars.slice(nextMiddleEnd));
        this._chars = nextChars;
        return;
      }

      var trend = this.trend;
      if (!trend) {
        var currentNumber = parseFloat(this._value);
        var previousNumber = parseFloat(this._prevValue);
        trend = !Number.isNaN(currentNumber) && !Number.isNaN(previousNumber) && currentNumber > previousNumber
          ? 1
          : -1;
      }

      var beforePrefixRect = numericTextRect(this._prefix);
      var beforeMiddleRect = numericTextRect(this._middle);
      var beforeSuffixRect = numericTextRect(this._suffix);
      var exitX = 0;
      if (prefixCount < oldMiddleEnd) {
        var firstExit = this._chars[prefixCount];
        var exitParent = firstExit.parentElement;
        var parentRect = exitParent === this._prefix ? beforePrefixRect :
          exitParent === this._suffix ? beforeSuffixRect :
            beforeMiddleRect;
        exitX = this._isRTL
          ? parentRect.left + firstExit.offsetLeft + firstExit.offsetWidth
          : parentRect.left + firstExit.offsetLeft;
      }

      var updatedChars = new Array(nextLength);
      var exitingChars = [];
      for (var prefixIndex = 0; prefixIndex < prefixCount; prefixIndex += 1) {
        updatedChars[prefixIndex] = this._chars[prefixIndex];
      }
      for (var exitIndex = prefixCount; exitIndex < oldMiddleEnd; exitIndex += 1) {
        exitingChars.push(this._chars[exitIndex]);
      }
      var enteringChars = new Array(middleLength);
      for (var middleIndex = 0; middleIndex < middleLength; middleIndex += 1) {
        var char = numericTextCreate("span", "char", middleLabels[middleIndex]);
        enteringChars[middleIndex] = char;
        updatedChars[prefixCount + middleIndex] = char;
      }
      var suffixStart = prefixCount + middleLength;
      for (var suffixIndex = 0; suffixIndex < suffixCount; suffixIndex += 1) {
        updatedChars[suffixStart + suffixIndex] = this._chars[oldMiddleEnd + suffixIndex];
      }

      if (exitingChars.length) {
        var exitLayer = numericTextCreate("span");
        exitLayer.toggleAttribute("inert", true);
        exitingChars.forEach(function (char) { exitLayer.appendChild(char); });
        var exitRecord = [exitLayer, exitX];
        this._exitingChars.push(exitRecord);
        this.shadowRoot.appendChild(exitLayer);
        var remaining = exitingChars.length;
        var exitStagger = this._getStagger(exitingChars);
        var self = this;
        exitingChars.forEach(function (char, index) {
          self._animateChar(char, true, trend, index * exitStagger, function () {
            char.remove();
            remaining -= 1;
            if (remaining === 0) {
              exitLayer.remove();
              var recordIndex = self._exitingChars.indexOf(exitRecord);
              if (recordIndex !== -1) self._exitingChars.splice(recordIndex, 1);
            }
          });
        });
      }

      this._prefix.replaceChildren.apply(this._prefix, updatedChars.slice(0, prefixCount));
      this._middle.replaceChildren.apply(this._middle, enteringChars);
      this._suffix.replaceChildren.apply(this._suffix, updatedChars.slice(suffixStart));
      this._chars = updatedChars;

      numericTextCancel(this._prefix);
      numericTextCancel(this._suffix);
      var afterPrefixRect = numericTextRect(this._prefix);
      var afterSuffixRect = numericTextRect(this._suffix);
      var currentLeft = this._isRTL ? afterPrefixRect.right : afterPrefixRect.left;
      this._exitingChars.forEach(function (record) {
        var exitLayer = record[0];
        var previousX = record[1];
        exitLayer.style.transform = "translateX(" + (previousX - currentLeft) + "px)";
      });

      var enterStagger = this._getStagger(enteringChars);
      for (var enterIndex = 0; enterIndex < enteringChars.length; enterIndex += 1) {
        this._animateChar(enteringChars[enterIndex], false, trend, enterIndex * enterStagger);
      }
      numericTextSlideSection(
        this._prefix,
        this._getEdgeDx(beforePrefixRect, afterPrefixRect, beforeMiddleRect, true),
        this.transition
      );
      numericTextSlideSection(
        this._suffix,
        this._getEdgeDx(beforeSuffixRect, afterSuffixRect, beforeMiddleRect, false),
        this.transition
      );
    }

    _getStagger(chars) {
      var visibleCount = 0;
      chars.forEach(function (char) {
        if (char.textContent !== "\\u00a0") visibleCount += 1;
      });
      return this.transition.duration * NUMERIC_TEXT_MOTION.stagger / (visibleCount || 1);
    }

    _getEdgeDx(beforeRect, afterRect, middleRect, isPrefix) {
      if (this._isRTL === isPrefix) {
        return (beforeRect.width ? beforeRect.right : middleRect.right) - afterRect.right;
      }
      return (beforeRect.width ? beforeRect.left : middleRect.left) - afterRect.left;
    }

    _animateChar(char, exiting, trend, delay, onfinish) {
      if (char.textContent === "\\u00a0" || typeof char.animate !== "function") {
        if (exiting && onfinish) window.setTimeout(onfinish, this.transition.duration + delay);
        return;
      }
      var displaced = "translateY(" +
        ((exiting ? -1 : 1) * trend * NUMERIC_TEXT_MOTION.y) +
        "em) scale(" + NUMERIC_TEXT_MOTION.scale + ") rotateZ(" +
        NUMERIC_TEXT_MOTION.rotate + "deg)";
      var blurred = "blur(" + NUMERIC_TEXT_MOTION.blur + "em)";
      var keyframes = exiting
        ? { opacity: 0, transform: displaced, filter: blurred }
        : { opacity: [0, 1], transform: [displaced, ""], filter: [blurred, ""] };
      var animation = char.animate(keyframes, {
        duration: this.transition.duration,
        easing: this.transition.easing,
        fill: "both",
        delay: delay,
      });
      if (onfinish) animation.onfinish = onfinish;
    }
  }

  if (!customElements.get("traccia-numeric-text")) {
    customElements.define("traccia-numeric-text", TracciaNumericText);
  }

  function renderNumericText(el, text) {
    if (!el) return;
    text = String(text);
    var previous = el.dataset.outputText || "";
    var readout = el.querySelector("traccia-numeric-text");
    if (!readout) {
      readout = document.createElement("traccia-numeric-text");
      readout.setAttribute("role", "img");
      readout.className = "numeric-text-readout";
      readout.setOptions({ transition: NUMERIC_TEXT_READOUT_TRANSITION });
      el.replaceChildren(readout);
    }
    var shouldAnimate = previous !== text && !document.body.classList.contains("viewer-loading");
    el.dataset.outputText = text;
    el.setAttribute("aria-label", text);
    readout.setAttribute("aria-label", text);
    readout.update(text, shouldAnimate);
  }

  function setSettingsOutput(el, text) {
    renderNumericText(el, text);
  }

  function syncSettingsControls() {
    if (!dom.setting_dim) return;
    dom.setting_dim.value = String(viewSettings.contextDimming);
    syncRangeProgress(dom.setting_dim);
    setSettingsOutput(dom.setting_dim_value, percentText(viewSettings.contextDimming));
    dom.setting_node_size.value = String(viewSettings.nodeScale);
    syncRangeProgress(dom.setting_node_size);
    setSettingsOutput(dom.setting_node_size_value, percentText(viewSettings.nodeScale));
    dom.setting_line_strength.value = String(viewSettings.lineStrength);
    syncRangeProgress(dom.setting_line_strength);
    setSettingsOutput(dom.setting_line_strength_value, percentText(viewSettings.lineStrength));
    dom.setting_label_density.value = String(viewSettings.labelDensity);
    syncRangeProgress(dom.setting_label_density);
    setSettingsOutput(dom.setting_label_density_value, percentText(viewSettings.labelDensity));
    dom.setting_separation.value = String(viewSettings.separation);
    syncRangeProgress(dom.setting_separation);
    setSettingsOutput(dom.setting_separation_value, percentText(viewSettings.separation));
    if (dom.setting_show_lines) dom.setting_show_lines.checked = !!viewSettings.showLines;
    if (dom.setting_show_categories) dom.setting_show_categories.checked = !!viewSettings.showCategories;
    if (dom.setting_show_category_labels) dom.setting_show_category_labels.checked = !!viewSettings.showCategoryLabels;
    if (dom.setting_show_skill_labels) dom.setting_show_skill_labels.checked = !!viewSettings.showSkillLabels;
    if (dom.setting_show_level_badges) dom.setting_show_level_badges.checked = !!viewSettings.showLevelBadges;
    if (dom.setting_show_background_dots) dom.setting_show_background_dots.checked = !!viewSettings.showBackgroundDots;
    applyBackgroundDotsSetting();
  }

  function applyBackgroundDotsSetting() {
    if (!dom.viewport) return;
    dom.viewport.dataset.dots = viewSettings.showBackgroundDots ? "true" : "false";
  }

  function applyViewSettingsChange(recomputeLayout) {
    viewSettings = normalizeViewSettings(viewSettings);
    saveViewSettings();
    syncSettingsControls();
    if (recomputeLayout) {
      layoutAndRender();
      return;
    }
    renderGraph();
    renderMinimapViewport();
  }

  function emptyFilters() {
    return {
      search: filters.search,
      domain: "",
      status: "",
      freshness: "",
      minConfidence: 0,
      maxSkills: "all",
      evidenceType: "",
    };
  }

  function filtersMatchDefault() {
    return filters.search === DEFAULT_FILTERS.search &&
      filters.domain === DEFAULT_FILTERS.domain &&
      filters.status === DEFAULT_FILTERS.status &&
      filters.freshness === DEFAULT_FILTERS.freshness &&
      filters.minConfidence === DEFAULT_FILTERS.minConfidence &&
      filters.maxSkills === DEFAULT_FILTERS.maxSkills &&
      filters.evidenceType === DEFAULT_FILTERS.evidenceType;
  }

  function applyScopeLimit(baseNodes) {
    var limit = filters.maxSkills;
    if (limit === "all" || limit == null) return baseNodes;
    limit = parseInt(limit, 10);
    if (!Number.isFinite(limit) || limit <= 0 || baseNodes.length <= limit) return baseNodes;

    // A skill tree reads best when branches stay balanced. Pick the strongest
    // candidates inside each visual branch, then round-robin across branches
    // so one overrepresented domain cannot consume the whole first view.
    var byBranch = {};
    baseNodes.forEach(function (node) {
      var branch = (node._visualGroup || "General Craft") + " / " + branchTopicForNode(node);
      if (!byBranch[branch]) byBranch[branch] = [];
      byBranch[branch].push(node);
    });

    Object.keys(byBranch).forEach(function (branch) {
      byBranch[branch].sort(compareTreeRank);
    });

    var branches = Object.keys(byBranch).sort(function (a, b) {
      return nodeTreeRank(byBranch[b][0]) - nodeTreeRank(byBranch[a][0]) ||
        byBranch[b].length - byBranch[a].length ||
        a.localeCompare(b);
    });

    var picked = [];
    var seen = new Set();
    var exhausted = false;
    while (picked.length < limit && !exhausted) {
      exhausted = true;
      branches.forEach(function (branch) {
        if (picked.length >= limit) return;
        var node = byBranch[branch].shift();
        if (!node) return;
        exhausted = false;
        if (seen.has(node.id)) return;
        seen.add(node.id);
        picked.push(node);
      });
    }
    return picked;
  }

  function compareTreeRank(a, b) {
    return nodeTreeRank(b) - nodeTreeRank(a) ||
      (a.name || a.id || "").localeCompare(b.name || b.id || "");
  }

  function nodeTreeRank(node) {
    if (typeof node._treeRank === "number") return node._treeRank;
    var ps = node.provenanceSummary || {};
    var evidenceCount = ps.evidenceCount || 0;
    var freshness = (node.freshness || "").toLowerCase();
    var freshnessScore = freshness === "active" ? 18 :
      freshness === "warming" ? 14 :
      freshness === "stale" ? -8 :
      freshness === "historical" ? -18 : 0;
    node._treeRank = (node.featured ? 1000 : 0) +
      (node.kind === "domain" ? 800 : 0) +
      (node.level || 0) * 100 +
      (node.historicalPeakLevel || node.level || 0) * 18 +
      (node.confidence || 0) * 120 +
      (node.coreSelfCentrality || 0) * 90 +
      Math.min(evidenceCount, 16) * 8 +
      freshnessScore;
    return node._treeRank;
  }

  function matchesFilters(node) {
    if (node.kind === "domain") return false;
    if (filters.domain && node._visualGroup !== filters.domain) return false;
    if (filters.status) {
      var st = (node.status || "active").toLowerCase();
      if (filters.status === "stale" && st !== "stale") return false;
      if (filters.status === "active" && st !== "active") return false;
      if (filters.status === "historical" && (node.freshness || "").toLowerCase() !== "historical") return false;
    }
    if (filters.freshness) {
      var freshness = (node.freshness || "").toLowerCase();
      if (filters.freshness === "current") {
        if (freshness !== "active" && freshness !== "warming") return false;
      } else if (freshness !== filters.freshness) {
        return false;
      }
    }
    if ((node.confidence || 0) < filters.minConfidence) return false;
    if (filters.evidenceType) {
      var types = (node.provenanceSummary || {}).evidenceTypes || {};
      if (!types[filters.evidenceType]) return false;
    }
    if (filters.search && !nodeMatchesSearch(node, filters.search)) return false;
    return true;
  }

  function nodeMatchesSearch(node, query) {
    var q = query.toLowerCase().trim();
    if (!q) return true;
    if ((node.name || "").toLowerCase().indexOf(q) !== -1) return true;
    if ((node._displayName || "").toLowerCase().indexOf(q) !== -1) return true;
    if ((node.domain || "").toLowerCase().indexOf(q) !== -1) return true;
    if ((node._visualGroup || "").toLowerCase().indexOf(q) !== -1) return true;
    if ((node._branchTopic || "").toLowerCase().indexOf(q) !== -1) return true;
    if ((node.description || "").toLowerCase().indexOf(q) !== -1) return true;
    return false;
  }

  function updateEmptyState() {
    var displayed = getDisplayedNodeIds();
    dom.empty_state.hidden = displayed.size > 0;
    updateLegendStats(displayed.size);
  }

  function updateLegendStats(visibleCount) {
    if (!dom.legend_stats) return;
    var total = nodes.length;
    if (visibleCount < total) {
      dom.legend_stats.textContent = visibleCount + " / " + total + " skills";
      return;
    }
    dom.legend_stats.textContent = total + " skills";
  }

  // --- Domain collapse/expand (decision 34: session-level for public viewer) ---
  function isDomainCollapsed(domain) {
    return !!collapsedDomains[domain];
  }

  function isNodeCollapsed(node) {
    return isDomainCollapsed(node.domain) || isDomainCollapsed(node._visualGroup);
  }

  function toggleDomain(domain) {
    collapsedDomains[domain] = !collapsedDomains[domain];
    renderGraph();
    updateEmptyState();
    sfx.domainToggle(!collapsedDomains[domain]);
  }

  function focusDomain(domain, fromInteraction) {
    var needsLayoutRefresh = !layoutCache || !filtersMatchDefault() || !!collapsedDomains[domain];
    filters = defaultFilters();
    filters.domain = "";
    collapsedDomains[domain] = false;
    selectedNodeId = null;
    focusedNodeIds.clear();
    activeFocus = null;

    dom.search_input.value = "";
    setSearchClearVisible(false);
    syncFilterControls();
    clearHash();
    if (needsLayoutRefresh) computeLayout();
    activeFocus = buildDomainFocus(domain);
    focusedNodeIds = new Set(activeFocus.labelIds);
    startFocusTransition(buildFocusDisplayState(activeFocus), fromInteraction);
    if (needsLayoutRefresh) {
      renderMinimap();
      updateEmptyState();
    } else {
      renderMinimapViewport();
    }
    var focusForDock = activeFocus;
    requestAnimationFrame(function () {
      if (activeFocus !== focusForDock) return;
      openFocusDock(focusForDock);
      requestAnimationFrame(function () {
        if (activeFocus !== focusForDock) return;
        if (fromInteraction) {
          setTimeout(function () { sfx.filterSwitch(); }, 8000);
        }
      });
    });
  }

  function focusTreeNode(id, fromInteraction) {
    var treeNode = getSyntheticTreeNode(id);
    if (!treeNode) return;
    var needsLayoutRefresh = !layoutCache || !filtersMatchDefault() ||
      !!(treeNode._visualGroup && collapsedDomains[treeNode._visualGroup]);
    filters = defaultFilters();
    filters.domain = "";
    if (treeNode._visualGroup) collapsedDomains[treeNode._visualGroup] = false;
    selectedNodeId = null;
    focusedNodeIds.clear();
    activeFocus = null;

    dom.search_input.value = "";
    setSearchClearVisible(false);
    syncFilterControls();
    clearHash();
    if (needsLayoutRefresh) computeLayout();

    activeFocus = buildTreeFocus(id);
    if (!activeFocus) return;
    focusedNodeIds = new Set(activeFocus.labelIds);
    focusedNodeIds.add(id);
    startFocusTransition(buildFocusDisplayState(activeFocus), fromInteraction);
    if (needsLayoutRefresh) {
      renderMinimap();
      updateEmptyState();
    } else {
      renderMinimapViewport();
    }
    var focusForDock = activeFocus;
    requestAnimationFrame(function () {
      if (activeFocus !== focusForDock) return;
      openFocusDock(focusForDock);
      if (fromInteraction) sfx.filterSwitch();
    });
  }

  // --- Selection & focus path ---
  function selectNode(id, fromInteraction) {
    selectedNodeId = id;
    focusedNodeIds = computeFocusPath(id);
    activeFocus = buildNodeFocus(id);

    startFocusTransition(buildFocusDisplayState(activeFocus), fromInteraction);
    centerOnNode(id, fromInteraction);
    openDrawer(id);

    if (fromInteraction) {
      sfx.nodeSelect();
    }
    updateHash(id);
  }

  function deselectNode() {
    clearCommittedFocus(true);
  }

  function clearCommittedFocus(animated) {
    selectedNodeId = null;
    focusedNodeIds.clear();
    activeFocus = null;
    startFocusTransition(emptyFocusDisplay(), !!animated);
    closeDrawer();
    clearHash();
  }

  function computeFocusPath(nodeId) {
    var ids = new Set([nodeId]);
    if (!layoutCache) return ids;
    var current = nodeId;
    while (layoutCache.branchParents[current]) {
      var parentId = layoutCache.branchParents[current];
      ids.add(parentId);
      var siblings = layoutCache.childrenByParent[parentId] || [];
      siblings.slice(0, 14).forEach(function (siblingId) {
        if (nodeById.has(siblingId)) ids.add(siblingId);
      });
      current = parentId;
    }
    return ids;
  }

  function centerOnNode(id, animated) {
    if (!layoutCache) return;
    var p = getDisplayPoint(id);
    if (!p) return;

    var rect = dom.canvas.getBoundingClientRect();
    var detailInset = selectionDetailInset(rect);
    var cx = (rect.width - detailInset) / 2;
    var cy = rect.height / 2;
    var targetScale = selectedNodeId === id ? Math.max(viewState.scale, Math.min(0.58, VIEW.maxScale)) : viewState.scale;
    var target = {
      x: cx - p.x * targetScale,
      y: cy - p.y * targetScale,
      scale: targetScale,
    };

    if (!animated || prefersReducedMotion()) {
      stopViewTween();
      stopCameraAnimation();
      setViewImmediate(target);
      scheduleViewUpdate(true);
      scheduleSettledCanvasRedraw(0);
      return;
    }

    animateViewTo(target, 240);
  }

  function centerOnDomain(domain, animated) {
    if (!layoutCache) return;
    var bbox = layoutCache.domainBBoxes[domain];
    if (!bbox) {
      resetView(animated);
      return;
    }

    var rect = dom.canvas.getBoundingClientRect();
    var padding = viewportFitPadding(rect);
    var availableWidth = Math.max(1, rect.width - padding.x * 2);
    var availableHeight = Math.max(1, rect.height - padding.y * 2);
    var scale = Math.min(
      availableWidth / Math.max(1, bbox.width),
      availableHeight / Math.max(1, bbox.height),
      0.82
    );
    scale = Math.max(scale, VIEW.minScale);
    var target = {
      x: rect.width / 2 - bbox.centerX * scale,
      y: rect.height / 2 - bbox.centerY * scale,
      scale: scale,
    };

    if (animated && !prefersReducedMotion()) {
      animateViewTo(target, 240);
      return;
    }
    setViewImmediate(target);
    scheduleViewUpdate(true, true);
  }

  function selectionDetailInset(rect) {
    if (!window.matchMedia("(min-width: 769px)").matches) return 0;
    return Math.min(390, Math.max(300, rect.width * 0.22));
  }

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function stopViewTween() {
    viewTweenToken += 1;
    if (viewTweenFrame) {
      cancelAnimationFrame(viewTweenFrame);
      viewTweenFrame = null;
    }
  }

  function animateViewTo(target, durationMs) {
    stopViewTween();
    stopCameraAnimation();
    targetViewState = cloneViewState(target);
    var token = viewTweenToken;
    sanitizeViewState();
    var start = cloneViewState(viewState);
    var startTime = performance.now();

    function step(now) {
      if (token !== viewTweenToken) return;
      var t = Math.min(1, (now - startTime) / durationMs);
      var eased = easeInOut(t);
      viewState.x = lerp(start.x, target.x, eased);
      viewState.y = lerp(start.y, target.y, eased);
      viewState.scale = safeScaleValue(lerp(start.scale, targetViewState.scale, eased));
      targetViewState = cloneViewState(target);
      scheduleViewUpdate(t === 1 && !(focusDisplay && focusDisplay.active), false);
      if (t < 1) {
        viewTweenFrame = requestAnimationFrame(step);
        return;
      }
      viewTweenFrame = null;
      setViewImmediate(target);
      scheduleSettledCanvasRedraw(focusDisplay && focusDisplay.active ? 8000 : 0);
    }

    viewTweenFrame = requestAnimationFrame(step);
  }

  function cloneViewState(state) {
    return {
      x: Number.isFinite(state.x) ? state.x : 0,
      y: Number.isFinite(state.y) ? state.y : 0,
      scale: safeScaleValue(state.scale),
    };
  }

  function safeScaleValue(value) {
    return Number.isFinite(value) && value > 0 ?
      Math.max(VIEW.minScale, Math.min(VIEW.maxScale, value)) :
      1;
  }

  function safeViewScale() {
    return safeScaleValue(viewState.scale);
  }

  function levelTextGraphPx(graphRadius) {
    return Math.max(3.8, Math.min(7.2, graphRadius * 0.54));
  }

  function canvasLevelTextFontSize(graphRadius) {
    return levelTextGraphPx(graphRadius);
  }

  function sanitizeViewState() {
    if (!Number.isFinite(viewState.x)) viewState.x = 0;
    if (!Number.isFinite(viewState.y)) viewState.y = 0;
    viewState.scale = safeScaleValue(viewState.scale);
  }

  function setViewImmediate(target) {
    viewState = cloneViewState(target);
    targetViewState = cloneViewState(target);
  }

  function syncTargetToCurrentView() {
    targetViewState = cloneViewState(viewState);
  }

  function stopPanInertia() {
    if (panInertiaFrame) {
      cancelAnimationFrame(panInertiaFrame);
      panInertiaFrame = null;
    }
    panSamples = [];
  }

  function stopCameraAnimation() {
    cameraGestureActive = false;
    wheelCameraActive = false;
    wheelZoomAnchor = null;
    if (wheelCameraTimer) {
      clearTimeout(wheelCameraTimer);
      wheelCameraTimer = null;
    }
    stopPanInertia();
    syncTargetToCurrentView();
  }

  function isCameraAnimating() {
    return cameraGestureActive || wheelCameraActive || !!panInertiaFrame || !!viewTweenFrame;
  }

  function holdWheelCameraActive(delay) {
    wheelCameraActive = true;
    if (wheelCameraTimer) clearTimeout(wheelCameraTimer);
    wheelCameraTimer = setTimeout(function () {
      wheelCameraTimer = null;
      wheelCameraActive = false;
      wheelZoomAnchor = null;
      scheduleViewUpdate(true, true);
    }, Math.max(80, delay || 0));
  }

  function setDirectView(target) {
    setViewImmediate(target);
    scheduleViewUpdate(false, false);
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function easeInOut(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function applyViewTransform() {
    sanitizeViewState();
    var cameraAnimating = isCameraAnimating();
    if (dom.graph_svg) {
      dom.graph_svg.classList.toggle("camera-moving", cameraAnimating);
    }
    resetSvgBitmapTransform();
    if (cameraAnimating && canvasBitmap && canvasCtx) {
      // Active movement has one visual camera: #graph-camera. The SVG overlay
      // stays at the same retained base view as the visible canvas bitmap, so
      // nodes, labels, lines, hit targets, and hover rings cannot be composited
      // from different camera states.
      setGraphZoomTransform(activeCameraBaseViewState());
      applyCameraCompositorTransform();
    } else {
      resetCameraCompositorTransform();
      setGraphZoomTransform(viewState);
    }
    syncDotBackgroundTransform();
  }

  function setGraphZoomTransform(state) {
    if (!dom.graph_zoom) return;
    var scale = safeScaleValue(state && state.scale);
    var x = state && Number.isFinite(state.x) ? state.x : 0;
    var y = state && Number.isFinite(state.y) ? state.y : 0;
    dom.graph_zoom.setAttribute("transform", "translate(" + x + "," + y + ") scale(" + scale + ")");
  }

  function resetSvgBitmapTransform() {
    if (!dom.graph_svg) return;
    dom.graph_svg.style.transform = "translate3d(0, 0, 0) scale(1)";
  }

  function syncDotBackgroundTransform() {
    if (!dom.viewport) return;
    var step = 28;
    var x = ((viewState.x % step) + step) % step;
    var y = ((viewState.y % step) + step) % step;
    dom.viewport.style.setProperty("--dot-offset-x", x + "px");
    dom.viewport.style.setProperty("--dot-offset-y", y + "px");
  }

  // scheduleViewUpdate batches all view-dependent work into one rAF:
  // - SVG overlay transform (cheap, just a setAttribute)
  // - Canvas bitmap transform (cheap compositor work during input)
  // - Optional canvas redraw (expensive all-node pixel pass, deferred on input)
  // - Minimap viewport update
  function scheduleViewUpdate(refreshCanvasLabels, redrawCanvas) {
    if (refreshCanvasLabels || redrawCanvas !== false) canvasRedrawPending = true;
    if (viewFrame) return;
    viewFrame = requestAnimationFrame(function () {
      viewFrame = null;
      var cameraAnimating = isCameraAnimating();
      applyCanvasBitmapTransform();
      applyViewTransform();
      if (canvasRedrawPending && !cameraAnimating) {
        canvasRedrawPending = false;
        renderCanvas();
      }
      if (!cameraAnimating) renderMinimapViewport();
    });
  }

  // --- Disclosure state helpers ---
  function readRootDurationMs(name, fallbackMs) {
    var raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    if (!raw) return fallbackMs;
    if (raw.endsWith("ms")) return parseFloat(raw);
    if (raw.endsWith("s")) return parseFloat(raw) * 1000;
    var parsed = parseFloat(raw);
    return Number.isFinite(parsed) ? parsed : fallbackMs;
  }

  function clearPanelHideTimer(el) {
    var timer = panelHideTimers.get(el);
    if (timer) {
      clearTimeout(timer);
      panelHideTimers.delete(el);
    }
  }

  function setPanelOpen(el, open) {
    if (!el) return;
    clearPanelHideTimer(el);
    if (open) {
      el.hidden = false;
      requestAnimationFrame(function () {
        if (!el.hidden) el.dataset.open = "true";
      });
      return;
    }
    el.dataset.open = "false";
    var closeMs = readRootDurationMs("--panel-close-dur", 160);
    panelHideTimers.set(el, setTimeout(function () {
      panelHideTimers.delete(el);
      if (el.dataset.open !== "true") el.hidden = true;
    }, closeMs + 20));
  }

  function togglePanel(el) {
    setPanelOpen(el, el.hidden || el.dataset.open !== "true");
  }

  function syncDisclosureButton(button, panel) {
    if (!button || !panel) return;
    button.setAttribute("aria-pressed", String(panel.dataset.open === "true"));
  }

  function setSearchClearVisible(visible) {
    if (!dom.search_clear) return;
    clearPanelHideTimer(dom.search_clear);
    if (visible) {
      dom.search_clear.hidden = false;
      requestAnimationFrame(function () {
        if (!dom.search_clear.hidden) dom.search_clear.dataset.visible = "true";
      });
      return;
    }
    dom.search_clear.dataset.visible = "false";
    panelHideTimers.set(dom.search_clear, setTimeout(function () {
      panelHideTimers.delete(dom.search_clear);
      if (dom.search_clear.dataset.visible !== "true") {
        dom.search_clear.hidden = true;
      }
    }, 180));
  }

  function setDetailSurfaceOpen(el, open) {
    if (!el) return;
    clearPanelHideTimer(el);
    if (open) {
      el.hidden = false;
      el.setAttribute("aria-hidden", "false");
      requestAnimationFrame(function () {
        if (el.hidden) return;
        el.classList.add("open");
        el.dataset.open = "true";
      });
      return;
    }
    el.classList.remove("open");
    el.dataset.open = "false";
    var closeMs = readRootDurationMs("--panel-close-dur", 160);
    panelHideTimers.set(el, setTimeout(function () {
      panelHideTimers.delete(el);
      if (el.dataset.open === "true") return;
      el.setAttribute("aria-hidden", "true");
      el.hidden = true;
    }, closeMs + 20));
  }

  // --- Drawer / sheet ---
  function openFocusDock(focus) {
    if (!focus) return;
    if (focusDockHydrationTimer) {
      clearTimeout(focusDockHydrationTimer);
      focusDockHydrationTimer = null;
    }
    var html = buildFocusDockHtml(focus, 8);
    var title = focus.title || "Selection";
    var desktop = window.matchMedia("(min-width: 769px)").matches;

    dom.drawer_title.textContent = title;
    dom.drawer_body.innerHTML = desktop ? html : "";
    if (desktop) revealDetailContent(dom.drawer_body);
    setDetailSurfaceOpen(dom.drawer, true);

    dom.sheet_title.textContent = title;
    dom.sheet_body.innerHTML = desktop ? "" : html;
    if (!desktop) revealDetailContent(dom.sheet_body);
    setDetailSurfaceOpen(dom.sheet, true);

    function hydrateFocusDockWhenIdle() {
      focusDockHydrationTimer = null;
      if (activeFocus !== focus) return;
      if (isCameraAnimating()) {
        focusDockHydrationTimer = setTimeout(hydrateFocusDockWhenIdle, 1200);
        return;
      }
      var hydratedHtml = buildFocusDockHtml(focus);
      dom.drawer_body.innerHTML = hydratedHtml;
      dom.sheet_body.innerHTML = hydratedHtml;
    }
    focusDockHydrationTimer = setTimeout(hydrateFocusDockWhenIdle, 30000);
  }

  function buildFocusDockHtml(focus, rowLimit) {
    var shown = focus.shownCount || 0;
    var total = focus.allCount || shown;
    var rows = typeof rowLimit === "number" ? (focus.shelfRows || []).slice(0, rowLimit) : (focus.shelfRows || []);
    var parts = [];
    parts.push(
      '<div class="detail-kicker"><span class="detail-domain">' +
      escapeHtml(focus.title || "Selection") +
      '</span><span class="detail-kind">Focus</span></div>'
    );
    parts.push(
      '<div class="detail-answer focus-summary"><p class="detail-answer__label">Scope</p>' +
      '<div class="detail-answer__value"><strong>' +
      escapeHtml(String(Math.min(shown, rows.length || shown))) +
      '</strong> prioritized on map from <strong>' +
      escapeHtml(String(total)) +
      '</strong> matching skills.</div></div>'
    );
    if (!rows.length) {
      parts.push(
        '<div class="detail-answer"><p class="detail-answer__label">Skills</p>' +
        '<div class="detail-answer__value">No visible skills match this focus.</div></div>'
      );
      return parts.join("");
    }
    parts.push('<div class="detail-answer"><p class="detail-answer__label">Ranked skills</p>');
    parts.push('<div class="focus-shelf" role="list">');
    rows.forEach(function (node, index) {
      parts.push(
        '<button class="detail-next-item focus-row" type="button" role="listitem" data-next-node-id="' +
        escapeHtml(node.id) +
        '"><span class="detail-next-item__name">' +
        escapeHtml(displayNameForNode(node)) +
        '</span><span class="detail-next-item__meta">' +
        escapeHtml(focusRowMeta(node, index)) +
        "</span></button>"
      );
    });
    if (total > shown) {
      parts.push(
        '<p class="focus-count">' +
        escapeHtml(String(total - shown)) +
        " more matching skills are outside the current map scope.</p>"
      );
    }
    parts.push("</div></div>");
    return parts.join("");
  }

  function focusRowMeta(node, index) {
    var pieces = ["#" + (index + 1), "L" + (node.level || 0)];
    if (node.confidence != null) pieces.push(Math.round(node.confidence * 100) + "%");
    if (node._branchTopic) pieces.push(node._branchTopic);
    return pieces.join(" / ");
  }

  function openDrawer(id) {
    var node = nodeById.get(id);
    if (!node) return;

    var html = buildNodeDetail(node);

    // Desktop drawer
    dom.drawer_title.textContent = displayNameForNode(node) || id;
    dom.drawer_body.innerHTML = html;
    revealDetailContent(dom.drawer_body);
    setDetailSurfaceOpen(dom.drawer, true);

    // Mobile sheet
    dom.sheet_title.textContent = displayNameForNode(node) || id;
    dom.sheet_body.innerHTML = html;
    revealDetailContent(dom.sheet_body);
    setDetailSurfaceOpen(dom.sheet, true);

    sfx.drawerOpen();
  }

  function revealDetailContent(container) {
    if (!container) return;
    var items = container.querySelectorAll(".detail-kicker, .detail-answer, .detail-more, .focus-row, .focus-count");
    items.forEach(function (item, index) {
      item.classList.add("detail-reveal", "is-new");
      item.style.transitionDelay = Math.min(index, 5) * 35 + "ms";
    });
    requestAnimationFrame(function () {
      items.forEach(function (item) {
        item.classList.remove("is-new");
      });
    });
  }

  function closeDrawer() {
    setDetailSurfaceOpen(dom.drawer, false);
    setDetailSurfaceOpen(dom.sheet, false);
    sfx.drawerClose();
  }

  function buildNodeDetail(node) {
    var ps = node.provenanceSummary || {};
    var confidencePct = Math.round((node.confidence || 0) * 100);
    var ringClass = node.confidence >= 0.75 ? "ring--high" :
                    node.confidence >= 0.45 ? "ring--medium" : "ring--low";
    var ringColor = node.confidence >= 0.75 ? "#6f8f7d" :
                    node.confidence >= 0.45 ? "#38796c" : "var(--text-dim)";

    var parts = [];

    // First screen: public-field-backed Node Brief. Unsupported lines are
    // omitted instead of padded with generic filler.
    parts.push(
      '<div class="detail-kicker"><span class="detail-domain">' +
      escapeHtml(nodeAreaName(node)) + '</span><span class="detail-kind">' +
      escapeHtml(node.kind || "skill") + "</span></div>"
    );
    parts.push(detailLines("What", nodeWhatLines(node)));
    parts.push(detailLines("Trust", nodeTrustLines(node, confidencePct)));
    var evidenceLines = nodeEvidenceLines(node);
    if (evidenceLines.length) parts.push(detailLines("Evidence", evidenceLines));
    var nextHtml = nodeNextHtml(node);
    if (nextHtml) parts.push(detailBlock("Next", nextHtml));

    parts.push('<details class="detail-more"><summary>More node detail</summary><div class="detail-more__content">');

    // Raw source labels are still useful, but only after the scan-level answers.
    if (node.name && node.name !== displayNameForNode(node)) {
      parts.push(
        '<div class="detail-section"><h3>Source label</h3><p>' +
        escapeHtml(node.name) + "</p></div>"
      );
    }
    if (node.domain && node.domain !== nodeAreaName(node)) {
      parts.push(
        '<div class="detail-section"><h3>Source domain</h3><p>' +
        escapeHtml(node.domain) + "</p></div>"
      );
    }
    if (node._branchTopic) {
      parts.push(
        '<div class="detail-section"><h3>Branch topic</h3><p>' +
        escapeHtml(node._branchTopic) + "</p></div>"
      );
    }

    // Description
    if (node.description) {
      parts.push('<div class="detail-section"><h3>Description</h3><p>' + escapeHtml(node.description) + "</p></div>");
    }

    // Confidence bar
    parts.push(
      '<div class="detail-section"><h3>Confidence</h3>' +
      '<div class="detail-confidence-bar"><div class="detail-confidence-bar__fill ' + ringClass +
      '" style="--confidence-scale:' + Math.max(0, Math.min(1, confidencePct / 100)) + "; background:" + ringColor + '"></div></div>' +
      "<p>" + confidencePct + "% confidence</p></div>"
    );

    // Stats grid
    parts.push('<div class="detail-section"><h3>Skill metrics</h3><div class="detail-stats">');
    parts.push(statBlock("L" + (node.level || 0), "Current level"));
    parts.push(statBlock("L" + (node.historicalPeakLevel || node.level || 0), "Peak level"));
    parts.push(statBlock(formatFreshness(node.freshness), "Freshness"));
    if (node.coreSelfCentrality != null) {
      parts.push(statBlock((node.coreSelfCentrality * 100).toFixed(0) + "%", "Centrality"));
    }
    parts.push("</div></div>");

    // Provenance summary (public-safe, decision 49)
    if (ps.evidenceCount > 0) {
      parts.push('<div class="detail-section"><h3>Evidence summary</h3>');
      parts.push(statBlock(ps.evidenceCount, "Evidence items"));
      parts.push(statBlock(ps.strongEvidenceCount || 0, "Strong"));
      parts.push("</div>");

      if (ps.evidenceTypes && Object.keys(ps.evidenceTypes).length) {
        parts.push(
          '<div class="detail-section"><h3>Evidence types</h3>' +
          detailSummaryRows(ps.evidenceTypes, function (t) { return t; }) +
          "</div>"
        );
      }

      if (ps.reliabilityTiers && Object.keys(ps.reliabilityTiers).length) {
        parts.push(
          '<div class="detail-section"><h3>Reliability tiers</h3>' +
          detailSummaryRows(ps.reliabilityTiers, function (t) { return t.replace("tier_", "tier "); }) +
          "</div>"
        );
      }

      if (ps.earliestAt || ps.latestAt) {
        parts.push('<div class="detail-section"><h3>Timeline</h3>');
        if (ps.earliestAt) parts.push("<p>Earliest evidence: " + escapeHtml(ps.earliestAt) + "</p>");
        if (ps.latestAt) parts.push("<p>Latest evidence: " + escapeHtml(ps.latestAt) + "</p>");
        parts.push("</div>");
      }
    } else {
      parts.push('<div class="detail-section"><h3>Evidence summary</h3><p>No public evidence summary available.</p></div>');
    }

    // Timeline fields
    var timelineParts = [];
    if (node.firstLearnedAt) timelineParts.push(["First learned", node.firstLearnedAt]);
    if (node.acquiredAt) timelineParts.push(["Acquired", node.acquiredAt]);
    if (node.lastEvidenceAt) timelineParts.push(["Last evidence", node.lastEvidenceAt]);
    if (node.historicalPeakAt) timelineParts.push(["Peak at", node.historicalPeakAt]);
    if (timelineParts.length) {
      parts.push('<div class="detail-section"><h3>Key dates</h3><dl class="detail-meta">');
      timelineParts.forEach(function (pair) {
        parts.push("<dt>" + escapeHtml(pair[0]) + "</dt><dd>" + escapeHtml(pair[1]) + "</dd>");
      });
      parts.push("</dl></div>");
    }

    parts.push("</div></details>");
    return parts.join("");
  }

  function detailLines(label, lines) {
    return detailBlock(label, lines.map(function (line) {
      return '<span class="detail-line">' + escapeHtml(line) + "</span>";
    }).join(""));
  }

  function detailBlock(label, bodyHtml) {
    return '<div class="detail-answer"><p class="detail-answer__label">' +
      escapeHtml(label) + '</p><div class="detail-answer__value">' + bodyHtml + "</div></div>";
  }

  function nodeWhatLines(node) {
    var lines = [];
    var area = nodeAreaName(node);
    var topic = node._branchTopic || "";
    var kind = node.kind || "skill";
    var level = node.level ? "L" + node.level : "";
    lines.push([kind, area, topic && topic !== area ? topic : "", level].filter(Boolean).join(" / "));
    if (node.description) lines.push(node.description);
    var label = displayNameForNode(node);
    if (!node.description && label) {
      lines.push('No public description exported; using display label "' + label + '".');
    }
    return lines;
  }

  function nodeTrustLines(node, confidencePct) {
    var lines = [];
    var confidenceLabel = confidencePct >= 75 ? "high confidence" :
      confidencePct >= 45 ? "medium confidence" : "low confidence";
    lines.push((confidencePct < 45 ? "Weak signal: " : "") + confidenceLabel + " (" + confidencePct + "%).");
    if (node.freshness) lines.push("Freshness: " + formatFreshness(node.freshness) + ".");
    if (node.provenanceSummary && node.provenanceSummary.latestAt) {
      lines.push("Last public signal: " + node.provenanceSummary.latestAt + ".");
    }
    if (node.historicalPeakLevel && node.level && node.historicalPeakLevel > node.level) {
      lines.push("Historical peak: L" + node.historicalPeakLevel + ".");
    }
    return lines;
  }

  function nodeEvidenceLines(node) {
    var ps = node.provenanceSummary || {};
    var lines = [];
    var count = ps.evidenceCount || 0;
    if (count) {
      var evidenceLine = count === 1 ? "1 public evidence item" : count + " public evidence items";
      if (ps.strongEvidenceCount) {
        evidenceLine += ", " + ps.strongEvidenceCount + " strong";
      }
      lines.push(evidenceLine + ".");
    }
    var types = topSummaryKeys(ps.evidenceTypes, 3);
    if (types.length) lines.push("Types: " + types.join(", ") + ".");
    var sources = topSummaryKeys(ps.sourceFamilies || ps.sourceCategories, 3);
    if (sources.length) lines.push("Sources: " + sources.join(", ") + ".");
    var tiers = topSummaryKeys(ps.reliabilityTiers, 2);
    if (tiers.length) lines.push("Reliability: " + tiers.join(", ") + ".");
    if (ps.earliestAt || ps.latestAt) {
      var range = ps.earliestAt && ps.latestAt && ps.earliestAt !== ps.latestAt ?
        ps.earliestAt + " to " + ps.latestAt :
        (ps.latestAt || ps.earliestAt);
      lines.push("Observed: " + range + ".");
    }
    return lines;
  }

  function nodeNextHtml(node) {
    var neighbors = connectedNodeSuggestions(node, 4);
    if (!neighbors.length) return "";
    return '<span class="detail-next-list">' + neighbors.map(function (item) {
      return '<button class="detail-next-item" type="button" data-next-node-id="' +
        escapeHtml(item.node.id) + '"><span class="detail-next-item__name">' +
        escapeHtml(displayNameForNode(item.node)) + '</span><span class="detail-next-item__meta">' +
        escapeHtml(item.meta) + "</span></button>";
    }).join("") + "</span>";
  }

  function connectedNodeSuggestions(node, limit) {
    var seen = new Set();
    return (adjacencyByNode.get(node.id) || [])
      .map(function (edge) {
        var otherId = edge.fromId === node.id ? edge.toId : edge.fromId;
        if (!otherId || seen.has(otherId)) return null;
        seen.add(otherId);
        var other = nodeById.get(otherId);
        if (!other || isNodeCollapsed(other)) return null;
        if (!isUsefulNextCandidate(node, other, edge)) return null;
        return { node: other, edge: edge, score: connectedNodeScore(node, other) };
      })
      .filter(Boolean)
      .sort(function (a, b) {
        return b.score - a.score ||
          displayNameForNode(a.node).localeCompare(displayNameForNode(b.node));
      })
      .slice(0, limit)
      .map(function (item) {
        return {
          node: item.node,
          meta: "Connected" + (item.node.confidence != null ? " / " + Math.round(item.node.confidence * 100) + "%" : ""),
        };
      });
  }

  function isUsefulNextCandidate(source, candidate, edge) {
    var kind = (candidate.kind || "").toLowerCase();
    if (kind === "domain" || kind === "root" || kind === "category" || kind === "cluster") return false;
    if (/^domain[._-]/.test(candidate.id || "")) return false;

    // Public exports currently contain many domain -> skill parent edges. For
    // an ordinary skill selection, the domain parent (for example Programming)
    // is not a useful "next" node, so it is filtered out. If the selected node
    // itself is a domain, its child skills remain useful suggestions.
    if ((source.kind || "").toLowerCase() !== "domain" && edge.edgeType === "parent_of") {
      return edge.fromId === source.id;
    }
    return true;
  }

  function connectedNodeScore(source, node) {
    var ps = node.provenanceSummary || {};
    var sameArea = nodeAreaName(source) === nodeAreaName(node) ? 20 : 0;
    return sameArea +
      (node.featured ? 100 : 0) +
      (node.level || 0) * 10 +
      (node.confidence || 0) * 20 +
      (node.coreSelfCentrality || 0) * 15 +
      Math.min(ps.evidenceCount || 0, 10);
  }

  function topSummaryKeys(summary, limit) {
    if (!summary) return [];
    return Object.keys(summary)
      .sort(function (a, b) {
        return (summary[b] || 0) - (summary[a] || 0) || a.localeCompare(b);
      })
      .slice(0, limit)
      .map(function (key) {
        return key.replace(/_/g, " ");
      });
  }

  function statBlock(value, label) {
    return '<div class="detail-stat"><div class="detail-stat__value">' + escapeHtml(String(value)) +
           '</div><div class="detail-stat__label">' + escapeHtml(label) + "</div></div>";
  }

  function detailSummaryRows(summary, labelFormatter) {
    var keys = Object.keys(summary || {}).sort(function (a, b) {
      return (summary[b] || 0) - (summary[a] || 0) || a.localeCompare(b);
    });
    if (!keys.length) return "";
    return '<dl class="detail-list">' + keys.map(function (key) {
      var label = labelFormatter ? labelFormatter(key) : key;
      return "<dt>" + escapeHtml(String(label).replace(/_/g, " ")) + "</dt><dd>" +
        escapeHtml(String(summary[key] || 0)) + "</dd>";
    }).join("") + "</dl>";
  }

  function formatFreshness(f) {
    var map = { active: "Active", warming: "Warming", stale: "Stale", historical: "Historical" };
    return map[(f || "").toLowerCase()] || f || "Unknown";
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // --- Minimap ---
  function renderMinimap() {
    if (!layoutCache) return;
    var ns = "http://www.w3.org/2000/svg";
    var fragment = document.createDocumentFragment();
    var pad = 80;
    var bounds = layoutCache.bounds;
    var minX = bounds.minX - pad;
    var minY = bounds.minY - pad;
    var w = layoutCache.totalWidth + pad * 2;
    var h = layoutCache.totalHeight + pad * 2;
    dom.minimap_svg.setAttribute("viewBox", minX + " " + minY + " " + w + " " + h);

    // Nodes as small dots
    var step = Math.max(1, Math.ceil(nodes.length / VIEW.maxMinimapDots));
    nodes.forEach(function (node, index) {
      if (index % step !== 0 && node.id !== selectedNodeId) return;
      var p = layoutCache.positions[node.id];
      if (!p) return;
      var dot = document.createElementNS(ns, "circle");
      dot.setAttribute("cx", p.x);
      dot.setAttribute("cy", p.y);
      dot.setAttribute("r", node.id === selectedNodeId ? 4 : 2);
      dot.setAttribute("fill", stripVarColor(nodeColor(node)));
      fragment.appendChild(dot);
    });

    // Viewport rect
    var rect = document.createElementNS(ns, "rect");
    rect.setAttribute("class", "minimap__viewport");
    rect.setAttribute("id", "minimap-viewport-rect");
    fragment.appendChild(rect);
    dom.minimap_svg.replaceChildren(fragment);

    renderMinimapViewport();
  }

  function renderMinimapViewport() {
    var rectEl = document.getElementById("minimap-viewport-rect");
    if (!rectEl || !dom.canvas) return;
    sanitizeViewState();
    var canvasRect = dom.canvas.getBoundingClientRect();
    var viewScale = safeViewScale();
    // Convert canvas viewport back to graph coordinates
    var gx = -viewState.x / viewScale;
    var gy = -viewState.y / viewScale;
    var gw = Math.max(0, canvasRect.width / viewScale);
    var gh = Math.max(0, canvasRect.height / viewScale);
    rectEl.setAttribute("x", gx);
    rectEl.setAttribute("y", gy);
    rectEl.setAttribute("width", gw);
    rectEl.setAttribute("height", gh);
  }

  function stripVarColor(c) {
    return c || "var(--text-dim)";
  }

  // --- Legend ---
  function renderLegend() {
    var list = dom.legend.querySelector("#legend-domains");
    list.innerHTML = "";
    domains.forEach(function (d) {
      var li = document.createElement("li");
      var swatch = document.createElement("span");
      swatch.className = "dot";
      swatch.style.background = stripVarColor(domainColorMap[d]);
      li.appendChild(swatch);
      li.appendChild(document.createTextNode(visualGroupDisplayName(d)));
      list.appendChild(li);
    });
  }

  // --- Filter bar population ---
  function renderFilters() {
    // Domains
    domains.forEach(function (d) {
      var opt = document.createElement("option");
      opt.value = d;
      opt.textContent = visualGroupDisplayName(d);
      dom.filter_domain.appendChild(opt);
    });

    // Evidence types
    var evidenceTypes = {};
    nodes.forEach(function (n) {
      var types = (n.provenanceSummary || {}).evidenceTypes || {};
      Object.keys(types).forEach(function (t) { evidenceTypes[t] = true; });
    });
    Object.keys(evidenceTypes).sort().forEach(function (t) {
      var opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t.replace(/_/g, " ");
      dom.filter_evidence.appendChild(opt);
    });
    syncFilterControls();
  }

  function syncFilterControls() {
    dom.filter_domain.value = filters.domain;
    dom.filter_status.value = filters.status;
    dom.filter_freshness.value = filters.freshness;
    dom.filter_scope.value = String(filters.maxSkills);
    dom.filter_confidence.value = filters.minConfidence;
    syncRangeProgress(dom.filter_confidence);
    renderNumericText(dom.filter_confidence_value, percentText(filters.minConfidence));
    dom.filter_evidence.value = filters.evidenceType;
  }

  // --- Pan & Zoom ---
  function initPanZoom() {
    var isPanning = false;
    var pendingPan = false;
    var startX, startY, startViewX, startViewY;

    dom.canvas.addEventListener("mousedown", function (e) {
      if (e.button !== 0) return;
      if (e.target.closest(".domain-label")) return;
      stopViewTween();
      stopCameraAnimation();
      resetPanSamples();
      cameraGestureActive = false;
      pendingPan = true;
      isPanning = !e.target.closest(".graph-node");
      startX = e.clientX;
      startY = e.clientY;
      startViewX = viewState.x;
      startViewY = viewState.y;
      if (isPanning) {
        cameraGestureActive = true;
        dom.canvas.classList.add("panning");
      }
      recordPanSample(startViewX, startViewY, performance.now());
      sfx.unlock();
    });

    window.addEventListener("mousemove", function (e) {
      if (!pendingPan && !isPanning) return;
      var dx = e.clientX - startX;
      var dy = e.clientY - startY;
      var moved = Math.hypot(dx, dy);
      if (!isPanning && moved >= DRAG_SELECT_THRESHOLD) {
        isPanning = true;
        cameraGestureActive = true;
        suppressNextGraphClick = true;
        dom.canvas.classList.add("panning");
      }
      if (!isPanning) return;
      setDirectView({
        x: startViewX + (e.clientX - startX),
        y: startViewY + (e.clientY - startY),
        scale: viewState.scale,
      });
      recordPanSample(viewState.x, viewState.y, performance.now());
      // Panning should not redraw canvas labels on every mousemove.
      // Only cheap SVG/canvas bitmap transforms run per frame. The expensive
      // all-node canvas redraw refreshes after the interaction settles.
      scheduleSettledCanvasRedraw(VIEW.cameraPanSettleMs);
    });

    window.addEventListener("mouseup", function (e) {
      if (isPanning) {
        if (!startPanInertia()) scheduleSettledCanvasRedraw(VIEW.cameraPanSettleMs);
      }
      if (pendingPan && Math.hypot(e.clientX - startX, e.clientY - startY) >= DRAG_SELECT_THRESHOLD) {
        suppressNextGraphClick = true;
      }
      pendingPan = false;
      isPanning = false;
      cameraGestureActive = false;
      dom.canvas.classList.remove("panning");
    });

    // Click empty canvas: hit-test for canvas-only nodes, else deselect.
    dom.canvas.addEventListener("click", function (e) {
      if (suppressNextGraphClick) {
        suppressNextGraphClick = false;
        e.preventDefault();
        e.stopPropagation();
        return;
      }
      // If the click landed on an SVG node or domain label, let the
      // delegated handler deal with it.
      if (e.target.closest(".graph-node") || e.target.closest(".domain-label")) return;

      // Canvas hit-test: check if a canvas-drawn node is near the click.
      var hitId = hitTestNode(e.clientX, e.clientY);
      if (hitId) {
        e.stopPropagation();
        if (nodeById.has(hitId)) {
          selectNode(hitId, true);
        } else {
          focusTreeNode(hitId, true);
        }
        return;
      }

      // Empty space click: deselect.
      if (e.target === dom.canvas || e.target === dom.graph_svg ||
          e.target === dom.graph_canvas || e.target.tagName === "svg") {
        deselectNode();
      }
    });

    // Wheel zoom
    dom.canvas.addEventListener("wheel", function (e) {
      e.preventDefault();
      var rect = dom.canvas.getBoundingClientRect();
      var clientPoint = wheelClientPoint(e);
      var mx = clientPoint.x - rect.left;
      var my = clientPoint.y - rect.top;
      var anchor = zoomAnchorForWheelEvent(clientPoint.x, clientPoint.y, mx, my);
      zoomAt(anchor, e);
    }, { passive: false });

    // Touch pan/pinch
    var touchState = null;
    dom.canvas.addEventListener("touchstart", function (e) {
      sfx.unlock();
      stopViewTween();
      stopCameraAnimation();
      if (e.touches.length === 1) {
        resetPanSamples();
        cameraGestureActive = true;
        touchState = {
          mode: "pan",
          startX: e.touches[0].clientX,
          startY: e.touches[0].clientY,
          startViewX: viewState.x,
          startViewY: viewState.y,
        };
        recordPanSample(viewState.x, viewState.y, performance.now());
      } else if (e.touches.length === 2) {
        cameraGestureActive = true;
        var dx = e.touches[0].clientX - e.touches[1].clientX;
        var dy = e.touches[0].clientY - e.touches[1].clientY;
        var rect = dom.canvas.getBoundingClientRect();
        var centerX = (e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left;
        var centerY = (e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top;
        touchState = {
          mode: "pinch",
          startDist: Math.max(1, Math.hypot(dx, dy)),
          startScale: viewState.scale,
          startGraphX: (centerX - viewState.x) / safeViewScale(),
          startGraphY: (centerY - viewState.y) / safeViewScale(),
        };
      }
    }, { passive: true });

    dom.canvas.addEventListener("touchmove", function (e) {
      if (!touchState) return;
      e.preventDefault();
      if (touchState.mode === "pan" && e.touches.length === 1) {
        setDirectView({
          x: touchState.startViewX + (e.touches[0].clientX - touchState.startX),
          y: touchState.startViewY + (e.touches[0].clientY - touchState.startY),
          scale: viewState.scale,
        });
        recordPanSample(viewState.x, viewState.y, performance.now());
        // Panning should not redraw canvas labels on every touchmove.
        scheduleSettledCanvasRedraw(VIEW.cameraPanSettleMs);
      } else if (touchState.mode === "pinch" && e.touches.length === 2) {
        var dx = e.touches[0].clientX - e.touches[1].clientX;
        var dy = e.touches[0].clientY - e.touches[1].clientY;
        var dist = Math.hypot(dx, dy);
        var rect = dom.canvas.getBoundingClientRect();
        var cx = (e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left;
        var cy = (e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top;
        var nextScale = safeScaleValue(touchState.startScale * (dist / touchState.startDist));
        setDirectView(viewForGraphPointAtScreen(cx, cy, touchState.startGraphX, touchState.startGraphY, nextScale));
        scheduleZoomLabelRefresh();
      }
    }, { passive: false });

    dom.canvas.addEventListener("touchend", function () {
      if (touchState) {
        if (touchState.mode !== "pan" || !startPanInertia()) {
          scheduleSettledCanvasRedraw(VIEW.cameraPanSettleMs);
        }
      }
      touchState = null;
      cameraGestureActive = false;
    });
  }

  function zoomAt(anchor, event) {
    stopViewTween();
    stopPanInertia();
    var pixels = normalizedWheelPixels(event);
    if (!pixels) return;
    if (event.shiftKey) pixels = pixels / 4;
    var rate = Math.abs(pixels) < 16 || event.ctrlKey ? WHEEL_ZOOM.trackpadRate : WHEEL_ZOOM.mouseRate;
    var scaleFactor = Math.pow(2, -pixels * rate);
    var base = cloneViewState(viewState);
    var nextScale = base.scale * scaleFactor;
    // Wheel zoom has one invariant: the graph coordinate under the cursor at
    // the start of the wheel burst stays under the same screen coordinate.
    // Re-deriving x/y from the prior screen transform is mathematically close,
    // but browser event coalescing and active compositor state make the graph
    // drift by visible subpixels over repeated wheel ticks.
    var target = viewForGraphPointAtScreen(
      anchor.screenX,
      anchor.screenY,
      anchor.graphX,
      anchor.graphY,
      nextScale
    );

    targetViewState = cloneViewState(target);
    holdWheelCameraActive(VIEW.cameraZoomCanvasSettleMs);
    setDirectView(target);
    scheduleZoomLabelRefresh();
    scheduleSettledCanvasRedraw(prefersReducedMotion() ? 0 : VIEW.cameraZoomCanvasSettleMs);
  }

  function wheelClientPoint(event) {
    if (!event || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) {
      return lastCanvasPointer || { x: 0, y: 0 };
    }
    if (event.clientX === 0 && event.clientY === 0 && lastCanvasPointer) {
      return lastCanvasPointer;
    }
    return { x: event.clientX, y: event.clientY };
  }

  function zoomAnchorForWheelEvent(clientX, clientY, fallbackX, fallbackY) {
    if (wheelCameraActive && wheelZoomAnchor) {
      return wheelZoomAnchor;
    }
    var graphPoint = graphPointForWheelAnchor(clientX, clientY, fallbackX, fallbackY);
    wheelZoomAnchor = {
      graphX: graphPoint.graphX,
      graphY: graphPoint.graphY,
      nodeId: graphPoint.nodeId,
      // Store the raw viewport-local cursor point for the whole burst. This is
      // the user's visual anchor; projecting the graph point back through the
      // current DOM matrix can reintroduce the stale-transform drift this code
      // is specifically trying to avoid.
      screenX: fallbackX,
      screenY: fallbackY,
    };
    return wheelZoomAnchor;
  }

  function graphPointForWheelAnchor(clientX, clientY, fallbackX, fallbackY) {
    // Wheel zoom is a camera operation, not a selection operation. Anchoring
    // to the nearest node center makes the whole map jump whenever the cursor
    // is near a node but not exactly on its center. The invariant here is the
    // usual canvas/map rule: the graph coordinate currently under the cursor
    // must remain under that same cursor for the whole wheel burst.
    var graphPoint = clientPointToGraphPoint(clientX, clientY);
    if (graphPoint) {
      return { graphX: graphPoint.x, graphY: graphPoint.y, nodeId: null };
    }
    var scale = safeViewScale();
    return {
      graphX: (fallbackX - viewState.x) / scale,
      graphY: (fallbackY - viewState.y) / scale,
      nodeId: null,
    };
  }

  function screenPointForGraphPoint(graphX, graphY) {
    if (!wheelCameraActive) {
      var clientPoint = graphPointToClientPoint(graphX, graphY);
      if (clientPoint && dom.canvas) {
        var rect = dom.canvas.getBoundingClientRect();
        return {
          x: clientPoint.x - rect.left,
          y: clientPoint.y - rect.top,
        };
      }
    }
    // Wheel events can be delivered faster than rAF paints. During a wheel
    // burst, project from the canonical view state instead of the possibly
    // stale DOM matrix so repeated deltas keep the same graph point locked.
    var scale = safeViewScale();
    return {
      x: viewState.x + graphX * scale,
      y: viewState.y + graphY * scale,
    };
  }

  function graphNodeIdAtClientPoint(clientX, clientY) {
    if (!dom.graph_nodes) return null;
    var elements = document.elementsFromPoint ?
      document.elementsFromPoint(clientX, clientY) :
      (document.elementFromPoint ? [document.elementFromPoint(clientX, clientY)] : []);
    var graphPoint = clientPointToGraphPoint(clientX, clientY);
    var seen = new Set();
    var fallbackId = null;
    var bestId = null;
    var bestDist = Infinity;

    elements.forEach(function (el) {
      if (!el || !el.closest) return;
      var nodeEl = el.closest(".graph-node");
      if (!nodeEl || !dom.graph_nodes.contains(nodeEl)) return;
      var id = nodeEl.getAttribute("data-id");
      if (!id || seen.has(id)) return;
      seen.add(id);
      if (!fallbackId) fallbackId = id;
      if (!graphPoint) return;
      var point = getDisplayPoint(id);
      if (!point) return;
      var dist = Math.hypot(point.x - graphPoint.x, point.y - graphPoint.y);
      if (dist < bestDist) {
        bestDist = dist;
        bestId = id;
      }
    });

    return bestId || fallbackId;
  }

  function zoomToScale(cx, cy, scale, base) {
    setDirectView(zoomTargetForScale(cx, cy, scale, base));
    // Zoom can request labels, but defer/throttle the expensive canvas redraw
    // until interaction settles so rapid wheel/pinch does not repaint labels
    // on every event.
    scheduleZoomLabelRefresh();
  }

  function zoomTargetForScale(cx, cy, scale, base) {
    var newScale = Math.max(VIEW.minScale, Math.min(VIEW.maxScale, scale));
    var baseScale = safeScaleValue(base.scale);
    var baseX = Number.isFinite(base.x) ? base.x : 0;
    var baseY = Number.isFinite(base.y) ? base.y : 0;
    var ratio = newScale / baseScale;
    return {
      x: cx - (cx - baseX) * ratio,
      y: cy - (cy - baseY) * ratio,
      scale: newScale,
    };
  }

  function viewForGraphPointAtScreen(cx, cy, graphX, graphY, scale) {
    var newScale = safeScaleValue(scale);
    return {
      x: cx - graphX * newScale,
      y: cy - graphY * newScale,
      scale: newScale,
    };
  }

  function normalizedWheelPixels(event) {
    if (event.deltaMode === 1) return event.deltaY * WHEEL_ZOOM.lineHeightPx;
    if (event.deltaMode === 2) return event.deltaY * WHEEL_ZOOM.pageHeightPx;
    return event.deltaY;
  }

  function resetPanSamples() {
    panSamples = [];
  }

  function recordPanSample(x, y, time) {
    panSamples.push({ x: x, y: y, time: time });
    while (panSamples.length > 2 && time - panSamples[0].time > PAN_INERTIA.sampleWindowMs) {
      panSamples.shift();
    }
  }

  function startPanInertia() {
    if (prefersReducedMotion() || panSamples.length < 2) {
      resetPanSamples();
      return false;
    }
    var first = panSamples[0];
    var last = panSamples[panSamples.length - 1];
    var elapsed = Math.max(1, last.time - first.time);
    var vx = (last.x - first.x) / elapsed;
    var vy = (last.y - first.y) / elapsed;
    var speed = Math.hypot(vx, vy);
    resetPanSamples();
    if (speed < PAN_INERTIA.minVelocity) return false;

    var limitedSpeed = Math.min(PAN_INERTIA.maxVelocity, speed);
    vx *= limitedSpeed / speed;
    vy *= limitedSpeed / speed;
    var lastTime = performance.now();
    var elapsedTotal = 0;

    function step(now) {
      var dt = Math.min(32, Math.max(0, now - lastTime));
      lastTime = now;
      elapsedTotal += dt;
      viewState.x += vx * dt;
      viewState.y += vy * dt;
      syncTargetToCurrentView();
      scheduleViewUpdate(false, false);
      var decay = Math.pow(PAN_INERTIA.friction, dt / 16);
      vx *= decay;
      vy *= decay;
      if (Math.hypot(vx, vy) < PAN_INERTIA.stopVelocity || elapsedTotal >= PAN_INERTIA.maxDurationMs) {
        panInertiaFrame = null;
        scheduleSettledCanvasRedraw(VIEW.cameraPanSettleMs);
        return;
      }
      panInertiaFrame = requestAnimationFrame(step);
    }

    panInertiaFrame = requestAnimationFrame(step);
    return true;
  }

  function scheduleZoomLabelRefresh() {
    if (zoomLabelTimer) clearTimeout(zoomLabelTimer);
    zoomLabelTimer = setTimeout(function () {
      zoomLabelTimer = null;
      if (isCameraAnimating()) {
        scheduleZoomLabelRefresh();
        return;
      }
      renderMinimapViewport();
    }, VIEW.cameraZoomLabelSettleMs);
    scheduleSettledCanvasRedraw(VIEW.cameraZoomCanvasSettleMs);
  }

  function resetView(animated) {
    if (!layoutCache) return;
    stopViewTween();
    stopCameraAnimation();
    var rect = dom.canvas.getBoundingClientRect();
    var bounds = layoutCache.bounds;
    var pad = viewportFitPadding(rect);
    var availableWidth = Math.max(1, rect.width - pad.x * 2);
    var availableHeight = Math.max(1, rect.height - pad.y * 2);
    var scale = Math.min(availableWidth / layoutCache.totalWidth, availableHeight / layoutCache.totalHeight, 1);
    scale = Math.max(scale, VIEW.minScale);
    var target = {
      x: (rect.width - (bounds.minX + bounds.maxX) * scale) / 2,
      y: (rect.height - (bounds.minY + bounds.maxY) * scale) / 2,
      scale: scale,
    };
    if (animated && !prefersReducedMotion()) {
      animateViewTo(target, 220);
      return;
    }
    setViewImmediate(target);
    renderGraph();
  }

  function viewportFitPadding(rect) {
    var shortest = Math.min(rect.width, rect.height);
    var pad = Math.max(18, Math.min(90, shortest * 0.08));
    return { x: pad, y: pad };
  }

  // --- Deep linking (decision 52) ---
  function handleDeepLink() {
    var hash = window.location.hash;
    var match = hash.match(/node=([^&]+)/);
    if (match && match[1]) {
      var id = decodeURIComponent(match[1]);
      if (nodeById.has(id)) {
        selectNode(id, false);
      }
    }
  }

  function updateHash(id) {
    history.replaceState(null, "", "#node=" + encodeURIComponent(id));
  }

  function clearHash() {
    history.replaceState(null, "", window.location.pathname + window.location.search);
  }

  window.addEventListener("hashchange", handleDeepLink);

  // --- Sound toggle ---
  function initSoundToggle() {
    var shouldBeOn = sfx.shouldBeOn(viewerConfig.enableSound);
    updateSoundToggle(shouldBeOn);

    // First user gesture unlocks audio (decision 57)
    function unlockOnce() {
      sfx.unlock();
      if (shouldBeOn && !sfx.isEnabled()) {
        sfx.setEnabled(true);
      }
      document.removeEventListener("pointerdown", unlockOnce);
      document.removeEventListener("keydown", unlockOnce);
    }
    document.addEventListener("pointerdown", unlockOnce);
    document.addEventListener("keydown", unlockOnce);
  }

  function updateSoundToggle(on) {
    dom.sound_toggle.setAttribute("aria-pressed", String(on));
    var swap = dom.sound_toggle.querySelector(".sound-icon-swap");
    if (swap) {
      swap.dataset.state = on ? "on" : "off";
    }
  }

  // --- Events ---
  function bindEvents() {
    initPanZoom();
    bindNodeLayerEvents();

    // Search
    var searchTimer = null;
    dom.search_input.addEventListener("input", function () {
      clearTimeout(searchTimer);
      setSearchClearVisible(!!dom.search_input.value);
      var val = dom.search_input.value;
      searchTimer = setTimeout(function () {
        clearCommittedFocus(false);
        filters.search = val;
        layoutAndRender();
        resetView(true);
      }, 120);
    });
    dom.search_clear.addEventListener("click", function () {
      dom.search_input.value = "";
      setSearchClearVisible(false);
      clearCommittedFocus(false);
      filters.search = "";
      layoutAndRender();
      resetView(true);
      dom.search_input.focus();
    });
    function toolbarItems() {
      if (!dom.action_dock) return [];
      return Array.prototype.slice.call(dom.action_dock.querySelectorAll("[data-toolbar-item]"));
    }
    function activeToolbarButton() {
      var disclosureButtons = [dom.search_toggle, dom.filter_toggle, dom.legend_toggle, dom.settings_toggle];
      for (var i = 0; i < disclosureButtons.length; i += 1) {
        if (disclosureButtons[i] && disclosureButtons[i].getAttribute("aria-pressed") === "true") {
          return disclosureButtons[i];
        }
      }
      return null;
    }
    function syncToolbarIndicator(target) {
      if (!dom.action_dock || !dom.toolbar_indicator) return;
      if (!target || !dom.action_dock.contains(target)) {
        dom.action_dock.style.setProperty("--toolbar-indicator-opacity", "0");
        return;
      }
      var dockRect = dom.action_dock.getBoundingClientRect();
      var targetRect = target.getBoundingClientRect();
      dom.action_dock.style.setProperty("--toolbar-indicator-x", (targetRect.left - dockRect.left) + "px");
      dom.action_dock.style.setProperty("--toolbar-indicator-y", (targetRect.top - dockRect.top) + "px");
      dom.action_dock.style.setProperty("--toolbar-indicator-opacity", "1");
    }
    function syncActiveToolbarIndicator() {
      requestAnimationFrame(function () {
        syncToolbarIndicator(activeToolbarButton());
      });
    }
    function initToolbarDockMotion() {
      if (!dom.action_dock || !dom.toolbar_indicator) return;
      toolbarItems().forEach(function (button) {
        button.addEventListener("pointerenter", function () {
          syncToolbarIndicator(button);
        });
        button.addEventListener("focusin", function () {
          syncToolbarIndicator(button);
        });
        button.addEventListener("pointerleave", syncActiveToolbarIndicator);
        button.addEventListener("focusout", syncActiveToolbarIndicator);
      });
      syncActiveToolbarIndicator();
    }
    function syncToolbarDisclosureButtons() {
      requestAnimationFrame(function () {
        syncDisclosureButton(dom.search_toggle, dom.search_panel);
        syncDisclosureButton(dom.filter_toggle, dom.filter_bar);
        syncDisclosureButton(dom.settings_toggle, dom.settings_panel);
        syncDisclosureButton(dom.legend_toggle, dom.legend);
        syncToolbarIndicator(activeToolbarButton());
      });
    }
    function openSearchPanel() {
      setPanelOpen(dom.filter_bar, false);
      setPanelOpen(dom.settings_panel, false);
      setPanelOpen(dom.legend, false);
      setPanelOpen(dom.search_panel, true);
      syncToolbarDisclosureButtons();
      requestAnimationFrame(function () {
        dom.search_input.focus();
        dom.search_input.select();
      });
    }
    if (dom.search_toggle) {
      dom.search_toggle.addEventListener("click", function () {
        sfx.dockButton();
        setPanelOpen(dom.filter_bar, false);
        setPanelOpen(dom.settings_panel, false);
        setPanelOpen(dom.legend, false);
        togglePanel(dom.search_panel);
        syncToolbarDisclosureButtons();
        requestAnimationFrame(function () {
          if (dom.search_panel.dataset.open === "true") {
            dom.search_input.focus();
            dom.search_input.select();
          }
        });
      });
    }
    initToolbarDockMotion();

    // Filters
    function seedRangeTick(el) {
      if (!el) return;
      el.dataset.lastSliderTickValue = String(el.value);
      el.classList.add("is-adjusting");
    }
    function releaseRangeTick(el) {
      if (!el) return;
      el.classList.remove("is-adjusting");
      delete el.dataset.lastSliderTickValue;
      sfx.cancelSliderTicks();
    }
    function playRangeTick(el) {
      if (!el) return;
      var next = Number(el.value);
      var previous = Number(el.dataset.lastSliderTickValue);
      if (!Number.isFinite(next)) return;
      if (!Number.isFinite(previous)) {
        el.dataset.lastSliderTickValue = String(next);
        return;
      }
      if (next === previous) return;
      el.dataset.lastSliderTickValue = String(next);
      sfx.sliderTick();
    }
    function onFilterChange() {
      filters.domain = dom.filter_domain.value;
      filters.status = dom.filter_status.value;
      filters.freshness = dom.filter_freshness.value;
      filters.maxSkills = parseScopeLimit(dom.filter_scope.value);
      filters.minConfidence = parseFloat(dom.filter_confidence.value);
      syncRangeProgress(dom.filter_confidence);
      renderNumericText(dom.filter_confidence_value, percentText(filters.minConfidence));
      filters.evidenceType = dom.filter_evidence.value;
      clearCommittedFocus(false);
      layoutAndRender();
      resetView(true);
      sfx.filterSwitch();
    }
    ["change"].forEach(function (evt) {
      dom.filter_domain.addEventListener(evt, onFilterChange);
      dom.filter_status.addEventListener(evt, onFilterChange);
      dom.filter_freshness.addEventListener(evt, onFilterChange);
      dom.filter_scope.addEventListener(evt, onFilterChange);
      dom.filter_evidence.addEventListener(evt, onFilterChange);
    });
    dom.filter_confidence.addEventListener("pointerdown", function () {
      sfx.unlock();
      seedRangeTick(dom.filter_confidence);
    });
    dom.filter_confidence.addEventListener("keydown", function (event) {
      if (!/^(ArrowLeft|ArrowRight|ArrowUp|ArrowDown|Home|End|PageUp|PageDown)$/.test(event.key)) return;
      sfx.unlock();
      if (!dom.filter_confidence.dataset.lastSliderTickValue) seedRangeTick(dom.filter_confidence);
    });
    dom.filter_confidence.addEventListener("input", function () {
      filters.minConfidence = parseFloat(dom.filter_confidence.value);
      syncRangeProgress(dom.filter_confidence);
      renderNumericText(dom.filter_confidence_value, percentText(filters.minConfidence));
      playRangeTick(dom.filter_confidence);
      clearCommittedFocus(false);
      layoutAndRender();
      resetView(true);
    });
    ["change", "pointerup", "lostpointercapture", "blur"].forEach(function (eventName) {
      dom.filter_confidence.addEventListener(eventName, function () {
        releaseRangeTick(dom.filter_confidence);
      });
    });
    dom.filter_clear.addEventListener("click", function () {
      dom.filter_domain.value = "";
      dom.filter_status.value = "";
      dom.filter_freshness.value = "";
      dom.filter_scope.value = "all";
      dom.filter_confidence.value = 0;
      dom.filter_evidence.value = "";
      filters = emptyFilters();
      clearCommittedFocus(false);
      syncFilterControls();
      layoutAndRender();
      setSearchClearVisible(!!dom.search_input.value);
      resetView(true);
      sfx.filterSwitch();
    });

    function parseScopeLimit(value) {
      return value === "all" ? "all" : parseInt(value, 10);
    }

    // Filter panel toggle
    if (dom.filter_toggle) {
      dom.filter_toggle.addEventListener("click", function () {
        sfx.dockButton();
        setPanelOpen(dom.search_panel, false);
        setPanelOpen(dom.settings_panel, false);
        setPanelOpen(dom.legend, false);
        togglePanel(dom.filter_bar);
        syncToolbarDisclosureButtons();
      });
    }

    // View settings
    var separationTimer = null;
    function bindSettingRange(el, key, recomputeLayout) {
      if (!el) return;
      el.addEventListener("pointerdown", function () {
        sfx.unlock();
        seedRangeTick(el);
      });
      el.addEventListener("keydown", function (event) {
        if (!/^(ArrowLeft|ArrowRight|ArrowUp|ArrowDown|Home|End|PageUp|PageDown)$/.test(event.key)) return;
        sfx.unlock();
        if (!el.dataset.lastSliderTickValue) seedRangeTick(el);
      });
      el.addEventListener("input", function () {
        viewSettings[key] = parseFloat(el.value);
        syncRangeProgress(el);
        playRangeTick(el);
        if (recomputeLayout) {
          if (separationTimer) clearTimeout(separationTimer);
          separationTimer = setTimeout(function () {
            separationTimer = null;
            applyViewSettingsChange(true);
          }, 80);
          syncSettingsControls();
          return;
        }
        applyViewSettingsChange(false);
      });
      el.addEventListener("change", function () {
        viewSettings[key] = parseFloat(el.value);
        if (separationTimer) {
          clearTimeout(separationTimer);
          separationTimer = null;
        }
        applyViewSettingsChange(recomputeLayout);
        releaseRangeTick(el);
      });
      el.addEventListener("pointerup", function () { releaseRangeTick(el); });
      el.addEventListener("lostpointercapture", function () { releaseRangeTick(el); });
      el.addEventListener("blur", function () { releaseRangeTick(el); });
    }
    function bindSettingCheckbox(el, key, recomputeLayout) {
      if (!el) return;
      el.addEventListener("change", function () {
        viewSettings[key] = !!el.checked;
        applyViewSettingsChange(recomputeLayout);
      });
    }
    bindSettingRange(dom.setting_dim, "contextDimming", false);
    bindSettingRange(dom.setting_node_size, "nodeScale", false);
    bindSettingRange(dom.setting_line_strength, "lineStrength", false);
    bindSettingRange(dom.setting_label_density, "labelDensity", false);
    bindSettingRange(dom.setting_separation, "separation", true);
    bindSettingCheckbox(dom.setting_show_lines, "showLines", false);
    bindSettingCheckbox(dom.setting_show_categories, "showCategories", false);
    bindSettingCheckbox(dom.setting_show_category_labels, "showCategoryLabels", false);
    bindSettingCheckbox(dom.setting_show_skill_labels, "showSkillLabels", false);
    bindSettingCheckbox(dom.setting_show_level_badges, "showLevelBadges", false);
    bindSettingCheckbox(dom.setting_show_background_dots, "showBackgroundDots", false);
    if (dom.settings_reset) {
      dom.settings_reset.addEventListener("click", function () {
        if (separationTimer) {
          clearTimeout(separationTimer);
          separationTimer = null;
        }
        viewSettings = defaultViewSettings();
        applyViewSettingsChange(true);
      });
    }
    if (dom.settings_toggle) {
      dom.settings_toggle.addEventListener("click", function () {
        sfx.dockButton();
        setPanelOpen(dom.search_panel, false);
        setPanelOpen(dom.filter_bar, false);
        setPanelOpen(dom.legend, false);
        togglePanel(dom.settings_panel);
        syncToolbarDisclosureButtons();
      });
    }

    // Toolbar
    dom.legend_toggle.addEventListener("click", function () {
      sfx.dockButton();
      setPanelOpen(dom.search_panel, false);
      setPanelOpen(dom.filter_bar, false);
      setPanelOpen(dom.settings_panel, false);
      togglePanel(dom.legend);
      syncToolbarDisclosureButtons();
    });
    dom.legend_close.addEventListener("click", function () {
      setPanelOpen(dom.legend, false);
      syncToolbarDisclosureButtons();
    });
    dom.minimap_toggle.addEventListener("click", function () {
      sfx.dockButton();
      var collapsed = dom.minimap.classList.toggle("collapsed");
      dom.minimap_toggle.setAttribute("aria-pressed", String(collapsed));
      syncActiveToolbarIndicator();
    });
    dom.sound_toggle.addEventListener("click", function () {
      var nowOn = !sfx.isEnabled();
      if (!nowOn) sfx.dockButton();
      sfx.setEnabled(nowOn);
      if (nowOn) sfx.dockButton();
      updateSoundToggle(nowOn);
    });
    dom.reset_view.addEventListener("click", function () {
      sfx.dockButton();
      resetView(true);
    });

    // Drawer/sheet close
    dom.drawer_close.addEventListener("click", closeDrawer);
    dom.sheet_close.addEventListener("click", closeDrawer);
    dom.drawer_body.addEventListener("click", handleDetailNextClick);
    dom.sheet_body.addEventListener("click", handleDetailNextClick);

    // Keyboard navigation (decision 39)
    document.addEventListener("keydown", function (e) {
      // Ignore if typing in an input
      if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA") {
        if (e.key === "Escape" && e.target === dom.search_input) {
          e.target.blur();
          setPanelOpen(dom.search_panel, false);
          syncToolbarDisclosureButtons();
        }
        return;
      }
      // Arrow navigation works from the currently focused node (via Tab or
      // mouse select). Enter/Space are handled by the node's own keydown.
      var focusedNodeId = null;
      if (e.target.classList && e.target.classList.contains("graph-node")) {
        focusedNodeId = e.target.getAttribute("data-id");
      }
      var navNodeId = focusedNodeId || selectedNodeId;

      switch (e.key) {
        case "Escape":
          if (selectedNodeId || activeFocus) clearCommittedFocus(true);
          break;
        case "/":
          e.preventDefault();
          openSearchPanel();
          break;
        case "r": case "R":
          resetView(true);
          break;
        case "f": case "F":
          setPanelOpen(dom.search_panel, false);
          setPanelOpen(dom.settings_panel, false);
          setPanelOpen(dom.legend, false);
          togglePanel(dom.filter_bar);
          syncToolbarDisclosureButtons();
          break;
        case "l": case "L":
          setPanelOpen(dom.search_panel, false);
          setPanelOpen(dom.filter_bar, false);
          setPanelOpen(dom.settings_panel, false);
          togglePanel(dom.legend);
          syncToolbarDisclosureButtons();
          break;
        case "s": case "S":
          setPanelOpen(dom.search_panel, false);
          setPanelOpen(dom.filter_bar, false);
          setPanelOpen(dom.legend, false);
          togglePanel(dom.settings_panel);
          syncToolbarDisclosureButtons();
          break;
        case "m": case "M":
          var collapsed = dom.minimap.classList.toggle("collapsed");
          dom.minimap_toggle.setAttribute("aria-pressed", String(collapsed));
          syncActiveToolbarIndicator();
          break;
        default:
          // Arrow key navigation between nearby nodes
          if (navNodeId && e.key.startsWith("Arrow")) {
            e.preventDefault();
            navigateArrow(e.key, navNodeId);
          }
      }
    });

    window.addEventListener("resize", function () {
      if (resizeFitTimer) clearTimeout(resizeFitTimer);
      resizeFitTimer = setTimeout(function () {
        resizeFitTimer = null;
        resizeCanvas();
        resolveDomainColors();
        resetView();
        syncActiveToolbarIndicator();
      }, 80);
    });
  }

  function bindNodeLayerEvents() {
    dom.graph_nodes.addEventListener("click", handleGraphNodeClick);
    dom.graph_nodes.addEventListener("keydown", handleGraphNodeKeydown);
    dom.canvas.addEventListener("pointermove", handleGraphPointerMove);
    dom.canvas.addEventListener("pointerleave", clearHoverNode);
  }

  function handleDetailNextClick(e) {
    var button = e.target && e.target.closest ? e.target.closest("[data-next-node-id]") : null;
    if (!button) return;
    var id = button.getAttribute("data-next-node-id");
    if (!id || !nodeById.has(id)) return;
    e.preventDefault();
    selectNode(id, true);
  }

  function graphNodeFromEvent(e) {
    if (!e.target || !e.target.closest) return null;
    var nodeEl = e.target.closest(".graph-node");
    if (!nodeEl || !dom.graph_nodes.contains(nodeEl)) return null;
    return nodeEl;
  }

  function handleGraphNodeClick(e) {
    if (suppressNextGraphClick) {
      suppressNextGraphClick = false;
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    var nodeEl = graphNodeFromEvent(e);
    if (!nodeEl) return;
    var nodeId = nodeEl.getAttribute("data-id");
    if (!nodeId) return;
    e.stopPropagation();
    activateGraphId(pointerActivationId(e, nodeId), true);
  }

  function handleGraphNodeKeydown(e) {
    if (e.key !== "Enter" && e.key !== " ") return;
    var nodeEl = graphNodeFromEvent(e);
    if (!nodeEl) return;
    var nodeId = nodeEl.getAttribute("data-id");
    if (!nodeId) return;
    e.preventDefault();
    e.stopPropagation();
    activateGraphId(nodeId, true);
  }

  function handleGraphPointerMove(e) {
    if (e && Number.isFinite(e.clientX) && Number.isFinite(e.clientY)) {
      lastCanvasPointer = { x: e.clientX, y: e.clientY };
    }
    if (!canvasReadyForInteractiveOverlays()) {
      clearHoverNode();
      return;
    }
    setHoverNode(graphNodeIdAtClientPoint(e.clientX, e.clientY) || hitTestNode(e.clientX, e.clientY));
  }

  function navigateArrow(key, fromNodeId) {
    var sourceId = fromNodeId || selectedNodeId;
    if (!layoutCache || !sourceId) return;
    var current = getDisplayPoint(sourceId);
    if (!current) return;
    var best = null;
    var bestDist = Infinity;
    nodes.forEach(function (node) {
      if (node.id === sourceId) return;
      // Skip nodes in collapsed domains or visual constellations.
      if (isNodeCollapsed(node)) return;
      var p = getDisplayPoint(node.id);
      if (!p) return;
      var dx = p.x - current.x;
      var dy = p.y - current.y;
      var dirOk = false;
      if (key === "ArrowUp" && dy < -10) dirOk = true;
      if (key === "ArrowDown" && dy > 10) dirOk = true;
      if (key === "ArrowLeft" && dx < -10) dirOk = true;
      if (key === "ArrowRight" && dx > 10) dirOk = true;
      if (!dirOk) return;
      var dist = Math.hypot(dx, dy);
      if (dist < bestDist) {
        bestDist = dist;
        best = node.id;
      }
    });
    if (best) {
      selectNode(best, true);
      // Move keyboard focus to the newly selected node so Tab continues
      // from it (decision 39).
      var bestEl = dom.graph_nodes.querySelector('[data-id="' + best + '"]');
      if (bestEl) bestEl.focus();
    }
  }

  // --- Boot ---
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
"""


# ---------------------------------------------------------------------------
# Phase 2: Admin curation viewer assets
# ---------------------------------------------------------------------------

ADMIN_VIEWER_HTML = """\
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>Skill Map - Admin Curation</title>
<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
<link rel="stylesheet" href="assets/admin.css">
<link rel="preload" href="graph.json" as="fetch" crossorigin>
<link rel="preload" href="curation.json" as="fetch" crossorigin>
</head>
<body class="viewer-loading admin-mode">

<!-- Top toolbar -->
<header class="toolbar" role="banner">
  <div class="toolbar__brand">
    <span class="toolbar__badge">ADMIN</span>
    <span class="toolbar__title" aria-label="Skill Map Admin">Skill Map Curation</span>
  </div>

  <div class="toolbar__search">
    <label class="search-field">
      <span class="search-field__icon" aria-hidden="true">&#128269;</span>
      <input
        id="search-input"
        type="search"
        class="search-field__input"
        placeholder="Search skills..."
        autocomplete="off"
        aria-label="Search skills"
        accesskey="/"
      >
      <button id="search-clear" class="search-field__clear" type="button" aria-label="Clear search" hidden>&#10005;</button>
    </label>
  </div>

  <div class="toolbar__actions">
    <button id="legend-toggle" class="toolbar__btn" type="button" aria-label="Toggle legend" title="Legend (L)">
      <span aria-hidden="true">&#9432;</span>
    </button>
    <button id="sound-toggle" class="toolbar__btn toolbar__btn--sound" type="button" aria-pressed="false" title="Toggle sound">
      <span class="sound-off" aria-hidden="true">&#128263;</span>
      <span class="sound-on" aria-hidden="true" hidden>&#128266;</span>
    </button>
    <button id="save-curation" class="toolbar__btn toolbar__btn--save" type="button" title="Save curation (Ctrl+S)">
      <span aria-hidden="true">&#128190;</span> Save
    </button>
    <button id="reset-view" class="toolbar__btn" type="button" aria-label="Reset view" title="Reset view (R)">
      <span aria-hidden="true">&#8962;</span>
    </button>
  </div>
</header>

<!-- Compact filter bar -->
<section class="filterbar" id="filter-bar" role="region" aria-label="Filters">
  <div class="filterbar__group">
    <label class="filterbar__label" for="filter-domain">Domain</label>
    <select id="filter-domain" class="filterbar__select" aria-label="Filter by domain">
      <option value="">All domains</option>
    </select>
  </div>
  <div class="filterbar__group">
    <label class="filterbar__label" for="filter-status">Status</label>
    <select id="filter-status" class="filterbar__select" aria-label="Filter by status">
      <option value="">All</option>
      <option value="active">Active</option>
      <option value="stale">Stale</option>
      <option value="historical">Historical</option>
      <option value="hidden">Hidden</option>
      <option value="disputed">Disputed</option>
      <option value="review">Review</option>
    </select>
  </div>
  <div class="filterbar__group">
    <label class="filterbar__label" for="filter-curation">Curation</label>
    <select id="filter-curation" class="filterbar__select" aria-label="Filter by curation state">
      <option value="">All</option>
      <option value="hidden">Hidden</option>
      <option value="featured">Featured</option>
      <option value="approved">Approved (LC/Disputed)</option>
      <option value="overridden">Any override</option>
    </select>
  </div>
  <button id="filter-clear" class="filterbar__clear" type="button">Clear filters</button>
</section>

<!-- Main graph viewport -->
<main class="viewport" id="viewport" role="main" aria-label="Skill graph">
  <div class="viewport__canvas" id="canvas">
    <!-- Not aria-hidden: nodes and domain labels inside are keyboard
         focusable (decisions 39, 34) with aria-labels, so hiding the SVG
         would remove them from the accessibility tree. -->
    <svg id="graph-svg" class="graph-svg" preserveAspectRatio="xMidYMid meet" role="group" aria-label="Skill graph">
      <defs>
        <radialGradient id="node-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="rgba(120,200,255,0.18)"/>
          <stop offset="100%" stop-color="rgba(120,200,255,0)"/>
        </radialGradient>
      </defs>
      <g id="graph-zoom">
        <g id="graph-edges"></g>
        <g id="graph-nodes"></g>
        <g id="graph-labels"></g>
      </g>
    </svg>
  </div>

  <!-- Curation summary panel -->
  <aside class="curation-summary" id="curation-summary" role="complementary" aria-label="Curation summary">
    <h2 class="curation-summary__title">Curation</h2>
    <div class="curation-summary__stats" id="curation-stats"></div>
  </aside>

  <!-- Empty state -->
  <div class="empty-state" id="empty-state" hidden>
    <p>No nodes match the current filters.</p>
  </div>

  <!-- Loading state -->
  <div class="loading-state" id="loading-state">
    <div class="loading-state__loaders" aria-hidden="true">
      <span class="spiral-loader" style="--spiral-size: 24px">
        <svg class="spiral-loader__phase spiral-loader__phase--fast" viewBox="0 0 16 16" focusable="false">
          <g class="spiral-loader__motion">
            <path class="spiral-loader__path" pathLength="100" d="M0.500 12.500 C4.952 12.500 7.236 8.784 7.525 5.488 C7.755 2.861 6.718 0.500 4.500 0.500 C2.282 0.500 1.245 2.861 1.475 5.488 C1.764 8.784 4.048 12.500 8.500 12.500 C12.952 12.500 15.236 8.784 15.525 5.488 C15.755 2.861 14.718 0.500 12.500 0.500 C10.282 0.500 9.245 2.861 9.475 5.488 C9.764 8.784 12.048 12.500 16.500 12.500 C20.952 12.500 23.236 8.784 23.525 5.488 C23.755 2.861 22.718 0.500 20.500 0.500 C18.282 0.500 17.248 2.861 17.480 5.488 C17.772 8.784 20.057 12.500 24.500 12.500"></path>
          </g>
        </svg>
        <svg class="spiral-loader__phase spiral-loader__phase--slow" viewBox="0 0 16 16" focusable="false">
          <g class="spiral-loader__motion">
            <path class="spiral-loader__path" pathLength="100" d="M0.500 12.500 C4.952 12.500 7.236 8.784 7.525 5.488 C7.755 2.861 6.718 0.500 4.500 0.500 C2.282 0.500 1.245 2.861 1.475 5.488 C1.764 8.784 4.048 12.500 8.500 12.500 C12.952 12.500 15.236 8.784 15.525 5.488 C15.755 2.861 14.718 0.500 12.500 0.500 C10.282 0.500 9.245 2.861 9.475 5.488 C9.764 8.784 12.048 12.500 16.500 12.500 C20.952 12.500 23.236 8.784 23.525 5.488 C23.755 2.861 22.718 0.500 20.500 0.500 C18.282 0.500 17.248 2.861 17.480 5.488 C17.772 8.784 20.057 12.500 24.500 12.500"></path>
          </g>
        </svg>
      </span>
    </div>
    <p class="t-shimmer loading-state__text" id="loading-message" data-text="Loading skill map...">Loading skill map...</p>
  </div>
</main>

<!-- Node detail / curation panel -->
<aside class="drawer" id="drawer" role="complementary" aria-label="Node details and curation" aria-hidden="true" hidden>
  <div class="drawer__header">
    <h2 class="drawer__title" id="drawer-title">-</h2>
    <button class="drawer__close" id="drawer-close" type="button" aria-label="Close drawer (Esc)">&times;</button>
  </div>
  <div class="drawer__body" id="drawer-body"></div>
</aside>

<!-- Save status toast -->
<div class="toast" id="save-toast" role="status" aria-live="polite" hidden></div>

<script src="assets/sfx.js" defer></script>
<script src="assets/admin.js" defer></script>
</body>
</html>
"""

ADMIN_VIEWER_CSS = """\
:root {
  --bg: #0b0e14;
  --bg-elevated: #131820;
  --bg-panel: #161c26;
  --border: #232c3a;
  --border-strong: #2f3a4d;
  --text: #e4e9f0;
  --text-muted: #8a95a8;
  --text-dim: #5a6478;
  --accent: #6cb6ff;
  --accent-soft: rgba(108, 182, 255, 0.15);
  --danger: #e85a5a;
  --danger-soft: rgba(232, 90, 90, 0.15);
  --success: #7fd1a3;
  --success-soft: rgba(127, 209, 163, 0.15);
  --warning: #e8c47a;
  --warning-soft: rgba(232, 196, 122, 0.15);
  --node-fill: #1c2330;
  --node-stroke: #3a4658;
  --edge: #2a3445;
  --edge-highlight: #6cb6ff;
  --shadow: 0 4px 24px rgba(0, 0, 0, 0.4);

  --domain-1: #6cb6ff;
  --domain-2: #7fd1a3;
  --domain-3: #d4a8e8;
  --domain-4: #e8c47a;
  --domain-5: #e89b7a;
  --domain-6: #7ad1e8;
  --domain-7: #c4e87a;
  --domain-8: #e87aad;

  --radius: 8px;
  --toolbar-h: 52px;
  --font-ui: "Traccia UI", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-label: "Traccia Label", "Traccia UI", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-display: "Traccia Display", "Traccia UI", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "Traccia Mono", "SFMono-Regular", Consolas, monospace;
}

@media (prefers-color-scheme: light) {
  :root {
    --bg: #f7f8fa;
    --bg-elevated: #ffffff;
    --bg-panel: #ffffff;
    --border: #e0e3ea;
    --border-strong: #c8cdd8;
    --text: #1a1f2e;
    --text-muted: #5a6478;
    --text-dim: #8a95a8;
    --accent: #2563eb;
    --accent-soft: rgba(37, 99, 235, 0.1);
    --danger: #dc2626;
    --danger-soft: rgba(220, 38, 38, 0.1);
    --success: #16a34a;
    --success-soft: rgba(22, 163, 74, 0.1);
    --warning: #d97706;
    --warning-soft: rgba(217, 119, 6, 0.1);
    --node-fill: #ffffff;
    --node-stroke: #c8cdd8;
    --edge: #d0d4de;
    --edge-highlight: #2563eb;
    --shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  }
}

* { box-sizing: border-box; }

html, body {
  margin: 0; padding: 0; height: 100%; overflow: hidden;
  font-family: var(--font-ui);
  font-size: 14px; color: var(--text); background: var(--bg);
  font-feature-settings: "kern" 1, "liga" 1, "calt" 1;
}
body { display: flex; flex-direction: column; }

.toolbar {
  display: flex; align-items: center; gap: 12px;
  height: var(--toolbar-h); padding: 0 14px;
  background: var(--bg-elevated); border-bottom: 1px solid var(--border);
  flex-shrink: 0; z-index: 20;
}
.toolbar__brand { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.toolbar__badge {
  font-family: var(--font-mono);
  font-size: 10px; font-weight: 700; letter-spacing: 1px;
  padding: 2px 6px; border-radius: 3px;
  background: var(--warning-soft); color: var(--warning);
  border: 1px solid var(--warning);
}
.toolbar__title { font-family: var(--font-display); font-weight: 600; font-size: 15px; }
.toolbar__search { flex: 1; max-width: 420px; }

.search-field {
  display: flex; align-items: center; gap: 6px;
  padding: 0 10px; height: 34px;
  background: var(--bg-panel); border: 1px solid var(--border);
  border-radius: var(--radius);
  transition:
    border-color 160ms cubic-bezier(0.23, 1, 0.32, 1),
    box-shadow 160ms cubic-bezier(0.23, 1, 0.32, 1),
    background-color 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.search-field:focus-within { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }
.search-field__icon { font-size: 13px; opacity: 0.6; }
.search-field__input {
  flex: 1; border: none; background: transparent; color: var(--text);
  font-size: 13px; outline: none;
}
.search-field__input::placeholder { color: var(--text-dim); }
.search-field__clear {
  border: none; background: none; color: var(--text-dim);
  cursor: pointer; font-size: 14px; padding: 2px;
  border-radius: var(--radius-sm);
  transition:
    color 120ms cubic-bezier(0.23, 1, 0.32, 1),
    background-color 120ms cubic-bezier(0.23, 1, 0.32, 1),
    transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
.search-field__clear:active { transform: scale(0.94); }

.toolbar__actions { display: flex; gap: 4px; flex-shrink: 0; }
.toolbar__btn {
  display: inline-flex; align-items: center; justify-content: center;
  gap: 4px; height: 34px; padding: 0 8px;
  border: 1px solid var(--border); background: var(--bg-panel);
  color: var(--text-muted); border-radius: var(--radius);
  cursor: pointer; font-size: 13px;
  transition:
    color 150ms cubic-bezier(0.23, 1, 0.32, 1),
    background-color 150ms cubic-bezier(0.23, 1, 0.32, 1),
    border-color 150ms cubic-bezier(0.23, 1, 0.32, 1),
    box-shadow 150ms cubic-bezier(0.23, 1, 0.32, 1),
    transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
.toolbar__btn:hover { color: var(--text); border-color: var(--border-strong); }
.toolbar__btn[aria-pressed="true"] { color: var(--accent); border-color: var(--accent); }
.toolbar__btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.toolbar__btn:active { transform: scale(0.96); }
.toolbar__btn--save {
  padding: 0 14px; font-weight: 600; color: var(--success);
  border-color: var(--success);
}
.toolbar__btn--save:hover { background: var(--success-soft); }
.toolbar__btn--save.dirty {
  animation: pulse-save 2s infinite;
}
@keyframes pulse-save {
  0%, 100% { box-shadow: 0 0 0 0 var(--success-soft); }
  50% { box-shadow: 0 0 0 4px var(--success-soft); }
}

.filterbar {
  display: flex; align-items: center; gap: 14px;
  padding: 8px 14px;
  background: var(--bg-elevated); border-bottom: 1px solid var(--border);
  flex-shrink: 0; flex-wrap: wrap; z-index: 15;
}
.filterbar__group { display: flex; align-items: center; gap: 5px; }
.filterbar__label { font-family: var(--font-mono); font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.4px; }
.filterbar__select {
  height: 28px; font-size: 12px; color: var(--text);
  background: var(--bg-panel); border: 1px solid var(--border);
  border-radius: 5px; padding: 0 6px;
}
.filterbar__select:focus { outline: 1px solid var(--accent); border-color: var(--accent); }
.filterbar__clear {
  margin-left: auto; height: 28px; padding: 0 10px;
  font-size: 12px; color: var(--text-muted);
  background: transparent; border: 1px solid var(--border);
  border-radius: 5px; cursor: pointer;
}
.filterbar__clear:hover { color: var(--text); border-color: var(--border-strong); }

.viewport {
  position: relative; flex: 1; overflow: hidden; background: var(--bg);
}
.viewport__canvas {
  position: absolute; inset: 0; cursor: grab; touch-action: none;
  opacity: 1; filter: none;
  transition: opacity 420ms cubic-bezier(0.23, 1, 0.32, 1),
    filter 420ms cubic-bezier(0.23, 1, 0.32, 1);
}
.viewport__canvas.panning { cursor: grabbing; }
body.viewer-loading .viewport__canvas {
  opacity: 0; filter: blur(8px);
}
.graph-svg { width: 100%; height: 100%; display: block; }
#graph-zoom { transition: opacity 0.2s; }

.graph-node { cursor: pointer; }
.graph-node__circle {
  fill: var(--node-fill); stroke-width: 2;
  transition: stroke-width 0.15s, filter 0.15s;
}
.graph-node:hover .graph-node__circle { stroke-width: 3; }
.graph-node__glow { fill: url(#node-glow); opacity: 0; transition: opacity 0.2s; }
.graph-node.selected .graph-node__glow { opacity: 1; }
.graph-node.curation-hidden .graph-node__circle {
  opacity: 0.25; stroke-dasharray: 4 3;
}
.graph-node.curation-featured .graph-node__circle {
  stroke: var(--warning) !important; stroke-width: 3;
}
.graph-node.curation-approved .graph-node__circle {
  stroke: var(--success) !important; stroke-width: 2.5;
}
.graph-node.status-disputed .graph-node__circle {
  stroke: var(--danger) !important;
}
.graph-node.status-review .graph-node__circle {
  stroke: var(--warning) !important; stroke-dasharray: 6 3;
}
.graph-node.status-hidden .graph-node__circle {
  opacity: 0.3; stroke-dasharray: 2 4;
}
.graph-node.dimmed { opacity: 0.5; }
.graph-node.matched .graph-node__circle { stroke: var(--accent) !important; stroke-width: 3; }

.graph-node__level {
  font-family: var(--font-mono);
  fill: var(--text); font-size: 11px; font-weight: 600;
  text-anchor: middle; dominant-baseline: central;
  pointer-events: none; user-select: none;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
}
.graph-node__label {
  font-family: var(--font-label);
  fill: var(--text-muted); font-size: 11px; text-anchor: middle;
  pointer-events: none; user-select: none;
}
.graph-node.selected .graph-node__label { fill: var(--text); font-weight: 600; }

.graph-node__pin {
  fill: var(--warning); pointer-events: none;
}

.domain-label {
  font-family: var(--font-display);
  fill: var(--text-dim); font-size: 18px; font-weight: 700;
  letter-spacing: 1px; text-anchor: middle;
  pointer-events: none; user-select: none; opacity: 0.2;
  cursor: pointer;
}
.domain-label.collapsed { opacity: 0.4; }

.graph-edge {
  fill: none; stroke: var(--edge); stroke-width: 1.2;
  opacity: 0.4; transition: stroke 0.2s, opacity 0.2s;
}
.graph-edge.highlighted { stroke: var(--edge-highlight); opacity: 1; stroke-width: 2; }
.graph-edge.dimmed { opacity: 0.08; }

.curation-summary {
  position: absolute; top: 14px; right: 14px;
  min-width: 200px; background: var(--bg-elevated);
  border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: var(--shadow); padding: 12px 14px; z-index: 12;
}
.curation-summary__title { margin: 0 0 8px; font-family: var(--font-mono); font-size: 12px; font-weight: 600; text-transform: uppercase; color: var(--text-dim); }
.curation-summary__stats { display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
.curation-summary__stat { display: flex; justify-content: space-between; }
.curation-summary__stat-value {
  font-family: var(--font-mono);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1, "zero" 1;
}

.drawer {
  position: fixed; top: 0; right: 0; bottom: 0;
  width: 420px; background: var(--bg-elevated);
  border-left: 1px solid var(--border); box-shadow: var(--shadow);
  z-index: 30; display: flex; flex-direction: column;
  transform: translateX(100%); transition: transform 0.25s ease;
}
.drawer.open { transform: translateX(0); }
.drawer__header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 18px; border-bottom: 1px solid var(--border);
}
.drawer__title { margin: 0; font-family: var(--font-display); font-size: 17px; font-weight: 600; }
.drawer__close {
  border: none; background: none; color: var(--text-dim);
  font-size: 22px; cursor: pointer; line-height: 1;
}
.drawer__body { flex: 1; overflow-y: auto; padding: 16px 18px; }

.detail-section { margin-bottom: 18px; }
.detail-section h3 {
  margin: 0 0 8px; font-size: 12px; text-transform: uppercase;
  color: var(--text-dim); letter-spacing: 0.4px; font-family: var(--font-mono);
}
.detail-meta {
  display: grid; grid-template-columns: auto 1fr; gap: 4px 12px;
  font-size: 13px; margin-bottom: 14px;
}
.detail-meta dt { color: var(--text-dim); }
.detail-meta dd { margin: 0; color: var(--text); }

.curation-controls { display: flex; flex-direction: column; gap: 10px; }
.curation-toggle {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; border-radius: var(--radius);
  border: 1px solid var(--border); background: var(--bg-panel);
  cursor: pointer;
  transition:
    background-color 150ms cubic-bezier(0.23, 1, 0.32, 1),
    border-color 150ms cubic-bezier(0.23, 1, 0.32, 1),
    box-shadow 150ms cubic-bezier(0.23, 1, 0.32, 1),
    transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}
.curation-toggle:hover { border-color: var(--border-strong); }
.curation-toggle:active { transform: scale(0.99); }
.curation-toggle.active { border-color: var(--accent); background: var(--accent-soft); }
.curation-toggle.active--danger { border-color: var(--danger); background: var(--danger-soft); }
.curation-toggle.active--success { border-color: var(--success); background: var(--success-soft); }
.curation-toggle.active--warning { border-color: var(--warning); background: var(--warning-soft); }
.curation-toggle__label { font-size: 13px; font-weight: 500; }
.curation-toggle__desc { font-size: 11px; color: var(--text-dim); margin-top: 2px; }

.curation-input-group { display: flex; flex-direction: column; gap: 4px; }
.curation-input-group label { font-size: 12px; color: var(--text-dim); }
.curation-input {
  width: 100%; padding: 8px 10px; font-size: 13px;
  color: var(--text); background: var(--bg-panel);
  border: 1px solid var(--border); border-radius: var(--radius);
  outline: none; resize: vertical;
  transition:
    background-color 160ms cubic-bezier(0.23, 1, 0.32, 1),
    border-color 160ms cubic-bezier(0.23, 1, 0.32, 1),
    box-shadow 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.curation-input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-soft); }

.toast {
  position: fixed; bottom: 24px; left: 50%;
  transform: translateX(-50%) translateY(100px);
  padding: 12px 24px; border-radius: var(--radius);
  background: var(--bg-elevated); border: 1px solid var(--border);
  box-shadow: var(--shadow); z-index: 50;
  font-size: 13px; transition: transform 0.3s ease;
}
.toast.show { transform: translateX(-50%) translateY(0); }
.toast.toast--success { border-color: var(--success); color: var(--success); }
.toast.toast--error { border-color: var(--danger); color: var(--danger); }

.empty-state, .loading-state {
  position: absolute; inset: 0;
  z-index: 45;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-dim); font-size: 14px; pointer-events: none;
}
.loading-state {
  flex-direction: column;
  gap: 18px;
  background: var(--bg);
  opacity: 1;
  transition: opacity 240ms cubic-bezier(0.23, 1, 0.32, 1);
}
.loading-state[data-closing="true"] {
  opacity: 0;
}
.loading-state__loaders {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
}
.loading-state__text {
  position: relative;
  display: inline-block;
  margin: 0;
  color: var(--text-dim);
}
.loading-state__text::before {
  content: attr(data-text);
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: linear-gradient(
    90deg,
    transparent 0%,
    transparent 40%,
    oklch(0.92 0.02 155 / 0.86) 50%,
    transparent 60%,
    transparent 100%
  );
  background-size: 220% 100%;
  background-repeat: no-repeat;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  animation: t-shimmer 1800ms cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
.spiral-loader {
  --spiral-size: 24px;
  position: relative;
  display: block;
  width: var(--spiral-size);
  height: var(--spiral-size);
  flex: 0 0 auto;
  color: oklch(0.934 0.012 91.522);
}
.spiral-loader__phase {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  opacity: 0;
}
.spiral-loader__phase--fast {
  animation: spiral-loader-fast-phase 4000ms steps(1, end) infinite;
}
.spiral-loader__phase--slow {
  animation: spiral-loader-slow-phase 4000ms steps(1, end) infinite;
}
.spiral-loader__motion {
  transform: translate(-0.5px, 1.5px);
}
.spiral-loader__phase--fast .spiral-loader__motion {
  animation: spiral-loader-slide 500ms cubic-bezier(0.167, 0.167, 0.833, 0.833) infinite;
}
.spiral-loader__phase--slow .spiral-loader__motion {
  animation: spiral-loader-slide 1000ms cubic-bezier(0.167, 0.167, 0.833, 0.833) infinite;
}
.spiral-loader__path {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.24;
  stroke-dasharray: 21 100;
  stroke-dashoffset: -23;
}
.spiral-loader__phase--fast .spiral-loader__path {
  animation: spiral-loader-trim 500ms cubic-bezier(0.32, 0.154, 0.826, 0.579) infinite;
}
.spiral-loader__phase--slow .spiral-loader__path {
  animation: spiral-loader-trim 1000ms cubic-bezier(0.32, 0.313, 0.826, 0.143) infinite;
}
@keyframes t-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: 0% 0; }
}
@keyframes spiral-loader-fast-phase {
  0%, 49.999% { opacity: 1; }
  50%, 100% { opacity: 0; }
}
@keyframes spiral-loader-slow-phase {
  0%, 49.999% { opacity: 0; }
  50%, 100% { opacity: 1; }
}
@keyframes spiral-loader-slide {
  from { transform: translate(-0.5px, 1.5px); }
  to { transform: translate(-8.5px, 1.5px); }
}
@keyframes spiral-loader-trim {
  from { stroke-dashoffset: -23; }
  to { stroke-dashoffset: -57; }
}

@media (max-width: 768px) {
  .toolbar { flex-wrap: wrap; height: auto; padding: 8px 10px; gap: 8px; }
  .toolbar__search { order: 3; flex: 1 1 100%; max-width: none; }
  .filterbar { padding: 6px 10px; gap: 8px; overflow-x: auto; flex-wrap: nowrap; }
  .filterbar__group { flex-shrink: 0; }
  .filterbar__clear { margin-left: 0; flex-shrink: 0; }
  .curation-summary { display: none; }
  .drawer { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
  .loading-state__text::before,
  .spiral-loader__phase,
  .spiral-loader__motion,
  .spiral-loader__path {
    animation: none !important;
  }
  .spiral-loader__phase--fast { opacity: 1; }
  .spiral-loader__phase--slow { opacity: 0; }
  .spiral-loader__motion { transform: translate(-4.5px, 1.5px); }
  .spiral-loader__path { stroke-dashoffset: -40; }
}
"""

ADMIN_VIEWER_JS = """\
/**
 * Phase 2 admin curation viewer for the finished-run skill map.
 *
 * Loads the full internal graph.json (admin-visible, includes hidden/
 * disputed/review/low-confidence nodes) plus curation.json. Lets the admin
 * apply curation overrides:
 *
 * - Hide/mute node from public map (and restore)
 * - Feature/pin important node
 * - Collapse/expand domain regions (saved as default)
 * - Add public label/note overrides
 * - Approve low-confidence nodes for publish
 * - Approve disputed/review nodes for publish
 *
 * Save action writes curation.json. When running locally (fetch save
 * succeeds), it writes directly to the export folder. Otherwise it triggers
 * a browser download of curation.json (static-export-safe fallback).
 */
(function () {
  "use strict";

  var graphData = null;
  var viewerConfig = { enableSound: true, version: 1, mode: "admin" };
  var nodes = [];
  var edges = [];
  var domains = [];
  var domainColorMap = {};
  var curation = { version: 1, nodes: {}, domains: {}, global: { defaultCollapsedDomains: [] } };
  var collapsedDomains = {}; // session-level collapse state
  var layoutCache = null;
  var selectedNodeId = null;
  var dirty = false;
  var filters = { search: "", domain: "", status: "", curation: "" };
  var viewState = { x: 0, y: 0, scale: 1 };
  var VIEW = {
    minScale: 0.15, maxScale: 4,
    nodeBaseRadius: 18, nodeSpacingX: 200, nodeSpacingY: 120, domainPaddingY: 40,
  };

  var LOADING_EXIT_MS = 260;
  var sfx = new window.SfxEngine();
  var $ = function (id) { return document.getElementById(id); };
  var dom = {};

  function cacheDom() {
    ["viewport", "canvas", "graph-svg", "graph-zoom", "graph-edges",
     "graph-nodes", "graph-labels", "search-input", "search-clear",
     "filter-domain", "filter-status", "filter-curation", "filter-clear",
     "sound-toggle", "save-curation", "reset-view",
     "legend-toggle",
     "drawer", "drawer-title", "drawer-body", "drawer-close",
     "empty-state", "loading-state", "loading-message", "curation-stats",
     "save-toast"
    ].forEach(function (id) {
      dom[id.replace(/-/g, "_")] = $(id);
    });
  }

  async function init() {
    cacheDom();
    bindEvents();
    initSoundToggle();

    try {
      var results = await Promise.all([
        fetch("graph.json").then(function (r) { return r.json(); }),
        fetch("curation.json").then(function (r) { return r.json(); }).catch(function () { return null; }),
        fetch("config.json").then(function (r) { return r.json(); }).catch(function () { return null; }),
      ]);
      graphData = results[0];
      if (results[1]) curation = normalizeCuration(results[1]);
      if (results[2]) viewerConfig = results[2];
    } catch (err) {
      showError("Failed to load graph data: " + err.message);
      return;
    }

    processData();
    initCollapsedDomains();
    renderFilters();
    renderCurationSummary();
    layoutAndRender();

    finishLoading();
  }

  function showError(msg) {
    if (dom.loading_state) {
      delete dom.loading_state.dataset.closing;
    }
    setLoadingMessage(msg);
    dom.loading_state.hidden = false;
  }

  function finishLoading() {
    document.body.classList.remove("viewer-loading");
    if (!dom.loading_state) return;
    dom.loading_state.dataset.closing = "true";
    var delay = prefersReducedMotion() ? 0 : LOADING_EXIT_MS;
    window.setTimeout(function () {
      dom.loading_state.hidden = true;
      delete dom.loading_state.dataset.closing;
    }, delay);
  }

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function setLoadingMessage(msg) {
    if (!dom.loading_message) {
      dom.loading_state.textContent = msg;
      return;
    }
    dom.loading_message.textContent = msg;
    dom.loading_message.dataset.text = msg;
  }

  function normalizeCuration(data) {
    if (!data || typeof data !== "object") data = {};
    return {
      version: data.version || 1,
      nodes: data.nodes || {},
      domains: data.domains || {},
      global: data.global || { defaultCollapsedDomains: [] },
    };
  }

  function processData() {
    nodes = (graphData.nodes || []).filter(function (n) { return n && n.id; });
    edges = (graphData.edges || []).filter(function (e) {
      return e && (e.from_skill_id || e.fromSkillId) && (e.to_skill_id || e.toSkillId);
    });

    var domainSet = {};
    nodes.forEach(function (n) {
      var d = extractDomain(n);
      n._domain = d;
      domainSet[d] = true;
    });
    domains = Object.keys(domainSet).sort();
    var palette = ["--domain-1","--domain-2","--domain-3","--domain-4","--domain-5","--domain-6","--domain-7","--domain-8"];
    domainColorMap = {};
    domains.forEach(function (d, i) {
      domainColorMap[d] = "var(" + palette[i % palette.length] + ")";
    });
  }

  function extractDomain(node) {
    var desc = node.description || "";
    if (desc.indexOf("::") !== -1) {
      return desc.split("::")[0].trim() || "Uncategorized";
    }
    if (node.kind === "domain") return node.name || "Uncategorized";
    return "Uncategorized";
  }

  function initCollapsedDomains() {
    var defaults = (curation.global && curation.global.defaultCollapsedDomains) || [];
    defaults.forEach(function (d) { collapsedDomains[d] = true; });
    Object.keys(curation.domains || {}).forEach(function (d) {
      if (curation.domains[d].collapsed) collapsedDomains[d] = true;
    });
  }

  // --- Curation helpers ---
  function nodeCuration(nodeId) {
    if (!curation.nodes[nodeId]) curation.nodes[nodeId] = {};
    return curation.nodes[nodeId];
  }

  function isNodeHidden(nodeId) {
    var entry = curation.nodes[nodeId] || {};
    return !!entry.hidden;
  }

  function isNodeFeatured(nodeId) {
    var entry = curation.nodes[nodeId] || {};
    return !!entry.featured;
  }

  function isLowConfidenceApproved(nodeId) {
    var entry = curation.nodes[nodeId] || {};
    return !!entry.approveLowConfidence;
  }

  function isDisputedApproved(nodeId) {
    var entry = curation.nodes[nodeId] || {};
    return !!entry.approveDisputed;
  }

  function hasAnyOverride(nodeId) {
    var entry = curation.nodes[nodeId] || {};
    return Object.keys(entry).length > 0;
  }

  function markDirty() {
    dirty = true;
    dom.save_curation.classList.add("dirty");
  }

  function clearDirty() {
    dirty = false;
    dom.save_curation.classList.remove("dirty");
  }

  // --- Layout ---
  function computeLayout() {
    var byDomain = {};
    nodes.forEach(function (n) {
      var d = n._domain;
      if (!byDomain[d]) byDomain[d] = [];
      byDomain[d].push(n);
    });

    var domainOrder = Object.keys(byDomain).sort(function (a, b) {
      return byDomain[b].length - byDomain[a].length;
    });

    var positions = {};
    var domainBBoxes = {};
    var curY = 0;
    var maxCols = 0;

    domainOrder.forEach(function (domain) {
      var domainNodes = byDomain[domain].slice().sort(function (a, b) {
        var lvlDiff = (b.level || 0) - (a.level || 0);
        if (lvlDiff !== 0) return lvlDiff;
        return (a.name || "").localeCompare(b.name || "");
      });

      var cols = Math.min(domainNodes.length, Math.ceil(Math.sqrt(domainNodes.length)) + 2);
      cols = Math.max(cols, 1);
      maxCols = Math.max(maxCols, cols);

      var startY = curY + VIEW.domainPaddingY;
      domainNodes.forEach(function (n, i) {
        var col = i % cols;
        var row = Math.floor(i / cols);
        positions[n.id] = { x: col * VIEW.nodeSpacingX, y: startY + row * VIEW.nodeSpacingY };
      });

      var rows = Math.ceil(domainNodes.length / cols);
      var domainHeight = rows * VIEW.nodeSpacingY + VIEW.domainPaddingY * 2;
      var domainWidth = cols * VIEW.nodeSpacingX;
      domainBBoxes[domain] = {
        x: 0, y: curY, width: domainWidth, height: domainHeight,
        centerX: domainWidth / 2, labelY: curY + 18,
      };
      curY += domainHeight;
    });

    layoutCache = { positions: positions, domainBBoxes: domainBBoxes, totalHeight: curY, totalWidth: maxCols * VIEW.nodeSpacingX };
  }

  function layoutAndRender() {
    computeLayout();
    renderGraph();
    updateEmptyState();
  }

  function nodeRadius(node) {
    return VIEW.nodeBaseRadius + (node.level || 0) * 4;
  }

  function nodeColor(node) {
    return domainColorMap[node._domain] || domainColorMap["Uncategorized"];
  }

  function matchesFilters(node) {
    if (filters.domain && node._domain !== filters.domain) return false;
    if (filters.status) {
      var st = (node.status || "active").toLowerCase();
      if (filters.status === "hidden" && st !== "hidden") return false;
      if (filters.status === "active" && st !== "active") return false;
      if (filters.status === "disputed" && st !== "disputed") return false;
      if (filters.status === "review" && st !== "review") return false;
      if (filters.status === "stale" && st !== "stale") return false;
      if (filters.status === "historical" && (node.freshness || "").toLowerCase() !== "historical") return false;
    }
    if (filters.curation) {
      if (filters.curation === "hidden" && !isNodeHidden(node.id)) return false;
      if (filters.curation === "featured" && !isNodeFeatured(node.id)) return false;
      if (filters.curation === "approved" && !isLowConfidenceApproved(node.id) && !isDisputedApproved(node.id)) return false;
      if (filters.curation === "overridden" && !hasAnyOverride(node.id)) return false;
    }
    if (filters.search) {
      var q = filters.search.toLowerCase();
      if ((node.name || "").toLowerCase().indexOf(q) === -1 &&
          (node._domain || "").toLowerCase().indexOf(q) === -1 &&
          (node.description || "").toLowerCase().indexOf(q) === -1) return false;
    }
    return true;
  }

  function getVisibleNodeIds() {
    var visible = new Set();
    nodes.forEach(function (node) {
      if (matchesFilters(node)) visible.add(node.id);
    });
    return visible;
  }

  function isDomainCollapsed(domain) {
    return !!collapsedDomains[domain];
  }

  function renderGraph() {
    if (!layoutCache) return;
    var pos = layoutCache.positions;
    var ns = "http://www.w3.org/2000/svg";

    dom.graph_edges.innerHTML = "";
    dom.graph_nodes.innerHTML = "";
    dom.graph_labels.innerHTML = "";

    // Domain labels
    Object.keys(layoutCache.domainBBoxes).forEach(function (domain) {
      var bbox = layoutCache.domainBBoxes[domain];
      var label = document.createElementNS(ns, "text");
      label.setAttribute("class", "domain-label" + (isDomainCollapsed(domain) ? " collapsed" : ""));
      label.setAttribute("x", bbox.centerX);
      label.setAttribute("y", bbox.labelY);
      label.textContent = domain.toUpperCase() + (isDomainCollapsed(domain) ? " [+]" : " [-]");
      label.addEventListener("click", function () { toggleDomain(domain); });
      dom.graph_labels.appendChild(label);
    });

    var visibleNodeIds = getVisibleNodeIds();

    // Edges
    edges.forEach(function (edge) {
      var fromId = edge.from_skill_id || edge.fromSkillId;
      var toId = edge.to_skill_id || edge.toSkillId;
      if (!visibleNodeIds.has(fromId) || !visibleNodeIds.has(toId)) return;
      // Skip edges into collapsed domains (except domain header node)
      var fromNode = nodes.find(function(n) { return n.id === fromId; });
      var toNode = nodes.find(function(n) { return n.id === toId; });
      if (fromNode && isDomainCollapsed(fromNode._domain) && fromNode.kind !== "domain") return;
      if (toNode && isDomainCollapsed(toNode._domain) && toNode.kind !== "domain") return;

      var from = pos[fromId];
      var to = pos[toId];
      if (!from || !to) return;

      var path = document.createElementNS(ns, "path");
      path.setAttribute("class", "graph-edge");
      path.setAttribute("d", bezierPath(from, to));
      var et = (edge.edge_type || edge.edgeType || "related_to").toLowerCase();
      if (et === "uses_tool" || et === "produces_artifact") path.setAttribute("stroke-dasharray", "3 3");
      else if (et !== "parent_of" && et !== "part_of") path.setAttribute("stroke-dasharray", "5 5");

      if (selectedNodeId && fromId !== selectedNodeId && toId !== selectedNodeId) {
        path.classList.add("dimmed");
      }
      dom.graph_edges.appendChild(path);
    });

    // Nodes
    nodes.forEach(function (node) {
      var p = pos[node.id];
      if (!p) return;
      if (!visibleNodeIds.has(node.id)) return;
      // In collapsed domains, only show domain-kind nodes
      if (isDomainCollapsed(node._domain) && node.kind !== "domain") return;

      var r = nodeRadius(node);
      var g = document.createElementNS(ns, "g");
      g.setAttribute("class", buildNodeClass(node));
      g.setAttribute("data-id", node.id);
      g.setAttribute("transform", "translate(" + p.x + "," + p.y + ")");
      if (selectedNodeId === node.id) g.classList.add("selected");

      var glow = document.createElementNS(ns, "circle");
      glow.setAttribute("class", "graph-node__glow");
      glow.setAttribute("r", r + 12);
      g.appendChild(glow);

      var circle = document.createElementNS(ns, "circle");
      circle.setAttribute("class", "graph-node__circle");
      circle.setAttribute("r", r);
      circle.style.stroke = nodeColor(node);
      g.appendChild(circle);

      var levelText = document.createElementNS(ns, "text");
      levelText.setAttribute("class", "graph-node__level");
      levelText.setAttribute("y", 1);
      levelText.textContent = "L" + (node.level || 0);
      g.appendChild(levelText);

      // Featured pin indicator
      if (isNodeFeatured(node.id)) {
        var pin = document.createElementNS(ns, "circle");
        pin.setAttribute("class", "graph-node__pin");
        pin.setAttribute("cx", r - 4);
        pin.setAttribute("cy", -(r - 4));
        pin.setAttribute("r", 4);
        g.appendChild(pin);
      }

      var labelText = document.createElementNS(ns, "text");
      labelText.setAttribute("class", "graph-node__label");
      labelText.setAttribute("y", r + 14);
      labelText.textContent = truncate(node.name || node.id, 20);
      g.appendChild(labelText);

      g.addEventListener("click", function (e) {
        e.stopPropagation();
        selectNode(node.id);
      });

      dom.graph_nodes.appendChild(g);
    });

    applyViewTransform();
  }

  function buildNodeClass(node) {
    var cls = "graph-node";
    var status = (node.status || "active").toLowerCase();
    cls += " status-" + status;
    if (isNodeHidden(node.id)) cls += " curation-hidden";
    if (isNodeFeatured(node.id)) cls += " curation-featured";
    if (isLowConfidenceApproved(node.id) || isDisputedApproved(node.id)) cls += " curation-approved";
    if ((node.freshness || "").toLowerCase() === "historical") cls += " dimmed";
    return cls;
  }

  function bezierPath(from, to) {
    var midY = from.y + (to.y - from.y) / 2;
    return "M" + from.x + "," + from.y + " C" + from.x + "," + midY + " " + to.x + "," + midY + " " + to.x + "," + to.y;
  }

  function truncate(s, n) {
    return s && s.length > n ? s.slice(0, n-1) + "\\u2026" : (s || "");
  }

  // --- Selection ---
  function selectNode(id) {
    selectedNodeId = id;
    renderGraph();
    centerOnNode(id);
    openDrawer(id);
    sfx.nodeSelect();
  }

  function deselectNode() {
    selectedNodeId = null;
    renderGraph();
    closeDrawer();
  }

  function centerOnNode(id) {
    if (!layoutCache) return;
    var p = layoutCache.positions[id];
    if (!p) return;
    var rect = dom.canvas.getBoundingClientRect();
    viewState.x = rect.width / 2 - p.x * viewState.scale;
    viewState.y = rect.height / 2 - p.y * viewState.scale;
    applyViewTransform();
  }

  function applyViewTransform() {
    dom.graph_zoom.setAttribute(
      "transform",
      "translate(" + viewState.x + "," + viewState.y + ") scale(" + viewState.scale + ")"
    );
  }

  function zoomAt(cx, cy, delta) {
    var newScale = Math.max(VIEW.minScale, Math.min(VIEW.maxScale, viewState.scale * (1 + delta)));
    var ratio = newScale / viewState.scale;
    viewState.x = cx - (cx - viewState.x) * ratio;
    viewState.y = cy - (cy - viewState.y) * ratio;
    viewState.scale = newScale;
    applyViewTransform();
  }

  function resetView() {
    if (!layoutCache) return;
    var rect = dom.canvas.getBoundingClientRect();
    var w = layoutCache.totalWidth + 100;
    var h = layoutCache.totalHeight + 100;
    var scale = Math.max(VIEW.minScale, Math.min(rect.width / w, rect.height / h, 1));
    viewState.scale = scale;
    viewState.x = rect.width / 2 - (layoutCache.totalWidth / 2) * scale;
    viewState.y = rect.height / 2 - (layoutCache.totalHeight / 2) * scale;
    applyViewTransform();
  }

  // --- Drawer with curation controls ---
  function openDrawer(id) {
    var node = nodes.find(function (n) { return n.id === id; });
    if (!node) return;

    dom.drawer_title.textContent = node.name || id;
    dom.drawer_body.innerHTML = buildNodeDetail(node);
    dom.drawer.hidden = false;
    dom.drawer.setAttribute("aria-hidden", "false");
    requestAnimationFrame(function () { dom.drawer.classList.add("open"); });
    bindCurationControls(node);
    sfx.drawerOpen();
  }

  function closeDrawer() {
    dom.drawer.classList.remove("open");
    setTimeout(function () {
      dom.drawer.setAttribute("aria-hidden", "true");
      dom.drawer.hidden = true;
    }, 250);
    sfx.drawerClose();
  }

  function buildNodeDetail(node) {
    var entry = curation.nodes[node.id] || {};
    var status = (node.status || "active").toLowerCase();
    var conf = node.confidence || 0;
    var isLowConf = conf < 0.25;
    var isDisputed = status === "disputed" || status === "review";

    var parts = [];

    // Node info
    parts.push('<div class="detail-section"><h3>Skill info</h3>');
    parts.push('<dl class="detail-meta">');
    parts.push('<dt>Domain</dt><dd>' + esc(node._domain) + '</dd>');
    parts.push('<dt>Level</dt><dd>L' + (node.level || 0) + '</dd>');
    parts.push('<dt>Confidence</dt><dd>' + Math.round(conf * 100) + '%</dd>');
    parts.push('<dt>Status</dt><dd>' + esc(status) + '</dd>');
    parts.push('<dt>Freshness</dt><dd>' + esc(node.freshness || 'unknown') + '</dd>');
    parts.push('</dl></div>');

    // Curation controls
    parts.push('<div class="detail-section"><h3>Curation</h3>');
    parts.push('<div class="curation-controls">');

    // Hide/restore toggle
    parts.push(toggleControl(
      "toggle-hidden", !!entry.hidden, "danger",
      entry.hidden ? "Hidden from public" : "Visible to public",
      entry.hidden ? "Click to restore" : "Hide/mute from public map",
      "curation-toggle--hidden"
    ));

    // Feature/pin toggle
    parts.push(toggleControl(
      "toggle-featured", !!entry.featured, "warning",
      entry.featured ? "Featured/pinned" : "Feature/pin",
      entry.featured ? "Click to unfeature" : "Mark as important on public map",
      "curation-toggle--featured"
    ));

    // Approve low-confidence (only relevant if node is low confidence)
    if (isLowConf) {
      parts.push(toggleControl(
        "toggle-approve-lc", !!entry.approveLowConfidence, "success",
        entry.approveLowConfidence ? "Low-confidence approved" : "Approve low-confidence",
        entry.approveLowConfidence ? "Node will be published despite low confidence" : "Publish this node despite low confidence (score unchanged)",
        "curation-toggle--approve-lc"
      ));
    }

    // Approve disputed/review (only relevant if node is disputed/review)
    if (isDisputed) {
      parts.push(toggleControl(
        "toggle-approve-disputed", !!entry.approveDisputed, "success",
        entry.approveDisputed ? "Disputed approved" : "Approve for publish",
        entry.approveDisputed ? "Node will be published despite disputed/review status" : "Publish this node despite disputed/review status",
        "curation-toggle--approve-disputed"
      ));
    }

    parts.push('</div></div>');

    // Public label override
    parts.push('<div class="detail-section"><h3>Public label override</h3>');
    parts.push('<div class="curation-input-group">');
    parts.push('<label for="input-label">Public label (replaces skill name)</label>');
    parts.push('<input type="text" id="input-label" class="curation-input" value="' + esc(entry.publicLabel || "") + '" placeholder="' + esc(node.name || "") + '">');
    parts.push('</div></div>');

    // Public note override
    parts.push('<div class="detail-section"><h3>Public note</h3>');
    parts.push('<div class="curation-input-group">');
    parts.push('<label for="input-note">Public-facing note shown in the drawer</label>');
    parts.push('<textarea id="input-note" class="curation-input" rows="3" placeholder="Add a public note...">' + esc(entry.publicNote || "") + '</textarea>');
    parts.push('</div></div>');

    return parts.join("");
  }

  function toggleControl(id, active, variant, label, desc, dataAttr) {
    var cls = "curation-toggle";
    if (active) cls += " active active--" + variant;
    return '<div class="' + cls + '" id="' + id + '" data-curation="' + dataAttr + '" role="switch" aria-checked="' + active + '" tabindex="0">' +
           '<div><div class="curation-toggle__label">' + label + '</div>' +
           '<div class="curation-toggle__desc">' + desc + '</div></div></div>';
  }

  function bindCurationControls(node) {
    var entry = nodeCuration(node.id);

    function toggleSwitch(el, key) {
      var isActive = !!entry[key];
      el.addEventListener("click", function () {
        entry[key] = !isActive;
        isActive = entry[key];
        el.classList.toggle("active", isActive);
        el.classList.toggle("active--danger", isActive && key === "hidden");
        el.classList.toggle("active--warning", isActive && key === "featured");
        el.classList.toggle("active--success", isActive && (key === "approveLowConfidence" || key === "approveDisputed"));
        el.setAttribute("aria-checked", String(isActive));
        markDirty();
        renderGraph();
        renderCurationSummary();
      });
    }

    var hideEl = $("toggle-hidden");
    if (hideEl) toggleSwitch(hideEl, "hidden");

    var featEl = $("toggle-featured");
    if (featEl) toggleSwitch(featEl, "featured");

    var lcEl = $("toggle-approve-lc");
    if (lcEl) toggleSwitch(lcEl, "approveLowConfidence");

    var dispEl = $("toggle-approve-disputed");
    if (dispEl) toggleSwitch(dispEl, "approveDisputed");

    var labelEl = $("input-label");
    if (labelEl) {
      labelEl.addEventListener("input", function () {
        var val = labelEl.value.trim();
        if (val) entry.publicLabel = val;
        else delete entry.publicLabel;
        markDirty();
      });
    }

    var noteEl = $("input-note");
    if (noteEl) {
      noteEl.addEventListener("input", function () {
        var val = noteEl.value.trim();
        if (val) entry.publicNote = val;
        else delete entry.publicNote;
        markDirty();
      });
    }
  }

  function toggleDomain(domain) {
    collapsedDomains[domain] = !collapsedDomains[domain];
    // Update curation default collapsed domains
    var defaults = curation.global.defaultCollapsedDomains || [];
    var idx = defaults.indexOf(domain);
    if (collapsedDomains[domain] && idx === -1) {
      defaults.push(domain);
    } else if (!collapsedDomains[domain] && idx !== -1) {
      defaults.splice(idx, 1);
    }
    curation.global.defaultCollapsedDomains = defaults;
    // Also store per-domain collapsed state
    if (!curation.domains[domain]) curation.domains[domain] = {};
    curation.domains[domain].collapsed = collapsedDomains[domain];
    markDirty();
    renderGraph();
    sfx.domainToggle(!collapsedDomains[domain]);
  }

  // --- Curation summary ---
  function renderCurationSummary() {
    if (!viewerConfig.curationSummary && !dirty) {
      // Use config summary if available and no unsaved changes
      var cs = viewerConfig.curationSummary;
      if (cs) {
        renderCurationSummaryFrom(cs);
        return;
      }
    }
    // Compute live from current curation state
    var hidden = 0, featured = 0, lcApproved = 0, dispApproved = 0, overridden = 0;
    nodes.forEach(function (n) {
      var hasOvr = false;
      if (isNodeHidden(n.id)) { hidden++; hasOvr = true; }
      if (isNodeFeatured(n.id)) { featured++; hasOvr = true; }
      if (isLowConfidenceApproved(n.id)) { lcApproved++; hasOvr = true; }
      if (isDisputedApproved(n.id)) { dispApproved++; hasOvr = true; }
      if (hasOvr) overridden++;
    });
    var collapsed = Object.keys(collapsedDomains).filter(function(d) { return collapsedDomains[d]; });
    renderCurationSummaryFrom({
      totalNodes: nodes.length,
      hiddenCount: hidden,
      featuredCount: featured,
      lowConfidenceApprovedCount: lcApproved,
      disputedApprovedCount: dispApproved,
      nodesWithOverrides: overridden,
      collapsedDomains: collapsed,
    });
  }

  function renderCurationSummaryFrom(cs) {
    var parts = [];
    parts.push(sumStat("Total nodes", cs.totalNodes));
    parts.push(sumStat("Hidden", cs.hiddenCount));
    parts.push(sumStat("Featured", cs.featuredCount));
    parts.push(sumStat("LC approved", cs.lowConfidenceApprovedCount));
    parts.push(sumStat("Disputed approved", cs.disputedApprovedCount));
    parts.push(sumStat("Collapsed domains", (cs.collapsedDomains || []).length));
    dom.curation_stats.innerHTML = parts.join("");
  }

  function sumStat(label, value) {
    return '<div class="curation-summary__stat"><span>' + label + '</span><span class="curation-summary__stat-value">' + value + '</span></div>';
  }

  function updateEmptyState() {
    dom.empty_state.hidden = getVisibleNodeIds().size > 0;
  }

  // --- Save curation ---
  async function saveCuration() {
    // Clean up empty entries
    var cleaned = { version: 1, nodes: {}, domains: {}, global: curation.global || {} };
    Object.keys(curation.nodes).forEach(function (id) {
      var entry = curation.nodes[id];
      var clean = {};
      Object.keys(entry).forEach(function (k) {
        if (entry[k] !== null && entry[k] !== undefined && entry[k] !== "") clean[k] = entry[k];
      });
      if (Object.keys(clean).length > 0) cleaned.nodes[id] = clean;
    });
    Object.keys(curation.domains).forEach(function (d) {
      var entry = curation.domains[d];
      var clean = {};
      Object.keys(entry).forEach(function (k) {
        if (entry[k] !== null && entry[k] !== undefined && entry[k] !== "") clean[k] = entry[k];
      });
      if (Object.keys(clean).length > 0) cleaned.domains[d] = clean;
    });

    var json = JSON.stringify(cleaned, null, 2);

    // Try to save via fetch (works when served from the export folder locally).
    // The export folder does not have a backend server, so this will typically
    // fail in a pure static file context. The fallback is a download.
    var saved = false;
    try {
      var resp = await fetch("curation.json", {
        method: "PUT",
        body: json,
        headers: { "Content-Type": "application/json" },
      });
      if (resp.ok || resp.status === 204) saved = true;
    } catch (_e) {
      // fetch PUT not supported (static file server) - fall through to download
    }

    if (!saved) {
      // Browser-safe fallback: trigger a download of curation.json.
      // The admin places this file in the export folder manually.
      downloadFile("curation.json", json);
      showToast("Downloaded curation.json - place it in the export folder", "success");
      sfx.nodeSelect(); // reuse as save confirmation
      clearDirty();
      return;
    }

    showToast("Curation saved", "success");
    sfx.nodeSelect();
    clearDirty();
    renderCurationSummary();
  }

  function downloadFile(filename, content) {
    var blob = new Blob([content], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 100);
  }

  function showToast(msg, type) {
    dom.save_toast.textContent = msg;
    dom.save_toast.className = "toast show toast--" + (type || "");
    dom.save_toast.hidden = false;
    setTimeout(function () {
      dom.save_toast.classList.remove("show");
      setTimeout(function () { dom.save_toast.hidden = true; }, 300);
    }, 3000);
  }

  // --- Filters ---
  function renderFilters() {
    domains.forEach(function (d) {
      var opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      dom.filter_domain.appendChild(opt);
    });
  }

  // --- Sound toggle ---
  function initSoundToggle() {
    var shouldBeOn = sfx.shouldBeOn(viewerConfig.enableSound);
    updateSoundToggle(shouldBeOn);
    function unlockOnce() {
      sfx.unlock();
      if (shouldBeOn && !sfx.isEnabled()) sfx.setEnabled(true);
      document.removeEventListener("pointerdown", unlockOnce);
      document.removeEventListener("keydown", unlockOnce);
    }
    document.addEventListener("pointerdown", unlockOnce);
    document.addEventListener("keydown", unlockOnce);
  }

  function updateSoundToggle(on) {
    dom.sound_toggle.setAttribute("aria-pressed", String(on));
    var offIcon = dom.sound_toggle.querySelector(".sound-off");
    var onIcon = dom.sound_toggle.querySelector(".sound-on");
    if (offIcon && onIcon) { offIcon.hidden = on; onIcon.hidden = !on; }
  }

  // --- Pan & Zoom ---
  function initPanZoom() {
    var isPanning = false, startX, startY, startVX, startVY;

    dom.canvas.addEventListener("mousedown", function (e) {
      if (e.button !== 0) return;
      if (e.target.closest(".graph-node")) return;
      isPanning = true;
      startX = e.clientX; startY = e.clientY;
      startVX = viewState.x; startVY = viewState.y;
      dom.canvas.classList.add("panning");
      sfx.unlock();
    });
    window.addEventListener("mousemove", function (e) {
      if (!isPanning) return;
      viewState.x = startVX + (e.clientX - startX);
      viewState.y = startVY + (e.clientY - startY);
      applyViewTransform();
    });
    window.addEventListener("mouseup", function () {
      isPanning = false;
      dom.canvas.classList.remove("panning");
    });
    dom.canvas.addEventListener("click", function (e) {
      if (e.target === dom.canvas || e.target === dom.graph_svg) deselectNode();
    });
    dom.canvas.addEventListener("wheel", function (e) {
      e.preventDefault();
      var rect = dom.canvas.getBoundingClientRect();
      zoomAt(e.clientX - rect.left, e.clientY - rect.top, -e.deltaY * 0.001);
    }, { passive: false });
  }

  // --- Events ---
  function bindEvents() {
    initPanZoom();

    var searchTimer = null;
    dom.search_input.addEventListener("input", function () {
      clearTimeout(searchTimer);
      dom.search_clear.hidden = !dom.search_input.value;
      var val = dom.search_input.value;
      searchTimer = setTimeout(function () {
        filters.search = val;
        renderGraph();
        updateEmptyState();
      }, 120);
    });
    dom.search_clear.addEventListener("click", function () {
      dom.search_input.value = "";
      dom.search_clear.hidden = true;
      filters.search = "";
      renderGraph();
      updateEmptyState();
    });

    function onFilterChange() {
      filters.domain = dom.filter_domain.value;
      filters.status = dom.filter_status.value;
      filters.curation = dom.filter_curation.value;
      renderGraph();
      updateEmptyState();
      sfx.filterSwitch();
    }
    ["change"].forEach(function (evt) {
      dom.filter_domain.addEventListener(evt, onFilterChange);
      dom.filter_status.addEventListener(evt, onFilterChange);
      dom.filter_curation.addEventListener(evt, onFilterChange);
    });
    dom.filter_clear.addEventListener("click", function () {
      dom.filter_domain.value = "";
      dom.filter_status.value = "";
      dom.filter_curation.value = "";
      filters = { search: filters.search, domain: "", status: "", curation: "" };
      renderGraph();
      updateEmptyState();
    });

    dom.save_curation.addEventListener("click", saveCuration);
    dom.sound_toggle.addEventListener("click", function () {
      var nowOn = !sfx.isEnabled();
      sfx.setEnabled(nowOn);
      updateSoundToggle(nowOn);
    });
    dom.reset_view.addEventListener("click", resetView);
    dom.drawer_close.addEventListener("click", closeDrawer);

    document.addEventListener("keydown", function (e) {
      if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT" || e.target.tagName === "TEXTAREA") {
        if (e.key === "Escape") e.target.blur();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveCuration();
        return;
      }
      switch (e.key) {
        case "Escape":
          if (selectedNodeId) { closeDrawer(); selectedNodeId = null; renderGraph(); }
          break;
        case "/":
          e.preventDefault();
          dom.search_input.focus();
          break;
        case "r": case "R":
          resetView();
          break;
      }
    });

    window.addEventListener("resize", function () { applyViewTransform(); });
  }

  function esc(s) {
    if (s == null) return "";
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
"""
