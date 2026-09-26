from pathlib import Path
import unittest

from validate_schema import read_yaml, validate_data_contracts


class DataContractTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.args = [read_yaml(root / name) for name in (
            'dataverse-schema.yaml', 'module-registry.yaml', 'module-data-map.yaml',
            'table-data-policies.yaml', 'solution-manifest.yaml')]
        self.schema, self.registry, self.mapping, self.policies, self.manifest = self.args

    def check_error(self, text):
        self.assertTrue(any(text in error for error in validate_data_contracts(*self.args)), text)

    def test_current_contracts(self):
        self.assertEqual([], validate_data_contracts(*self.args))

    def test_new_module_requires_mapping(self):
        self.registry['modules'].append({'key': 'new_module'})
        self.check_error('Module mapping: missing new_module')

    def test_duplicate_module_key(self):
        self.registry['modules'].append(self.registry['modules'][0])
        self.check_error('duplicate module keys')

    def test_bad_table_reference(self):
        self.mapping['modules']['fto']['tables'].append('Unknown')
        self.check_error('fto: unknown table Unknown')

    def test_new_table_requires_policy_and_mapping(self):
        self.schema['tables']['NewTable'] = {'ownership': 'user_or_team', 'columns': {}}
        self.check_error('Table policy: missing NewTable')
        self.check_error('unmapped table NewTable')

    def test_ownership_regression(self):
        self.schema['tables']['DOR']['ownership'] = 'organization'
        self.check_error('DOR: schema ownership mismatch')

    def test_unknown_policy_profile(self):
        self.policies['tables']['DOR']['security_profile'] = 'unknown'
        self.policies['tables']['DOR']['retention_profile'] = 'unknown'
        self.check_error('DOR: unknown security profile')
        self.check_error('DOR: unknown retention profile')

    def test_hidden_evaluator_protection_cannot_disappear(self):
        del self.policies['tables']['ScenarioRun']['evaluator_only_columns']
        self.check_error('ScenarioRun: missing evaluator-only protection')

    def test_undefined_protected_column(self):
        self.policies['tables']['ScenarioRun']['evaluator_only_columns'].append('Missing')
        self.check_error('unknown protected column Missing')

    def test_retention_cannot_enable_purge_or_bypass_hold(self):
        self.policies['retention_profiles']['training_record']['automatic_delete'] = True
        self.policies['retention_profiles']['incident_record']['legal_hold_blocks_disposition'] = False
        self.check_error('invalid retention safeguard automatic_delete')
        self.check_error('invalid retention safeguard legal_hold_blocks_disposition')

    def test_storage_environment_must_exist(self):
        self.mapping['external_stores']['evidence_media']['environment_variables'] = ['Missing']
        self.check_error('undefined environment variable Missing')

    def test_storage_requires_real_locator(self):
        self.mapping['external_stores']['evidence_media']['locator_columns'] = ['BodycamMedia.Missing']
        self.check_error('invalid URL locator BodycamMedia.Missing')
        self.check_error('BodycamMedia.StorageUrl: missing storage mapping')

    def test_module_cannot_drop_its_storage_dependency(self):
        self.mapping['modules']['bodycam']['external_stores'].remove('evidence_media')
        self.check_error('bodycam: missing external store evidence_media')

    def test_storage_reference_typo(self):
        self.mapping['modules']['bodycam']['external_stores'].append('missing')
        self.check_error('bodycam: unknown external store missing')


if __name__ == '__main__':
    unittest.main()
