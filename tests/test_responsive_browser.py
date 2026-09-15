"""Run with: python -m pytest -q tests/test_responsive_browser.py.

Requires `pip install playwright` and `python -m playwright install chromium`.
The fixture server always creates a separate temporary SQLite database.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from playwright.sync_api import sync_playwright
from responsive_checks import PAGE_PATHS, GEOMETRY


@pytest.fixture(scope='module')
def portal(tmp_path_factory):
    existing = os.environ.get('MCPD_RESPONSIVE_MANIFEST')
    if existing:
        yield json.loads(Path(existing).read_text())
        return
    folder = tmp_path_factory.mktemp('responsive-portal')
    with (folder / 'server.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('responsive_server.py')), str(folder)], stdout=log, stderr=log)
        try:
            manifest = folder / 'manifest.json'
            deadline = time.monotonic() + 90
            while not manifest.exists():
                assert process.poll() is None, (folder / 'server.log').read_text()
                assert time.monotonic() < deadline, 'Responsive fixture did not start'
                time.sleep(.2)
            yield json.loads(manifest.read_text())
        finally:
            process.terminate()
            process.wait(timeout=15)


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        yield browser
        browser.close()


# These aliases intentionally route to their current replacement. Explicitly
# assert them so a redirect to login cannot masquerade as a successful page test.
ALIASES = {'/reports/new':'/tools/narrative', '/reference':'/officer-handbook',
    '/notifications/inbox':'/dashboard',
    '/performance/submit':'/performance/my-stats',
    '/sentinel/fto-instructor':'/sentinel/fto-center'}


@pytest.mark.parametrize('width', [320, 390, 768, 1020])
def test_all_active_pages_fit_phone_and_tablet(browser, portal, width, tmp_path):
    context = browser.new_context(viewport={'width':width,'height':844})
    context.add_init_script("sessionStorage.setItem('mcpd.mobile.incident.state', JSON.stringify({callType:'domestic-disturbance',incidentBasics:{location:'Synthetic training location'},persons:[{id:'test-person',role:'Witness',name:'Synthetic Witness'}]}));")
    page = context.new_page()
    failures = []
    try:
        for path in PAGE_PATHS + portal['details']:
            # Private credit tools have a separate hard-coded owner identity.
            # Their permission-denied page is tested without weakening access.
            if path in ('/', '/login', '/register'):
                context.clear_cookies()
            else:
                context.add_cookies([portal['complete' if 'scenario-paperwork' in path else 'live']])
            response = page.goto(portal['base'] + path)
            page.wait_for_load_state('networkidle')
            if path == '/private/credit-simulator/':
                assert response.status == 403
                continue
            actual = page.url.removeprefix(portal['base']).split('?')[0]
            expected = ALIASES.get(path, path)
            # Law Lookup intentionally remembers its current search view.
            if path == '/legal' and actual == '/legal/search': expected = actual
            if path == '/officers' and actual == '/profile': expected = actual
            problems = []
            if response.status != 200 or actual != expected:
                problems.append(f'HTTP {response.status}, destination {actual}')
            geometry = page.evaluate(GEOMETRY)
            for key in ('outside', 'clipped', 'oversized') + (('cramped','textZoom') if width < 768 else ()):
                if geometry[key]: problems.append(f'{key}: {geometry[key]}')
            if geometry['scrollWidth'] > geometry['width'] + 2:
                problems.append('document horizontal overflow')
            if path == '/dashboard' and geometry['mainWidth'] < width - 20:
                problems.append('desktop sidebar width still reserved on mobile')
            if path == '/mobile/home' and width < 768:
                menu = page.locator('.mcpd-mobile-menu-link').bounding_box()
                brand = page.locator('.mcpd-mobile-topbar strong').bounding_box()
                if menu['height'] > 50 or brand['height'] > 30:
                    problems.append('mobile header labels wrap vertically')
            if problems:
                failures.append(path + ': ' + '; '.join(problems))
                page.screenshot(path=str(tmp_path / f'failure-{len(failures)}.png'))
        assert not failures, '\n'.join(failures)
    finally:
        context.close()


def test_navigation_dialogs_and_desktop_layout(browser, portal):
    context = browser.new_context(viewport={'width':390,'height':844})
    context.add_cookies([portal['live']])
    page = context.new_page()
    try:
        page.goto(portal['base'] + '/dashboard')
        sidebar = page.locator('[data-nav-menu]')
        assert sidebar.evaluate('(e) => e.inert')
        page.locator('[data-nav-toggle]').click()
        page.locator('[data-nav-close]').wait_for(state='visible')
        assert not sidebar.evaluate('(e) => e.inert')
        assert page.locator('#ai-fab').evaluate('(e) => getComputedStyle(e).visibility') == 'hidden'
        page.locator('[data-nav-close]').click()
        assert sidebar.evaluate('(e) => e.inert')
        page.locator('[data-nav-toggle]').click()
        page.keyboard.press('Escape')
        assert page.locator('[data-nav-toggle]').get_attribute('aria-expanded') == 'false'

        page.locator('#ai-fab').click()
        panel = page.locator('#ai-panel')
        assert panel.is_visible()
        rect = panel.bounding_box()
        assert rect['x'] >= 0 and rect['x'] + rect['width'] <= 390
        assert rect['y'] >= 0 and rect['y'] + rect['height'] <= 844
        page.locator('#ai-close-btn').click()
        assert not panel.is_visible()

        diagram = next(path for path in portal['details'] if '/officer-diagram/' in path)
        page.goto(portal['base'] + diagram)
        page.locator('[data-tool="vehicle"]').click()
        page.locator('[data-recon-stage]').click()
        dialog = page.get_by_role('dialog')
        dialog.wait_for(state='visible')
        box = dialog.bounding_box()
        assert box['x'] >= 0 and box['x'] + box['width'] <= 390
        assert box['y'] >= 0 and box['y'] + box['height'] <= 844
        page.get_by_role('button', name='Sedan', exact=True).click()
        assert not dialog.is_visible()
        page.locator('[data-zoom-select]').select_option('1.25')
        canvas = page.locator('[data-recon-canvas]').bounding_box()
        objects = page.locator('[data-recon-object-layer]').bounding_box()
        assert abs(canvas['width'] - objects['width']) < 2
        assert page.locator('.recon-svg-object').count() == 1

        page.goto(portal['base'] + '/admin/users')
        page.wait_for_load_state('networkidle')
        # The current short fixture table fits by wrapping. Simulate a table
        # with non-shrinkable media/columns to exercise the scroll fallback.
        page.locator('table').evaluate('(e) => { e.style.minWidth = "900px"; }')
        page.set_viewport_size({'width':388,'height':844})
        scrollable = page.locator('.mobile-table-scroll')
        scrollable.first.wait_for(state='visible')
        region = scrollable.first
        region.focus()
        page.keyboard.press('ArrowRight')
        page.wait_for_function('() => document.activeElement.scrollLeft > 0')

        # Simulate phone rotation: primary actions remain usable in a short view.
        page.set_viewport_size({'width':844,'height':390})
        page.goto(portal['base'] + '/sentinel/fto-center/scenario-lab/')
        assert not page.evaluate(GEOMETRY)['outside']

        page.set_viewport_size({'width':1440,'height':900})
        page.goto(portal['base'] + '/dashboard')
        assert not sidebar.evaluate('(e) => e.inert')
        assert not page.locator('[data-nav-toggle]').is_visible()
        assert not page.locator('[data-nav-close]').is_visible()
        assert page.locator('main').bounding_box()['x'] >= 240
        assert len(page.locator('.mcpd-clean-grid').last.evaluate('(e) => getComputedStyle(e).gridTemplateColumns.split(" ")')) == 4
    finally:
        context.close()


def test_patrol_order_and_mobile_keyboard_dock(browser, portal):
    context = browser.new_context(viewport={'width':390,'height':844})
    context.add_init_script("sessionStorage.setItem('mcpd.mobile.incident.state', JSON.stringify({callType:'domestic-disturbance',incidentBasics:{location:'Synthetic training location'}}));")
    context.add_cookies([portal['live']])
    page = context.new_page()
    try:
        page.goto(portal['base'] + '/sentinel/fto-center/scenario-lab/')
        radio = page.locator('.patrol-radio').bounding_box()
        action = page.locator('.patrol-action').bounding_box()
        activity = page.locator('.patrol-activity').bounding_box()
        assert radio['y'] < action['y'] < activity['y']
        page.goto(portal['base'] + '/mobile/incident/basics')
        editor = page.locator('input:not([type=hidden]):not([type=checkbox]):not([type=radio])').first
        editor.focus()
        page.wait_for_function('() => document.body.classList.contains("mobile-keyboard-open")')
        assert not page.evaluate(GEOMETRY)['outside']
    finally:
        context.close()
