import html
import json
import os
import shutil
import zipfile

from .vehicle_inspection_overlay import calibrated_overlay_fields, calibrated_signature_boxes


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'generated', 'vehicle_inspections'))
TEMPLATE_SOURCE_DIR = r'C:\Users\rober\Desktop\inspection sheets'


def inspection_template_directory():
    return TEMPLATE_SOURCE_DIR


def list_template_images():
    if not os.path.isdir(TEMPLATE_SOURCE_DIR):
        return []
    items = []
    for entry in os.listdir(TEMPLATE_SOURCE_DIR):
        lower = entry.lower()
        if lower.endswith(('.jpg', '.jpeg', '.png')):
            items.append(entry)
    return sorted(items)


def template_image_abspath(filename):
    safe_name = os.path.basename(filename or '')
    if not safe_name or safe_name != (filename or ''):
        return ''
    return os.path.join(TEMPLATE_SOURCE_DIR, safe_name)


def _export_template_directory(day_directory):
    return os.path.join(day_directory, 'source_templates')


def copy_template_images(day_directory):
    template_names = list_template_images()
    if not template_names:
        return []
    export_dir = _export_template_directory(day_directory)
    os.makedirs(export_dir, exist_ok=True)
    copied = []
    for name in template_names:
        source_path = template_image_abspath(name)
        if not source_path or not os.path.isfile(source_path):
            continue
        destination_path = os.path.join(export_dir, name)
        if not os.path.isfile(destination_path):
            shutil.copy2(source_path, destination_path)
        copied.append(name)
    return copied


def write_calibration_map(day_directory, calibration_map):
    path = os.path.join(day_directory, 'vehicle_inspection_calibration_map.json')
    serializable = {}
    for key, value in (calibration_map or {}).items():
        serializable[key] = {
            'page_index': int(value.get('page_index', 0) or 0),
            'global_x_offset': int(value.get('global_x_offset', 0) or 0),
            'global_y_offset': int(value.get('global_y_offset', 0) or 0),
            'global_scale': float(value.get('global_scale', 1.0) or 1.0),
        }
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(
            {
                'source_template_directory': TEMPLATE_SOURCE_DIR,
                'templates': serializable,
            },
            handle,
            indent=2,
        )
    return path


def write_export_manifest(day_directory, log_date, inspections, generated_files):
    path = os.path.join(day_directory, f'vehicle-inspections-{log_date}-manifest.json')
    rows = []
    for inspection, file_path in zip(inspections, generated_files):
        rows.append(
            {
                'inspection_id': inspection.id,
                'inspection_date': str(inspection.inspection_date or ''),
                'vehicle_number': inspection.vehicle_number or '',
                'status': inspection.status or '',
                'created_by': inspection.created_by,
                'updated_by': inspection.updated_by,
                'export_file': os.path.basename(file_path),
                'officer_signed': bool(inspection.officer_signature),
                'sgt_signed': bool(inspection.sgt_signature),
                'watch_commander_signed': bool(inspection.watch_commander_signature),
            }
        )
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(
            {
                'log_date': log_date,
                'count': len(rows),
                'exports': rows,
            },
            handle,
            indent=2,
        )
    return path


def _single_json_payload(inspection, condition_map, template_name, calibration_map):
    active_calibration = calibration_map.get(template_name, {}) if template_name else {}
    overlay_fields = calibrated_overlay_fields(inspection, condition_map, active_calibration) if template_name else []
    overlay_signatures = calibrated_signature_boxes(inspection, active_calibration) if template_name else []
    return {
        'inspection': {
            'id': inspection.id,
            'inspection_date': str(inspection.inspection_date or ''),
            'vehicle_number': inspection.vehicle_number or '',
            'mileage': inspection.mileage or '',
            'fuel_level': inspection.fuel_level or '',
            'remarks': inspection.remarks or '',
            'status': inspection.status or '',
            'correction_reason': inspection.correction_reason or '',
            'officer_signed': bool(inspection.officer_signature),
            'sgt_signed': bool(inspection.sgt_signature),
            'watch_commander_signed': bool(inspection.watch_commander_signature),
        },
        'conditions': condition_map or {},
        'template_overlay': {
            'template_name': template_name,
            'calibration': active_calibration,
            'fields': overlay_fields,
            'signatures': [
                {
                    'key': item.get('key'),
                    'label': item.get('label'),
                    'left': item.get('left'),
                    'top': item.get('top'),
                    'width': item.get('width'),
                    'height': item.get('height'),
                    'signed': bool(item.get('image')),
                }
                for item in overlay_signatures
            ],
        },
    }


