(function () {
  var root = document.querySelector('[data-accident-recon]');
  if (!root) return;

  var canvas = root.querySelector('[data-recon-canvas]');
  var stateScript = root.querySelector('[data-recon-state]');
  var saveButton = document.querySelector('[data-recon-save]');
  var toolButtons = Array.prototype.slice.call(root.querySelectorAll('[data-tool]'));
  var gridToggle = root.querySelector('[data-grid-toggle]');
  var snapToggle = root.querySelector('[data-snap-toggle]');
  var unitsSelect = root.querySelector('[data-units-select]');
  var zoomSelect = root.querySelector('[data-zoom-select]');
  var resetButton = root.querySelector('[data-recon-redraw]');
  var undoButton = root.querySelector('[data-recon-undo]');
  var ctx = canvas.getContext('2d');
  var selectedTool = 'select';
  var selectedItem = null;
  var dragOffset = null;
  var zoom = 1;
  var history = [];

  function parseState() {
    try {
      return JSON.parse(stateScript.textContent || '{}');
    } catch (err) {
      return {};
    }
  }

  var state = parseState();
  state.vehicles = state.vehicles || [];
  state.objects = state.objects || [];
  state.measurements = state.measurements || [];
  state.canvasItems = state.canvasItems || [];
  state.units = state.units || 'ft';

  function pushHistory() {
    history.push(JSON.stringify(state));
    if (history.length > 20) history.shift();
  }

  function setTool(tool) {
    selectedTool = tool;
    toolButtons.forEach(function (button) {
      button.classList.toggle('is-active', button.getAttribute('data-tool') === tool);
    });
  }

  function snap(value) {
    if (!snapToggle || !snapToggle.checked) return value;
    return Math.round(value / 10) * 10;
  }

  function getPointer(evt) {
    var rect = canvas.getBoundingClientRect();
    return {
      x: (evt.clientX - rect.left) * (canvas.width / rect.width) / zoom,
      y: (evt.clientY - rect.top) * (canvas.height / rect.height) / zoom
    };
  }

  function allItems() {
    return state.vehicles.concat(state.objects, state.canvasItems);
  }

  function itemAt(point) {
    var items = allItems().slice().reverse();
    for (var i = 0; i < items.length; i += 1) {
      var item = items[i];
      var w = item.type === 'vehicle' ? 82 : 44;
      var h = item.type === 'vehicle' ? 38 : 44;
      if (point.x >= item.x - w / 2 && point.x <= item.x + w / 2 && point.y >= item.y - h / 2 && point.y <= item.y + h / 2) {
        return item;
      }
    }
    return null;
  }

  function drawRoadBase() {
    ctx.save();
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (gridToggle && gridToggle.checked) {
      ctx.strokeStyle = '#e9edf3';
      ctx.lineWidth = 1;
      for (var gx = 0; gx < canvas.width; gx += 20) {
        ctx.beginPath();
        ctx.moveTo(gx, 0);
        ctx.lineTo(gx, canvas.height);
        ctx.stroke();
      }
      for (var gy = 0; gy < canvas.height; gy += 20) {
        ctx.beginPath();
        ctx.moveTo(0, gy);
        ctx.lineTo(canvas.width, gy);
        ctx.stroke();
      }
    }

    ctx.fillStyle = '#757b83';
    ctx.fillRect(0, 215, canvas.width, 150);
    ctx.fillRect(420, 0, 170, canvas.height);
    ctx.fillStyle = '#5f666f';
    ctx.fillRect(0, 238, canvas.width, 104);
    ctx.fillRect(445, 0, 120, canvas.height);

    ctx.strokeStyle = '#f3c94a';
    ctx.lineWidth = 3;
    ctx.setLineDash([26, 18]);
    ctx.beginPath();
    ctx.moveTo(0, 290);
    ctx.lineTo(canvas.width, 290);
    ctx.moveTo(505, 0);
    ctx.lineTo(505, canvas.height);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 5;
    for (var x = 430; x <= 555; x += 18) {
      ctx.beginPath();
      ctx.moveTo(x, 198);
      ctx.lineTo(x, 218);
      ctx.moveTo(x, 362);
      ctx.lineTo(x, 382);
      ctx.stroke();
    }
    for (var y = 224; y <= 350; y += 18) {
      ctx.beginPath();
      ctx.moveTo(395, y);
      ctx.lineTo(420, y);
      ctx.moveTo(590, y);
      ctx.lineTo(615, y);
      ctx.stroke();
    }

    ctx.fillStyle = '#1f2937';
    ctx.font = 'bold 14px Arial';
    ctx.fillText('N', canvas.width - 52, 58);
    ctx.strokeStyle = '#1f2937';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(canvas.width - 48, 94);
    ctx.lineTo(canvas.width - 48, 66);
    ctx.lineTo(canvas.width - 56, 80);
    ctx.moveTo(canvas.width - 48, 66);
    ctx.lineTo(canvas.width - 40, 80);
    ctx.stroke();

    ctx.strokeStyle = '#111827';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(canvas.width - 185, canvas.height - 42);
    ctx.lineTo(canvas.width - 85, canvas.height - 42);
    ctx.stroke();
    ctx.font = '12px Arial';
    ctx.fillText('0', canvas.width - 190, canvas.height - 50);
    ctx.fillText('50 ' + (state.units || 'ft'), canvas.width - 105, canvas.height - 50);
    ctx.restore();
  }

  function drawVehicle(item) {
    ctx.save();
    ctx.translate(item.x, item.y);
    ctx.rotate((item.rotation || 0) * Math.PI / 180);
    ctx.fillStyle = item === selectedItem ? '#dbeafe' : '#f8fafc';
    ctx.strokeStyle = item.label === 'V2' ? '#b91c1c' : '#0f4c81';
    ctx.lineWidth = 3;
    ctx.fillRect(-41, -19, 82, 38);
    ctx.strokeRect(-41, -19, 82, 38);
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(-26, -14, 20, 28);
    ctx.fillRect(8, -14, 20, 28);
    ctx.restore();
    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 15px Arial';
    ctx.fillText(item.label || 'V', item.x - 15, item.y - 27);
  }

  function drawObject(item) {
    ctx.save();
    ctx.translate(item.x, item.y);
    ctx.rotate((item.rotation || 0) * Math.PI / 180);
    ctx.strokeStyle = '#111827';
    ctx.fillStyle = item.type === 'pedestrian' ? '#fef3c7' : '#f8fafc';
    ctx.lineWidth = 2;
    if (item.type === 'arrow') {
      ctx.beginPath();
      ctx.moveTo(-28, 0);
      ctx.lineTo(28, 0);
      ctx.lineTo(18, -8);
      ctx.moveTo(28, 0);
      ctx.lineTo(18, 8);
      ctx.stroke();
    } else if (item.type === 'zone') {
      ctx.setLineDash([6, 5]);
      ctx.strokeRect(-34, -22, 68, 44);
      ctx.setLineDash([]);
    } else if (item.type === 'camera') {
      ctx.strokeRect(-18, -12, 36, 24);
      ctx.beginPath();
      ctx.arc(0, 0, 8, 0, Math.PI * 2);
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.arc(0, 0, 18, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
    ctx.restore();
    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 13px Arial';
    ctx.fillText(item.label || item.type || 'Obj', item.x - 18, item.y - 25);
  }

  function drawMeasurements() {
    state.measurements.forEach(function (m) {
      var sx = m.startX || 120;
      var sy = m.startY || 120;
      var ex = m.endX || 260;
      var ey = m.endY || 140;
      ctx.strokeStyle = '#0f4c81';
      ctx.lineWidth = 2;
      ctx.setLineDash([8, 6]);
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(ex, ey);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#0f172a';
      ctx.font = '12px Arial';
      ctx.fillText((m.label || 'Measurement') + ': ' + (m.value || '') + ' ' + (m.units || state.units || 'ft'), (sx + ex) / 2 + 8, (sy + ey) / 2 - 8);
    });
  }

  function drawCrashMarkers() {
    ctx.save();
    ctx.translate(505, 290);
    ctx.strokeStyle = '#dc2626';
    ctx.fillStyle = '#facc15';
    ctx.lineWidth = 3;
    ctx.beginPath();
    for (var i = 0; i < 16; i += 1) {
      var radius = i % 2 === 0 ? 26 : 12;
      var angle = (Math.PI * 2 * i) / 16;
      ctx.lineTo(Math.cos(angle) * radius, Math.sin(angle) * radius);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.restore();
    ctx.fillStyle = '#991b1b';
    ctx.font = 'bold 12px Arial';
    ctx.fillText('POI', 493, 328);
  }

  function redraw() {
    ctx.save();
    ctx.setTransform(zoom, 0, 0, zoom, 0, 0);
    drawRoadBase();
    drawMeasurements();
    state.canvasItems.forEach(drawObject);
    state.objects.forEach(drawObject);
    state.vehicles.forEach(drawVehicle);
    drawCrashMarkers();
    ctx.restore();
  }

  function nextLabel(type) {
    if (type === 'vehicle') return 'V' + (state.vehicles.length + state.canvasItems.filter(function (i) { return i.type === 'vehicle'; }).length + 1);
    if (type === 'pedestrian') return 'P' + (state.canvasItems.filter(function (i) { return i.type === 'pedestrian'; }).length + 1);
    if (type === 'bicycle') return 'B' + (state.canvasItems.filter(function (i) { return i.type === 'bicycle'; }).length + 1);
    if (type === 'measure') return 'M' + (state.measurements.length + 1);
    if (type === 'point') return 'PT';
    return type.charAt(0).toUpperCase() + (state.canvasItems.length + 1);
  }

  function addCanvasItem(type, point) {
    pushHistory();
    if (type === 'measure') {
      state.measurements.push({ label: nextLabel(type), value: 'field measure', units: state.units, startX: snap(point.x - 45), startY: snap(point.y), endX: snap(point.x + 45), endY: snap(point.y) });
      redraw();
      return;
    }
    if (type === 'clear-all') {
      if (window.confirm('Clear unsaved canvas items and measurements from this diagram view?')) {
        state.canvasItems = [];
        state.measurements = [];
        redraw();
      }
      return;
    }
    var normalizedType = type === 'select' ? 'point' : type;
    state.canvasItems.push({
      clientId: 'item-' + Date.now(),
      type: normalizedType,
      label: nextLabel(normalizedType),
      x: snap(point.x),
      y: snap(point.y),
      rotation: 0
    });
    redraw();
  }

  canvas.addEventListener('pointerdown', function (evt) {
    var point = getPointer(evt);
    if (selectedTool !== 'select') {
      addCanvasItem(selectedTool, point);
      return;
    }
    selectedItem = itemAt(point);
    if (selectedItem) {
      dragOffset = { x: point.x - selectedItem.x, y: point.y - selectedItem.y };
      canvas.setPointerCapture(evt.pointerId);
    }
    redraw();
  });

  canvas.addEventListener('pointermove', function (evt) {
    if (!selectedItem || !dragOffset) return;
    var point = getPointer(evt);
    selectedItem.x = snap(point.x - dragOffset.x);
    selectedItem.y = snap(point.y - dragOffset.y);
    redraw();
  });

  canvas.addEventListener('pointerup', function () {
    dragOffset = null;
  });

  canvas.addEventListener('dblclick', function () {
    if (!selectedItem) return;
    var label = window.prompt('Diagram label', selectedItem.label || '');
    if (label !== null) {
      selectedItem.label = label.trim() || selectedItem.label;
      redraw();
    }
  });

  toolButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      setTool(button.getAttribute('data-tool'));
      if (selectedTool === 'clear-all') addCanvasItem('clear-all', { x: 0, y: 0 });
    });
  });

  if (unitsSelect) {
    unitsSelect.addEventListener('change', function () {
      state.units = unitsSelect.value;
      redraw();
    });
  }

  if (zoomSelect) {
    zoomSelect.addEventListener('change', function () {
      zoom = parseFloat(zoomSelect.value) || 1;
      redraw();
    });
  }

  [gridToggle, snapToggle].forEach(function (control) {
    if (control) control.addEventListener('change', redraw);
  });

  if (resetButton) resetButton.addEventListener('click', redraw);
  if (undoButton) {
    undoButton.addEventListener('click', function () {
      var previous = history.pop();
      if (!previous) return;
      state = JSON.parse(previous);
      redraw();
    });
  }

  if (saveButton) {
    saveButton.addEventListener('click', function () {
      saveButton.disabled = true;
      saveButton.textContent = 'Saving...';
      fetch(root.getAttribute('data-save-url'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state)
      }).then(function (response) {
        if (!response.ok) throw new Error('Save failed');
        return response.json();
      }).then(function () {
        saveButton.textContent = 'Saved';
        setTimeout(function () {
          saveButton.textContent = 'Save';
          saveButton.disabled = false;
        }, 1200);
      }).catch(function () {
        saveButton.textContent = 'Save failed';
        saveButton.disabled = false;
        window.alert('Unable to save the diagram. Your work is still on screen; try again.');
      });
    });
  }

  setTool('select');
  redraw();
}());
