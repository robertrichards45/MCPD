/* Reconstruction Diagram Editor v4
 * Procedural canvas drawing — no external image deps.
 * Supports: road, intersection, curve_left, curve_right, car, truck,
 *   motorcycle, person, traffic_light, stop_sign, yield_sign,
 *   waypoint, callout, arrow, skid, impact, compass, text, point,
 *   deer, cone
 */

(() => {
  const BUILD = "2026-05-04.1";
  const root = document.querySelector("[data-recon-editor]");
  if (!root) return;

  const caseId   = root.getAttribute("data-case-id");
  const saveUrl  = root.getAttribute("data-save-url");
  const loadUrl  = root.getAttribute("data-load-url");
  const uploadUrl = root.getAttribute("data-upload-url");

  const canvas   = root.querySelector("canvas");
  const ctx      = canvas.getContext("2d");
  const statusEl = root.querySelector("[data-status]");
  const palette  = root.querySelector("[data-palette]");

  // Vehicle colors by label prefix (V1..V4, then cycle)
  const VEH_PALETTE = ["#2d6fbf","#cc2222","#1d8a36","#cc7700","#7733aa","#0099aa"];
  function vehColor(label) {
    const idx = parseInt((label || "1").replace(/\D/g, "")) - 1;
    return VEH_PALETTE[Math.max(0, idx) % VEH_PALETTE.length];
  }

  const DEFAULTS = {
    road:          { w: 260, h: 120 },
    intersection:  { w: 260, h: 260 },
    curve_left:    { w: 260, h: 260 },
    curve_right:   { w: 260, h: 260 },
    car:           { w: 84,  h: 46,  label: "V1" },
    truck:         { w: 110, h: 54,  label: "T1" },
    motorcycle:    { w: 56,  h: 28,  label: "M1" },
    person:        { w: 28,  h: 28,  label: "P"  },
    traffic_light: { w: 36,  h: 88  },
    stop_sign:     { w: 62,  h: 82  },
    yield_sign:    { w: 62,  h: 70  },
    waypoint:      { w: 36,  h: 52,  label: "1"  },
    callout:       { w: 190, h: 72,  label: "Note" },
    arrow:         { w: 140, h: 30  },
    skid:          { w: 130, h: 22  },
    impact:        { w: 52,  h: 52  },
    compass:       { w: 62,  h: 62  },
    text:          { w: 200, h: 44,  label: "Note" },
    point:         { w: 24,  h: 24,  label: "P"  },
    deer:          { w: 68,  h: 54  },
    cone:          { w: 40,  h: 50  },
  };

  const state = {
    view: { x: 0, y: 0, scale: 1 },
    items: [],
    selectedId: null,
    dragging: null,
    lastSavedAt: 0,
  };

  const GRID = 20;
  let rafPending = false;

  // ── Utility ─────────────────────────────────────────────────────────────────

  function setStatus(msg) { if (statusEl) statusEl.textContent = msg; }
  function scheduleDraw() {
    if (rafPending) return;
    rafPending = true;
    requestAnimationFrame(() => { rafPending = false; draw(); });
  }
  function uid() { return Math.random().toString(36).slice(2) + "-" + Math.random().toString(36).slice(2); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function snap(v) { return Math.round(v / GRID) * GRID; }

  function worldToScreen(pt) {
    return { x: (pt.x - state.view.x) * state.view.scale, y: (pt.y - state.view.y) * state.view.scale };
  }
  function screenToWorld(pt) {
    return { x: pt.x / state.view.scale + state.view.x, y: pt.y / state.view.scale + state.view.y };
  }
  function getMousePos(e) {
    const r = canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }
  function resizeCanvasToContainer() {
    const wrap = root.querySelector("[data-canvas-wrap]");
    const r = wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width  = Math.max(1, Math.floor(r.width  * dpr));
    canvas.height = Math.max(1, Math.floor(r.height * dpr));
    canvas.style.width  = Math.floor(r.width)  + "px";
    canvas.style.height = Math.floor(r.height) + "px";
    scheduleDraw();
  }

  // ── Item defaults ────────────────────────────────────────────────────────────

  function defaultItem(type, at) {
    const d = DEFAULTS[type] || { w: 80, h: 60 };
    return { id: uid(), type, x: snap(at.x), y: snap(at.y), w: d.w, h: d.h, rot: 0, label: d.label || "" };
  }

  // ── Hit testing ──────────────────────────────────────────────────────────────

  function itemAt(wpt) {
    for (let i = state.items.length - 1; i >= 0; i--) {
      const it = state.items[i];
      if (wpt.x >= it.x && wpt.x <= it.x + it.w && wpt.y >= it.y && wpt.y <= it.y + it.h) return it;
    }
    return null;
  }

  // ── Canvas helpers ───────────────────────────────────────────────────────────

  function roundRect(x, y, w, h, r, fill, stroke) {
    const rr = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + rr, y);
    ctx.arcTo(x + w, y,     x + w, y + h, rr);
    ctx.arcTo(x + w, y + h, x,     y + h, rr);
    ctx.arcTo(x,     y + h, x,     y,     rr);
    ctx.arcTo(x,     y,     x + w, y,     rr);
    ctx.closePath();
    if (fill)   ctx.fill();
    if (stroke) ctx.stroke();
  }

  function circle(cx, cy, r) {
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();
  }

  function dashedLine(x0, y0, x1, y1, dash, gap) {
    const dx = x1 - x0, dy = y1 - y0;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const seg = dash + gap;
    const n = Math.floor(dist / seg);
    const ux = dx / dist, uy = dy / dist;
    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
      const a = i * seg;
      const b = Math.min(dist, a + dash);
      ctx.moveTo(x0 + ux * a, y0 + uy * a);
      ctx.lineTo(x0 + ux * b, y0 + uy * b);
    }
    ctx.stroke();
  }

  function arrowLine(x0, y0, x1, y1) {
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
    const ang = Math.atan2(y1 - y0, x1 - x0);
    const head = 12;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x1 - head * Math.cos(ang - Math.PI / 6), y1 - head * Math.sin(ang - Math.PI / 6));
    ctx.lineTo(x1 - head * Math.cos(ang + Math.PI / 6), y1 - head * Math.sin(ang + Math.PI / 6));
    ctx.closePath();
    ctx.fillStyle = ctx.strokeStyle; ctx.fill();
  }

  function wrapText(text, x, y, maxW, lh, maxL) {
    const words = (text || "").split(/\s+/);
    let line = "", lc = 0;
    for (const w of words) {
      const test = line ? line + " " + w : w;
      if (ctx.measureText(test).width > maxW && line) {
        ctx.fillText(line, x, y + lc * lh); line = w; lc++;
        if (lc >= maxL) return;
      } else { line = test; }
    }
    if (lc < maxL) ctx.fillText(line, x, y + lc * lh);
  }

  function octagon(cx, cy, r) {
    ctx.beginPath();
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 - Math.PI / 8;
      i === 0 ? ctx.moveTo(cx + r * Math.cos(a), cy + r * Math.sin(a))
              : ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
    }
    ctx.closePath();
  }

  function triangle(cx, cy, r, pointDown) {
    ctx.beginPath();
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI * 2 + (pointDown ? 0 : -Math.PI / 2);
      i === 0 ? ctx.moveTo(cx + r * Math.cos(a), cy + r * Math.sin(a))
              : ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
    }
    ctx.closePath();
  }

  function starBurst(cx, cy, outerR, innerR, points) {
    ctx.beginPath();
    for (let i = 0; i < points * 2; i++) {
      const r = i % 2 === 0 ? outerR : innerR;
      const a = (i / (points * 2)) * Math.PI * 2 - Math.PI / 2;
      i === 0 ? ctx.moveTo(cx + r * Math.cos(a), cy + r * Math.sin(a))
              : ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
    }
    ctx.closePath();
  }

  // ── Item drawers ─────────────────────────────────────────────────────────────

  function drawRoad(x, y, w, h) {
    const grad = ctx.createLinearGradient(x, y, x, y + h);
    grad.addColorStop(0, "#2a2d30"); grad.addColorStop(1, "#1f2225");
    ctx.fillStyle = grad;
    roundRect(x, y, w, h, 14, true, false);
    ctx.strokeStyle = "rgba(255,255,255,0.30)";
    ctx.lineWidth = Math.max(2, Math.min(6, h * 0.03));
    ctx.beginPath();
    ctx.moveTo(x + 10, y + 10); ctx.lineTo(x + w - 10, y + 10);
    ctx.moveTo(x + 10, y + h - 10); ctx.lineTo(x + w - 10, y + h - 10);
    ctx.stroke();
    ctx.strokeStyle = "rgba(201,168,106,0.95)";
    ctx.lineWidth = Math.max(2, Math.min(6, h * 0.035));
    dashedLine(x + 16, y + h / 2, x + w - 16, y + h / 2, 18, 14);
  }

  function drawIntersection(x, y, w, h) {
    const grad = ctx.createLinearGradient(x, y, x, y + h);
    grad.addColorStop(0, "#2a2d30"); grad.addColorStop(1, "#1f2225");
    ctx.fillStyle = grad;
    roundRect(x, y, w, h, 18, true, false);
    ctx.fillStyle = "rgba(255,255,255,0.05)";
    ctx.fillRect(x + w * 0.38, y + 10, w * 0.24, h - 20);
    ctx.fillRect(x + 10, y + h * 0.38, w - 20, h * 0.24);
    // Crosswalk markings
    ctx.fillStyle = "rgba(255,255,255,0.18)";
    for (let i = 0; i < 3; i++) {
      ctx.fillRect(x + 12 + i * (w * 0.10), y + h * 0.38 - 18, w * 0.07, 10);
      ctx.fillRect(x + 12 + i * (w * 0.10), y + h * 0.62 + 8,  w * 0.07, 10);
      ctx.fillRect(x + w * 0.38 - 18, y + 12 + i * (h * 0.10), 10, h * 0.07);
      ctx.fillRect(x + w * 0.62 + 8,  y + 12 + i * (h * 0.10), 10, h * 0.07);
    }
    ctx.strokeStyle = "rgba(201,168,106,0.95)";
    ctx.lineWidth = Math.max(2, Math.min(6, w * 0.018));
    dashedLine(x + 20, y + h / 2, x + w - 20, y + h / 2, 18, 14);
    dashedLine(x + w / 2, y + 20, x + w / 2, y + h - 20, 18, 14);
  }

  function drawCurve(x, y, w, h, dir) {
    const cx = x + (dir < 0 ? w : 0);
    const cy = y + h;
    const outerR = Math.min(w, h) * 0.95;
    const roadW  = Math.max(40, Math.min(90, outerR * 0.28));
    const innerR = Math.max(10, outerR - roadW);
    ctx.fillStyle = "#232629";
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, Math.PI, Math.PI * 1.5, dir > 0);
    ctx.arc(cx, cy, innerR, Math.PI * 1.5, Math.PI, dir > 0);
    ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.30)"; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(cx, cy, outerR - 10, Math.PI, Math.PI * 1.5, dir > 0); ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, cy, innerR + 10, Math.PI, Math.PI * 1.5, dir > 0); ctx.stroke();
    ctx.strokeStyle = "rgba(201,168,106,0.95)"; ctx.lineWidth = 4;
    const midR = (outerR + innerR) / 2;
    const step = (Math.PI / 2) / 10;
    for (let a = Math.PI; a < Math.PI * 1.5; a += step) {
      ctx.beginPath(); ctx.arc(cx, cy, midR, a, Math.min(Math.PI * 1.5, a + step * 0.55), false); ctx.stroke();
    }
  }

  function drawCar(x, y, w, h, label) {
    const col = vehColor(label);
    const dark = "#0a0a0a";
    // Shadow
    ctx.fillStyle = "rgba(0,0,0,0.18)";
    ctx.beginPath(); ctx.ellipse(x + w/2, y + h + 4, w * 0.42, 5, 0, 0, Math.PI * 2); ctx.fill();
    // Body
    ctx.fillStyle = col; ctx.strokeStyle = dark; ctx.lineWidth = 1.5;
    roundRect(x + w * 0.04, y + h * 0.06, w * 0.92, h * 0.88, h * 0.18, true, true);
    // Bumpers
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    roundRect(x + w * 0.12, y + h * 0.02, w * 0.76, h * 0.10, 3, true, false);
    roundRect(x + w * 0.12, y + h * 0.88, w * 0.76, h * 0.10, 3, true, false);
    // Front windshield
    ctx.fillStyle = "rgba(180,220,255,0.82)"; ctx.strokeStyle = "rgba(0,0,0,0.3)"; ctx.lineWidth = 1;
    roundRect(x + w * 0.20, y + h * 0.12, w * 0.60, h * 0.22, 4, true, true);
    // Rear windshield
    roundRect(x + w * 0.20, y + h * 0.66, w * 0.60, h * 0.20, 4, true, true);
    // Roof / cabin tint
    ctx.fillStyle = "rgba(0,0,0,0.20)";
    roundRect(x + w * 0.22, y + h * 0.34, w * 0.56, h * 0.30, 4, true, false);
    // Wheels
    ctx.strokeStyle = dark; ctx.lineWidth = 1.5;
    for (const [wx, wy] of [[0.02, 0.08],[0.02, 0.62],[0.76, 0.08],[0.76, 0.62]]) {
      ctx.fillStyle = "#222";
      roundRect(x + w * wx, y + h * wy, w * 0.20, h * 0.26, 3, true, true);
      ctx.fillStyle = "#555";
      roundRect(x + w * wx + w*0.04, y + h * wy + h*0.05, w * 0.12, h * 0.16, 2, true, false);
    }
    // Label
    ctx.fillStyle = "rgba(255,255,255,0.92)";
    ctx.font = `bold ${Math.max(9, h * 0.28)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText((label || "V").slice(0, 3), x + w / 2, y + h * 0.50);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  }

  function drawTruck(x, y, w, h, label) {
    const col = vehColor(label);
    // Shadow
    ctx.fillStyle = "rgba(0,0,0,0.15)";
    ctx.beginPath(); ctx.ellipse(x + w/2, y + h + 5, w * 0.44, 5, 0, 0, Math.PI * 2); ctx.fill();
    // Trailer body
    ctx.fillStyle = col; ctx.strokeStyle = "#0a0a0a"; ctx.lineWidth = 1.5;
    roundRect(x + w * 0.04, y + h * 0.06, w * 0.92, h * 0.88, h * 0.12, true, true);
    // Cab (front)
    ctx.fillStyle = "rgba(0,0,0,0.25)";
    roundRect(x + w * 0.06, y + h * 0.08, w * 0.32, h * 0.84, 5, true, false);
    // Windshield
    ctx.fillStyle = "rgba(180,220,255,0.80)"; ctx.strokeStyle = "rgba(0,0,0,0.3)"; ctx.lineWidth = 1;
    roundRect(x + w * 0.08, y + h * 0.12, w * 0.26, h * 0.28, 4, true, true);
    // Bumper
    ctx.fillStyle = "rgba(0,0,0,0.40)";
    roundRect(x + w * 0.06, y + h * 0.02, w * 0.32, h * 0.10, 3, true, false);
    // Wheels (6)
    ctx.strokeStyle = "#0a0a0a"; ctx.lineWidth = 1.5;
    for (const [wx, wy] of [[0.01,0.08],[0.01,0.62],[0.32,0.08],[0.32,0.62],[0.75,0.08],[0.75,0.62]]) {
      ctx.fillStyle = "#222"; roundRect(x+w*wx, y+h*wy, w*0.18, h*0.26, 3, true, true);
      ctx.fillStyle = "#555"; roundRect(x+w*wx+w*0.03, y+h*wy+h*0.05, w*0.12, h*0.16, 2, true, false);
    }
    // Label
    ctx.fillStyle = "rgba(255,255,255,0.90)";
    ctx.font = `bold ${Math.max(9, h * 0.28)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText((label || "T").slice(0, 3), x + w * 0.65, y + h * 0.50);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  }

  function drawMotorcycle(x, y, w, h, label) {
    const col = vehColor(label);
    ctx.fillStyle = col; ctx.strokeStyle = "#111"; ctx.lineWidth = 1.5;
    // Body (narrow)
    roundRect(x + w * 0.10, y + h * 0.28, w * 0.80, h * 0.44, 4, true, true);
    // Wheels
    ctx.fillStyle = "#111";
    ctx.beginPath(); ctx.arc(x + w * 0.15, y + h * 0.50, h * 0.22, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(x + w * 0.85, y + h * 0.50, h * 0.22, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#555";
    ctx.beginPath(); ctx.arc(x + w * 0.15, y + h * 0.50, h * 0.12, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(x + w * 0.85, y + h * 0.50, h * 0.12, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.font = `bold ${Math.max(8, h * 0.30)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText((label || "M").slice(0, 2), x + w / 2, y + h * 0.50);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  }

  function drawPerson(x, y, w, h, label) {
    const sz = Math.min(w, h);
    const cx = x + w / 2, cy = y + h / 2;
    ctx.fillStyle = "#5a3e8a"; ctx.strokeStyle = "#333"; ctx.lineWidth = 1.5;
    // Head
    ctx.beginPath(); ctx.arc(cx, y + sz * 0.22, sz * 0.18, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // Body
    ctx.fillStyle = "#5a3e8a";
    ctx.fillRect(cx - sz * 0.14, y + sz * 0.38, sz * 0.28, sz * 0.32);
    ctx.strokeRect(cx - sz * 0.14, y + sz * 0.38, sz * 0.28, sz * 0.32);
    // Legs
    ctx.strokeStyle = "#5a3e8a"; ctx.lineWidth = sz * 0.12;
    ctx.beginPath(); ctx.moveTo(cx - sz*0.08, y+sz*0.70); ctx.lineTo(cx - sz*0.14, y+sz*0.95); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + sz*0.08, y+sz*0.70); ctx.lineTo(cx + sz*0.14, y+sz*0.95); ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.font = `bold ${Math.max(6, sz * 0.22)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText((label || "P").slice(0,1), cx, y + sz * 0.52);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  }

  function drawTrafficLight(x, y, w, h) {
    // Pole
    ctx.fillStyle = "#555";
    ctx.fillRect(x + w * 0.42, y + h * 0.58, w * 0.16, h * 0.42);
    // Housing
    ctx.fillStyle = "#1a1a1a"; ctx.strokeStyle = "#333"; ctx.lineWidth = 1.5;
    roundRect(x + w * 0.12, y + h * 0.02, w * 0.76, h * 0.60, 8, true, true);
    // Lenses
    const lenses = [
      { cy: y + h * 0.12, lit: "#ff2020", dark: "#3a0000" },
      { cy: y + h * 0.30, lit: "#ffcc00", dark: "#3a2800" },
      { cy: y + h * 0.48, lit: "#00dd44", dark: "#003a15" },
    ];
    for (const l of lenses) {
      ctx.fillStyle = l.lit;
      ctx.beginPath(); ctx.arc(x + w / 2, l.cy, w * 0.20, 0, Math.PI * 2); ctx.fill();
      // Glare
      ctx.fillStyle = "rgba(255,255,255,0.25)";
      ctx.beginPath(); ctx.arc(x + w * 0.42, l.cy - w*0.07, w * 0.07, 0, Math.PI * 2); ctx.fill();
    }
  }

  function drawStopSign(x, y, w, h) {
    const cx = x + w / 2, cy = y + h * 0.44;
    const r = Math.min(w, h * 0.80) * 0.46;
    ctx.fillStyle = "#cc0000"; ctx.strokeStyle = "white"; ctx.lineWidth = Math.max(2, r * 0.10);
    octagon(cx, cy, r); ctx.fill(); ctx.stroke();
    // Inner white octagon outline
    ctx.strokeStyle = "white"; ctx.lineWidth = Math.max(1, r * 0.06);
    octagon(cx, cy, r * 0.84); ctx.stroke();
    // Text
    ctx.fillStyle = "white";
    ctx.font = `bold ${Math.max(8, r * 0.44)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("STOP", cx, cy);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    // Pole
    ctx.fillStyle = "#888"; ctx.fillRect(x + w * 0.44, y + h * 0.82, w * 0.12, h * 0.17);
  }

  function drawYieldSign(x, y, w, h) {
    const cx = x + w / 2, cy = y + h * 0.40;
    const r = Math.min(w, h * 0.80) * 0.48;
    ctx.fillStyle = "white"; ctx.strokeStyle = "#cc0000"; ctx.lineWidth = Math.max(3, r * 0.14);
    triangle(cx, cy, r, true); ctx.fill(); ctx.stroke();
    ctx.strokeStyle = "#cc0000"; ctx.lineWidth = Math.max(2, r * 0.08);
    triangle(cx, cy + r * 0.08, r * 0.70, true); ctx.stroke();
    ctx.fillStyle = "#cc0000";
    ctx.font = `bold ${Math.max(7, r * 0.36)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("YIELD", cx, cy + r * 0.12);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
    ctx.fillStyle = "#888"; ctx.fillRect(x + w * 0.44, y + h * 0.80, w * 0.12, h * 0.18);
  }

  function drawWaypoint(x, y, w, h, label) {
    const cx = x + w / 2;
    const headR = Math.min(w, h * 0.55) * 0.44;
    const headCy = y + headR + h * 0.04;
    // Drop shadow
    ctx.fillStyle = "rgba(0,0,0,0.20)";
    ctx.beginPath(); ctx.ellipse(cx, y + h - 3, w * 0.28, 4, 0, 0, Math.PI * 2); ctx.fill();
    // Pin body
    ctx.fillStyle = "#FFCC00"; ctx.strokeStyle = "#996600"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(cx, headCy, headR, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // Pin tail
    ctx.fillStyle = "#FFCC00";
    ctx.beginPath();
    ctx.moveTo(cx - headR * 0.55, headCy + headR * 0.65);
    ctx.lineTo(cx, y + h - 4);
    ctx.lineTo(cx + headR * 0.55, headCy + headR * 0.65);
    ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "#996600"; ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cx - headR * 0.55, headCy + headR * 0.65);
    ctx.lineTo(cx, y + h - 4);
    ctx.lineTo(cx + headR * 0.55, headCy + headR * 0.65);
    ctx.stroke();
    // Highlight
    ctx.fillStyle = "rgba(255,255,255,0.30)";
    ctx.beginPath(); ctx.arc(cx - headR * 0.25, headCy - headR * 0.25, headR * 0.30, 0, Math.PI * 2); ctx.fill();
    // Number
    ctx.fillStyle = "#333";
    ctx.font = `bold ${Math.max(9, headR * 1.1)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText((label || "1").slice(0, 2), cx, headCy + 1);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  }

  function drawCallout(x, y, w, h, label) {
    const boxH = h * 0.72;
    // Box
    ctx.fillStyle = "rgba(255,253,215,0.97)"; ctx.strokeStyle = "#c9b840"; ctx.lineWidth = 1.5;
    roundRect(x, y, w, boxH, 8, true, true);
    // Tail
    ctx.fillStyle = "rgba(255,253,215,0.97)";
    ctx.beginPath();
    ctx.moveTo(x + w * 0.18, y + boxH);
    ctx.lineTo(x + w * 0.08, y + h);
    ctx.lineTo(x + w * 0.34, y + boxH);
    ctx.closePath(); ctx.fill();
    ctx.strokeStyle = "#c9b840"; ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x + w * 0.18, y + boxH + 1);
    ctx.lineTo(x + w * 0.08, y + h);
    ctx.lineTo(x + w * 0.34, y + boxH + 1);
    ctx.stroke();
    // Text
    ctx.fillStyle = "#111"; ctx.font = "12px Arial";
    wrapText(label || "Note", x + 8, y + 15, w - 16, 14, 4);
  }

  function drawSkid(x, y, w, h) {
    ctx.save();
    ctx.globalAlpha = 0.72;
    ctx.strokeStyle = "#1a1a1a"; ctx.lineWidth = Math.max(4, h * 0.5);
    ctx.lineCap = "round";
    // Two parallel skid tracks
    const off = h * 0.18;
    ctx.beginPath(); ctx.moveTo(x + 8, y + h / 2 - off); ctx.lineTo(x + w - 8, y + h / 2 - off); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 8, y + h / 2 + off); ctx.lineTo(x + w - 8, y + h / 2 + off); ctx.stroke();
    ctx.restore();
  }

  function drawImpact(x, y, w, h) {
    const cx = x + w / 2, cy = y + h / 2;
    const r = Math.min(w, h) * 0.46;
    ctx.fillStyle = "#ff8800"; ctx.strokeStyle = "#cc3300"; ctx.lineWidth = 2;
    starBurst(cx, cy, r, r * 0.45, 8); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#ffee88"; ctx.strokeStyle = "#cc6600"; ctx.lineWidth = 1;
    starBurst(cx, cy, r * 0.55, r * 0.25, 6); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#cc2200";
    ctx.font = `bold ${Math.max(8, r * 0.55)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("!", cx, cy + 1);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  }

  function drawCompass(x, y, w, h) {
    const cx = x + w / 2, cy = y + h / 2;
    const r = Math.min(w, h) * 0.46;
    ctx.fillStyle = "white"; ctx.strokeStyle = "#aaa"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    // North arrow
    ctx.fillStyle = "#cc2222";
    ctx.beginPath();
    ctx.moveTo(cx, cy - r * 0.70);
    ctx.lineTo(cx - r * 0.22, cy);
    ctx.lineTo(cx + r * 0.22, cy);
    ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#333";
    ctx.beginPath();
    ctx.moveTo(cx, cy + r * 0.70);
    ctx.lineTo(cx - r * 0.22, cy);
    ctx.lineTo(cx + r * 0.22, cy);
    ctx.closePath(); ctx.fill();
    // N label
    ctx.fillStyle = "#cc2222";
    ctx.font = `bold ${Math.max(8, r * 0.42)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText("N", cx, cy - r * 0.82);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  }

  function drawText(x, y, w, h, label) {
    ctx.fillStyle = "rgba(255,255,255,0.90)"; ctx.strokeStyle = "rgba(0,0,0,0.22)"; ctx.lineWidth = 1.5;
    roundRect(x, y, w, h, 8, true, true);
    ctx.fillStyle = "#111"; ctx.font = "13px Arial";
    wrapText(label || "Note", x + 10, y + 16, w - 20, 15, 3);
  }

  function drawPoint(x, y, w, h, label) {
    const cx = x + w / 2, cy = y + h / 2;
    ctx.fillStyle = "#c9a86a"; ctx.strokeStyle = "#7a5f2a"; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(cx, cy, Math.max(6, Math.min(w, h) / 2), 0, Math.PI * 2);
    ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#111";
    ctx.font = `bold ${Math.max(8, Math.min(w, h) * 0.50)}px Arial`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText((label || "P").slice(0, 2), cx, cy + 1);
    ctx.textAlign = "left"; ctx.textBaseline = "alphabetic";
  }

  function drawDeer(x, y, w, h) {
    ctx.fillStyle = "#8B6914"; ctx.strokeStyle = "#5c4010"; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.ellipse(x + w * 0.50, y + h * 0.60, w * 0.32, h * 0.24, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#c4902a";
    ctx.beginPath(); ctx.arc(x + w * 0.78, y + h * 0.30, w * 0.18, 0, Math.PI * 2); ctx.fill();
    // Legs
    ctx.strokeStyle = "#5c4010"; ctx.lineWidth = Math.max(2, w * 0.05);
    for (const [lx] of [[0.30],[0.40],[0.58],[0.68]]) {
      ctx.beginPath(); ctx.moveTo(x + w * lx, y + h * 0.78); ctx.lineTo(x + w * lx, y + h * 0.98); ctx.stroke();
    }
    // Ears
    ctx.fillStyle = "#c4902a";
    ctx.beginPath(); ctx.ellipse(x + w * 0.70, y + h * 0.16, w * 0.10, h * 0.08, -0.4, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(x + w * 0.88, y + h * 0.18, w * 0.08, h * 0.07, 0.4, 0, Math.PI * 2); ctx.fill();
  }

  function drawCone(x, y, w, h) {
    ctx.fillStyle = "#e67e22"; ctx.strokeStyle = "#a04000"; ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x + w / 2, y + h * 0.04);
    ctx.lineTo(x + w * 0.92, y + h * 0.90);
    ctx.lineTo(x + w * 0.08, y + h * 0.90);
    ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.78)";
    ctx.fillRect(x + w * 0.22, y + h * 0.48, w * 0.56, h * 0.11);
    ctx.fillRect(x + w * 0.28, y + h * 0.64, w * 0.44, h * 0.09);
    ctx.fillStyle = "#111"; ctx.fillRect(x + w * 0.08, y + h * 0.88, w * 0.84, h * 0.08);
  }

  // ── Main draw ────────────────────────────────────────────────────────────────

  function withItemTransform(it, fn) {
    const s = worldToScreen({ x: it.x, y: it.y });
    const w = it.w * state.view.scale;
    const h = it.h * state.view.scale;
    const cx = s.x + w / 2, cy = s.y + h / 2;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((it.rot || 0) * (Math.PI / 180));
    ctx.translate(-cx, -cy);
    fn({ s, w, h, cx, cy });
    ctx.restore();
  }

  function drawItem(it) {
    withItemTransform(it, ({ s, w, h }) => {
      const x = s.x, y = s.y;
      ctx.save();
      switch (it.type) {
        case "road":          drawRoad(x, y, w, h); break;
        case "intersection":  drawIntersection(x, y, w, h); break;
        case "curve_left":    drawCurve(x, y, w, h, -1); break;
        case "curve_right":   drawCurve(x, y, w, h,  1); break;
        case "car":           drawCar(x, y, w, h, it.label); break;
        case "truck":         drawTruck(x, y, w, h, it.label); break;
        case "motorcycle":    drawMotorcycle(x, y, w, h, it.label); break;
        case "person":        drawPerson(x, y, w, h, it.label); break;
        case "traffic_light": drawTrafficLight(x, y, w, h); break;
        case "stop_sign":     drawStopSign(x, y, w, h); break;
        case "yield_sign":    drawYieldSign(x, y, w, h); break;
        case "waypoint":      drawWaypoint(x, y, w, h, it.label); break;
        case "callout":       drawCallout(x, y, w, h, it.label); break;
        case "arrow": {
          ctx.strokeStyle = "#c9a86a"; ctx.lineWidth = 5;
          arrowLine(x + 8, y + h / 2, x + w - 8, y + h / 2); break;
        }
        case "skid":    drawSkid(x, y, w, h); break;
        case "impact":  drawImpact(x, y, w, h); break;
        case "compass": drawCompass(x, y, w, h); break;
        case "text":    drawText(x, y, w, h, it.label); break;
        case "point":   drawPoint(x, y, w, h, it.label); break;
        case "deer":    drawDeer(x, y, w, h); break;
        case "cone":    drawCone(x, y, w, h); break;
        default: { ctx.fillStyle = "rgba(0,0,0,0.08)"; ctx.fillRect(x, y, w, h); }
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
    ctx.strokeStyle = "#1d3fa8"; ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]); ctx.strokeRect(s.x, s.y, w, h); ctx.setLineDash([]);
    ctx.fillStyle = "#1d3fa8";
    ctx.beginPath(); ctx.arc(s.x + w / 2, s.y - 18, 6, 0, Math.PI * 2); ctx.fill();
    ctx.fillRect(s.x + w - 8, s.y + h - 8, 10, 10);
    ctx.restore();
  }

  function drawGrid() {
    const dpr = window.devicePixelRatio || 1;
    const width  = canvas.width  / dpr;
    const height = canvas.height / dpr;
    const tl = screenToWorld({ x: 0, y: 0 });
    const br = screenToWorld({ x: width, y: height });
    const x0 = Math.floor(tl.x / GRID) * GRID;
    const y0 = Math.floor(tl.y / GRID) * GRID;
    const x1 = Math.ceil(br.x / GRID) * GRID;
    const y1 = Math.ceil(br.y / GRID) * GRID;
    ctx.save(); ctx.lineWidth = 1; ctx.strokeStyle = "rgba(0,0,0,0.07)";
    for (let px = x0; px <= x1; px += GRID) {
      const a = worldToScreen({ x: px, y: y0 }); const b = worldToScreen({ x: px, y: y1 });
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    for (let py = y0; py <= y1; py += GRID) {
      const a = worldToScreen({ x: x0, y: py }); const b = worldToScreen({ x: x1, y: py });
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    ctx.restore();
  }

  function draw() {
    const dpr = window.devicePixelRatio || 1;
    const width  = canvas.width  / dpr;
    const height = canvas.height / dpr;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.save(); ctx.fillStyle = "#f4f4f4"; ctx.fillRect(0, 0, width, height); ctx.restore();
    drawGrid();
    for (const it of state.items) drawItem(it);
  }

  // ── Interaction ──────────────────────────────────────────────────────────────

  function handleKey(e) {
    if (!state.selectedId) return;
    const idx = state.items.findIndex(x => x.id === state.selectedId);
    if (idx < 0) return;
    const it = state.items[idx];
    if (e.key === "Delete" || e.key === "Backspace") {
      state.items.splice(idx, 1); state.selectedId = null; scheduleDraw(); return;
    }
    if (e.key === "Escape") { state.selectedId = null; scheduleDraw(); return; }
    if (e.key === "r" || e.key === "R") { it.rot = (it.rot + 15) % 360; scheduleDraw(); return; }
    if (e.key === "l" || e.key === "L") {
      const editable = ["car","truck","motorcycle","person","waypoint","callout","text","point"];
      if (editable.includes(it.type)) {
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
    if (!it) { state.selectedId = null; scheduleDraw(); return; }
    state.selectedId = it.id;
    const s = worldToScreen({ x: it.x, y: it.y });
    const ww = it.w * state.view.scale, hh = it.h * state.view.scale;
    if (Math.hypot(m.x - (s.x + ww / 2), m.y - (s.y - 18)) <= 10) {
      state.dragging = { id: it.id, mode: "rotate", start: m, baseRot: it.rot || 0 }; scheduleDraw(); return;
    }
    if (Math.abs(m.x - (s.x + ww)) <= 12 && Math.abs(m.y - (s.y + hh)) <= 12) {
      state.dragging = { id: it.id, mode: "resize", start: m, baseW: it.w, baseH: it.h }; scheduleDraw(); return;
    }
    state.dragging = { id: it.id, mode: "move", offx: wpt.x - it.x, offy: wpt.y - it.y };
    scheduleDraw();
  }

  function handlePointerMove(e) {
    if (!state.dragging) return;
    const m = getMousePos(e), wpt = screenToWorld(m);
    const it = state.items.find(x => x.id === state.dragging.id);
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
      it.rot = (state.dragging.baseRot + (m.x - state.dragging.start.x) * 0.5) % 360;
    }
    scheduleDraw();
  }

  function handlePointerUp() { state.dragging = null; }

  // Double-click to edit label
  canvas.addEventListener("dblclick", (e) => {
    const wpt = screenToWorld(getMousePos(e));
    const it = itemAt(wpt);
    if (!it) return;
    const editable = ["car","truck","motorcycle","person","waypoint","callout","text","point"];
    if (editable.includes(it.type)) {
      const v = prompt("Label:", it.label || "");
      if (v !== null) { it.label = v; scheduleDraw(); }
    }
  });

  // ── Panning & zooming ────────────────────────────────────────────────────────

  let panning = null;
  canvas.addEventListener("pointerdown", (e) => {
    if (e.button === 1 || e.shiftKey) {
      panning = { start: getMousePos(e), base: { ...state.view } };
      canvas.setPointerCapture(e.pointerId); return;
    }
    handlePointerDown(e);
  });
  canvas.addEventListener("pointermove", (e) => {
    if (panning) {
      const m = getMousePos(e);
      state.view.x = panning.base.x - (m.x - panning.start.x) / state.view.scale;
      state.view.y = panning.base.y - (m.y - panning.start.y) / state.view.scale;
      scheduleDraw(); return;
    }
    handlePointerMove(e);
  });
  canvas.addEventListener("pointerup", (e) => { panning = null; handlePointerUp(e); });
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const m = getMousePos(e), before = screenToWorld(m);
    state.view.scale = clamp(state.view.scale * (e.deltaY > 0 ? 0.92 : 1.08), 0.3, 3.0);
    const after = screenToWorld(m);
    state.view.x += before.x - after.x; state.view.y += before.y - after.y;
    scheduleDraw();
  }, { passive: false });
  window.addEventListener("keydown", handleKey);
  window.addEventListener("resize", resizeCanvasToContainer);

  // ── Save / Load / Export ─────────────────────────────────────────────────────

  async function saveDiagram() {
    const payload = { v: 2, caseId, savedAt: new Date().toISOString(), view: state.view, items: state.items };
    const r = await fetch(saveUrl, { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!r.ok) { setStatus("Save failed"); return false; }
    state.lastSavedAt = Date.now(); setStatus("Saved"); return true;
  }

  async function loadDiagram() {
    try {
      const r = await fetch(loadUrl, { credentials: "same-origin" });
      if (!r.ok) throw new Error("no-diagram");
      const data = await r.json();
      if (data && Array.isArray(data.items)) {
        state.items = data.items; state.view = data.view || state.view;
        setStatus("Loaded diagram");
      }
    } catch {
      state.items = [
        { ...defaultItem("intersection", { x: 260, y: 160 }) },
        { ...defaultItem("car",  { x: 310, y: 240 }), label: "V1" },
        { ...defaultItem("car",  { x: 500, y: 320 }), label: "V2", rot: 90 },
        { ...defaultItem("waypoint", { x: 370, y: 270 }), label: "1" },
        { ...defaultItem("compass",  { x: 620, y: 100 }) },
      ];
      setStatus(`New diagram (editor ${BUILD})`);
    }
    scheduleDraw();
  }

  async function exportAndAttach() {
    if (!await saveDiagram()) return;
    const wrap = root.querySelector("[data-canvas-wrap]");
    const r = wrap.getBoundingClientRect();
    const tmp = document.createElement("canvas");
    tmp.width = Math.floor(r.width); tmp.height = Math.floor(r.height);
    const tctx = tmp.getContext("2d");
    tctx.fillStyle = "#ffffff"; tctx.fillRect(0, 0, tmp.width, tmp.height);
    tctx.drawImage(canvas, 0, 0, tmp.width, tmp.height);
    const blob = await new Promise(res => tmp.toBlob(res, "image/png"));
    if (!blob) { setStatus("Export failed"); return; }
    const fd = new FormData();
    fd.append("kind", "diagram"); fd.append("file", blob, `case-${caseId}-diagram.png`);
    const up = await fetch(uploadUrl, { method: "POST", credentials: "same-origin", body: fd });
    if (!up.ok) { setStatus("Upload failed"); return; }
    setStatus("Exported + attached"); window.location.reload();
  }

  function clearDiagram() {
    if (!confirm("Clear diagram?")) return;
    state.items = []; state.selectedId = null; scheduleDraw(); setStatus("Cleared");
  }

  // ── Palette ──────────────────────────────────────────────────────────────────

  function setupPalette() {
    if (!palette) return;
    palette.querySelectorAll("[data-item]").forEach((el) => {
      el.setAttribute("draggable", "true");
      el.addEventListener("dragstart", (ev) => ev.dataTransfer?.setData("text/plain", el.dataset.item || ""));
      el.addEventListener("click", () => {
        const wrap = root.querySelector("[data-canvas-wrap]");
        const r = wrap.getBoundingClientRect();
        const at = screenToWorld({ x: r.width * 0.5, y: r.height * 0.5 });
        const it = defaultItem(el.dataset.item, at);
        state.items.push(it); state.selectedId = it.id; scheduleDraw();
      });
    });
    const wrap = root.querySelector("[data-canvas-wrap]");
    wrap.addEventListener("dragover", ev => ev.preventDefault());
    wrap.addEventListener("drop", (ev) => {
      ev.preventDefault();
      const type = ev.dataTransfer?.getData("text/plain") || "";
      if (!type) return;
      const r = canvas.getBoundingClientRect();
      const at = screenToWorld({ x: ev.clientX - r.left, y: ev.clientY - r.top });
      const it = defaultItem(type, at);
      state.items.push(it); state.selectedId = it.id; scheduleDraw();
    });
  }

  // ── Toolbar ──────────────────────────────────────────────────────────────────

  root.querySelector("[data-action='save']")?.addEventListener("click", e => { e.preventDefault(); saveDiagram(); });
  root.querySelector("[data-action='export']")?.addEventListener("click", e => { e.preventDefault(); exportAndAttach(); });
  root.querySelector("[data-action='clear']")?.addEventListener("click", e => { e.preventDefault(); clearDiagram(); });
  root.querySelector("[data-action='fit']")?.addEventListener("click", e => { e.preventDefault(); state.view = { x: 0, y: 0, scale: 1 }; scheduleDraw(); });

  // ── Boot ─────────────────────────────────────────────────────────────────────

  setupPalette();
  resizeCanvasToContainer();
  setStatus(`Loading... (editor ${BUILD})`);
  loadDiagram();
})();