def write_single_json_summary(day_directory, inspection, condition_map, template_name, calibration_map):
    path = os.path.join(day_directory, f'vehicle-inspection-{inspection.inspection_date}-{inspection.id}.json')
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(
            _single_json_payload(inspection, condition_map, template_name, calibration_map or {}),
            handle,
            indent=2,
        )
    return path


def write_day_json_summary(day_directory, log_date, inspections, condition_maps, template_name, calibration_map):
    items = []
    for inspection in inspections:
        items.append(
            _single_json_payload(
                inspection,
                condition_maps.get(inspection.id, {}),
                template_name,
                calibration_map or {},
            )
        )
    path = os.path.join(day_directory, f'vehicle-inspections-{log_date}.json')
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(
            {
                'log_date': log_date,
                'count': len(items),
                'items': items,
            },
            handle,
            indent=2,
        )
    return path


def build_single_export_bundle(inspection, condition_map, printed_at, template_names=None, calibration_map=None):
    directory = ensure_day_export_directory(inspection.inspection_date)
    effective_templates = template_names or copy_template_images(directory)
    effective_calibration = calibration_map or {}
    template_name = effective_templates[0] if effective_templates else None
    calibration_path = write_calibration_map(directory, effective_calibration)
    export_path = write_inspection_export(
        inspection,
        condition_map,
        printed_at,
        template_names=effective_templates,
        calibration_map=effective_calibration,
    )
    json_path = write_single_json_summary(
        directory,
        inspection,
        condition_map,
        template_name,
        effective_calibration,
    )
    manifest_path = write_export_manifest(
        directory,
        str(inspection.inspection_date or ''),
        [inspection],
        [export_path],
    )

    zip_path = os.path.join(
        directory,
        f'vehicle-inspection-{inspection.inspection_date}-{inspection.id}.zip',
    )
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(export_path, arcname=os.path.basename(export_path))
        if os.path.isfile(json_path):
            bundle.write(json_path, arcname=os.path.basename(json_path))
        if os.path.isfile(calibration_path):
            bundle.write(calibration_path, arcname=os.path.basename(calibration_path))
        if os.path.isfile(manifest_path):
            bundle.write(manifest_path, arcname=os.path.basename(manifest_path))
        template_dir = _export_template_directory(directory)
        if os.path.isdir(template_dir):
            for name in effective_templates:
                image_path = os.path.join(template_dir, name)
                if os.path.isfile(image_path):
                    bundle.write(image_path, arcname=os.path.join('source_templates', name))
    return zip_path


def _split_log_date(log_date):
    parts = (log_date or '').split('-')
    if len(parts) != 3:
        return 'unknown', 'Unknown', 'unknown'
    year, month, day = parts
    month_names = {
        '01': 'January',
        '02': 'February',
        '03': 'March',
        '04': 'April',
        '05': 'May',
        '06': 'June',
        '07': 'July',
        '08': 'August',
        '09': 'September',
        '10': 'October',
        '11': 'November',
        '12': 'December',
    }
    return year, month_names.get(month, month), f'{year}-{month}-{day}'


def day_export_directory(log_date):
    year, month_name, day_key = _split_log_date(log_date)
    return os.path.join(BASE_DIR, year, month_name, day_key)


def ensure_day_export_directory(log_date):
    path = day_export_directory(log_date)
    os.makedirs(path, exist_ok=True)
    return path


