export type IncidentBasics = {
  occurredDate: string;
  occurredTime: string;
  location: string;
  callSource: string;
  summary: string;
};

export type TimelineEntry = {
  id: string;
  label: string;
  timestamp: string;
  notes: string;
};

export type PersonEntry = {
  id: string;
  role: string;
  name: string;
  dob: string;
  ssn: string;
  address: string;
  phone: string;
  idNumber: string;
  state: string;
  descriptors: string;
  source: 'manual' | 'id_scan_future';
};

export type ChecklistEntry = {
  id: string;
  label: string;
  completed: boolean;
};

export type FactEntry = {
  id: string;
  label: string;
  value: string;
};

export type StatementEntry = {
  id: string;
  variant: 'standard' | 'traffic';
  formTitle: string;
  formId: number | null;
  personId: string;
  speaker: string;
  speakerSsn: string;
  officerName: string;
  officerBadge: string;
  location: string;
  statementDate: string;
  statementTime: string;
  statementSubject: string;
  plainLanguage: string;
  formattedDraft: string;
  reviewedDraft: string;
  trafficAnswers: Record<string, string>;
  initialsDataUrl: string;
  signatureDataUrl: string;
  witnessingSignatureDataUrl: string;
  updatedAt: string;
};

export type PacketStatus =
  | 'not_started'
  | 'draft'
  | 'basics_complete'
  | 'forms_reviewed'
  | 'packet_ready'
  | 'sending'
  | 'sent';

export type IncidentState = {
  callType: string | null;
  incidentBasics: IncidentBasics;
  timeline: TimelineEntry[];
  persons: PersonEntry[];
  selectedForms: string[];
  statutes: string[];
  checklist: ChecklistEntry[];
  facts: FactEntry[];
  narrative: string;
  statements: StatementEntry[];
  packetStatus: PacketStatus;
};

export const INCIDENT_STORE_KEY = 'mcpd.mobile.incident.state';

export const defaultIncidentState: IncidentState = {
  callType: null,
  incidentBasics: {
    occurredDate: '',
    occurredTime: '',
    location: '',
    callSource: '',
    summary: '',
  },
  timeline: [],
  persons: [],
  selectedForms: [],
  statutes: [],
  checklist: [],
  facts: [],
  narrative: '',
  statements: [],
  packetStatus: 'not_started',
};

export const useIncidentStore = {
  storageKey: INCIDENT_STORE_KEY,
  getInitialState(): IncidentState {
    return structuredClone(defaultIncidentState);
  },
};
