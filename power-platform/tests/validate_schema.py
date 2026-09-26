"""Validate the source model, not a deployed Dataverse solution."""
from pathlib import Path
import argparse
import sys

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject silently overwritten YAML definitions."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'Duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def read_yaml(path):
    return yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueKeyLoader)


def validate(schema, registry):
    errors = []
    tables = schema.get('tables', {})
    choices = registry.get('choices', {})
    if not tables or not choices:
        errors.append('Schema tables and choice registry must be nonempty')
    for name, values in choices.items():
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v for v in values):
            errors.append(f'{name}: choice values must be nonempty strings')
        elif len(values) != len(set(values)):
            errors.append(f'{name}: duplicate choice values')
    primitives = {'text', 'multiline', 'yesno', 'date', 'datetime', 'whole', 'decimal', 'currency', 'url'}
    for name, table in tables.items():
        if not table.get('primary_name'):
            errors.append(f'{name}: missing primary_name')
        if table.get('ownership') not in {'organization', 'user_or_team'}:
            errors.append(f'{name}: invalid ownership')
        if not table.get('columns'):
            errors.append(f'{name}: missing columns')
        for column, kind in table.get('columns', {}).items():
            path = f'{name}.{column}'
            if not isinstance(kind, str):
                errors.append(f'{path}: column type must be a string')
            elif kind.startswith(('choice:', 'multichoice:')):
                if kind.split(':', 1)[1] not in choices:
                    errors.append(f'{path}: undefined choice {kind}')
            elif kind.startswith('lookup:'):
                if kind.split(':', 1)[1] not in tables:
                    errors.append(f'{path}: undefined lookup {kind}')
            elif kind not in primitives:
                errors.append(f'{path}: unsupported or unresolved type {kind}')
    for name, expected in {
        'FTOProgramType': ['Standard8Week', 'Accelerated4Week', 'Custom'],
        'FTOPhase': ['I', 'II', 'III', 'IV'],
        'DORStatus': ['Draft', 'SubmittedToTrainee', 'TraineeAcknowledged', 'SubmittedToSupervisor', 'Approved', 'Returned'],
    }.items():
        if choices.get(name) != expected:
            errors.append(f'{name}: required FTO lifecycle values changed')
    return errors