def _sheet_html(inspection, condition_map, printed_at, template_names=None, calibration_map=None):
    def esc(value):
        return html.escape(str(value or ''))

    template_names = template_names or []
    calibration_map = calibration_map or {}
    overlay_block = ''
    template_block = ''
    if template_names:
        overlay_name = template_names[0]
        overlay_settings = calibration_map.get(overlay_name, {})
        overlay_fields = calibrated_overlay_fields(inspection, condition_map, overlay_settings)
        overlay_signatures = calibrated_signature_boxes(inspection, overlay_settings)
        overlay_field_html = ''.join(
            f'<div style="position:absolute; left:{item["left"]}px; top:{item["top"]}px; font-size:12px; line-height:1.2; color:#b00020; font-weight:600; background:rgba(255,255,255,0.75); padding:1px 3px; max-width:220px; word-break:break-word;">{esc(item["text"])}</div>'
            for item in overlay_fields
        )
        overlay_sig_html = ''.join(
            (
                f'<div style="position:absolute; left:{item["left"]}px; top:{item["top"]}px; width:{item["width"]}px; height:{item["height"]}px;'
                ' border:1px dashed rgba(0,0,0,0.35); background:rgba(255,255,255,0.45); overflow:hidden;">'
                + (
                    f'<img src="data:image/png;base64,{esc(item["image"]).split(",", 1)[1]}" alt="{esc(item["label"])} Signature" style="width:100%; height:100%; object-fit:contain; display:block;" />'
                    if item.get('image') and str(item.get('image')).startswith('data:image')
                    else f'<div style="display:flex; align-items:center; justify-content:center; width:100%; height:100%; font-size:11px; color:#666; text-align:center; padding:4px; box-sizing:border-box;">{esc(item["label"])}</div>'
                )
                + '</div>'
            )
            for item in overlay_signatures
        )
        x_offset = int(overlay_settings.get('global_x_offset', 0) or 0)
        y_offset = int(overlay_settings.get('global_y_offset', 0) or 0)
        scale = float(overlay_settings.get('global_scale', 1.0) or 1.0)
        overlay_block = f"""
    <div class="label">Overlay Preview (Page 1 Template)</div>
    <div style="position:relative; display:inline-block; max-width:100%; border:1px solid #ddd; background:#fff; overflow:hidden; margin-bottom:12px;">
      <img src="source_templates/{esc(overlay_name)}" alt="{esc(overlay_name)}" style="display:block; width:100%; max-width:720px; height:auto;" />
      {overlay_field_html}
      {overlay_sig_html}
    </div>
    <div style="margin-bottom:12px; font-size:12px; color:#333;">{esc(overlay_name)} | X={x_offset} Y={y_offset} Scale={scale:.2f}</div>
"""

        template_parts = []
        for name in template_names:
            settings = calibration_map.get(name, {})
            x = int(settings.get('global_x_offset', 0) or 0)
            y = int(settings.get('global_y_offset', 0) or 0)
            s = float(settings.get('global_scale', 1.0) or 1.0)
            template_parts.append(
                '<li>'
                f'{esc(name)} | X={x} Y={y} Scale={s:.2f}'
                '</li>'
            )
        template_block = f"""
    <div class="label">Source Inspection Sheets</div>
    <ul>{''.join(template_parts)}</ul>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Vehicle Inspection {esc(inspection.id)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 18px; color: #111; }}
    .sheet {{ border: 2px solid #111; padding: 14px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 18px; margin-bottom: 12px; }}
    .label {{ font-size: 12px; color: #555; text-transform: uppercase; }}
    .value {{ font-size: 16px; border-bottom: 1px solid #999; min-height: 24px; padding-top: 3px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
    th, td {{ border: 1px solid #999; padding: 6px 8px; text-align: left; }}
    .remarks {{ min-height: 70px; border: 1px solid #999; padding: 8px; margin-bottom: 12px; }}
  </style>
</head>
<body>
  <div class="sheet">
    <h2>Patrol Vehicle Inspection</h2>
    <p>Printed: {esc(printed_at)}</p>
{overlay_block}
    <div class="grid">
      <div><div class="label">Date</div><div class="value">{esc(inspection.inspection_date)}</div></div>
      <div><div class="label">Vehicle #</div><div class="value">{esc(inspection.vehicle_number)}</div></div>
      <div><div class="label">Mileage</div><div class="value">{esc(inspection.mileage)}</div></div>
      <div><div class="label">Fuel Level</div><div class="value">{esc(inspection.fuel_level)}</div></div>
    </div>
    <table>
      <thead><tr><th>Item</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td>Lights</td><td>{esc(condition_map.get('lights'))}</td></tr>
        <tr><td>Tires</td><td>{esc(condition_map.get('tires'))}</td></tr>
        <tr><td>Equipment</td><td>{esc(condition_map.get('equipment'))}</td></tr>
        <tr><td>Cleanliness</td><td>{esc(condition_map.get('cleanliness'))}</td></tr>
      </tbody>
    </table>
    <div class="label">Remarks</div>
    <div class="remarks">{esc(inspection.remarks)}</div>
    <table>
      <thead><tr><th>Patrol Officer</th><th>Patrol Sgt</th><th>Watch Commander</th></tr></thead>
      <tbody><tr><td>{'Signed' if inspection.officer_signature else ''}</td><td>{'Signed' if inspection.sgt_signature else ''}</td><td>{'Signed' if inspection.watch_commander_signature else ''}</td></tr></tbody>
    </table>
{template_block}
  </div>
</body>
</html>"""


