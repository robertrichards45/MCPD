import copy
from pathlib import Path
import unittest
import yaml

from validate_schema import UniqueKeyLoader, read_yaml, validate


class SchemaValidationTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.schema = read_yaml(root / 'dataverse-schema.yaml')
        self.registry = read_yaml(root / 'dataverse-choices.yaml')

    def test_current_model(self):
        self.assertEqual([], validate(self.schema, self.registry))

    def test_unresolved_types_and_references(self):
        for kind in ['choice', 'multichoice', 'choice[Draft,Closed]', 'choice:Missing', 'multichoice:Missing', 'lookup:Missing']:
            with self.subTest(kind=kind):
                schema = copy.deepcopy(self.schema)
                schema['tables']['SavedWork']['columns']['Status'] = kind
                self.assertTrue(any('SavedWork.Status' in e for e in validate(schema, self.registry)))

    def test_duplicate_yaml_key(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate YAML key'):
            yaml.load('tables:\n  Report: {}\n  Report: {}\n', Loader=UniqueKeyLoader)

    def test_duplicate_choice_value(self):
        self.registry['choices']['Priority'].append('Normal')
        self.assertTrue(any('duplicate choice' in e for e in validate(self.schema, self.registry)))

    def test_fto_lifecycle_cannot_be_silently_removed(self):
        self.registry['choices']['DORStatus'].remove('TraineeAcknowledged')
        self.assertTrue(any('required FTO lifecycle' in e for e in validate(self.schema, self.registry)))

    def test_multiselect_programs_reference_same_program_registry(self):
        self.assertEqual('multichoice:FTOProgramType', self.schema['tables']['TaskBookItem']['columns']['RequiredProgramTypes'])


if __name__ == '__main__':
    unittest.main()
