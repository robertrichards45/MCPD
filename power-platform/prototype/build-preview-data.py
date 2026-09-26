"""Build preview scope and FTO reference data from project sources."""
import csv
import json
from pathlib import Path
import re
import yaml

root = Path(__file__).resolve().parents[1]
modules = yaml.safe_load((root / 'module-registry.yaml').read_text(encoding='utf-8'))['modules']
sections = {}
section = None
for line in (root / 'FULL_ORIGINAL_PORTAL_INVENTORY.md').read_text(encoding='utf-8').splitlines():
    if line.startswith('### '):
        section = re.sub(r'^\d+\. ', '', line[4:])
        sections[section] = []
    elif line.startswith('#### '):
        section = line[5:]
        sections[section] = []
    elif line.startswith('## '):
        section = None
    elif line.startswith('- ') and section:
        sections[section].append(line[2:])
mapping = {
    'dashboard': 'Dashboard', 'incident_reporting': 'Incident Reporting — Desktop',
    'mobile_reporting': 'Mobile Incident Reporting', 'forms': 'Forms Library & Management',
    'call_type_rules': 'Forms Library & Management', 'policy_search': 'Legal Reference System',
    'orders': 'Orders & Memoranda', 'handbook': 'Reference Materials', 'paperwork_guide': 'Reference Materials',
    'training': 'Training Management', 'qualifications': 'Training Management',
    'bodycam': 'Bodycam Footage Management', 'bolo': 'BOLO System', 'personnel': 'Personnel Management',
    'performance': 'Performance Evaluation', 'accident_reconstruction': 'Accident Reconstruction',
    'armory': 'Armory', 'rfi': 'RFI', 'truck_gate': 'Truck Gate', 'vehicle_inspections': 'Vehicle Inspections',
    'cleo': 'CLEO Structured Reporting', 'stats': 'Statistics & Activity Tracking',
    'announcements': 'Announcements', 'watch_commander': 'Watch Commander Tools',
    'assistant_operations': 'Assistant Operations', 'ai_assistant': 'AI Assistant & Tools',
    'data_exchange': 'Data Export & Import', 'administration': 'Security / Administration / Builder',
    'builder': 'Security / Administration / Builder',
}
sentinel = {
    'report_inspector': ['Automated completeness and consistency cues', 'Approved source and version citations', 'Human review and correction lifecycle'],
    'fto': ['Standard 8-week and accelerated 4-week programs', '31 DOR categories with 1–7 / N-O scale', 'Digital task book', 'Weekly and phase evaluations', 'Remedial training and re-evaluation', 'Trainee acknowledgment and supervisor review'],
    'scenario_lab': ['Dispatch and response', 'Investigation and persistent world state', 'Notifications and evidence', 'End-of-call paperwork', 'FTO review and remediation', 'Hidden evaluator state'],
    'analytics': ['Training readiness', 'Report quality', 'FTO progress', 'Operations and personnel', 'Role-scoped analytics'],
}
for module in modules:
    module['capabilities'] = sentinel[module['key']] if module['key'] in sentinel else sections[mapping[module['key']]]
def csv_rows(name):
    with (root / 'seed' / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
data = {'modules': modules, 'categories': csv_rows('fto-rating-categories.csv'),
        'anchors': csv_rows('fto-rating-anchors.csv'), 'tasks': csv_rows('fto-phase-tasks.csv'),
        'accountCapabilities': sections['Authentication & Account Management']}
output = 'window.SENTINEL_DATA = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n'
(Path(__file__).parent / 'preview-data.js').write_text(output, encoding='utf-8')
print(f"Built {len(modules)} module definitions and {len(data['categories'])} DOR categories.")
