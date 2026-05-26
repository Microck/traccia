#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { chromium } from "playwright";

const url = process.argv[2] || "http://127.0.0.1:3023";
const executablePath =
  process.env.CHROMIUM_EXECUTABLE ||
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ||
  "/usr/bin/chromium-browser";
const viewportWidth = Number(process.env.TRACCIA_PERF_VIEWPORT_WIDTH || 1440);
const viewportHeight = Number(process.env.TRACCIA_PERF_VIEWPORT_HEIGHT || 950);
const viewportDpr = Number(process.env.TRACCIA_PERF_VIEWPORT_DPR || 1);
const hasTouch = process.env.TRACCIA_PERF_HAS_TOUCH === "1";
const isMobile = process.env.TRACCIA_PERF_IS_MOBILE === "1";
const runMouseDrag = !hasTouch || process.env.TRACCIA_PERF_INCLUDE_MOUSE_DRAG === "1";
const maxP95FrameGapMs = Number(process.env.TRACCIA_PERF_MAX_P95_FRAME_GAP_MS || 180);
const maxLongTaskMs = Number(process.env.TRACCIA_PERF_MAX_LONG_TASK_MS || 250);
const maxTotalLongTaskMs = Number(process.env.TRACCIA_PERF_MAX_TOTAL_LONG_TASK_MS || 2500);
const maxCanvasCoverageMissFrames = Number(
  process.env.TRACCIA_PERF_MAX_CANVAS_COVERAGE_MISS_FRAMES || 0,
);
const maxInputMicrotaskMs = Number(process.env.TRACCIA_PERF_MAX_INPUT_MICROTASK_MS || 50);
const maxInputRafP95Ms = Number(process.env.TRACCIA_PERF_MAX_INPUT_RAF_P95_MS || 120);
const maxInputRafMs = Number(process.env.TRACCIA_PERF_MAX_INPUT_RAF_MS || 220);
const failGlobalFrameBudgets = process.env.TRACCIA_PERF_FAIL_GLOBAL_FRAME_BUDGETS === "1";

function percentile(values, p) {
  if (!values.length) return 0;
  const sorted = values.slice().sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p));
  return sorted[index];
}

async function imageDelta(before, after) {
  const dir = await mkdtemp(join(tmpdir(), "traccia-pixel-delta-"));
  const beforePath = join(dir, "before.png");
  const afterPath = join(dir, "after.png");
  await writeFile(beforePath, before);
  await writeFile(afterPath, after);
  const python = String.raw`
import json
import sys
from PIL import Image, ImageChops, ImageStat

before = Image.open(sys.argv[1]).convert("RGBA")
after = Image.open(sys.argv[2]).convert("RGBA")
if before.size != after.size:
    raise SystemExit(f"image size mismatch: {before.size} != {after.size}")
diff = ImageChops.difference(before, after)
stat = ImageStat.Stat(diff)
pixels = before.size[0] * before.size[1]
changed = 0
for pixel in diff.getdata():
    if pixel != (0, 0, 0, 0):
        changed += 1
mean_abs = sum(stat.sum) / max(1, pixels * 4 * 255)
print(json.dumps({
    "width": before.size[0],
    "height": before.size[1],
    "changedPixelRatio": changed / max(1, pixels),
    "meanAbsoluteRatio": mean_abs,
}))
`;
  const result = spawnSync("python3", ["-c", python, beforePath, afterPath], {
    encoding: "utf8",
  });
  await rm(dir, { recursive: true, force: true });
  if (result.status !== 0) {
    throw new Error(`pixel delta failed: ${result.stderr || result.stdout}`);
  }
  return JSON.parse(result.stdout);
}

const browser = await chromium.launch({
  executablePath,
  headless: true,
  args: [
    "--no-sandbox",
    "--ignore-gpu-blocklist",
    "--enable-gpu-rasterization",
    "--enable-zero-copy",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
  ],
});

const page = await browser.newPage({
  viewport: { width: viewportWidth, height: viewportHeight },
  deviceScaleFactor: viewportDpr,
  hasTouch,
  isMobile,
});

const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => {
  consoleErrors.push(error.message);
});

await page.goto(url, { waitUntil: "networkidle" });
await page.waitForFunction(
  () => document.body && !document.body.classList.contains("viewer-loading"),
  null,
  { timeout: 30000 },
);
await page.waitForSelector(".domain-label", { timeout: 30000 });

