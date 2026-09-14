import os
import re

from ..models import Form


def _text(value):
    return ' '.join(str(value or '').split()).strip()


def _key(value):
    return re.sub(r'[^a-z0-9]+', '', _text(value).lower())


def find_active_form(document_name):
    """Resolve one selected training document to the active real MCPD Form row."""
    target = _key(document_name)
    if not target:
        return None
    try:
        rows = Form.query.filter_by(is_active=True).all()
    except Exception:
        return None

    exact = [row for row in rows if _key(getattr(row, 'title', '')) == target]
    if exact:
        return exact[0]

    # Tolerate punctuation/spacing differences such as OPNAV 5580-2 vs 5580 2,
    # but do not guess between materially different form families.
    close = []
    for row in rows:
        candidate = _key(getattr(row, 'title', ''))
        if not candidate:
            continue
        if target in candidate or candidate in target:
            close.append((abs(len(candidate) - len(target)), row))
    if not close:
        return None
    close.sort(key=lambda item: item[0])
    if len(close) > 1 and close[0][0] == close[1][0]:
        return None
    return close[0][1]


def render_actual_training_pdf(document_name, values):
    """Render a temporary PDF using the portal's actual source form and renderer.

    No SavedForm is created, no operational workflow is invoked, and the returned
    path is temporary. The caller is responsible for deleting the rendered output.
    """
    form = find_active_form(document_name)
    if form is None:
        return None, {'error': 'active_form_not_found'}

    # Lazy import avoids route-registration cycles while deliberately reusing the
    # exact same PDF source/schema rules as the production Forms module.
    from ..routes.forms import _normalize_payload, _pdf_source_for_form, _schema_for_form
    from ..services.forms_pdf_renderer import render_form_pdf

    source_pdf = _pdf_source_for_form(form)
    if not source_pdf or not os.path.exists(source_pdf):
        return None, {'error': 'source_pdf_unavailable', 'form_id': form.id, 'title': form.title}

    schema = _schema_for_form(form)
    payload = _normalize_payload({'values': dict(values or {})}, schema)
    output_path, render_meta = render_form_pdf(source_pdf, schema, payload, blank_mode=False)
    if not output_path or not os.path.exists(output_path):
        return None, {'error': 'render_failed', 'form_id': form.id, 'title': form.title}

    meta = dict(render_meta or {})
    meta.update({
        'form_id': form.id,
        'form_title': form.title,
        'source_pdf': source_pdf,
        'training_only': True,
    })
    return output_path, meta
