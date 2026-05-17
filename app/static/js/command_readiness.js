/* MCPD Command Readiness Stabilization Layer
   Improves demo stability, mobile spacing, dashboard consistency, and map usability. */
(function () {
  'use strict';

  var MAP_IDS = ['mcpd-dashboard-map', 'mcpd-fs-map', 'mcpd-mobile-map'];
  var BASE_SAFE_BOUNDS = [[31.535, -84.125], [31.615, -84.010]];

  function patchLeaflet(L) {
    if (!L || L.__mcpdCommandReadyPatched) return L;
    L.__mcpdCommandReadyPatched = true;
    var originalMap = L.map;
    L.map = function (element, options) {
      var el = typeof element === 'string' ? document.getElementById(element) : element;
      var id = el && el.id ? el.id : '';
      var isMcpdMap = MAP_IDS.indexOf(id) !== -1 || (el && el.classList && (
        el.classList.contains('mcpd-map-canvas-wrap') ||
        el.classList.contains('mcpd-mobile-map-canvas') ||
        el.classList.contains('mcpd-map-fullscreen-canvas')
      ));
      var patchedOptions = Object.assign({}, options || {});
      if (isMcpdMap) {
        patchedOptions.maxBounds = BASE_SAFE_BOUNDS;
        patchedOptions.maxBoundsViscosity = 0.15;
        patchedOptions.dragging = true;
        patchedOptions.touchZoom = true;
        patchedOptions.doubleClickZoom = true;
        patchedOptions.boxZoom = true;
        patchedOptions.keyboard = true;
        patchedOptions.scrollWheelZoom = id === 'mcpd-fs-map';
      }
      var map = originalMap.call(this, element, patchedOptions);
      if (isMcpdMap) {
        setTimeout(function () {
          try {
            map.setMaxBounds(BASE_SAFE_BOUNDS);
            map.options.maxBoundsViscosity = 0.15;
            map.dragging && map.dragging.enable();
            map.touchZoom && map.touchZoom.enable();
            map.doubleClickZoom && map.doubleClickZoom.enable();
            map.boxZoom && map.boxZoom.enable();
            map.keyboard && map.keyboard.enable();
            if (id === 'mcpd-fs-map' && map.scrollWheelZoom) map.scrollWheelZoom.enable();
            map.invalidateSize();
          } catch (err) {
            console.warn('MCPD map stabilization skipped:', err);
          }
        }, 120);
      }
      return map;
    };
    return L;
  }

  if (window.L) {
    patchLeaflet(window.L);
  } else {
    var pendingLeaflet;
    try {
      Object.defineProperty(window, 'L', {
        configurable: true,
        get: function () { return pendingLeaflet; },
        set: function (value) {
          pendingLeaflet = patchLeaflet(value);
          try {
            Object.defineProperty(window, 'L', { configurable: true, writable: true, value: pendingLeaflet });
          } catch (err) {
            window.L = pendingLeaflet;
          }
        }
      });
    } catch (err) {}
  }

  function stabilizeLayout() {
    document.documentElement.style.setProperty('--mobile-dock-height', '92px');
    document.querySelectorAll('.mcpd-dashboard, .mcpd-command-main, .mobile-shell, .mcpd-mobile-app, .demo-main, .command-center').forEach(function (node) {
      node.classList.add('mcpd-command-ready-surface');
    });
    document.querySelectorAll('main, .mcpd-dashboard, .mobile-shell, .mcpd-command-main, .command-center').forEach(function (node) {
      if (!node.getAttribute('id')) node.setAttribute('id', 'main-content');
    });
    document.querySelectorAll('.mcpd-map-canvas-wrap, .mcpd-mobile-map-canvas, .mcpd-map-fullscreen-canvas').forEach(function (node) {
      node.classList.add('mcpd-map-command-ready');
      if (!node.getAttribute('tabindex')) node.setAttribute('tabindex', '0');
    });
    document.querySelectorAll('.mcpd-action-card, .mcpd-panel, .demo-panel, .demo-stat-card, .demo-launch-card, .command-panel, .command-metric').forEach(function (card) {
      card.classList.add('mcpd-command-ready-card');
    });
  }

  function installMutationStabilizer() {
    if (!('MutationObserver' in window)) return;
    var scheduled = false;
    var observer = new MutationObserver(function () {
      if (scheduled) return;
      scheduled = true;
      window.requestAnimationFrame(function () {
        scheduled = false;
        stabilizeLayout();
      });
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  document.addEventListener('DOMContentLoaded', function () {
    stabilizeLayout();
    installMutationStabilizer();
    if (window.L) patchLeaflet(window.L);
  });
}());
