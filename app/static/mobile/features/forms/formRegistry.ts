export type MobileFormSourceKind = 'acroform' | 'xfa' | 'static' | 'missing';

export type MobileFormSectionSummary = {
  title: string;
  fieldCount: number;
  sampleLabels: string[];
};

export type MobileFormRecord = {
  id: number;
  title: string;
  category: string;
  familyKey: string;
  sourceKind: MobileFormSourceKind;
  fieldCount: number;
  checkboxCount: number;
  textCount: number;
  signatureCount: number;
  initialCount: number;
  conditionalGroupCount: number;
  sectionSummaries: MobileFormSectionSummary[];
  mappingNote: string;
  status: string;
  statusLabel: string;
  latestSavedFormId: number | null;
  editUrl: string;
  previewUrl: string;
  downloadUrl: string;
  isReady: boolean;
  previewMode: 'saved' | 'blank';
};

export const legacyFormAliases: Record<string, string> = {
  incidentreport: 'DD FORM 1920 ALCOHOL INCIDENT REPORT',
  witnessstatement: 'OPNAV 5580 2 Voluntary Statement',
  voluntarystatement: 'OPNAV 5580 2 Voluntary Statement',
  useofforcereport: 'NAVMC 11130 Statement of Force Use of Detention',
  evidencepropertyform: 'OPNAV 5580 22Evidence Custody Document',
  evidenceform: 'OPNAV 5580 22Evidence Custody Document',
  propertyform: 'OPNAV 5580 22Evidence Custody Document',
  victimsassistanceworksheet: 'DD Form 2701 VWAP',
  incidentaccidentreport: 'SF 91 MOTOR VEHICLE ACCIDENT CRASH REPORT',
  vehicleimpoundform: 'DD Form 2506Vehicle Impoundment Report',
  fieldsketch: 'TA FIELD SKETCH NEW',
  donvehiclereport: 'OPNAV 5580 12 DON VEHICLE REPORT',
  fieldinterviewcard: 'OPNAV 5580 21Field Interview Card',
  citationnoticedocumentation: 'UNSECURED BUILDING NOTICE',
};

export function normalizeFormLookupKey(value: string): string {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

export function resolveLegacyFormAlias(value: string): string {
  const lookup = normalizeFormLookupKey(value);
  return legacyFormAliases[lookup] || value;
}

export function resolveRegistryRecord(records: MobileFormRecord[], title: string): MobileFormRecord | null {
  const wanted = normalizeFormLookupKey(resolveLegacyFormAlias(title));
  return records.find((record) => normalizeFormLookupKey(record.title) === wanted) || null;
}