async function cameraState() {
  return page.evaluate(() => {
    const graphZoom = document.querySelector("#graph-zoom");
    const graphSvg = document.querySelector("#graph-svg");
    const graphCanvas = document.querySelector("#graph-canvas");
    function parseGraphZoomTransform(transform) {
      const match = String(transform || "").match(
        /translate\(\s*(-?[0-9.eE]+)\s*,\s*(-?[0-9.eE]+)\s*\)\s*scale\(\s*(-?[0-9.eE]+)\s*\)/,
      );
      if (!match) return { x: 0, y: 0, scale: 1 };
      return {
        x: Number.parseFloat(match[1]) || 0,
        y: Number.parseFloat(match[2]) || 0,
        scale: Number.parseFloat(match[3]) || 1,
      };
    }
    function parseOrigin(origin) {
      const parts = String(origin || "0px 0px").split(/\s+/);
      return {
        x: Number.parseFloat(parts[0]) || 0,
        y: Number.parseFloat(parts[1] || parts[0]) || 0,
      };
    }
    function matrixFor(transform) {
      if (!transform || transform === "none") return new DOMMatrix();
      return new DOMMatrix(transform);
    }
    function projectCssPoint(rect, style, point) {
      const origin = parseOrigin(style.transformOrigin);
      const matrix = matrixFor(style.transform);
      const localX = point.x - origin.x;
      const localY = point.y - origin.y;
      return {
        x: rect.left + origin.x + matrix.a * localX + matrix.c * localY + matrix.e,
        y: rect.top + origin.y + matrix.b * localX + matrix.d * localY + matrix.f,
      };
    }
    function layoutRectFor(element, viewportRect) {
      const style = getComputedStyle(element);
      return {
        left: viewportRect.left + (Number.parseFloat(style.left) || 0),
        top: viewportRect.top + (Number.parseFloat(style.top) || 0),
      };
    }
    function canvasCoverageMissPx() {
      const viewport = document.querySelector("#canvas");
      if (!viewport || !graphCanvas) return Infinity;
      const viewportRect = viewport.getBoundingClientRect();
      const canvasStyle = getComputedStyle(graphCanvas);
      const canvasRect = layoutRectFor(graphCanvas, viewportRect);
      const width = Number.parseFloat(canvasStyle.width) || graphCanvas.clientWidth || 0;
      const height = Number.parseFloat(canvasStyle.height) || graphCanvas.clientHeight || 0;
      const origin = parseOrigin(canvasStyle.transformOrigin);
      const matrix = matrixFor(canvasStyle.transform);
      const corners = [
        { x: 0, y: 0 },
        { x: width, y: 0 },
        { x: 0, y: height },
        { x: width, y: height },
      ].map((point) => {
        const localX = point.x - origin.x;
        const localY = point.y - origin.y;
        return {
          x: canvasRect.left + origin.x + matrix.a * localX + matrix.c * localY + matrix.e,
          y: canvasRect.top + origin.y + matrix.b * localX + matrix.d * localY + matrix.f,
        };
      });
      const minX = Math.min(...corners.map((point) => point.x));
      const maxX = Math.max(...corners.map((point) => point.x));
      const minY = Math.min(...corners.map((point) => point.y));
      const maxY = Math.max(...corners.map((point) => point.y));
      return Math.max(
        Math.max(0, minX - viewportRect.left),
        Math.max(0, minY - viewportRect.top),
        Math.max(0, viewportRect.right - maxX),
        Math.max(0, viewportRect.bottom - maxY),
      );
    }
    function svgCanvasAlignment() {
      if (!graphZoom || !graphSvg || !graphCanvas) return { maxDeltaPx: Infinity, aligned: false };
      const viewport = document.querySelector("#canvas");
      if (!viewport) return { maxDeltaPx: Infinity, aligned: false };
      const base = parseGraphZoomTransform(graphZoom.getAttribute("transform"));
      const viewportRect = viewport.getBoundingClientRect();
      const svgRect = layoutRectFor(graphSvg, viewportRect);
      const canvasRect = layoutRectFor(graphCanvas, viewportRect);
      const svgStyle = getComputedStyle(graphSvg);
      const canvasStyle = getComputedStyle(graphCanvas);
      const canvasPad = Math.abs(Number.parseFloat(graphCanvas.style.left) || 0);
      const points = [
        { x: 0, y: 0 },
        { x: 500, y: -240 },
        { x: 1100, y: 820 },
      ];
      let maxDeltaPx = 0;
      for (const point of points) {
        const baseX = base.x + point.x * base.scale;
        const baseY = base.y + point.y * base.scale;
        const svgPoint = projectCssPoint(svgRect, svgStyle, { x: baseX, y: baseY });
        const canvasPoint = projectCssPoint(canvasRect, canvasStyle, {
          x: baseX + canvasPad,
          y: baseY + canvasPad,
        });
        maxDeltaPx = Math.max(
          maxDeltaPx,
          Math.abs(svgPoint.x - canvasPoint.x),
          Math.abs(svgPoint.y - canvasPoint.y),
        );
      }
      return { maxDeltaPx, aligned: maxDeltaPx <= 1.5 };
    }
    const alignment = svgCanvasAlignment();
    return {
      graphZoomTransform: graphZoom?.getAttribute("transform") || "",
      graphSvgTransform: graphSvg ? getComputedStyle(graphSvg).transform : "",
      graphCanvasTransform: graphCanvas ? getComputedStyle(graphCanvas).transform : "",
      graphCanvasTransformOrigin: graphCanvas ? getComputedStyle(graphCanvas).transformOrigin : "",
      svgCanvasAlignmentMaxDeltaPx: alignment.maxDeltaPx,
      svgCanvasAligned: alignment.aligned,
      canvasCoverageMissPx: canvasCoverageMissPx(),
    };
  });
}