def validate_data_contracts(schema, module_registry, data_map, policies, manifest):
    errors = []
    tables = schema['tables']
    modules = data_map.get('modules', {})
    stores = data_map.get('external_stores', {})
    table_policies = policies.get('tables', {})
    security = policies.get('security_profiles', {})
    retention = policies.get('retention_profiles', {})
    classifications = policies.get('classifications', [])
    environment = {item['name'] for item in manifest['environment_variables']}
    registered = [item['key'] for item in module_registry['modules']]
    if len(registered) != len(set(registered)):
        errors.append('Module registry: duplicate module keys')
    for label, expected, actual in [
        ('Module mapping', set(registered), set(modules)),
        ('Table policy', set(tables), set(table_policies)),
    ]:
        for missing in sorted(expected - actual):
            errors.append(f'{label}: missing {missing}')
        for extra in sorted(actual - expected):
            errors.append(f'{label}: unknown {extra}')

    def names(value, label):
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            errors.append(f'{label}: expected a list of names')
            return []
        if len(value) != len(set(value)):
            errors.append(f'{label}: duplicate names')
        return value

    covered = set()
    used_stores = set()
    for name, module in modules.items():
        sources = names(module.get('tables'), f'{name}.tables')
        if not sources:
            errors.append(f'{name}: no mapped tables')
        for source in sources:
            if source not in tables:
                errors.append(f'{name}: unknown table {source}')
            covered.add(source)
        for store in names(module.get('external_stores'), f'{name}.external_stores'):
            if store not in stores:
                errors.append(f'{name}: unknown external store {store}')
            used_stores.add(store)
    for table in sorted(set(tables) - covered):
        errors.append(f'Module mapping: unmapped table {table}')
    locators = set()
    for name, store in stores.items():
        if name not in used_stores:
            errors.append(f'{name}: unused external store')
        for field in ('provider', 'access_rule', 'retention_rule', 'deployment_gate'):
            if not store.get(field):
                errors.append(f'{name}: missing {field}')
        config = names(store.get('environment_variables'), f'{name}.environment_variables')
        if not config:
            errors.append(f'{name}: missing environment configuration')
        for variable in config:
            if variable not in environment:
                errors.append(f'{name}: undefined environment variable {variable}')
        fields = names(store.get('locator_columns'), f'{name}.locator_columns')
        if not fields:
            errors.append(f'{name}: missing locator columns')
        for field in fields:
            table, _, column = field.partition('.')
            if tables.get(table, {}).get('columns', {}).get(column) != 'url':
                errors.append(f'{name}: invalid URL locator {field}')
            if field in locators:
                errors.append(f'{name}: duplicate storage assignment {field}')
            locators.add(field)
        for module, mapping in modules.items():
            if any(f.split('.')[0] in mapping.get('tables', []) for f in fields):
                if name not in mapping.get('external_stores', []):
                    errors.append(f'{module}: missing external store {name}')
    for table, definition in tables.items():
        for column, kind in definition['columns'].items():
            if kind == 'url' and f'{table}.{column}' not in locators:
                errors.append(f'{table}.{column}: missing storage mapping')
    if policies.get('development_data') != 'synthetic_only':
        errors.append('Data policies: development must use synthetic_only')
    for name, profile in security.items():
        if profile.get('ownership') not in ('organization', 'user_or_team') or not profile.get('access_rule'):
            errors.append(f'{name}: invalid security profile')
    for name, profile in retention.items():
        for field, expected in [('production_schedule_required', True), ('automatic_delete', False), ('legal_hold_blocks_disposition', True)]:
            if profile.get(field) is not expected:
                errors.append(f'{name}: invalid retention safeguard {field}')
        if not profile.get('schedule_key') or not profile.get('disposition'):
            errors.append(f'{name}: incomplete retention policy')
    for name, policy in table_policies.items():
        if policy.get('classification') not in classifications:
            errors.append(f'{name}: unknown classification')
        profile = security.get(policy.get('security_profile'))
        if profile is None:
            errors.append(f'{name}: unknown security profile')
        elif profile['ownership'] != policy.get('ownership'):
            errors.append(f'{name}: security ownership mismatch')
        if policy.get('ownership') != tables.get(name, {}).get('ownership'):
            errors.append(f'{name}: schema ownership mismatch')
        if policy.get('retention_profile') not in retention:
            errors.append(f'{name}: unknown retention profile')
        for column in names(policy.get('evaluator_only_columns', []), f'{name}.evaluator_only_columns'):
            if column not in tables.get(name, {}).get('columns', {}):
                errors.append(f'{name}: unknown protected column {column}')
    # Guard the known sensitive runtime state against accidental policy deletion.
    for name, required in {
        'ScenarioDefinition': {'ScenarioJson'},
        'ScenarioRun': {'WorldStateJson', 'EvaluatorStateJson', 'RunSeed'},
        'ScenarioAction': {'HiddenEvaluatorResultJson', 'StructuredActionJson'},
        'ScenarioEvidence': {'DiscoveryCondition', 'StructuredDataJson'},
        'ScenarioNotification': {'TriggerCondition', 'EvaluatorComments'},
        'CompetencyObservation': {'EvidenceJson', 'DraftRating'},
    }.items():
        if not required.issubset(table_policies.get(name, {}).get('evaluator_only_columns', [])):
            errors.append(f'{name}: missing evaluator-only protection')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        schema = read_yaml(args.root / 'dataverse-schema.yaml')
        registry = read_yaml(args.root / 'dataverse-choices.yaml')
        errors = validate(schema, registry)
        errors += validate_data_contracts(
            schema, read_yaml(args.root / 'module-registry.yaml'),
            read_yaml(args.root / 'module-data-map.yaml'),
            read_yaml(args.root / 'table-data-policies.yaml'),
            read_yaml(args.root / 'solution-manifest.yaml'))
    except (OSError, ValueError, yaml.YAMLError, TypeError, AttributeError, KeyError) as exc:
        errors = [str(exc)]
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f"PASS: {len(schema['tables'])} tables, {len(registry['choices'])} choices; schema, module/storage mappings and table policies resolve.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
