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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        schema = read_yaml(args.root / 'dataverse-schema.yaml')
        registry = read_yaml(args.root / 'dataverse-choices.yaml')
        errors = validate(schema, registry)
    except (OSError, ValueError, yaml.YAMLError, TypeError, AttributeError) as exc:
        errors = [str(exc)]
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f"PASS: {len(schema['tables'])} tables, {len(registry['choices'])} choice definitions; all choice and lookup references resolve.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