await page.evaluate(({ runMouseDrag }) => {
  function cameraState() {
    const graphZoom = document.querySelector("#graph-zoom");
    const graphSvg = document.querySelector("#graph-svg");
    const graphCanvas = document.querySelector("#graph-canvas");
    function parseGraphZoomTransform(transform) {
      const match = String(transform || "").match(
        /translate\(\s*(-?[0-9.eE]+)\s*,\s*(-?[0-9.eE]+)\s*\)\s*scale\(\s*(-?[0-9.eE]+)\s*\)/,
      );
      if (!match) return { x: 0, y: 0, scale: 1 };
      return {
        x: Number.parseFloat(match[1]) || 0,
        y: Number.parseFloat(match[2]) || 0,
        scale: Number.parseFloat(match[3]) || 1,
      };
    }
    function parseOrigin(origin) {
      const parts = String(origin || "0px 0px").split(/\s+/);
      return {
        x: Number.parseFloat(parts[0]) || 0,
        y: Number.parseFloat(parts[1] || parts[0]) || 0,
      };
    }
    function matrixFor(transform) {
      if (!transform || transform === "none") return new DOMMatrix();
      return new DOMMatrix(transform);
    }
    function projectCssPoint(rect, style, point) {
      const origin = parseOrigin(style.transformOrigin);
      const matrix = matrixFor(style.transform);
      const localX = point.x - origin.x;
      const localY = point.y - origin.y;
      return {
        x: rect.left + origin.x + matrix.a * localX + matrix.c * localY + matrix.e,
        y: rect.top + origin.y + matrix.b * localX + matrix.d * localY + matrix.f,
      };
    }
    function layoutRectFor(element, viewportRect) {
      const style = getComputedStyle(element);
      return {
        left: viewportRect.left + (Number.parseFloat(style.left) || 0),
        top: viewportRect.top + (Number.parseFloat(style.top) || 0),
      };
    }
    function canvasCoverageMissPx() {
      const viewport = document.querySelector("#canvas");
      if (!viewport || !graphCanvas) return Infinity;
      const viewportRect = viewport.getBoundingClientRect();
      const canvasStyle = getComputedStyle(graphCanvas);
      const canvasRect = layoutRectFor(graphCanvas, viewportRect);
      const width = Number.parseFloat(canvasStyle.width) || graphCanvas.clientWidth || 0;
      const height = Number.parseFloat(canvasStyle.height) || graphCanvas.clientHeight || 0;
      const origin = parseOrigin(canvasStyle.transformOrigin);
      const matrix = matrixFor(canvasStyle.transform);
      const corners = [
        { x: 0, y: 0 },
        { x: width, y: 0 },
        { x: 0, y: height },
        { x: width, y: height },
      ].map((point) => {
        const localX = point.x - origin.x;
        const localY = point.y - origin.y;
        return {
          x: canvasRect.left + origin.x + matrix.a * localX + matrix.c * localY + matrix.e,
          y: canvasRect.top + origin.y + matrix.b * localX + matrix.d * localY + matrix.f,
        };
      });
      const minX = Math.min(...corners.map((point) => point.x));
      const maxX = Math.max(...corners.map((point) => point.x));
      const minY = Math.min(...corners.map((point) => point.y));
      const maxY = Math.max(...corners.map((point) => point.y));
      return Math.max(
        Math.max(0, minX - viewportRect.left),
        Math.max(0, minY - viewportRect.top),
        Math.max(0, viewportRect.right - maxX),
        Math.max(0, viewportRect.bottom - maxY),
      );
    }
    function svgCanvasAlignment() {
      if (!graphZoom || !graphSvg || !graphCanvas) return { maxDeltaPx: Infinity, aligned: false };
      const viewport = document.querySelector("#canvas");
      if (!viewport) return { maxDeltaPx: Infinity, aligned: false };
      const base = parseGraphZoomTransform(graphZoom.getAttribute("transform"));
      const viewportRect = viewport.getBoundingClientRect();
      const svgRect = layoutRectFor(graphSvg, viewportRect);
      const canvasRect = layoutRectFor(graphCanvas, viewportRect);
      const svgStyle = getComputedStyle(graphSvg);
      const canvasStyle = getComputedStyle(graphCanvas);
      const canvasPad = Math.abs(Number.parseFloat(graphCanvas.style.left) || 0);
      const points = [
        { x: 0, y: 0 },
        { x: 500, y: -240 },
        { x: 1100, y: 820 },
      ];
      let maxDeltaPx = 0;
      for (const point of points) {
        const baseX = base.x + point.x * base.scale;
        const baseY = base.y + point.y * base.scale;
        const svgPoint = projectCssPoint(svgRect, svgStyle, { x: baseX, y: baseY });
        const canvasPoint = projectCssPoint(canvasRect, canvasStyle, {
          x: baseX + canvasPad,
          y: baseY + canvasPad,
        });
        maxDeltaPx = Math.max(
          maxDeltaPx,
          Math.abs(svgPoint.x - canvasPoint.x),
          Math.abs(svgPoint.y - canvasPoint.y),
        );
      }
      return { maxDeltaPx, aligned: maxDeltaPx <= 1.5 };
    }
    const alignment = svgCanvasAlignment();
    return {
      graphZoomTransform: graphZoom?.getAttribute("transform") || "",
      graphSvgTransform: graphSvg ? graphSvg.style.transform : "",
      graphCanvasTransform: graphCanvas ? graphCanvas.style.transform : "",
      graphCanvasTransformOrigin: graphCanvas ? getComputedStyle(graphCanvas).transformOrigin : "",
      svgCanvasAlignmentMaxDeltaPx: alignment.maxDeltaPx,
      svgCanvasAligned: alignment.aligned,
      canvasCoverageMissPx: canvasCoverageMissPx(),
    };
  }

  function cameraChanged(before, after) {
    return (
      before.graphZoomTransform !== after.graphZoomTransform ||
      before.graphSvgTransform !== after.graphSvgTransform ||
      before.graphCanvasTransform !== after.graphCanvasTransform
    );
  }

  window.__tracciaInputProbe = { records: [] };
  const probe = window.__tracciaInputProbe;

  function inlinePx(value) {
    return Number.parseFloat(value || "0") || 0;
  }

  function parseOrigin(origin) {
    const parts = String(origin || "0px 0px").split(/\s+/);
    return {
      x: Number.parseFloat(parts[0]) || 0,
      y: Number.parseFloat(parts[1] || parts[0]) || 0,
    };
  }

  function matrixFor(transform) {
    if (!transform || transform === "none") return new DOMMatrix();
    return new DOMMatrix(transform);
  }

  function canvasCoverageMissPxLite() {
    const viewport = document.querySelector("#canvas");
    const graphCanvas = document.querySelector("#graph-canvas");
    if (!viewport || !graphCanvas) return Infinity;
    const viewportWidth = viewport.clientWidth || window.innerWidth || 0;
    const viewportHeight = viewport.clientHeight || window.innerHeight || 0;
    const canvasStyle = graphCanvas.style;
    const left = inlinePx(canvasStyle.left);
    const top = inlinePx(canvasStyle.top);
    const width = inlinePx(canvasStyle.width) || graphCanvas.width || 0;
    const height = inlinePx(canvasStyle.height) || graphCanvas.height || 0;
    const origin = parseOrigin(canvasStyle.transformOrigin);
    const matrix = matrixFor(canvasStyle.transform);
    const corners = [
      { x: 0, y: 0 },
      { x: width, y: 0 },
      { x: 0, y: height },
      { x: width, y: height },
    ].map((point) => {
      const localX = point.x - origin.x;
      const localY = point.y - origin.y;
      return {
        x: left + origin.x + matrix.a * localX + matrix.c * localY + matrix.e,
        y: top + origin.y + matrix.b * localX + matrix.d * localY + matrix.f,
      };
    });
    const minX = Math.min(...corners.map((point) => point.x));
    const maxX = Math.max(...corners.map((point) => point.x));
    const minY = Math.min(...corners.map((point) => point.y));
    const maxY = Math.max(...corners.map((point) => point.y));
    return Math.max(
      Math.max(0, minX),
      Math.max(0, minY),
      Math.max(0, viewportWidth - maxX),
      Math.max(0, viewportHeight - maxY),
    );
  }

  function cameraStateForInput() {
    const graphZoom = document.querySelector("#graph-zoom");
    const graphSvg = document.querySelector("#graph-svg");
    const graphCanvas = document.querySelector("#graph-canvas");
    const graphSvgTransform = graphSvg ? graphSvg.style.transform : "";
    const graphCanvasTransform = graphCanvas ? graphCanvas.style.transform : "";
    return {
      graphZoomTransform: graphZoom?.getAttribute("transform") || "",
      graphSvgTransform,
      graphCanvasTransform,
      svgCanvasAligned: graphSvgTransform === graphCanvasTransform,
      svgCanvasAlignmentMaxDeltaPx: graphSvgTransform === graphCanvasTransform ? 0 : Infinity,
      canvasCoverageMissPx: canvasCoverageMissPxLite(),
    };
  }

  function recordInput(type) {
    const startedAt = performance.now();
    const before = cameraStateForInput();
    const record = { type, microtask: null, raf: null };
    probe.records.push(record);

    queueMicrotask(() => {
      const after = cameraStateForInput();
      record.microtask = {
        elapsedMs: performance.now() - startedAt,
        changed: cameraChanged(before, after),
        svgCanvasSame: after.graphSvgTransform === after.graphCanvasTransform,
        svgCanvasAligned: after.svgCanvasAligned,
        svgCanvasAlignmentMaxDeltaPx: after.svgCanvasAlignmentMaxDeltaPx,
        canvasCoverageMissPx: after.canvasCoverageMissPx,
      };
    });

    requestAnimationFrame(() => {
      const after = cameraStateForInput();
      record.raf = {
        elapsedMs: performance.now() - startedAt,
        changed: cameraChanged(before, after),
        svgCanvasSame: after.graphSvgTransform === after.graphCanvasTransform,
        svgCanvasAligned: after.svgCanvasAligned,
        svgCanvasAlignmentMaxDeltaPx: after.svgCanvasAlignmentMaxDeltaPx,
        canvasCoverageMissPx: after.canvasCoverageMissPx,
      };
    });
  }

  const canvas = document.querySelector("#canvas");
  if (canvas) {
    canvas.addEventListener("wheel", () => recordInput("wheel"), { capture: true, passive: true });
    canvas.addEventListener("touchmove", (event) => {
      recordInput(event.touches && event.touches.length === 2 ? "pinchmove" : "touchmove");
    }, { capture: true, passive: true });
  }
  if (runMouseDrag) {
    window.addEventListener("mousemove", (event) => {
      if (event.buttons === 1) recordInput("dragmove");
    }, { capture: true, passive: true });
  }
}, { runMouseDrag });

