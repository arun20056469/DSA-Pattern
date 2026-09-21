(function () {
  "use strict";

  var COLORS = {
    accent: "#6c8cff",
    green: "#4caf50",
    orange: "#ffa726",
    red: "#ef5350",
    muted: "#9aa0b0",
    surface: "#262b3a",
    surface2: "#1f2330",
    border: "#3a4152",
    text: "#e6e8ef",
  };

  function resolveColor(c) {
    if (!c) return COLORS.surface;
    if (c[0] === "#") return c;
    return COLORS[c] || c;
  }

  var SVG_NS = "http://www.w3.org/2000/svg";

  function el(tag, attrs, children) {
    var e = document.createElementNS(SVG_NS, tag);
    for (var k in attrs) {
      if (Object.prototype.hasOwnProperty.call(attrs, k)) e.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) { e.appendChild(c); });
    return e;
  }

  function textEl(x, y, str, opts) {
    opts = opts || {};
    var t = el("text", {
      x: x, y: y,
      "text-anchor": opts.anchor || "middle",
      "dominant-baseline": opts.baseline || "middle",
      fill: opts.fill || COLORS.text,
      "font-size": opts.size || 13,
      "font-weight": opts.weight || "normal",
      "font-family": "-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif",
    });
    t.textContent = str;
    return t;
  }

  function ensureArrowMarker(svg, id, color) {
    var defsId = "defs-" + id;
    var defs = svg.querySelector("defs");
    if (!defs) {
      defs = el("defs", {});
      svg.appendChild(defs);
    }
    if (svg.querySelector("#" + id)) return;
    var marker = el("marker", {
      id: id, viewBox: "0 0 10 10", refX: "9", refY: "5",
      markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse",
    }, [el("path", { d: "M0,0 L10,5 L0,10 z", fill: color })]);
    defs.appendChild(marker);
  }

  // ---------------------------------------------------------------- renderers

  function renderArray(svg, step) {
    var n = step.values.length;
    var boxW = 52, boxH = 52, gap = 10;
    var startX = 24, mainY = 78;
    var width = Math.max(360, startX * 2 + n * (boxW + gap));
    var hasWindow = !!step.window;
    var hasPointers = step.pointers && step.pointers.length > 0;
    var hasSecondary = !!step.secondary;
    var height = 40 + (hasPointers ? 50 : 0) + boxH + (hasWindow ? 14 : 0) + (hasSecondary ? 46 : 20);
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);

    if (hasWindow) {
      var w = step.window;
      var wx = startX + w.start * (boxW + gap) - 6;
      var wEndX = startX + w.end * (boxW + gap) + boxW + 6;
      svg.appendChild(el("rect", {
        x: wx, y: mainY - 8, width: wEndX - wx, height: boxH + 16,
        fill: "none", stroke: COLORS.accent, "stroke-width": 2.5, rx: 10,
      }));
    }

    var faded = {};
    (step.faded || []).forEach(function (i) { faded[i] = true; });
    var hl = {};
    (step.highlights || []).forEach(function (h) { hl[h.index] = h.color; });

    for (var i = 0; i < n; i++) {
      var x = startX + i * (boxW + gap);
      var fill = COLORS.surface;
      var opacity = 1;
      if (faded[i]) opacity = 0.28;
      if (hl[i] !== undefined) fill = resolveColor(hl[i]);
      var g = el("g", { opacity: opacity });
      g.appendChild(el("rect", { x: x, y: mainY, width: boxW, height: boxH, rx: 8, fill: fill, stroke: COLORS.border, "stroke-width": 1.4 }));
      g.appendChild(textEl(x + boxW / 2, mainY + boxH / 2 + 1, step.values[i], { size: 15 }));
      svg.appendChild(g);
    }

    // dependency arrows (drawn above the boxes)
    (step.arrows || []).forEach(function (a) {
      var color = resolveColor(a.color);
      var mid = "arrowhead-" + color.replace("#", "");
      ensureArrowMarker(svg, mid, color);
      var x1 = startX + a.fromIndex * (boxW + gap) + boxW / 2;
      var x2 = startX + a.toIndex * (boxW + gap) + boxW / 2;
      var topY = mainY - (hasPointers ? 44 : 6);
      var peak = topY - 18;
      var path = el("path", {
        d: "M " + x1 + " " + topY + " Q " + ((x1 + x2) / 2) + " " + peak + " " + x2 + " " + topY,
        fill: "none", stroke: color, "stroke-width": 2, "marker-end": "url(#" + mid + ")",
      });
      svg.appendChild(path);
    });

    // pointer labels above boxes
    (step.pointers || []).forEach(function (p) {
      var color = resolveColor(p.color);
      var x = startX + p.index * (boxW + gap) + boxW / 2;
      var labelY = mainY - 30;
      svg.appendChild(textEl(x, labelY, p.label, { fill: color, weight: "bold", size: 12 }));
      svg.appendChild(el("line", { x1: x, y1: labelY + 8, x2: x, y2: mainY - 4, stroke: color, "stroke-width": 2 }));
    });

    // secondary chips
    if (hasSecondary) {
      var sy = mainY + boxH + (hasWindow ? 22 : 14) + 8;
      var sx = startX;
      step.secondary.forEach(function (chip) {
        var chipW = Math.max(50, chip.length * 6.6 + 16);
        if (sx + chipW > width - startX) { sx = startX; sy += 26; }
        svg.appendChild(el("rect", { x: sx, y: sy, width: chipW, height: 20, rx: 10, fill: COLORS.surface2, stroke: COLORS.border, "stroke-width": 1 }));
        svg.appendChild(textEl(sx + chipW / 2, sy + 11, chip, { size: 10.5, fill: COLORS.muted }));
        sx += chipW + 8;
      });
      var neededHeight = sy + 30;
      if (neededHeight > height) svg.setAttribute("viewBox", "0 0 " + width + " " + neededHeight);
    }
  }

  function renderGrid(svg, step) {
    var rows = step.cells.length, cols = step.cells[0] ? step.cells[0].length : 0;
    var maxWidth = 480;
    var cellSize = Math.max(26, Math.min(52, Math.floor(maxWidth / cols)));
    var startX = 20, startY = 20;
    var width = startX * 2 + cols * cellSize;
    var height = startY * 2 + rows * cellSize;
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);

    var hl = {};
    (step.highlights || []).forEach(function (h) { hl[h.r + "," + h.c] = h.color; });
    var faded = {};
    (step.faded || []).forEach(function (fc) { faded[fc[0] + "," + fc[1]] = true; });

    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var key = r + "," + c;
        var val = step.cells[r][c];
        var x = startX + c * cellSize, y = startY + r * cellSize;
        var fill = val === "" ? COLORS.surface2 : COLORS.surface;
        if (hl[key]) fill = resolveColor(hl[key]);
        var opacity = faded[key] ? 0.3 : 1;
        var g = el("g", { opacity: opacity });
        g.appendChild(el("rect", { x: x, y: y, width: cellSize - 3, height: cellSize - 3, rx: 5, fill: fill, stroke: COLORS.border, "stroke-width": 1 }));
        if (val !== "") g.appendChild(textEl(x + (cellSize - 3) / 2, y + (cellSize - 3) / 2 + 1, val, { size: cellSize > 34 ? 13 : 10 }));
        svg.appendChild(g);
      }
    }
  }

  function renderBits(svg, step) {
    var boxSize = 30, gap = 4, labelW = 120;
    var maxBits = Math.max.apply(null, step.rows.map(function (r) { return r.bits.length; }));
    var width = labelW + maxBits * (boxSize + gap) + 20;
    var height = step.rows.length * (boxSize + 14) + 20;
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);

    var hlCols = {};
    (step.highlightCols || []).forEach(function (c) { hlCols[c] = true; });

    step.rows.forEach(function (row, ri) {
      var y = 16 + ri * (boxSize + 14);
      svg.appendChild(textEl(labelW - 12, y + boxSize / 2, row.label, { anchor: "end", fill: COLORS.muted, size: 12 }));
      row.bits.forEach(function (bit, ci) {
        var x = labelW + ci * (boxSize + gap);
        var fill = hlCols[ci] ? COLORS.accent : COLORS.surface;
        svg.appendChild(el("rect", { x: x, y: y, width: boxSize, height: boxSize, rx: 5, fill: fill, stroke: COLORS.border, "stroke-width": 1 }));
        svg.appendChild(textEl(x + boxSize / 2, y + boxSize / 2 + 1, bit, { size: 14 }));
      });
    });
  }

  function renderGraph(svg, step) {
    var xs = step.nodes.map(function (n) { return n.x; });
    var ys = step.nodes.map(function (n) { return n.y; });
    var minX = Math.min.apply(null, xs), maxX = Math.max.apply(null, xs);
    var minY = Math.min.apply(null, ys), maxY = Math.max.apply(null, ys);
    var scale = 78;
    var pad = 50;
    var width = (maxX - minX) * scale + pad * 2 || 300;
    var height = (maxY - minY) * scale + pad * 2 || 220;
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);

    function px(x) { return (x - minX) * scale + pad; }
    function py(y) { return height - ((y - minY) * scale + pad); }

    var byId = {};
    step.nodes.forEach(function (n) { byId[n.id] = n; });

    (step.edges || []).forEach(function (e) {
      var a = byId[e.from], b = byId[e.to];
      if (!a || !b) return;
      var color = resolveColor(e.color || "border");
      var mid = "arrowhead-" + color.replace("#", "");
      ensureArrowMarker(svg, mid, color);
      var x1 = px(a.x), y1 = py(a.y), x2 = px(b.x), y2 = py(b.y);
      var dx = x2 - x1, dy = y2 - y1, len = Math.sqrt(dx * dx + dy * dy) || 1;
      var r = 22;
      var sx = x1 + (dx / len) * r, sy = y1 + (dy / len) * r;
      var ex = x2 - (dx / len) * r, ey = y2 - (dy / len) * r;
      svg.appendChild(el("line", { x1: sx, y1: sy, x2: ex, y2: ey, stroke: color, "stroke-width": 2, "marker-end": "url(#" + mid + ")" }));
      if (e.label) {
        svg.appendChild(textEl((sx + ex) / 2, (sy + ey) / 2 - 8, e.label, { size: 10.5, fill: COLORS.muted }));
      }
    });

    step.nodes.forEach(function (n) {
      var x = px(n.x), y = py(n.y);
      var fill = resolveColor(n.color);
      svg.appendChild(el("circle", { cx: x, cy: y, r: 22, fill: fill, stroke: COLORS.border, "stroke-width": 1.5 }));
      var labelStr = String(n.label);
      var fontSize = labelStr.length > 4 ? 9.5 : 12.5;
      svg.appendChild(textEl(x, y + 1, labelStr, { size: fontSize, fill: fill === COLORS.surface || fill === COLORS.surface2 ? COLORS.text : "#0f1117", weight: "600" }));
    });
  }

  function renderIntervals(svg, step) {
    var width = 520, leftPad = 20, rightPad = 20;
    var usable = width - leftPad - rightPad;
    var rows = Math.max.apply(null, step.items.map(function (it) { return it.row; })) + 1;
    var rowH = 42;
    var height = rows * rowH + 30;
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);

    var span = (step.scaleMax - step.scaleMin) || 1;
    function px(v) { return leftPad + ((v - step.scaleMin) / span) * usable; }

    step.items.forEach(function (it) {
      var x1 = px(it.start), x2 = px(it.end);
      var y = 15 + it.row * rowH;
      svg.appendChild(el("rect", { x: x1, y: y, width: Math.max(4, x2 - x1), height: 26, rx: 6, fill: resolveColor(it.color), stroke: COLORS.border, "stroke-width": 1 }));
      svg.appendChild(textEl((x1 + x2) / 2, y + 13, it.label, { size: 11, fill: "#0f1117", weight: "600" }));
    });
  }

  var RENDERERS = { array: renderArray, grid: renderGrid, bits: renderBits, graph: renderGraph, intervals: renderIntervals };

  // ---------------------------------------------------------------- player

  function PatternVisualizer(container, trace) {
    this.container = container;
    this.trace = trace;
    this.index = 0;
    this.timer = null;
    this.buildDom();
    this.render();
  }

  PatternVisualizer.prototype.buildDom = function () {
    this.container.innerHTML =
      '<div class="viz-canvas-wrap"><svg class="viz-svg" xmlns="' + SVG_NS + '"></svg></div>' +
      '<p class="viz-caption"></p>' +
      '<div class="viz-controls">' +
      '<button type="button" class="viz-btn" data-action="reset" title="Restart">⟲</button>' +
      '<button type="button" class="viz-btn" data-action="prev" title="Previous step">◀</button>' +
      '<button type="button" class="viz-btn viz-play" data-action="play">▶ Play</button>' +
      '<button type="button" class="viz-btn" data-action="next" title="Next step">▶</button>' +
      '<span class="viz-step-label"></span>' +
      '<select class="viz-speed" title="Playback speed">' +
      '<option value="1700">Slow</option><option value="900" selected>Normal</option><option value="400">Fast</option>' +
      '</select>' +
      '</div>';
    this.svg = this.container.querySelector(".viz-svg");
    this.caption = this.container.querySelector(".viz-caption");
    this.stepLabel = this.container.querySelector(".viz-step-label");
    this.playBtn = this.container.querySelector('[data-action="play"]');
    this.speedSelect = this.container.querySelector(".viz-speed");

    var self = this;
    this.container.querySelector('[data-action="reset"]').addEventListener("click", function () { self.stop(); self.goTo(0); });
    this.container.querySelector('[data-action="prev"]').addEventListener("click", function () { self.stop(); self.goTo(self.index - 1); });
    this.container.querySelector('[data-action="next"]').addEventListener("click", function () { self.stop(); self.goTo(self.index + 1); });
    this.playBtn.addEventListener("click", function () { self.togglePlay(); });
  };

  PatternVisualizer.prototype.goTo = function (i) {
    if (i < 0 || i >= this.trace.length) return;
    this.index = i;
    this.render();
  };

  PatternVisualizer.prototype.render = function () {
    while (this.svg.firstChild) this.svg.removeChild(this.svg.firstChild);
    var step = this.trace[this.index];
    var renderer = RENDERERS[step.type];
    if (renderer) renderer(this.svg, step);
    this.caption.textContent = step.caption || "";
    this.stepLabel.textContent = "Step " + (this.index + 1) + " / " + this.trace.length;
    var prevBtn = this.container.querySelector('[data-action="prev"]');
    var nextBtn = this.container.querySelector('[data-action="next"]');
    prevBtn.disabled = this.index === 0;
    nextBtn.disabled = this.index === this.trace.length - 1;
    if (this.index === this.trace.length - 1) this.stop();
  };

  PatternVisualizer.prototype.togglePlay = function () {
    if (this.timer) { this.stop(); return; }
    var self = this;
    if (this.index === this.trace.length - 1) this.index = -1;
    this.playBtn.textContent = "⏸ Pause";
    var delay = parseInt(this.speedSelect.value, 10);
    this.timer = setInterval(function () {
      if (self.index >= self.trace.length - 1) { self.stop(); return; }
      self.goTo(self.index + 1);
    }, delay);
  };

  PatternVisualizer.prototype.stop = function () {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    this.playBtn.textContent = "▶ Play";
  };

  function init(containerId, traceUrl) {
    var container = document.getElementById(containerId);
    if (!container) return;
    fetch(traceUrl).then(function (r) {
      if (!r.ok) throw new Error("trace not found");
      return r.json();
    }).then(function (trace) {
      new PatternVisualizer(container, trace);
    }).catch(function () {
      container.innerHTML = '<p class="viz-caption">No step-by-step visualization available for this pattern yet.</p>';
    });
  }

  window.PatternVisualizer = { init: init };
})();
