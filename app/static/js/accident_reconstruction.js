(function () {
  var root = document.querySelector('[data-accident-recon]');
  if (!root) return;

  var canvas = root.querySelector('[data-recon-canvas]');
  var stage = root.querySelector('[data-recon-stage]');
  var objectLayer = root.querySelector('[data-recon-object-layer]');
  var stateScript = root.querySelector('[data-recon-state]');
  var saveButton = document.querySelector('[data-recon-save]');
  var exportPngButton = document.querySelector('[data-recon-export-png]');
  var toolButtons = Array.prototype.slice.call(root.querySelectorAll('[data-tool]'));
  var gridToggle = root.querySelector('[data-grid-toggle]');
  var snapToggle = root.querySelector('[data-snap-toggle]');
  var unitsSelect = root.querySelector('[data-units-select]');
  var zoomSelect = root.querySelector('[data-zoom-select]');
  var resetButton = root.querySelector('[data-recon-redraw]');
  var undoButton = root.querySelector('[data-recon-undo]');
  var modal = document.querySelector('[data-recon-asset-modal]');
  var modalClose = document.querySelector('[data-recon-asset-close]');
  var modalAssets = Array.prototype.slice.call(document.querySelectorAll('[data-asset-kind]'));
  var ctx = canvas.getContext('2d');
  var selectedTool = 'select';
  var selectedItem = null;
  var dragState = null;
  var pendingInsertPoint = null;
  var zoom = 1;
  var history = [];
  var svgCache = {};

  var ASSETS = {
    sedan: '/static/icons/vehicles/sedan.svg',
    suv: '/static/icons/vehicles/suv.svg',
    pickup: '/static/icons/vehicles/pickup.svg',
    patrol: '/static/icons/vehicles/patrol.svg',
    truck: '/static/icons/vehicles/truck.svg',
    motorcycle: '/static/icons/vehicles/motorcycle.svg',
    pedestrian: '/static/icons/people/pedestrian.svg',
    officer: '/static/icons/people/officer.svg',
    'stop-sign': '/static/icons/traffic/stop-sign.svg',
    'traffic-light': '/static/icons/traffic/traffic-light.svg',
    cone: '/static/icons/traffic/cone.svg',
    barrier: '/static/icons/traffic/barrier.svg',
    building: '/static/icons/traffic/building.svg',
    tree: '/static/icons/traffic/tree.svg',
    arrow: '/static/icons/diagram/arrow.svg',
    skid: '/static/icons/diagram/skid.svg',
    impact: '/static/icons/diagram/impact.svg'
  };

  var SIZES = {
    sedan: [92, 46],
    suv: [98, 52],
    pickup: [106, 52],
    patrol: [96, 48],
    truck: [132, 64],
    motorcycle: [76, 40],
    pedestrian: [38, 38],
    officer: [40, 42],
    'stop-sign': [52, 60],
    'traffic-light': [34, 70],
    cone: [38, 44],
    barrier: [96, 44],
    building: [86, 72],
    tree: [62, 68],
    arrow: [120, 32],
    skid: [128, 38],
    impact: [58, 58],
    text: [160, 44],
    measure: [120, 28]
  };

  function parseState() {
    try {
      return JSON.parse(stateScript.textContent || '{}');
    } catch (err) {
      return {};
    }
  }

  var state = parseState();
  state.vehicles = (state.vehicles || []).map(function (item, index) {
    var assetType = normalizeVehicleType(item.vehicleType || item.assetType || item.make_model || item.type);
    return normalizeItem(item, {
      kind: 'vehicle',
      assetType: assetType,
      label: item.label || 'V' + (index + 1)
    });
  });
  state.objects = (state.objects || []).map(function (item) {
    return normalizeItem(item, {
      kind: 'object',
      assetType: normalizeObjectType(item.assetType || item.type),
      label: item.label || item.type || 'Obj'
    });
  });
  state.canvasItems = (state.canvasItems || []).map(function (item) {
    return normalizeItem(item, {
      kind: item.kind || inferKind(item.assetType || item.type),
      assetType: normalizeObjectType(item.assetType || item.type),
      label: item.label || nextLabel(item.type || item.assetType || 'object')
    });
  });
  state.measurements = state.measurements || [];
  state.units = state.units || 'ft';

  function normalizeVehicleType(value) {
    var raw = String(value || '').toLowerCase();
    if (raw.indexOf('suv') !== -1) return 'suv';
    if (raw.indexOf('pickup') !== -1 || raw.indexOf('truck') !== -1 && raw.indexOf('commercial') === -1) return 'pickup';
    if (raw.indexOf('patrol') !== -1 || raw.indexOf('police') !== -1) return 'patrol';
    if (raw.indexOf('commercial') !== -1 || raw.indexOf('semi') !== -1 || raw.indexOf('tractor') !== -1) return 'truck';
    if (raw.indexOf('motor') !== -1) return 'motorcycle';
    return 'sedan';
  }

  function normalizeObjectType(value) {
    var raw = String(value || '').toLowerCase().replace(/_/g, '-');
    if (raw === 'vehicle') return 'sedan';
    if (raw === 'person') return 'pedestrian';
    if (ASSETS[raw]) return raw;
    if (raw.indexOf('stop') !== -1) return 'stop-sign';
    if (raw.indexOf('light') !== -1) return 'traffic-light';
    if (raw.indexOf('skid') !== -1) return 'skid';
    if (raw.indexOf('impact') !== -1 || raw.indexOf('point') !== -1) return 'impact';
    if (raw.indexOf('arrow') !== -1) return 'arrow';
    return 'cone';
  }

  function inferKind(assetType) {
    if (['sedan', 'suv', 'pickup', 'patrol', 'truck', 'motorcycle'].indexOf(assetType) !== -1) return 'vehicle';
    if (['pedestrian', 'officer'].indexOf(assetType) !== -1) return 'person';
    if (['arrow', 'skid', 'impact'].indexOf(assetType) !== -1) return 'diagram';
    return 'object';
  }

  function normalizeItem(item, defaults) {
    var assetType = defaults.assetType || 'sedan';
    var size = SIZES[assetType] || [64, 48];
    return {
      id: item.id || null,
      clientId: item.clientId || 'asset-' + Date.now() + '-' + Math.random().toString(36).slice(2),
      kind: defaults.kind || inferKind(assetType),
      type: item.type || defaults.kind || inferKind(assetType),
      assetType: assetType,
      label: item.label || defaults.label || '',
      notes: item.notes || '',
      x: Number(item.x || item.x_position || 260),
      y: Number(item.y || item.y_position || 220),
      width: Number(item.width || size[0]),
      height: Number(item.height || size[1]),
      rotation: Number(item.rotation || item.rot || 0)
    };
  }

  function pushHistory() {
    history.push(JSON.stringify(state));
    if (history.length > 25) history.shift();
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
    var rect = stage.getBoundingClientRect();
    return {
      x: (evt.clientX - rect.left) * (canvas.width / rect.width) / zoom,
      y: (evt.clientY - rect.top) * (canvas.height / rect.height) / zoom
    };
  }

  function allItems() {
    return state.vehicles.concat(state.objects, state.canvasItems);
  }

  function nextLabel(type) {
    var normalized = normalizeObjectType(type);
    if (['sedan', 'suv', 'pickup', 'patrol', 'truck', 'motorcycle', 'vehicle'].indexOf(type) !== -1 || inferKind(normalized) === 'vehicle') {
      return 'V' + (allItems().filter(function (i) { return i.kind === 'vehicle'; }).length + 1);
    }
    if (normalized === 'pedestrian' || normalized === 'officer') return 'P' + (allItems().filter(function (i) { return i.kind === 'person'; }).length + 1);
    if (normalized === 'impact') return 'POI';
    if (normalized === 'arrow') return 'DOT';
    if (normalized === 'skid') return 'SKID';
    return 'O' + (allItems().filter(function (i) { return i.kind === 'object'; }).length + 1);
  }

  function drawRoadBase() {
    ctx.save();
    ctx.setTransform(zoom, 0, 0, zoom, 0, 0);
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

    ctx.fillStyle = '#747b84';
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

  function renderObjects() {
    objectLayer.innerHTML = '';
    var scaleX = objectLayer.clientWidth / canvas.width;
    var scaleY = objectLayer.clientHeight / canvas.height;
    allItems().forEach(function (item) {
      var node = document.createElement('div');
      node.className = 'recon-svg-object' + (item === selectedItem ? ' is-selected' : '');
      node.dataset.clientId = item.clientId;
      node.style.width = (item.width * scaleX) + 'px';
      node.style.height = (item.height * scaleY) + 'px';
      node.style.left = ((item.x - item.width / 2) * scaleX) + 'px';
      node.style.top = ((item.y - item.height / 2) * scaleY) + 'px';
      node.style.transform = 'rotate(' + (item.rotation || 0) + 'deg)';
      node.title = (item.label || item.assetType) + (item.notes ? ': ' + item.notes : '');

      var img = document.createElement('img');
      img.src = ASSETS[item.assetType] || ASSETS.cone;
      img.alt = item.label || item.assetType;
      node.appendChild(img);

      var label = document.createElement('span');
      label.className = 'recon-svg-label';
      label.textContent = item.label || '';
      node.appendChild(label);

      var rotate = document.createElement('button');
      rotate.className = 'recon-rotate-handle';
      rotate.type = 'button';
      rotate.textContent = '↻';
      rotate.setAttribute('aria-label', 'Rotate ' + (item.label || item.assetType));
      node.appendChild(rotate);

      objectLayer.appendChild(node);
    });
  }

  function redraw() {
    drawRoadBase();
    renderObjects();
  }

  function showVehicleModal(point) {
    pendingInsertPoint = point;
    if (modal) modal.hidden = false;
  }

  function hideVehicleModal() {
    if (modal) modal.hidden = true;
  }

  function addAsset(assetType, point) {
    pushHistory();
    var size = SIZES[assetType] || [64, 48];
    var kind = inferKind(assetType);
    var item = normalizeItem({
      clientId: 'asset-' + Date.now() + '-' + Math.random().toString(36).slice(2),
      x: snap(point.x),
      y: snap(point.y),
      width: size[0],
      height: size[1],
      rotation: 0
    }, {
      kind: kind,
      assetType: assetType,
      label: nextLabel(assetType)
    });
    if (kind === 'vehicle') state.canvasItems.push(item);
    else state.canvasItems.push(item);
    selectedItem = item;
    redraw();
  }

  function addMeasurement(point) {
    pushHistory();
    state.measurements.push({
      label: 'M' + (state.measurements.length + 1),
      value: 'field measure',
      units: state.units,
      startX: snap(point.x - 45),
      startY: snap(point.y),
      endX: snap(point.x + 45),
      endY: snap(point.y)
    });
    redraw();
  }

  function addText(point) {
    pushHistory();
    var note = window.prompt('Diagram note', 'Note');
    if (note === null) return;
    var item = normalizeItem({
      clientId: 'asset-' + Date.now(),
      x: snap(point.x),
      y: snap(point.y),
      width: 160,
      height: 44,
      rotation: 0,
      label: note.trim() || 'Note',
      notes: note.trim() || ''
    }, { kind: 'object', assetType: 'building', label: note.trim() || 'Note' });
    state.canvasItems.push(item);
    selectedItem = item;
    redraw();
  }

  function handleToolInsert(tool, point) {
    if (tool === 'vehicle') return showVehicleModal(point);
    if (tool === 'measure') return addMeasurement(point);
    if (tool === 'text') return addText(point);
    if (tool === 'clear-all') {
      if (window.confirm('Clear unsaved diagram objects and measurements from this view?')) {
        pushHistory();
        state.canvasItems = [];
        state.measurements = [];
        selectedItem = null;
        redraw();
      }
      return;
    }
    var map = {
      pedestrian: 'pedestrian',
      officer: 'officer',
      'stop-sign': 'stop-sign',
      'traffic-light': 'traffic-light',
      cone: 'cone',
      barrier: 'barrier',
      building: 'building',
      tree: 'tree',
      arrow: 'arrow',
      skid: 'skid',
      impact: 'impact'
    };
    addAsset(map[tool] || 'cone', point);
  }

  objectLayer.addEventListener('pointerdown', function (evt) {
    var objectNode = evt.target.closest('.recon-svg-object');
    if (!objectNode) {
      selectedItem = null;
      redraw();
      return;
    }
    var item = allItems().filter(function (candidate) {
      return candidate.clientId === objectNode.dataset.clientId;
    })[0];
    if (!item) return;
    selectedItem = item;
    var point = getPointer(evt);
    var isRotate = evt.target.closest('.recon-rotate-handle');
    dragState = {
      item: item,
      mode: isRotate ? 'rotate' : 'move',
      offsetX: point.x - item.x,
      offsetY: point.y - item.y,
      startRotation: item.rotation || 0
    };
    objectLayer.setPointerCapture(evt.pointerId);
    evt.preventDefault();
    redraw();
  });

  objectLayer.addEventListener('pointermove', function (evt) {
    if (!dragState) return;
    var point = getPointer(evt);
    var item = dragState.item;
    if (dragState.mode === 'rotate') {
      var angle = Math.atan2(point.y - item.y, point.x - item.x) * 180 / Math.PI;
      item.rotation = Math.round(angle);
    } else {
      item.x = snap(point.x - dragState.offsetX);
      item.y = snap(point.y - dragState.offsetY);
    }
    redraw();
  });

  objectLayer.addEventListener('pointerup', function () {
    if (dragState) pushHistory();
    dragState = null;
  });

  objectLayer.addEventListener('dblclick', function () {
    if (!selectedItem) return;
    var label = window.prompt('Diagram label', selectedItem.label || '');
    if (label !== null) selectedItem.label = label.trim() || selectedItem.label;
    var notes = window.prompt('Optional notes', selectedItem.notes || '');
    if (notes !== null) selectedItem.notes = notes.trim();
    redraw();
  });

  stage.addEventListener('pointerdown', function (evt) {
    if (evt.target.closest('.recon-svg-object')) return;
    var point = getPointer(evt);
    if (selectedTool !== 'select') {
      handleToolInsert(selectedTool, point);
    } else {
      selectedItem = null;
      redraw();
    }
  });

  toolButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      setTool(button.getAttribute('data-tool'));
      if (selectedTool === 'clear-all') handleToolInsert('clear-all', { x: 0, y: 0 });
    });
  });

  modalAssets.forEach(function (button) {
    button.addEventListener('click', function () {
      addAsset(button.dataset.assetType, pendingInsertPoint || { x: 260, y: 220 });
      hideVehicleModal();
      setTool('select');
    });
  });

  if (modalClose) modalClose.addEventListener('click', hideVehicleModal);
  if (modal) {
    modal.addEventListener('click', function (evt) {
      if (evt.target === modal) hideVehicleModal();
    });
  }

  if (unitsSelect) {
    unitsSelect.addEventListener('change', function () {
      state.units = unitsSelect.value;
      redraw();
    });
  }

  if (zoomSelect) {
    zoomSelect.addEventListener('change', function () {
      zoom = parseFloat(zoomSelect.value) || 1;
      canvas.style.width = (980 * zoom) + 'px';
      objectLayer.style.width = canvas.style.width;
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
      selectedItem = null;
      redraw();
    });
  }

  function serializableState() {
    return {
      vehicles: state.vehicles,
      objects: state.objects,
      measurements: state.measurements,
      canvasItems: state.canvasItems,
      units: state.units
    };
  }

  if (saveButton) {
    saveButton.addEventListener('click', function () {
      saveButton.disabled = true;
      saveButton.textContent = 'Saving...';
      fetch(root.getAttribute('data-save-url'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(serializableState())
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

  function roadSvg() {
    return '' +
      '<rect width="980" height="580" fill="#fff"/>' +
      '<rect x="0" y="215" width="980" height="150" fill="#747b84"/><rect x="420" y="0" width="170" height="580" fill="#747b84"/>' +
      '<rect x="0" y="238" width="980" height="104" fill="#5f666f"/><rect x="445" y="0" width="120" height="580" fill="#5f666f"/>' +
      '<path d="M0 290H980M505 0V580" stroke="#f3c94a" stroke-width="3" stroke-dasharray="26 18"/>' +
      '<path d="M430 198v20M448 198v20M466 198v20M484 198v20M502 198v20M520 198v20M538 198v20M556 198v20M430 362v20M448 362v20M466 362v20M484 362v20M502 362v20M520 362v20M538 362v20M556 362v20" stroke="#fff" stroke-width="5"/>' +
      '<path d="M395 224h25M395 242h25M395 260h25M395 278h25M395 296h25M395 314h25M395 332h25M395 350h25M590 224h25M590 242h25M590 260h25M590 278h25M590 296h25M590 314h25M590 332h25M590 350h25" stroke="#fff" stroke-width="5"/>' +
      '<text x="928" y="58" font-family="Arial" font-size="14" font-weight="700" fill="#1f2937">N</text>' +
      '<path d="M932 94V66l-8 14M932 66l8 14" stroke="#1f2937" stroke-width="2" fill="none"/>';
  }

  function escapeXml(value) {
    return String(value || '').replace(/[<>&"']/g, function (ch) {
      return ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' })[ch];
    });
  }

  function svgToGroup(svgText) {
    var inner = svgText.replace(/^[\s\S]*?<svg[^>]*>/i, '').replace(/<\/svg>\s*$/i, '');
    return inner;
  }

  function fetchSvg(assetType) {
    var path = ASSETS[assetType] || ASSETS.cone;
    if (svgCache[path]) return Promise.resolve(svgCache[path]);
    return fetch(path).then(function (response) {
      if (!response.ok) throw new Error('asset failed');
      return response.text();
    }).then(function (text) {
      svgCache[path] = text;
      return text;
    });
  }

  function exportPng() {
    var items = allItems();
    Promise.all(items.map(function (item) { return fetchSvg(item.assetType); })).then(function (svgTexts) {
      var objectSvg = items.map(function (item, index) {
        var content = svgToGroup(svgTexts[index]);
        var x = item.x - item.width / 2;
        var y = item.y - item.height / 2;
        return '<g transform="translate(' + x + ' ' + y + ') rotate(' + (item.rotation || 0) + ' ' + (item.width / 2) + ' ' + (item.height / 2) + ') scale(' + (item.width / 120) + ' ' + (item.height / 60) + ')">' + content + '</g>' +
          '<text x="' + item.x + '" y="' + (item.y - item.height / 2 - 8) + '" text-anchor="middle" font-family="Arial" font-size="13" font-weight="800" fill="#0a2440">' + escapeXml(item.label) + '</text>';
      }).join('');
      var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 580" width="1960" height="1160">' + roadSvg() + objectSvg + '</svg>';
      var blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
      var url = URL.createObjectURL(blob);
      var image = new Image();
      image.onload = function () {
        var exportCanvas = document.createElement('canvas');
        exportCanvas.width = 1960;
        exportCanvas.height = 1160;
        var exportCtx = exportCanvas.getContext('2d');
        exportCtx.fillStyle = '#fff';
        exportCtx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
        exportCtx.drawImage(image, 0, 0, exportCanvas.width, exportCanvas.height);
        var link = document.createElement('a');
        link.download = 'accident-reconstruction-diagram.png';
        link.href = exportCanvas.toDataURL('image/png');
        link.click();
        URL.revokeObjectURL(url);
      };
      image.src = url;
    }).catch(function () {
      window.alert('Unable to export SVG assets right now. The diagram remains saved on screen.');
    });
  }

  if (exportPngButton) exportPngButton.addEventListener('click', exportPng);
  window.addEventListener('resize', redraw);
  setTool('select');
  redraw();
}());