function cameraChanged(before, after) {
  return (
    before.graphZoomTransform !== after.graphZoomTransform ||
    before.graphSvgTransform !== after.graphSvgTransform ||
    before.graphCanvasTransform !== after.graphCanvasTransform
  );
}

async function dispatchSyntheticTouch(type, points) {
  await page.evaluate(({ type, points }) => {
    const canvas = document.querySelector("#canvas");
    if (!canvas) throw new Error("Canvas missing for synthetic touch pan.");
    const touchPoints = points.map((point, index) => ({
      clientX: point.x,
      clientY: point.y,
      identifier: point.id || index + 1,
      target: canvas,
    }));
    const event = new Event(type, { bubbles: true, cancelable: true });
    Object.defineProperty(event, "touches", {
      value: type === "touchend" ? [] : touchPoints,
    });
    Object.defineProperty(event, "changedTouches", { value: touchPoints });
    canvas.dispatchEvent(event);
  }, { type, points });
}

const initialSoundPressed = await page.locator("#sound-toggle").getAttribute("aria-pressed");
const svgNodeBodyCount = await page.locator(".graph-node__circle").count();
const svgSkillLabelCount = await page.locator("#graph-labels .graph-node__label").count();
const zoomProbeBox = await page.locator("#canvas").boundingBox();
if (!zoomProbeBox) {
  throw new Error("Viewer canvas was not measurable for zoom probe.");
}
const zoomCameraBefore = await cameraState();
const zoomPixelsBefore = await page.locator("#canvas").screenshot();
await page.mouse.move(
  zoomProbeBox.x + zoomProbeBox.width * 0.5,
  zoomProbeBox.y + zoomProbeBox.height * 0.5,
);
await page.mouse.wheel(0, -420);
const zoomPixelsImmediate = await page.locator("#canvas").screenshot();
const zoomPixelDelta = await imageDelta(zoomPixelsBefore, zoomPixelsImmediate);
const zoomCameraImmediate = await cameraState();
await page.waitForTimeout(80);
const zoomCameraDuring = await cameraState();
const zoomOpacityDuring = await page
  .locator("#graph-zoom")
  .evaluate((node) => Number.parseFloat(getComputedStyle(node).opacity));
await page.waitForTimeout(700);
const zoomOutCameraBefore = await cameraState();
await page.mouse.wheel(0, 720);
const zoomOutCameraImmediate = await cameraState();
await page.waitForTimeout(120);
const zoomOutCameraDuring = await cameraState();
await page.waitForTimeout(420);

const domainLabels = await page
  .locator(".domain-label")
  .evaluateAll((nodes) => nodes.map((node) => node.textContent.trim()).filter(Boolean));
const targetText =
  domainLabels.find((text) => /AI|Automation|Code|Tooling|Data|Analysis/.test(text)) ||
  domainLabels[0];

