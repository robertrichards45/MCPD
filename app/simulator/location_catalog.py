"""Approved non-sensitive facility and roadway references for synthetic patrol training.

The source material for these building-number/name pairs is the MCPD Officer/FTO
Handbook Security Checklist. Public roadway names are limited to names documented
on public-facing MCLB Albany maps/pages. The repository is public, so this module
purposely contains only ordinary/public-facing or administrative destinations
needed to make training dispatches realistic. It does NOT reproduce the security
checklist, security routes, weapons/ammunition facilities, perimeter
vulnerabilities, or other LES-sensitive entries.

Keep sensitive locations in an agency-private/admin-managed source if they are ever
needed for training. Do not expand this public catalog by copying the full
Security Checklist into source control.
"""

import random


SAFE_TRAINING_FACILITIES = {
    'commissary': 'Bldg. 7501 — Commissary',
    'fitness_center': 'Bldg. 7960 — Fitness Center',
    'credit_union': 'Bldg. 7727 — Credit Union',
    'marine_corps_exchange': 'Bldg. 7500 — Marine Corps Exchange',
    'cdc_annex': 'Bldg. 2200 — Child Development Center Annex',
    'human_resources': 'Bldg. 2151 — Human Resources / BWAS',
    'contracting': 'Bldg. 2100 — Contracting',
    'hq_company': 'Bldg. 2090 — Headquarters Company Office',
    'officers_club': "Bldg. 2081 — Officer's Club",
    'logcom_hq': 'Bldg. 3500 — LOGCOM Headquarters',
    'dla_office': 'Bldg. 4710 — DLA Office',
    'cafeteria': 'Bldg. 3508 — Cafeteria',
    'soi_logistics': 'Bldg. 7260 — SOI East Logistics Detachment Office',
    'mwr': 'Bldg. 7530 — MWR',
    'cdc': 'Bldg. 7600 — Child Development Center',
    'youth_sports': 'Bldg. 7601 — Youth Sports Center',
    'boys_girls_club': "Bldg. 7602 — Boys and Girls Club",
    'ordnance_maintenance': 'Bldg. 7200 — Ordnance Maintenance Company',
    'photo_lab': 'Bldg. 5040 — Photo Lab',
    'base_maintenance': 'Bldg. 1291 — Base Maintenance',
}

# Public roadway names only. These names are documented on public MCLB Albany
# pages/maps and are not intended to represent a security patrol route.
PUBLIC_MCLB_ROADS = (
    'Radford Boulevard',
    'Putnam Boulevard',
    'Goodloe Circle',
    'Wilkinson Road',
    'Weed Street',
    'Johnson Road',
    'Walker Avenue',
)

_PUBLIC_MCLB_ROAD_ALIASES = (
    'radford boulevard', 'radford blvd',
    'putnam boulevard', 'putnam blvd',
    'goodloe circle',
    'wilkinson road', 'wilkinson rd',
    'weed street', 'weed st',
    'johnson road', 'johnson rd',
    'walker avenue', 'walker ave',
)

# Crash locations deliberately use ordinary public roadway references and public
# landmarks. A seed locks the location for the entire synthetic call.
CRASH_LOCATIONS = (
    'Radford Boulevard near Bldg. 3500 — LOGCOM Headquarters',
    'Radford Boulevard at Walker Avenue',
    'Putnam Boulevard near the housing community',
    'Goodloe Circle near Bldg. 10200',
    'Wilkinson Road at Weed Street',
    'Johnson Road',
)

# Scenario-family pools intentionally use only non-sensitive facilities above.
DISORDERLY_LOCATIONS = tuple(SAFE_TRAINING_FACILITIES[key] for key in (
    'commissary', 'fitness_center', 'credit_union', 'marine_corps_exchange',
    'officers_club', 'cafeteria', 'mwr', 'youth_sports', 'boys_girls_club',
))

PROPERTY_DAMAGE_LOCATIONS = tuple(
    f"{SAFE_TRAINING_FACILITIES[key]} parking area"
    for key in ('marine_corps_exchange', 'fitness_center', 'logcom_hq', 'dla_office', 'base_maintenance')
)

RETAIL_LOCATIONS = tuple(SAFE_TRAINING_FACILITIES[key] for key in (
    'marine_corps_exchange', 'commissary',
))

MEDICAL_LOCATIONS = tuple(SAFE_TRAINING_FACILITIES[key] for key in (
    'human_resources', 'contracting', 'hq_company', 'logcom_hq', 'dla_office',
    'soi_logistics', 'mwr', 'base_maintenance',
))

# Traffic/self-initiated scenarios should sound like patrol on the actual
# installation rather than a generic "installation roadway."
TRAFFIC_LOCATIONS = (
    'Radford Boulevard near Bldg. 3500 — LOGCOM Headquarters',
    'Putnam Boulevard',
    'Goodloe Circle',
    'Wilkinson Road',
    'Weed Street',
    'Johnson Road',
)

# The Security Checklist identifies gate/checkpoint entries differently from
# ordinary numbered facilities. Do not fabricate a building number for a gate.
ACCESS_CONTROL_LOCATIONS = (
    'Installation access-control inspection area — gate designation provided by Dispatch',
)


def _clean(value):
    return ' '.join(str(value or '').split()).strip()


def crash_location_for_seed(seed=None):
    """Choose one stable public-road crash location for a synthetic run."""
    try:
        chosen_seed = int(seed)
    except (TypeError, ValueError):
        chosen_seed = 1
    return random.Random(chosen_seed).choice(CRASH_LOCATIONS)


def is_vehicle_crash_dispatch(text):
    low = _clean(text).lower()
    return any(term in low for term in (
        'vehicle crash',
        'motor vehicle crash',
        'traffic crash',
        'vehicle collision',
        'motor vehicle collision',
        'two-vehicle crash',
        'single-vehicle crash',
    ))


def dispatch_has_public_road(text):
    low = _clean(text).lower()
    return any(alias in low for alias in _PUBLIC_MCLB_ROAD_ALIASES)


def enrich_vehicle_crash_dispatch(text, seed=None):
    """Replace a generic installation crash dispatch with a real public road.

    Existing dispatches that already name a known public MCLB roadway are left
    untouched. This helper changes location wording only; it never invents injury,
    traffic, enforcement, or investigative facts.
    """
    clean = _clean(text)
    if not clean or not is_vehicle_crash_dispatch(clean) or dispatch_has_public_road(clean):
        return clean

    location = crash_location_for_seed(seed)
    generic = 'Respond to a vehicle crash aboard the installation.'
    if clean.lower().startswith(generic.lower()):
        remainder = clean[len(generic):].strip()
        replacement = f'Respond to a vehicle crash on {location}, MCLB Albany.'
        return f'{replacement} {remainder}'.strip()

    return f'Location: {location}, MCLB Albany. {clean}'


def facility_values():
    """Return a copy for admin/reference use without exposing mutable globals."""
    return dict(SAFE_TRAINING_FACILITIES)
