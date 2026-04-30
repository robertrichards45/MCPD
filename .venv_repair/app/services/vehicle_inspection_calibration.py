import json
import os
import csv

from .vehicle_inspection_files import list_template_images


CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'vehicle_inspection_template_map.json')
)


def _default_config():
    templates = []
    for index, name in enumerate(list_template_images()):
        templates.append(
            {
                'page_index': index,
                'filename': name,
                'global_x_offset': 0,
                'global_y_offset': 0,
                'global_scale': 1.0,
            }
        )
    return {
        'template_id': 'mcpd_vehicle_inspection_v1',
        'templates': templates,
    }


def load_calibration():
    if not os.path.isfile(CONFIG_PATH):
        config = _default_config()
        save_calibration(config)
        return config

    with open(CONFIG_PATH, 'r', encoding='utf-8') as handle:
        config = json.load(handle)

    template_map = {item.get('filename'): item for item in config.get('templates', []) if item.get('filename')}
    for index, name in enumerate(list_template_images()):
        if name not in template_map:
            config.setdefault('templates', []).append(
                {
                    'page_index': index,
                    'filename': name,
                    'global_x_offset': 0,
                    'global_y_offset': 0,
                    'global_scale': 1.0,
                }
            )
    return config


def save_calibration(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as handle:
        json.dump(config, handle, indent=2)


def reset_template_settings(filename):
    return update_template_settings(filename, 0, 0, 1.0)


def reset_all_calibration():
    config = _default_config()
    save_calibration(config)
    return config


def clone_first_page_settings_to_all():
    config = load_calibration()
    templates = config.get('templates', [])
    if not templates:
        return config

    first = None
    for item in templates:
        if item.get('page_index', 0) == 0:
            first = item
            break
    if first is None:
        first = templates[0]

    x_offset = int(first.get('global_x_offset', 0) or 0)
    y_offset = int(first.get('global_y_offset', 0) or 0)
    scale = float(first.get('global_scale', 1.0) or 1.0)

    for item in templates:
        item['global_x_offset'] = x_offset
        item['global_y_offset'] = y_offset
        item['global_scale'] = scale

    save_calibration(config)
    return config


def clone_template_settings_to_all(filename):
    config = load_calibration()
    templates = config.get('templates', [])
    if not templates:
        return False

    source = None
    for item in templates:
        if item.get('filename') == filename:
            source = item
            break
    if source is None:
        return False

    x_offset = int(source.get('global_x_offset', 0) or 0)
    y_offset = int(source.get('global_y_offset', 0) or 0)
    scale = float(source.get('global_scale', 1.0) or 1.0)

    for item in templates:
        item['global_x_offset'] = x_offset
        item['global_y_offset'] = y_offset
        item['global_scale'] = scale

    save_calibration(config)
    return True


def nudge_template_settings(filename, dx=0, dy=0, dscale=0.0):
    config = load_calibration()
    for item in config.get('templates', []):
        if item.get('filename') == filename:
            item['global_x_offset'] = int(item.get('global_x_offset', 0) or 0) + int(dx or 0)
            item['global_y_offset'] = int(item.get('global_y_offset', 0) or 0) + int(dy or 0)
            current_scale = float(item.get('global_scale', 1.0) or 1.0)
            next_scale = round(current_scale + float(dscale or 0.0), 2)
            item['global_scale'] = max(0.1, next_scale)
            save_calibration(config)
            return item
    return None


def reset_template_scale(filename):
    config = load_calibration()
    for item in config.get('templates', []):
        if item.get('filename') == filename:
            item['global_scale'] = 1.0
            save_calibration(config)
            return item
    return None


def reset_template_position(filename):
    config = load_calibration()
    for item in config.get('templates', []):
        if item.get('filename') == filename:
            item['global_x_offset'] = 0
            item['global_y_offset'] = 0
            save_calibration(config)
            return item
    return None


def import_calibration_config(payload):
    if not isinstance(payload, dict):
        return False
    incoming_templates = payload.get('templates')
    if not isinstance(incoming_templates, list):
        return False

    config = load_calibration()
    known = {item.get('filename'): item for item in config.get('templates', []) if item.get('filename')}

    for item in incoming_templates:
        if not isinstance(item, dict):
            continue
        filename = item.get('filename')
        if not filename or filename not in known:
            continue
        target = known[filename]
        target['global_x_offset'] = int(item.get('global_x_offset', 0) or 0)
        target['global_y_offset'] = int(item.get('global_y_offset', 0) or 0)
        target['global_scale'] = float(item.get('global_scale', 1.0) or 1.0)

    save_calibration(config)
    return True


def import_calibration_csv_text(text):
    if not isinstance(text, str):
        return False
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        return False

    config = load_calibration()
    known = {item.get('filename'): item for item in config.get('templates', []) if item.get('filename')}
    seen = set()

    for row in rows:
        filename = (row.get('filename') or '').strip()
        if not filename or filename in seen or filename not in known:
            continue
        target = known[filename]
        try:
            target['global_x_offset'] = int((row.get('global_x_offset') or '0').strip())
        except ValueError:
            target['global_x_offset'] = 0
        try:
            target['global_y_offset'] = int((row.get('global_y_offset') or '0').strip())
        except ValueError:
            target['global_y_offset'] = 0
        try:
            target['global_scale'] = float((row.get('global_scale') or '1.0').strip())
        except ValueError:
            target['global_scale'] = 1.0
        seen.add(filename)

    if not seen:
        return False

    save_calibration(config)
    return True


def update_template_settings(filename, x_offset, y_offset, scale):
    config = load_calibration()
    for item in config.get('templates', []):
        if item.get('filename') == filename:
            item['global_x_offset'] = x_offset
            item['global_y_offset'] = y_offset
            item['global_scale'] = scale
            save_calibration(config)
            return item
    return None


def calibration_by_filename():
    config = load_calibration()
    return {
        item.get('filename'): item
        for item in config.get('templates', [])
        if item.get('filename')
    }
