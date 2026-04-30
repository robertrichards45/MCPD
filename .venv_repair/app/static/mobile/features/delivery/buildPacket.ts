import type { IncidentState } from '../../store/useIncidentStore';

export type PacketValidationItem = {
  field: string;
  message: string;
};

export type PacketPreview = {
  callType: string | null;
  basics: IncidentState['incidentBasics'];
  narrative: string;
  forms: string[];
  statements: IncidentState['statements'];
  errors: PacketValidationItem[];
  warnings: PacketValidationItem[];
  canSend: boolean;
};

export function buildPacket(state: IncidentState): PacketPreview {
  const errors: PacketValidationItem[] = [];
  const warnings: PacketValidationItem[] = [];
  const narrative = (state.narrative || '').trim();

  if (!state.callType) {
    errors.push({ field: 'Call Type', message: 'Select the incident call type before sending.' });
  }
  if (!state.incidentBasics.occurredDate) {
    errors.push({ field: 'Incident Date', message: 'Incident date is missing.' });
  }
  if (!state.incidentBasics.occurredTime) {
    errors.push({ field: 'Incident Time', message: 'Incident time is missing.' });
  }
  if (!state.incidentBasics.location) {
    errors.push({ field: 'Location', message: 'Incident location is missing.' });
  }
  if (!state.incidentBasics.summary) {
    errors.push({ field: 'Summary', message: 'Incident summary is missing.' });
  }
  if (!narrative) {
    errors.push({ field: 'Narrative', message: 'Narrative review is still blank.' });
  }
  if (!state.selectedForms.length) {
    errors.push({ field: 'Forms', message: 'Select at least one form for the packet.' });
  }

  state.checklist.forEach((item) => {
    if (!item.completed) {
      warnings.push({ field: 'Checklist', message: item.label });
    }
  });

  return {
    callType: state.callType,
    basics: state.incidentBasics,
    narrative,
    forms: state.selectedForms,
    statements: state.statements,
    errors,
    warnings,
    canSend: errors.length === 0,
  };
}
