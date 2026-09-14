"""Approved non-sensitive facility references for synthetic patrol training.

The source material for these building-number/name pairs is the MCPD Officer/FTO
Handbook Security Checklist.  The repository is public, so this module purposely
contains only ordinary/public-facing or administrative destinations needed to make
training dispatches realistic.  It does NOT reproduce the security checklist,
security routes, weapons/ammunition facilities, perimeter vulnerabilities, or
other LES-sensitive entries.

Keep sensitive locations in an agency-private/admin-managed source if they are ever
needed for training.  Do not expand this public catalog by copying the full
Security Checklist into source control.
"""

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

# These are synthetic roadside descriptions anchored to an approved facility
# number/name rather than a security route or checkpoint location.
TRAFFIC_LOCATIONS = tuple(
    f"installation roadway near {SAFE_TRAINING_FACILITIES[key]}"
    for key in ('marine_corps_exchange', 'fitness_center', 'logcom_hq', 'base_maintenance')
)

# The Security Checklist identifies gate/checkpoint entries differently from
# ordinary numbered facilities.  Do not fabricate a building number for a gate.
ACCESS_CONTROL_LOCATIONS = (
    'Installation access-control inspection area — gate designation provided by Dispatch',
)


def facility_values():
    """Return a copy for admin/reference use without exposing mutable globals."""
    return dict(SAFE_TRAINING_FACILITIES)
