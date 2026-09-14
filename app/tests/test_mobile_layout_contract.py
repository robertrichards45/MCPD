from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding='utf-8')


def test_base_loads_mobile_layers_last_and_uses_safe_viewport():
    base = _read('app/templates/base.html')
    assert 'width=device-width, initial-scale=1, viewport-fit=cover' in base
    assert "filename='css/mobile-refresh.css'" in base
    assert "filename='css/mobile-global.css'" in base
    assert base.index("filename='css/mcpd-unified.css'") < base.index("filename='css/mobile-refresh.css'")
    assert base.index("filename='css/mobile-refresh.css'") < base.index("filename='css/mobile-global.css'")
    assert "'mobile-foundation' in (body_class|default(''))" in base


def test_real_phone_view_toggle_reports_current_responsive_mode():
    base = _read('app/templates/base.html')
    assert 'function isResponsiveMobileView()' in base
    assert "matchMedia('(max-width: 1020px)')" in base
    assert "setView(isResponsiveMobileView() ? 'desktop' : 'mobile')" in base
    assert "window.addEventListener('resize', syncViewLabels" in base


def test_mobile_stabilizer_covers_overflow_touch_forms_and_scenario_priority():
    css = _read('app/static/css/mobile-global.css')
    assert '@media (max-width: 767px)' in css
    assert 'font-size: 16px !important' in css
    assert 'overflow-x: auto !important' in css
    assert 'max-height: calc(100dvh - 20px)' in css
    assert 'nav-mobile-open' in css
    assert '.patrol-workspace' in css
    assert '"radio"' in css
    assert '"action"' in css
    assert 'body.force-mobile-view:not(.mobile-foundation)' in css


def test_signature_canvas_coordinates_scale_when_css_resizes_canvas():
    js = _read('app/static/js/app.js')
    assert 'canvas.width / rect.width' in js
    assert 'canvas.height / rect.height' in js
    assert "document.body.classList.toggle('nav-mobile-open', open)" in js
    assert "event.key === 'Escape'" in js
    assert "{ passive: false }" in js


def test_mobile_home_no_longer_loads_installation_map_or_gps_bundle():
    home = _read('app/templates/mobile_home.html')
    assert 'Incident Workspace' in home
    assert 'Continue Incident' in home
    assert 'leaflet.min' not in home.lower()
    assert 'mcpd-mobile-map' not in home
    assert 'Installation Map' not in home
    assert 'navigator.geolocation' not in home


def test_mobile_primary_dock_names_incident_workspace_action():
    dock = _read('app/templates/partials/mobile_tab_bar.html')
    assert 'Open incident workspace' in dock
    assert '<span class="mobile-tab-label">Incident</span>' in dock
