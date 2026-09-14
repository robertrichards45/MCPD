from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding='utf-8')


def test_base_loads_mobile_layers_last_and_uses_safe_viewport():
    base = _read('app/templates/base.html')
    assert 'width=device-width, initial-scale=1, viewport-fit=cover' in base
    assert "filename='css/mobile-refresh.css'" in base
    assert "filename='css/mobile-global.css'" in base
    assert "filename='css/mobile-components.css'" in base
    assert "filename='css/mobile-audit.css'" in base
    assert base.index("filename='css/mcpd-unified.css'") < base.index("filename='css/mobile-refresh.css'")
    assert base.index("filename='css/mobile-refresh.css'") < base.index('{% block head %}')
    assert base.index('{% block head %}') < base.index("filename='css/mobile-global.css'")
    assert base.index("filename='css/mobile-global.css'") < base.index("filename='css/mobile-components.css'")
    assert base.index("filename='css/mobile-components.css'") < base.index("filename='css/mobile-audit.css'")
    assert "filename='js/mobile-audit.js'" in base
    assert "'mobile-foundation' in (body_class|default(''))" in base


def test_real_phone_view_toggle_reports_current_responsive_mode():
    base = _read('app/templates/base.html')
    assert 'function isResponsiveMobileView()' in base
    assert "matchMedia('(max-width: 1020px)')" in base
    assert "setView(isResponsiveMobileView() ? 'desktop' : 'mobile')" in base
    assert "window.addEventListener('resize', syncViewLabels" in base
    assert "document.body.classList.contains('mobile-foundation')" in base


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


def test_mobile_component_layer_covers_high_use_workflows():
    css = _read('app/static/css/mobile-components.css')
    for selector in (
        '.mfc-row-2',
        '.cmd-counts-row',
        '.cmd-packet-row',
        '.spr-summary-row',
        '.spr-approval-btns',
        '.bodycam-main-grid',
        '.accident-layout',
        '.fto-actions',
    ):
        assert selector in css
    assert '@media (max-width: 480px)' in css
    assert 'grid-template-columns: minmax(0, 1fr) !important' in css


def test_mobile_audit_layer_handles_header_return_path_and_keyboard_dock():
    css = _read('app/static/css/mobile-audit.css')
    js = _read('app/static/js/mobile-audit.js')
    nav = _read('app/templates/partials/nav.html')

    assert '.mcpd-mobile-home-link' in css
    assert '.mobile-keyboard-open .mobile-tab-bar' in css
    assert '.mcpd-header-search' in css
    assert '@media (max-width: 1020px)' in css
    assert 'data-force-mobile' in nav
    assert 'Mobile Home' in nav

    assert "setStoredView('mobile')" in js
    assert "setStoredView('desktop')" in js
    assert 'mobile-keyboard-open' in js
    assert 'window.visualViewport' in js
    assert "event.target.scrollIntoView" in js


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


def test_mobile_more_keeps_incident_workflow_inside_mobile_portal():
    more = _read('app/templates/mobile_more.html')
    assert "url_for('mobile.incident_start')" in more
    assert "'/reports#reports-new'" not in more
    assert 'Incident Workspace' in more
    assert 'data-force-desktop' in more
    assert "'Desktop Dashboard'" in more


def test_fast_capture_uses_local_calendar_date_not_utc_date():
    fast_capture = _read('app/templates/mobile_fast_capture.html')
    assert 'getFullYear()' in fast_capture
    assert 'getMonth() + 1' in fast_capture
    assert 'getDate()' in fast_capture
    assert 'toISOString().slice(0, 10)' not in fast_capture


def test_fast_capture_merges_and_recovers_existing_incident_drafts():
    fast_capture = _read('app/templates/mobile_fast_capture.html')
    assert 'readExistingState' in fast_capture
    assert 'hasMeaningfulState' in fast_capture
    assert 'loadServerDraftIfNeeded' in fast_capture
    assert "fetch('/mobile/api/incident/draft'" in fast_capture
    assert "method: 'GET'" in fast_capture
    assert "method: 'POST'" in fast_capture
    assert 'mergeFacts' in fast_capture
    assert 'mergeUnique' in fast_capture
    assert 'next.statements' in fast_capture
    assert 'next.formDrafts' in fast_capture
    assert 'scheduleAutosave' in fast_capture
    assert 'CSS.escape' not in fast_capture


def test_mobile_shell_only_references_existing_mobile_runtime_bundle():
    shell = _read('app/templates/mobile_shell.html')
    assert "filename='mobile/incident-core.js'" in shell
    assert (ROOT / 'app/static/mobile/incident-core.js').exists()
    assert 'mobile_incident.js' not in shell
    assert 'data-theme-toggle' in shell
    assert 'internalNavigation' in shell
    assert 'markInternalNavigation' in shell
    assert "target.origin === window.location.origin" in shell
    assert "window.addEventListener('beforeunload'" in shell
