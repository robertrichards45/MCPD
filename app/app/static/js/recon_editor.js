/* Minimal drag/drop reconstruction diagram editor (no external deps).
 * - Items: road, car, deer, cone, arrow, text, measurement point
 * - Save: writes JSON to /reconstruction/<case_id>/diagram.json
 * - Export PNG: posts a generated PNG as an attachment (kind=diagram)
 */

(() => {
  const BUILD = "2026-02-10.3";
  const root = document.querySelector("[data-recon-editor]");
  if (!root) return;

  const assets = {
    car: new Image(),
    deer: new Image(),
  };
  // Same-origin SVG assets (more realistic than procedural shapes).
  assets.car.src = "/static/img/recon/car_top.svg";
  assets.deer.src = "/static/img/recon/deer.svg";
  assets.car.onload = () => scheduleDraw();
  assets.deer.onload = () => scheduleDraw();

  const caseId = root.getAttribute("data-case-id");
  const saveUrl = root.getAttribute("data-save-url");
  const loadUrl = root.getAttribute("data-load-url");
  const uploadUrl = root.getAttribute("data-upload-url");

  const canvas = root.querySelector("canvas");
  const ctx = canvas.getContext("2d");

  const statusEl = root.querySelector("[data-status]");
  const btnSave = root.querySelector("[data-action='save']");
  const btnExport = root.querySelector("[data-action='export']");
  const btnClear = root.querySelector("[data-action='clear']");
  const btnFit = root.querySelector("[data-action='fit']");

  const palette = root.querySelector("[data-palette]");

  const state = {
    view: { x: 0, y: 0, scale: 1 },
    items: [],
    selectedId: null,
    dragging: null, // {id, offx, offy, mode:'move'|'rotate'|'resize'}
    lastSavedAt: 0,
  };

  const GRID = 20;
  let rafPending = false;

  function setStatus(msg) {
    if (!statusEl) return;
    statusEl.textContent = msg;
  }

  function scheduleDraw() {
    if (rafPending) return;
    rafPending = true;
    requestAnimationFrame(() => {
      rafPending = false;
      draw();
    });
  }

  function nowMs() {
    return Date.now();
  }

  function uid() {
    return Math.random().toString(36).slice(2) + "-" + Math.random().toString(36).slice(2);
  }

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function snap(v) {
    return Math.round(v / GRID) * GRID;
  }

  function worldToScreen(pt) {
    return {
      x: (pt.x - state.view.x) * state.view.scale,
      y: (pt.y - state.view.y) * state.view.scale,
    };
  }

  function screenToWorld(pt) {
    return {
      x: pt.x / state.view.scale + state.view.x,
      y: pt.y / state.view.scale + state.view.y,
    };
  }

  function getMousePos(e) {
    const r = canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function resizeCanvasToContainer() {
    const wrap = root.querySelector("[data-canvas-wrap]");
    const r = wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    // Use container size; CSS controls the editor's visible height.
    canvas.width = Math.max(1, Math.floor(r.width * dpr));
    canvas.height = Math.max(1, Math.floor(r.height * dpr));
    canvas.style.width = Math.floor(r.width) + "px";
    canvas.style.height = Math.floor(r.height) + "px";
    scheduleDraw();
  }

  function defaultItem(type, at) {
    const base = {
      id: uid(),
      type,
      x: snap(at.x),
      y: snap(at.y),
      w: 120,
      h: 80,
      rot: 0,
      label: "",
    };
    switch (type) {
      case "road":
        return { ...base, w: 260, h: 120 };
      case "intersection":
        return { ...base, w: 260, h: 260 };
      case "curve_left":
        return { ...base, w: 260, h: 260 };
      case "curve_right":
        return { ...base, w: 260, h: 260 };
      case "car":
        return { ...base, w: 90, h: 45, label: "V" };
      case "deer":
        return { ...base, w: 70, h: 55 };
      case "cone":
        return { ...base, w: 40, h: 40 };
      case "arrow":
        return { ...base, w: 140, h: 30 };
      case "text":
        return { ...base, w: 220, h: 40, label: "Note" };
      case "point":
        return { ...base, w: 20, h: 20, label: "P" };
      default:
        return base;
    }
  }

  function itemAt(worldPt) {
    // Topmost first.
    for (let i = state.items.length - 1; i >= 0; i--) {
      const it = state.items[i];
      if (hitItem(it, worldPt)) return it;
    }
    return null;
  }

  function hitItem(it, p) {
    // Cheap: ignore rotation for hit test (keeps it simple).
    return p.x >= it.x && p.x <= it.x + it.w && p.y >= it.y && p.y <= it.y + it.h;
  }

  function drawGrid() {
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.width / dpr;
    const height = canvas.height / dpr;

    const topLeft = screenToWorld({ x: 0, y: 0 });
    const bottomRight = screenToWorld({ x: width, y: height });

    const x0 = Math.floor(topLeft.x / GRID) * GRID;
    const y0 = Math.floor(topLeft.y / GRID) * GRID;
    const x1 = Math.ceil(bottomRight.x / GRID) * GRID;
    const y1 = Math.ceil(bottomRight.y / GRID) * GRID;

    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(0,0,0,0.06)";
    for (let x = x0; x <= x1; x += GRID) {
      const s0 = worldToScreen({ x, y: y0 });
      const s1 = worldToScreen({ x, y: y1 });
      ctx.beginPath();
      ctx.moveTo(s0.x, s0.y);
      ctx.lineTo(s1.x, s1.y);
      ctx.stroke();
    }
    for (let y = y0; y <= y1; y += GRID) {
      const s0 = worldToScreen({ x: x0, y });
      const s1 = worldToScreen({ x: x1, y });
      ctx.beginPath();
      ctx.moveTo(s0.x, s0.y);
      ctx.lineTo(s1.x, s1.y);
      ctx.stroke();
    }
    ctx.restore();
  }

  function withItemTransform(it, fn) {
    const s = worldToScreen({ x: it.x, y: it.y });
    const w = it.w * state.view.scale;
    const h = it.h * state.view.scale;
    const cx = s.x + w / 2;
    const cy = s.y + h / 2;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((it.rot || 0) * (Math.PI / 180));
    ctx.translate(-cx, -cy);
    fn({ s, w, h, cx, cy });
    ctx.restore();
  }

  function drawItem(it) {
    withItemTransform(it, ({ s, w, h }) => {
      const x = s.x;
      const y = s.y;
      ctx.save();
      switch (it.type) {
        case "road": {
          // Asphalt slab + lane lines
          const grad = ctx.createLinearGradient(x, y, x, y + h);
          grad.addColorStop(0, "#2a2d30");
          grad.addColorStop(1, "#1f2225");
          ctx.fillStyle = grad;
          roundRect(ctx, x, y, w, h, 14, true, false);

          // edge lines
          ctx.strokeStyle = "rgba(255,255,255,0.30)";
          ctx.lineWidth = Math.max(2, Math.min(6, h * 0.03));
          ctx.beginPath();
          ctx.moveTo(x + 10, y + 10);
          ctx.lineTo(x + w - 10, y + 10);
          ctx.moveTo(x + 10, y + h - 10);
          ctx.lineTo(x + w - 10, y + h - 10);
          ctx.stroke();

          // center dashed line
          ctx.strokeStyle = "rgba(201,168,106,0.95)";
          ctx.lineWidth = Math.max(2, Math.min(6, h * 0.035));
          const mid = y + h / 2;
          dashedLine(x + 16, mid, x + w - 16, mid, 16, 14);
          break;
        }
        case "intersection": {
          const grad = ctx.createLinearGradient(x, y, x, y + h);
          grad.addColorStop(0, "#2a2d30");
          grad.addColorStop(1, "#1f2225");
          ctx.fillStyle = grad;
          roundRect(ctx, x, y, w, h, 18, true, false);

          // crossing roads
          ctx.fillStyle = "rgba(255,255,255,0.06)";
          ctx.fillRect(x + w * 0.38, y + 10, w * 0.24, h - 20);
          ctx.fillRect(x + 10, y + h * 0.38, w - 20, h * 0.24);

          // dashed center lines on both axes
          ctx.strokeStyle = "rgba(201,168,106,0.95)";
          ctx.lineWidth = Math.max(2, Math.min(6, w * 0.018));
          dashedLine(x + 20, y + h / 2, x + w - 20, y + h / 2, 16, 14);
          dashedLine(x + w / 2, y + 20, x + w / 2, y + h - 20, 16, 14);
          break;
        }
        case "curve_left":
        case "curve_right": {
          // Curved roadway segment (quarter circle).
          const dir = it.type === "curve_left" ? -1 : 1;
          const cx = x + (dir < 0 ? w : 0);
          const cy = y + h;
          const outerR = Math.min(w, h) * 0.95;
          const roadW = Math.max(40, Math.min(90, outerR * 0.28));
          const innerR = Math.max(10, outerR - roadW);

          // Asphalt ring.
          ctx.fillStyle = "#232629";
          ctx.beginPath();
          ctx.arc(cx, cy, outerR, Math.PI, Math.PI * 1.5, dir > 0);
          ctx.arc(cx, cy, innerR, Math.PI * 1.5, Math.PI, dir > 0);
          ctx.closePath();
          ctx.fill();

          // Edge lines.
          ctx.strokeStyle = "rgba(255,255,255,0.30)";
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.arc(cx, cy, outerR - 10, Math.PI, Math.PI * 1.5, dir > 0);
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(cx, cy, innerR + 10, Math.PI, Math.PI * 1.5, dir > 0);
          ctx.stroke();

          // Center dashed line.
          ctx.strokeStyle = "rgba(201,168,106,0.95)";
          ctx.lineWidth = 4;
          const midR = (outerR + innerR) / 2;
          // Draw dashes by angle steps.
          const a0 = Math.PI;
          const a1 = Math.PI * 1.5;
          const step = (Math.PI / 2) / 10;
          for (let a = a0; a < a1; a += step) {
            const dashA0 = a;
            const dashA1 = Math.min(a1, a + step * 0.55);
            ctx.beginPath();
            ctx.arc(cx, cy, midR, dashA0, dashA1, false);
            ctx.stroke();
          }

          break;
        }
        case "car": {
          if (assets.car.complete && assets.car.naturalWidth > 0) {
            ctx.drawImage(assets.car, x, y, w, h);
          } else {
            // fallback
            ctx.fillStyle = "#f5f2ea";
            ctx.strokeStyle = "rgba(17,17,17,0.9)";
            ctx.lineWidth = 2;
            roundRect(ctx, x, y, w, h, 10, true, true);
          }

          // label
          const label = (it.label || "V").slice(0, 4);
          ctx.fillStyle = "#111";
          ctx.font = `bold ${Math.max(12, Math.min(18, h * 0.55))}px Arial`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(label, x + w / 2, y + h / 2);
          ctx.textAlign = "left";
          ctx.textBaseline = "alphabetic";
          break;
        }
        case "deer": {
          if (assets.deer.complete && assets.deer.naturalWidth > 0) {
            ctx.drawImage(assets.deer, x, y, w, h);
          } else {
            ctx.fillStyle = "#7a4a1f";
            ctx.beginPath();
            ctx.ellipse(x + w * 0.5, y + h * 0.6, w * 0.35, h * 0.25, 0, 0, Math.PI * 2);
            ctx.fill();
          }
          break;
        }
        case "cone": {
          // Traffic cone with stripes
          ctx.fillStyle = "#e67e22";
          ctx.strokeStyle = "rgba(17,17,17,0.9)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(x + w / 2, y + h * 0.06);
          ctx.lineTo(x + w * 0.92, y + h * 0.92);
          ctx.lineTo(x + w * 0.08, y + h * 0.92);
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
          ctx.fillStyle = "rgba(255,255,255,0.75)";
          ctx.fillRect(x + w * 0.20, y + h * 0.52, w * 0.60, h * 0.12);
          ctx.fillRect(x + w * 0.26, y + h * 0.68, w * 0.48, h * 0.10);
          ctx.fillStyle = "#111";
          ctx.fillRect(x + w * 0.10, y + h * 0.90, w * 0.80, h * 0.08);
          break;
        }
        case "arrow": {
          ctx.strokeStyle = "#c9a86a";
          ctx.lineWidth = 5;
          arrow(x + 8, y + h / 2, x + w - 8, y + h / 2);
          break;
        }
        case "text": {
          ctx.fillStyle = "rgba(255,255,255,0.85)";
          ctx.strokeStyle = "rgba(0,0,0,0.25)";
          ctx.lineWidth = 1.5;
          roundRect(ctx, x, y, w, h, 10, true, true);
          ctx.fillStyle = "#111";
          ctx.font = "14px Arial";
          wrapText(ctx, it.label || "Note", x + 10, y + 18, w - 20, 16, 3);
          break;
        }
        case "point": {
          ctx.fillStyle = "#c9a86a";
          ctx.beginPath();
          ctx.arc(x + w / 2, y + h / 2, Math.max(6, Math.min(w, h) / 2), 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = "#111";
          ctx.font = "bold 12px Arial";
          ctx.fillText((it.label || "P").slice(0, 2), x + 4, y + h - 6);
          break;
        }
        default: {
          ctx.fillStyle = "rgba(0,0,0,0.08)";
          ctx.fillRect(x, y, w, h);
        }
      }
      ctx.restore();
    });

    if (it.id === state.selectedId) drawSelection(it);
  }

  function drawSelection(it) {
    const s = worldToScreen({ x: it.x, y: it.y });
    const w = it.w * state.view.scale;
    const h = it.h * state.view.scale;

    ctx.save();
    ctx.strokeStyle = "#1d3fa8";
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(s.x, s.y, w, h);
    ctx.setLineDash([]);

    // rotate handle
    const hx = s.x + w / 2;
    const hy = s.y - 18;
    ctx.fillStyle = "#1d3fa8";
    ctx.beginPath();
    ctx.arc(hx, hy, 6, 0, Math.PI * 2);
    ctx.fill();

    // resize handle
    ctx.fillStyle = "#1d3fa8";
    ctx.fillRect(s.x + w - 8, s.y + h - 8, 10, 10);

    ctx.restore();
  }

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.width / dpr;
    const height = canvas.height / dpr;

    // Clear in device pixels, then draw in CSS pixels.
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // background
    ctx.save();
    ctx.fillStyle = "#f7f7f7";
    ctx.fillRect(0, 0, width, height);
    ctx.restore();

    drawGrid();
    for (const it of state.items) drawItem(it);
  }

  function roundRect(ctx2, x, y, w, h, r, fill, stroke) {
    const rr = Math.min(r, w / 2, h / 2);
    ctx2.beginPath();
    ctx2.moveTo(x + rr, y);
    ctx2.arcTo(x + w, y, x + w, y + h, rr);
    ctx2.arcTo(x + w, y + h, x, y + h, rr);
    ctx2.arcTo(x, y + h, x, y, rr);
    ctx2.arcTo(x, y, x + w, y, rr);
    ctx2.closePath();
    if (fill) ctx2.fill();
    if (stroke) ctx2.stroke();
  }

  function dashedLine(x0, y0, x1, y1, dash, gap) {
    const dx = x1 - x0;
    const dy = y1 - y0;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const seg = dash + gap;
    const n = Math.floor(dist / seg);
    const ux = dx / dist;
    const uy = dy / dist;
    for (let i = 0; i <= n; i++) {
      const a = i * seg;
      const b = Math.min(dist, a + dash);
      ctx.beginPath();
      ctx.moveTo(x0 + ux * a, y0 + uy * a);
      ctx.lineTo(x0 + ux * b, y0 + uy * b);
      ctx.stroke();
    }
  }

  function arrow(x0, y0, x1, y1) {
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();
    const ang = Math.atan2(y1 - y0, x1 - x0);
    const head = 10;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x1 - head * Math.cos(ang - Math.PI / 6), y1 - head * Math.sin(ang - Math.PI / 6));
    ctx.lineTo(x1 - head * Math.cos(ang + Math.PI / 6), y1 - head * Math.sin(ang + Math.PI / 6));
    ctx.closePath();
    ctx.fillStyle = ctx.strokeStyle;
    ctx.fill();
  }

  function wrapText(ctx2, text, x, y, maxWidth, lineHeight, maxLines) {
    const words = (text || "").split(/\s+/);
    let line = "";
    let lineCount = 0;
    for (let n = 0; n < words.length; n++) {
      const test = line ? line + " " + words[n] : words[n];
      const w = ctx2.measureText(test).width;
      if (w > maxWidth && line) {
        ctx2.fillText(line, x, y + lineCount * lineHeight);
        line = words[n];
        lineCount++;
        if (lineCount >= maxLines) return;
      } else {
        line = test;
      }
    }
    if (lineCount < maxLines) ctx2.fillText(line, x, y + lineCount * lineHeight);
  }

  function handleKey(e) {
    if (!state.selectedId) return;
    const idx = state.items.findIndex((x) => x.id === state.selectedId);
    if (idx < 0) return;
    const it = state.items[idx];

    if (e.key === "Delete" || e.key === "Backspace") {
      state.items.splice(idx, 1);
      state.selectedId = null;
      scheduleDraw();
    }
    if (e.key === "Escape") {
      state.selectedId = null;
      scheduleDraw();
    }
    if (e.key === "r" || e.key === "R") {
      it.rot = (it.rot + 15) % 360;
      scheduleDraw();
    }
    if (e.key === "l" || e.key === "L") {
      if (it.type === "car" || it.type === "text" || it.type === "point") {
        const v = prompt("Label:", it.label || "");
        if (v !== null) it.label = v;
        scheduleDraw();
      }
    }
  }

  function handlePointerDown(e) {
    canvas.setPointerCapture(e.pointerId);
    const m = getMousePos(e);
    const wpt = screenToWorld(m);

    const it = itemAt(wpt);
    if (!it) {
      state.selectedId = null;
      scheduleDraw();
      return;
    }
    state.selectedId = it.id;

    // detect handles (ignore rotation for now; handles are unrotated)
    const s = worldToScreen({ x: it.x, y: it.y });
    const ww = it.w * state.view.scale;
    const hh = it.h * state.view.scale;
    const rotateHandle = { x: s.x + ww / 2, y: s.y - 18 };
    const resizeHandle = { x: s.x + ww, y: s.y + hh };

    const distRot = Math.hypot(m.x - rotateHandle.x, m.y - rotateHandle.y);
    if (distRot <= 10) {
      state.dragging = { id: it.id, mode: "rotate", start: m, baseRot: it.rot || 0 };
      scheduleDraw();
      return;
    }
    if (Math.abs(m.x - resizeHandle.x) <= 12 && Math.abs(m.y - resizeHandle.y) <= 12) {
      state.dragging = { id: it.id, mode: "resize", start: m, baseW: it.w, baseH: it.h };
      scheduleDraw();
      return;
    }

    state.dragging = { id: it.id, mode: "move", offx: wpt.x - it.x, offy: wpt.y - it.y };
    scheduleDraw();
  }

  function handlePointerMove(e) {
    if (!state.dragging) return;
    const m = getMousePos(e);
    const wpt = screenToWorld(m);
    const it = state.items.find((x) => x.id === state.dragging.id);
    if (!it) return;

    if (state.dragging.mode === "move") {
      it.x = snap(wpt.x - state.dragging.offx);
      it.y = snap(wpt.y - state.dragging.offy);
    } else if (state.dragging.mode === "resize") {
      const dx = (m.x - state.dragging.start.x) / state.view.scale;
      const dy = (m.y - state.dragging.start.y) / state.view.scale;
      it.w = clamp(snap(state.dragging.baseW + dx), 20, 2000);
      it.h = clamp(snap(state.dragging.baseH + dy), 20, 2000);
    } else if (state.dragging.mode === "rotate") {
      // simple: map horizontal movement to rotation
      const dx = m.x - state.dragging.start.x;
      it.rot = (state.dragging.baseRot + dx * 0.5) % 360;
    }
    scheduleDraw();
  }

  function handlePointerUp(e) {
    state.dragging = null;
  }

  async function loadDiagram() {
    try {
      const r = await fetch(loadUrl, { credentials: "same-origin" });
      if (!r.ok) throw new Error("no-diagram");
      const data = await r.json();
      if (data && Array.isArray(data.items)) {
        state.items = data.items;
        state.view = data.view || state.view;
        setStatus("Loaded diagram");
      }
    } catch {
      // default scene
      state.items = [
        { ...defaultItem("intersection", { x: 260, y: 160 }), label: "" },
        { ...defaultItem("car", { x: 320, y: 260 }), label: "V1" },
        { ...defaultItem("car", { x: 520, y: 340 }), label: "V2", rot: 90 },
        { ...defaultItem("deer", { x: 470, y: 250 }) },
      ];
      setStatus(`New diagram (editor ${BUILD})`);
    }
    scheduleDraw();
  }

  async function saveDiagram() {
    const payload = { v: 1, caseId, savedAt: new Date().toISOString(), view: state.view, items: state.items };
    const r = await fetch(saveUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      setStatus("Save failed");
      return false;
    }
    state.lastSavedAt = nowMs();
    setStatus("Saved");
    return true;
  }

  function exportPngBlob() {
    return new Promise((resolve) => {
      const wrap = root.querySelector("[data-canvas-wrap]");
      const r = wrap.getBoundingClientRect();
      const tmp = document.createElement("canvas");
      tmp.width = Math.floor(r.width);
      tmp.height = Math.floor(r.height);
      const tctx = tmp.getContext("2d");

      // Render at 1x screen pixels (good enough for report packets; keep simple).
      // Export exactly what the user sees.
      tctx.fillStyle = "#ffffff";
      tctx.fillRect(0, 0, tmp.width, tmp.height);
      tctx.drawImage(canvas, 0, 0, tmp.width, tmp.height);

      tmp.toBlob((b) => resolve(b), "image/png");
    });
  }

  async function exportAndAttach() {
    const ok = await saveDiagram();
    if (!ok) return;
    const blob = await exportPngBlob();
    if (!blob) {
      setStatus("Export failed");
      return;
    }
    const fd = new FormData();
    fd.append("kind", "diagram");
    fd.append("file", blob, `case-${caseId}-diagram.png`);
    const r = await fetch(uploadUrl, { method: "POST", credentials: "same-origin", body: fd });
    if (!r.ok) {
      setStatus("Upload failed");
      return;
    }
    setStatus("Exported + attached");
    // Refresh page so attachment list shows it.
    window.location.reload();
  }

  function clearDiagram() {
    if (!confirm("Clear diagram?")) return;
    state.items = [];
    state.selectedId = null;
    scheduleDraw();
    setStatus("Cleared");
  }

  function fitView() {
    state.view = { x: 0, y: 0, scale: 1 };
    scheduleDraw();
  }

  function setupPalette() {
    if (!palette) return;
    palette.querySelectorAll("[data-item]").forEach((el) => {
      el.setAttribute("draggable", "true");
      el.addEventListener("dragstart", (ev) => {
        ev.dataTransfer?.setData("text/plain", el.getAttribute("data-item") || "");
      });
      el.addEventListener("click", () => {
        const type = el.getAttribute("data-item");
        const wrap = root.querySelector("[data-canvas-wrap]");
        const r = wrap.getBoundingClientRect();
        const at = screenToWorld({ x: r.width * 0.5, y: r.height * 0.5 });
        const it = defaultItem(type, at);
        state.items.push(it);
        state.selectedId = it.id;
        scheduleDraw();
      });
    });

    // Drop onto canvas to place at the drop point.
    const wrap = root.querySelector("[data-canvas-wrap]");
    wrap.addEventListener("dragover", (ev) => {
      ev.preventDefault();
    });
    wrap.addEventListener("drop", (ev) => {
      ev.preventDefault();
      const type = ev.dataTransfer?.getData("text/plain") || "";
      if (!type) return;
      const r = canvas.getBoundingClientRect();
      const m = { x: ev.clientX - r.left, y: ev.clientY - r.top };
      const at = screenToWorld(m);
      const it = defaultItem(type, at);
      state.items.push(it);
      state.selectedId = it.id;
      scheduleDraw();
    });
  }

  // Canvas wheel zoom (ctrl+wheel or plain wheel)
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const m = getMousePos(e);
    const before = screenToWorld(m);
    const delta = e.deltaY > 0 ? 0.92 : 1.08;
    state.view.scale = clamp(state.view.scale * delta, 0.4, 2.5);
    const after = screenToWorld(m);
    // keep cursor anchored
    state.view.x += before.x - after.x;
    state.view.y += before.y - after.y;
    scheduleDraw();
  }, { passive: false });

  // Middle mouse / space+drag to pan (simple)
  let panning = null;
  canvas.addEventListener("pointerdown", (e) => {
    if (e.button === 1 || e.shiftKey) {
      panning = { start: getMousePos(e), base: { ...state.view } };
      canvas.setPointerCapture(e.pointerId);
      return;
    }
    handlePointerDown(e);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (panning) {
      const m = getMousePos(e);
      const dx = (m.x - panning.start.x) / state.view.scale;
      const dy = (m.y - panning.start.y) / state.view.scale;
      state.view.x = panning.base.x - dx;
      state.view.y = panning.base.y - dy;
      scheduleDraw();
      return;
    }
    handlePointerMove(e);
  });
  canvas.addEventListener("pointerup", (e) => {
    panning = null;
    handlePointerUp(e);
  });

  window.addEventListener("keydown", handleKey);

  btnSave?.addEventListener("click", (e) => { e.preventDefault(); saveDiagram(); });
  btnExport?.addEventListener("click", (e) => { e.preventDefault(); exportAndAttach(); });
  btnClear?.addEventListener("click", (e) => { e.preventDefault(); clearDiagram(); });
  btnFit?.addEventListener("click", (e) => { e.preventDefault(); fitView(); });

  window.addEventListener("resize", () => resizeCanvasToContainer());

  setupPalette();
  resizeCanvasToContainer();
  setStatus(`Loading... (editor ${BUILD})`);
  loadDiagram();
})();