def write_inspection_export(inspection, condition_map, printed_at, template_names=None, calibration_map=None):
    directory = ensure_day_export_directory(inspection.inspection_date)
    effective_templates = template_names or copy_template_images(directory)
    write_calibration_map(directory, calibration_map or {})
    filename = f'vehicle-inspection-{inspection.inspection_date}-{inspection.id}.html'
    path = os.path.join(directory, filename)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(
            _sheet_html(
                inspection,
                condition_map,
                printed_at,
                template_names=effective_templates,
                calibration_map=calibration_map,
            )
        )
    return path


def build_day_export_zip(log_date, inspections, condition_maps, printed_at, template_names=None, calibration_map=None):
    directory = ensure_day_export_directory(log_date)
    effective_templates = template_names or copy_template_images(directory)
    effective_calibration = calibration_map or {}
    template_name = effective_templates[0] if effective_templates else None
    calibration_path = write_calibration_map(directory, effective_calibration)
    generated_files = []
    for inspection in inspections:
        generated_files.append(
            write_inspection_export(
                inspection,
                condition_maps.get(inspection.id, {}),
                printed_at,
                template_names=effective_templates,
                calibration_map=effective_calibration,
            )
        )
    json_path = write_day_json_summary(
        directory,
        log_date,
        inspections,
        condition_maps,
        template_name,
        effective_calibration,
    )
    manifest_path = write_export_manifest(directory, log_date, inspections, generated_files)

    zip_path = os.path.join(directory, f'vehicle-inspections-{log_date}.zip')
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for file_path in generated_files:
            bundle.write(file_path, arcname=os.path.basename(file_path))
        if os.path.isfile(json_path):
            bundle.write(json_path, arcname=os.path.basename(json_path))
        if os.path.isfile(calibration_path):
            bundle.write(calibration_path, arcname=os.path.basename(calibration_path))
        if os.path.isfile(manifest_path):
            bundle.write(manifest_path, arcname=os.path.basename(manifest_path))
        template_dir = _export_template_directory(directory)
        if os.path.isdir(template_dir):
            for name in effective_templates:
                image_path = os.path.join(template_dir, name)
                if os.path.isfile(image_path):
                    bundle.write(image_path, arcname=os.path.join('source_templates', name))
    return zip_path
