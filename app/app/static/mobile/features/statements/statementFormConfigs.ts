import type { StatementVariant } from './types';

export type StatementFormConfig = {
  variant: StatementVariant;
  title: string;
  formTitle: string;
  formId: number;
  bodyCapacity: number;
  bodyLineLength: number;
  initialCount: number;
};

export const statementFormConfigs: Record<StatementVariant, StatementFormConfig> = {
  standard: {
    variant: 'standard',
    title: 'Voluntary Statement',
    formTitle: 'OPNAV 5580 2 Voluntary Statement',
    formId: 11,
    bodyCapacity: 37,
    bodyLineLength: 58,
    initialCount: 3,
  },
  traffic: {
    variant: 'traffic',
    title: 'Traffic Voluntary Statement',
    formTitle: 'OPNAV 5580 2 Voluntary Statement Traffic',
    formId: 12,
    bodyCapacity: 69,
    bodyLineLength: 54,
    initialCount: 4,
  },
};

export const trafficStatementQuestions = [
  'Would you please describe the accident?',
  'How fast were you driving when the accident occurred?',
  'Did you wear glasses or corrective lenses?',
  'Did you take any evasive actions to avoid the accident or collision?',
  'Did you experience any dizziness or fatigue while driving?',
  'Do you have any medical conditions that might have contributed to the cause of the accident?',
];

