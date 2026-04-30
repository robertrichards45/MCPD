def base_overlay_fields(inspection, condition_map):
    return [
        {
            'key': 'date',
            'text': str(inspection.inspection_date or ''),
            'x': 470,
            'y': 44,
        },
        {
            'key': 'vehicle_number',
            'text': str(inspection.vehicle_number or ''),
            'x': 112,
            'y': 44,
        },
        {
            'key': 'mileage',
            'text': str(inspection.mileage or ''),
            'x': 112,
            'y': 88,
        },
        {
            'key': 'fuel_level',
            'text': str(inspection.fuel_level or ''),
            'x': 470,
            'y': 88,
        },
        {
            'key': 'lights',
            'text': str(condition_map.get('lights', '') or ''),
            'x': 200,
            'y': 210,
        },
        {
            'key': 'tires',
            'text': str(condition_map.get('tires', '') or ''),
            'x': 200,
            'y': 242,
        },
        {
            'key': 'equipment',
            'text': str(condition_map.get('equipment', '') or ''),
            'x': 200,
            'y': 274,
        },
        {
            'key': 'cleanliness',
            'text': str(condition_map.get('cleanliness', '') or ''),
            'x': 200,
            'y': 306,
        },
        {
            'key': 'remarks',
            'text': str(inspection.remarks or ''),
            'x': 112,
            'y': 372,
        },
    ]


def base_overlay_field_layout():
    return [
        {'key': 'date', 'label': 'Date', 'x': 470, 'y': 44},
        {'key': 'vehicle_number', 'label': 'Vehicle #', 'x': 112, 'y': 44},
        {'key': 'mileage', 'label': 'Mileage', 'x': 112, 'y': 88},
        {'key': 'fuel_level', 'label': 'Fuel Level', 'x': 470, 'y': 88},
        {'key': 'lights', 'label': 'Lights', 'x': 200, 'y': 210},
        {'key': 'tires', 'label': 'Tires', 'x': 200, 'y': 242},
        {'key': 'equipment', 'label': 'Equipment', 'x': 200, 'y': 274},
        {'key': 'cleanliness', 'label': 'Cleanliness', 'x': 200, 'y': 306},
        {'key': 'remarks', 'label': 'Remarks', 'x': 112, 'y': 372},
    ]


def calibrated_overlay_fields(inspection, condition_map, calibration=None):
    calibration = calibration or {}
    x_offset = int(calibration.get('global_x_offset', 0) or 0)
    y_offset = int(calibration.get('global_y_offset', 0) or 0)
    scale = float(calibration.get('global_scale', 1.0) or 1.0)
    fields = []
    for item in base_overlay_fields(inspection, condition_map):
        fields.append(
            {
                **item,
                'left': int((item['x'] + x_offset) * scale),
                'top': int((item['y'] + y_offset) * scale),
            }
        )
    return fields


def calibrated_signature_boxes(inspection, calibration=None):
    calibration = calibration or {}
    x_offset = int(calibration.get('global_x_offset', 0) or 0)
    y_offset = int(calibration.get('global_y_offset', 0) or 0)
    scale = float(calibration.get('global_scale', 1.0) or 1.0)

    base_boxes = [
        {
            'key': 'officer_signature',
            'label': 'Patrol Officer',
            'image': inspection.officer_signature,
            'x': 96,
            'y': 615,
            'w': 180,
            'h': 54,
        },
        {
            'key': 'sgt_signature',
            'label': 'Patrol Sgt',
            'image': inspection.sgt_signature,
            'x': 315,
            'y': 615,
            'w': 180,
            'h': 54,
        },
        {
            'key': 'watch_commander_signature',
            'label': 'Watch Commander',
            'image': inspection.watch_commander_signature,
            'x': 534,
            'y': 615,
            'w': 180,
            'h': 54,
        },
    ]

    boxes = []
    for item in base_boxes:
        boxes.append(
            {
                **item,
                'left': int((item['x'] + x_offset) * scale),
                'top': int((item['y'] + y_offset) * scale),
                'width': int(item['w'] * scale),
                'height': int(item['h'] * scale),
            }
        )
    return boxes


def calibrated_signature_layout(calibration=None):
    calibration = calibration or {}
    x_offset = int(calibration.get('global_x_offset', 0) or 0)
    y_offset = int(calibration.get('global_y_offset', 0) or 0)
    scale = float(calibration.get('global_scale', 1.0) or 1.0)

    base_boxes = [
        {'key': 'officer_signature', 'label': 'Officer Sig', 'x': 96, 'y': 615, 'w': 180, 'h': 54},
        {'key': 'sgt_signature', 'label': 'Sgt Sig', 'x': 315, 'y': 615, 'w': 180, 'h': 54},
        {'key': 'watch_commander_signature', 'label': 'WC Sig', 'x': 534, 'y': 615, 'w': 180, 'h': 54},
    ]
    boxes = []
    for item in base_boxes:
        boxes.append(
            {
                **item,
                'left': int((item['x'] + x_offset) * scale),
                'top': int((item['y'] + y_offset) * scale),
                'width': int(item['w'] * scale),
                'height': int(item['h'] * scale),
            }
        )
    return boxes


def calibrated_field_layout(calibration=None):
    calibration = calibration or {}
    x_offset = int(calibration.get('global_x_offset', 0) or 0)
    y_offset = int(calibration.get('global_y_offset', 0) or 0)
    scale = float(calibration.get('global_scale', 1.0) or 1.0)
    fields = []
    for item in base_overlay_field_layout():
        fields.append(
            {
                **item,
                'left': int((item['x'] + x_offset) * scale),
                'top': int((item['y'] + y_offset) * scale),
            }
        )
    return fields