await page.locator(".domain-label", { hasText: targetText }).first().click({ force: true });
await page.waitForTimeout(3000);

const viewportBox = await page.locator("#canvas").boundingBox();
if (!viewportBox) {
  throw new Error("Viewer canvas was not measurable.");
}
const startX = viewportBox.x + viewportBox.width * 0.52;
const startY = viewportBox.y + viewportBox.height * 0.54;
let dragCameraBefore = null;
let dragCameraImmediate = null;
let dragPixelDelta = null;
if (runMouseDrag) {
  await page.mouse.move(startX, startY);
  dragCameraBefore = await cameraState();
  const dragPixelsBefore = await page.locator("#canvas").screenshot();
  await page.mouse.down();
  await page.mouse.move(startX + 42, startY + 27);
  const dragPixelsImmediate = await page.locator("#canvas").screenshot();
  dragPixelDelta = await imageDelta(dragPixelsBefore, dragPixelsImmediate);
  dragCameraImmediate = await cameraState();
}

await page.evaluate(() => {
  window.__tracciaViewerMetrics = {};
  window.__tracciaPerf = {
    errors: [],
    frameGaps: [],
    graphCameraTransforms: [],
    longTasks: [],
    lastFrame: performance.now(),
    minGraphZoomOpacity: 1,
    observing: true,
  };
  const perf = window.__tracciaPerf;
  perf.observer = new PerformanceObserver((list) => {
    list.getEntries().forEach((entry) => {
      perf.longTasks.push(entry.duration);
    });
  });
  try {
    perf.observer.observe({ entryTypes: ["longtask"] });
  } catch (error) {
    perf.errors.push(String(error));
  }
  function perfFrame(now) {
    if (!perf.observing) return;
    perf.frameGaps.push(now - perf.lastFrame);
    perf.lastFrame = now;
    const graphZoom = document.querySelector("#graph-zoom");
    const graphSvg = document.querySelector("#graph-svg");
    if (graphZoom) {
      perf.graphCameraTransforms.push([
        graphZoom.getAttribute("transform") || "",
        graphSvg ? graphSvg.style.transform : "",
      ].join(" | "));
    }
    requestAnimationFrame(perfFrame);
  }
  requestAnimationFrame(perfFrame);
  perf.startedAt = performance.now();

  window.__tracciaChunkProbe = {
    observing: true,
    frames: 0,
    coverageMissFrames: 0,
    maxCoverageMissPx: 0,
  };
  const probe = window.__tracciaChunkProbe;
  const canvas = document.querySelector("#graph-canvas");
  const viewport = document.querySelector("#canvas");
  function inlinePx(value) {
    return Number.parseFloat(value || "0") || 0;
  }
  function parseOrigin(origin) {
    const parts = String(origin || "0px 0px").split(/\s+/);
    return {
      x: Number.parseFloat(parts[0]) || 0,
      y: Number.parseFloat(parts[1] || parts[0]) || 0,
    };
  }
  function matrixFor(transform) {
    if (!transform || transform === "none") return new DOMMatrix();
    return new DOMMatrix(transform);
  }
  function transformedCanvasCoverageMissPx() {
    if (!canvas || !viewport) return Infinity;
    const viewportWidth = viewport.clientWidth || window.innerWidth || 0;
    const viewportHeight = viewport.clientHeight || window.innerHeight || 0;
    const left = inlinePx(canvas.style.left);
    const top = inlinePx(canvas.style.top);
    const width = inlinePx(canvas.style.width) || canvas.width || 0;
    const height = inlinePx(canvas.style.height) || canvas.height || 0;
    const origin = parseOrigin(canvas.style.transformOrigin);
    const matrix = matrixFor(canvas.style.transform);
    const corners = [
      { x: 0, y: 0 },
      { x: width, y: 0 },
      { x: 0, y: height },
      { x: width, y: height },
    ].map((point) => {
      const localX = point.x - origin.x;
      const localY = point.y - origin.y;
      return {
        x: left + origin.x + matrix.a * localX + matrix.c * localY + matrix.e,
        y: top + origin.y + matrix.b * localX + matrix.d * localY + matrix.f,
      };
    });
    const minX = Math.min(...corners.map((point) => point.x));
    const maxX = Math.max(...corners.map((point) => point.x));
    const minY = Math.min(...corners.map((point) => point.y));
    const maxY = Math.max(...corners.map((point) => point.y));
    return Math.max(
      Math.max(0, minX),
      Math.max(0, minY),
      Math.max(0, viewportWidth - maxX),
      Math.max(0, viewportHeight - maxY),
    );
  }
  function frame() {
    if (!probe.observing) return;
    if (canvas) {
      const missPx = transformedCanvasCoverageMissPx();
      if (missPx > 1) {
        probe.coverageMissFrames += 1;
        probe.maxCoverageMissPx = Math.max(probe.maxCoverageMissPx, missPx);
      }
    }
    probe.frames += 1;
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
});

// The probes above intentionally take screenshots immediately after input to
// verify visual movement. Screenshot capture can delay the next rAF, so reset
// input timing here and collect clean interaction samples for latency budgets.
await page.evaluate(() => {
  if (window.__tracciaInputProbe) {
    window.__tracciaInputProbe.records = [];
  }
});
await page.mouse.move(startX, startY);
await page.mouse.wheel(0, -180);
await page.waitForTimeout(80);

if (runMouseDrag) {
  for (let step = 2; step <= 24; step += 1) {
    await page.mouse.move(startX + step * 42, startY + step * 27);
    await page.waitForTimeout(16);
  }
  await page.mouse.up();
}
if (hasTouch) {
  const touchStartX = viewportBox.x + viewportBox.width * 0.42;
  const touchStartY = viewportBox.y + viewportBox.height * 0.48;
  await dispatchSyntheticTouch("touchstart", [{ x: touchStartX, y: touchStartY, id: 1 }]);
  await page.waitForTimeout(16);
  for (let step = 1; step <= 16; step += 1) {
    await dispatchSyntheticTouch("touchmove", [{
      x: touchStartX + step * 18,
      y: touchStartY + step * 11,
      id: 1,
    }]);
    await page.waitForTimeout(16);
  }
  await dispatchSyntheticTouch("touchend", [{
    x: touchStartX + 16 * 18,
    y: touchStartY + 16 * 11,
    id: 1,
  }]);
  await page.waitForTimeout(80);

  const pinchCenterX = viewportBox.x + viewportBox.width * 0.5;
  const pinchCenterY = viewportBox.y + viewportBox.height * 0.5;
  await dispatchSyntheticTouch("touchstart", [
    { x: pinchCenterX - 36, y: pinchCenterY, id: 1 },
    { x: pinchCenterX + 36, y: pinchCenterY, id: 2 },
  ]);
  await page.waitForTimeout(16);
  for (let step = 1; step <= 12; step += 1) {
    const spread = 36 + step * 5;
    await dispatchSyntheticTouch("touchmove", [
      { x: pinchCenterX - spread, y: pinchCenterY - step * 1.5, id: 1 },
      { x: pinchCenterX + spread, y: pinchCenterY + step * 1.5, id: 2 },
    ]);
    await page.waitForTimeout(16);
  }
  await dispatchSyntheticTouch("touchend", [
    { x: pinchCenterX - 96, y: pinchCenterY - 18, id: 1 },
    { x: pinchCenterX + 96, y: pinchCenterY + 18, id: 2 },
  ]);
}
await page.waitForTimeout(900);

const measurement = await page.evaluate((probe) => {
  const errors = [];
  const perf = window.__tracciaPerf;
  if (!perf) throw new Error("Performance recorder was not initialized.");
  perf.observing = false;
  if (perf.observer) perf.observer.disconnect();
  if (window.__tracciaChunkProbe) window.__tracciaChunkProbe.observing = false;

  return {
    target: probe.targetText,
    durationMs: performance.now() - perf.startedAt,
    dragCameraBefore: probe.dragCameraBefore,
    dragCameraImmediate: probe.dragCameraImmediate,
    frameGaps: perf.frameGaps,
    graphCameraTransformCount: new Set(perf.graphCameraTransforms).size,
    minGraphZoomOpacity: perf.minGraphZoomOpacity,
    longTasks: perf.longTasks,
    selectedDomains: document.querySelectorAll(".domain-label.selected").length,
    shelfRows: document.querySelectorAll("#drawer .focus-row, #sheet .focus-row").length,
    canvasOpacity: Number.parseFloat(getComputedStyle(document.querySelector(".graph-canvas")).opacity),
    focusActiveClass: document.querySelector(".graph-svg.focus-active") ? 1 : 0,
    chunkProbe: window.__tracciaChunkProbe || null,
    inputProbe: window.__tracciaInputProbe || null,
    viewerMetrics: window.__tracciaViewerMetrics || {},
    errors: perf.errors.concat(errors),
  };
}, { targetText, dragCameraBefore, dragCameraImmediate });

await browser.close();

const p95FrameGapMs = percentile(measurement.frameGaps, 0.95);
const maxFrameGapMs = measurement.frameGaps.length ? Math.max(...measurement.frameGaps) : 0;
const maxLongTask = measurement.longTasks.length ? Math.max(...measurement.longTasks) : 0;
const totalLongTask = measurement.longTasks.reduce((sum, value) => sum + value, 0);
const inputRecords = measurement.inputProbe?.records || [];

function summarizeInputProbe(records) {
  const byType = {};
  const inputTypes = ["wheel", "dragmove"];
  if (hasTouch) inputTypes.push("touchmove", "pinchmove");
  for (const type of inputTypes) {
    if (type === "dragmove" && !runMouseDrag) continue;
    const matching = records.filter((record) => record.type === type);
    const rafTimes = matching.map((record) => record.raf?.elapsedMs).filter(Number.isFinite);
    const microtaskTimes = matching
      .map((record) => record.microtask?.elapsedMs)
      .filter(Number.isFinite);
    byType[type] = {
      count: matching.length,
      firstRafMs: Number((rafTimes[0] || 0).toFixed(2)),
      maxRafMs: Number((rafTimes.length ? Math.max(...rafTimes) : 0).toFixed(2)),
      p95RafMs: Number(percentile(rafTimes, 0.95).toFixed(2)),
      maxMicrotaskMs: Number((microtaskTimes.length ? Math.max(...microtaskTimes) : 0).toFixed(2)),
      allRafChanged: matching.every((record) => record.raf?.changed),
      allRafSvgCanvasSame: matching.every((record) => record.raf?.svgCanvasSame),
      allRafSvgCanvasAligned: matching.every((record) => record.raf?.svgCanvasAligned),
      maxSvgCanvasAlignmentDeltaPx: Number(
        Math.max(
          0,
          ...matching
            .map((record) => record.raf?.svgCanvasAlignmentMaxDeltaPx)
            .filter(Number.isFinite),
        ).toFixed(2),
      ),
      maxCanvasCoverageMissPx: Number(
        Math.max(
          0,
          ...matching
            .map((record) => record.raf?.canvasCoverageMissPx)
            .filter(Number.isFinite),
        ).toFixed(2),
      ),
    };
  }
  return byType;
}
const inputProbeSummary = summarizeInputProbe(inputRecords);

const result = {
  url,
  viewport: {
    width: viewportWidth,
    height: viewportHeight,
    dpr: viewportDpr,
    hasTouch,
    isMobile,
    runMouseDrag,
  },
  targetText,
  initialSoundPressed,
  svgNodeBodyCount,
  svgSkillLabelCount,
  zoomProbe: {
    before: zoomCameraBefore,
    immediate: zoomCameraImmediate,
    during: zoomCameraDuring,
    pixelDeltaImmediate: zoomPixelDelta,
    changedImmediately: cameraChanged(zoomCameraBefore, zoomCameraImmediate),
    changedDuringWheel: cameraChanged(zoomCameraBefore, zoomCameraDuring),
    svgCanvasSameImmediate:
      zoomCameraImmediate.graphSvgTransform === zoomCameraImmediate.graphCanvasTransform,
    svgCanvasAlignedImmediate: zoomCameraImmediate.svgCanvasAligned,
    svgCanvasAlignmentMaxDeltaPx: Number(zoomCameraImmediate.svgCanvasAlignmentMaxDeltaPx.toFixed(2)),
    canvasCoverageMissPx: Number(zoomCameraImmediate.canvasCoverageMissPx.toFixed(2)),
    opacityDuringWheel: zoomOpacityDuring,
  },
  zoomOutProbe: {
    before: zoomOutCameraBefore,
    immediate: zoomOutCameraImmediate,
    during: zoomOutCameraDuring,
    changedImmediately: cameraChanged(zoomOutCameraBefore, zoomOutCameraImmediate),
    changedDuringWheel: cameraChanged(zoomOutCameraBefore, zoomOutCameraDuring),
    svgCanvasAlignedImmediate: zoomOutCameraImmediate.svgCanvasAligned,
    svgCanvasAlignmentMaxDeltaPx: Number(zoomOutCameraImmediate.svgCanvasAlignmentMaxDeltaPx.toFixed(2)),
    canvasCoverageMissPx: Number(zoomOutCameraImmediate.canvasCoverageMissPx.toFixed(2)),
  },
  selectedDomains: measurement.selectedDomains,
  dragProbe: runMouseDrag ? {
    before: measurement.dragCameraBefore,
    immediate: measurement.dragCameraImmediate,
    pixelDeltaImmediate: dragPixelDelta,
    changedImmediately: cameraChanged(measurement.dragCameraBefore, measurement.dragCameraImmediate),
    svgCanvasSameImmediate:
      measurement.dragCameraImmediate.graphSvgTransform === measurement.dragCameraImmediate.graphCanvasTransform,
    svgCanvasAlignedImmediate: measurement.dragCameraImmediate.svgCanvasAligned,
    svgCanvasAlignmentMaxDeltaPx: Number(
      measurement.dragCameraImmediate.svgCanvasAlignmentMaxDeltaPx.toFixed(2),
    ),
    canvasCoverageMissPx: Number(measurement.dragCameraImmediate.canvasCoverageMissPx.toFixed(2)),
  } : null,
  shelfRows: measurement.shelfRows,
  canvasOpacity: measurement.canvasOpacity,
  focusActiveClass: measurement.focusActiveClass,
  frameCount: measurement.frameGaps.length,
  graphCameraTransformCount: measurement.graphCameraTransformCount,
  minGraphZoomOpacityDuringDrag: measurement.minGraphZoomOpacity,
  p95FrameGapMs: Number(p95FrameGapMs.toFixed(2)),
  maxFrameGapMs: Number(maxFrameGapMs.toFixed(2)),
  longTaskCount: measurement.longTasks.length,
  maxLongTaskMs: Number(maxLongTask.toFixed(2)),
  totalLongTaskMs: Number(totalLongTask.toFixed(2)),
  chunkProbe: measurement.chunkProbe,
  inputProbe: inputProbeSummary,
  viewerMetrics: measurement.viewerMetrics,
  consoleErrors,
  observerErrors: measurement.errors,
  budgets: {
    maxP95FrameGapMs,
    maxLongTaskMs,
    maxTotalLongTaskMs,
    maxCanvasCoverageMissFrames,
    maxInputMicrotaskMs,
    maxInputRafP95Ms,
    maxInputRafMs,
    failGlobalFrameBudgets,
  },
};

console.log(JSON.stringify(result, null, 2));

const failures = [];
if (initialSoundPressed !== "true") failures.push("sound toggle was not on by default");
if (svgNodeBodyCount !== 0) {
  failures.push(`SVG duplicate node bodies were created (${svgNodeBodyCount})`);
}
if (!cameraChanged(zoomCameraBefore, zoomCameraImmediate)) {
  failures.push("SVG graph camera did not update immediately after wheel input");
}
if (!zoomCameraImmediate.svgCanvasAligned) {
  failures.push(
    `SVG overlay and canvas projected different immediate wheel positions ` +
      `(${zoomCameraImmediate.svgCanvasAlignmentMaxDeltaPx.toFixed(2)}px)`,
  );
}
if (zoomCameraImmediate.canvasCoverageMissPx > 1) {
  failures.push(
    `wheel exposed ${zoomCameraImmediate.canvasCoverageMissPx.toFixed(2)}px of uncovered canvas`,
  );
}
if (!cameraChanged(zoomOutCameraBefore, zoomOutCameraImmediate)) {
  failures.push("zoom-out camera did not update immediately after wheel input");
}
if (!zoomOutCameraImmediate.svgCanvasAligned) {
  failures.push(
    `zoom-out SVG/canvas visual positions diverged ` +
      `(${zoomOutCameraImmediate.svgCanvasAlignmentMaxDeltaPx.toFixed(2)}px)`,
  );
}
if (zoomOutCameraImmediate.canvasCoverageMissPx > 1) {
  failures.push(
    `zoom-out exposed ${zoomOutCameraImmediate.canvasCoverageMissPx.toFixed(2)}px of uncovered canvas`,
  );
}
if (zoomPixelDelta.changedPixelRatio < 0.002) {
  failures.push(
    `viewer pixels barely changed immediately after wheel input ` +
      `(${zoomPixelDelta.changedPixelRatio.toFixed(6)})`,
  );
}
if (!cameraChanged(zoomCameraBefore, zoomCameraDuring)) {
  failures.push("SVG graph camera did not update during wheel zoom");
}
if (zoomOpacityDuring < 0.99) {
  failures.push(`SVG graph camera faded during wheel zoom (${zoomOpacityDuring})`);
}
if (!measurement.selectedDomains) failures.push("domain selection did not activate");
if (runMouseDrag) {
  if (!cameraChanged(measurement.dragCameraBefore, measurement.dragCameraImmediate)) {
    failures.push("SVG graph camera did not update immediately after drag input");
  }
  if (measurement.dragCameraImmediate.graphSvgTransform !== measurement.dragCameraImmediate.graphCanvasTransform) {
    failures.push("SVG overlay and canvas used different immediate drag transforms");
  }
  if (dragPixelDelta.changedPixelRatio < 0.002) {
    failures.push(
      `viewer pixels barely changed immediately after drag input ` +
        `(${dragPixelDelta.changedPixelRatio.toFixed(6)})`,
    );
  }
}
if (!measurement.shelfRows) failures.push("focus shelf did not populate");
if (measurement.canvasOpacity < 0.95) failures.push("canvas context was faded out");
if (measurement.focusActiveClass) failures.push("focus mode hid non-focused SVG nodes");
if (measurement.graphCameraTransformCount < 2) failures.push("SVG graph camera did not update during drag");
if (measurement.minGraphZoomOpacity < 0.99) {
  failures.push(`SVG graph camera faded during drag (${measurement.minGraphZoomOpacity})`);
}
if ((measurement.viewerMetrics.cameraCacheBlit || 0) > 0) {
  failures.push(`canvas cache blitted during active camera input (${measurement.viewerMetrics.cameraCacheBlit})`);
}
if ((measurement.viewerMetrics.cameraCacheMissRedraw || 0) > 0) {
  failures.push(
    `canvas cache redrew during active camera input (${measurement.viewerMetrics.cameraCacheMissRedraw})`,
  );
}
if ((measurement.viewerMetrics.cameraCacheDeferredMiss || 0) > 0) {
  failures.push(
    `canvas cache exceeded active guard band (${measurement.viewerMetrics.cameraCacheDeferredMiss})`,
  );
}
if (consoleErrors.length) failures.push("browser console errors were emitted");
if (failGlobalFrameBudgets) {
  if (p95FrameGapMs > maxP95FrameGapMs) {
    failures.push(`p95 frame gap ${p95FrameGapMs.toFixed(2)}ms > ${maxP95FrameGapMs}ms`);
  }
  if (maxLongTask > maxLongTaskMs) {
    failures.push(`max long task ${maxLongTask.toFixed(2)}ms > ${maxLongTaskMs}ms`);
  }
  if (totalLongTask > maxTotalLongTaskMs) {
    failures.push(`total long task ${totalLongTask.toFixed(2)}ms > ${maxTotalLongTaskMs}ms`);
  }
}
if ((measurement.chunkProbe?.coverageMissFrames || 0) > maxCanvasCoverageMissFrames) {
  failures.push(
    `canvas coverage missed for ${measurement.chunkProbe.coverageMissFrames} frames ` +
      `(max ${measurement.chunkProbe.maxCoverageMissPx.toFixed(2)}px)`,
  );
}

const firstWheelInput = inputRecords.find((record) => record.type === "wheel");
const firstDragInput = inputRecords.find((record) => record.type === "dragmove");
const requiredInputRecords = [];
if (!hasTouch) requiredInputRecords.push(["wheel", firstWheelInput]);
if (runMouseDrag) requiredInputRecords.push(["drag", firstDragInput]);
if (hasTouch) {
  requiredInputRecords.push(["touch", inputRecords.find((record) => record.type === "touchmove")]);
  requiredInputRecords.push(["pinch", inputRecords.find((record) => record.type === "pinchmove")]);
}
for (const [label, record] of requiredInputRecords) {
  if (!record) {
    failures.push(`input probe did not record ${label} input`);
    continue;
  }
  if (!record.microtask) {
    failures.push(`${label} input probe did not reach post-event microtask`);
  } else {
    if (record.microtask.elapsedMs > maxInputMicrotaskMs) {
      failures.push(
        `${label} post-event microtask ${record.microtask.elapsedMs.toFixed(2)}ms > ${maxInputMicrotaskMs}ms`,
      );
    }
  }
  if (!record.raf) {
    failures.push(`${label} input probe did not reach next animation frame`);
  } else {
    if (!record.raf.changed) failures.push(`${label} camera did not change by next animation frame`);
    if (!record.raf.svgCanvasAligned) {
      failures.push(
        `${label} SVG/canvas visual positions diverged by next animation frame ` +
          `(${record.raf.svgCanvasAlignmentMaxDeltaPx.toFixed(2)}px)`,
      );
    }
    if (record.raf.canvasCoverageMissPx > 1) {
      failures.push(`${label} exposed ${record.raf.canvasCoverageMissPx.toFixed(2)}px of uncovered canvas`);
    }
  }
}

for (const [type, summary] of Object.entries(inputProbeSummary)) {
  if (!summary.count) continue;
  if (summary.p95RafMs > maxInputRafP95Ms) {
    failures.push(`${type} p95 next-frame update ${summary.p95RafMs.toFixed(2)}ms > ${maxInputRafP95Ms}ms`);
  }
  if (summary.maxRafMs > maxInputRafMs) {
    failures.push(`${type} max next-frame update ${summary.maxRafMs.toFixed(2)}ms > ${maxInputRafMs}ms`);
  }
}

for (const record of inputRecords) {
  if (!record.raf) continue;
  if (!record.raf.changed) failures.push(`${record.type} camera did not change by next animation frame`);
  if (!record.raf.svgCanvasAligned) {
    failures.push(
      `${record.type} SVG/canvas visual positions diverged by next animation frame ` +
        `(${record.raf.svgCanvasAlignmentMaxDeltaPx.toFixed(2)}px)`,
    );
  }
  if (record.raf.canvasCoverageMissPx > 1) {
    failures.push(`${record.type} exposed ${record.raf.canvasCoverageMissPx.toFixed(2)}px of uncovered canvas`);
  }
  if (record.raf.elapsedMs > maxInputRafMs) {
    failures.push(`${record.type} next-frame update ${record.raf.elapsedMs.toFixed(2)}ms > ${maxInputRafMs}ms`);
  }
}

if (failures.length) {
  console.error("Viewer performance check failed:");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}
