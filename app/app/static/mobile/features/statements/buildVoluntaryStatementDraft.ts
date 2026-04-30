import type { MobileStatement } from './types';

export type BuildVoluntaryStatementDraftInput = {
  statement: MobileStatement;
  incidentBasics?: {
    occurredDate?: string;
    occurredTime?: string;
    location?: string;
    summary?: string;
  };
};

export function buildVoluntaryStatementDraft(input: BuildVoluntaryStatementDraftInput): string {
  const statement = input.statement;
  const basics = input.incidentBasics || {};
  const date = statement.statementDate || basics.occurredDate || '[date]';
  const time = statement.statementTime || basics.occurredTime || '[time]';
  const location = statement.location || basics.location || '[location]';
  const subject = statement.statementSubject || basics.summary || 'the incident';
  const year = String(date).includes('-') ? String(date).split('-')[0] : '';
  const officer = statement.officerBadge
    ? `${statement.officerName}, badge ${statement.officerBadge}`
    : (statement.officerName || 'the undersigned officer');

  const lead = [
    `I, ${statement.speaker || 'Unknown Declarant'}${statement.speakerSsn ? `, SSN ${statement.speakerSsn},` : ','} make the following free and voluntary statement to ${officer}, whom I know to be a police officer with the Marine Corps Police Department, MCLB Albany, Georgia.`,
    'I make this statement of my own free will and without any threats or promises extended to me.',
    statement.variant === 'traffic'
      ? `I fully understand that this statement is given concerning my knowledge of a traffic accident that occurred on ${date}${year ? ` in the year ${year}` : ''} at approximately ${time} at ${location}.`
      : `I fully understand that this statement is given concerning my knowledge of ${subject} that occurred on ${date}${year ? ` in the year ${year}` : ''} at approximately ${time} at ${location}.`,
  ].join(' ');

  const body = String(statement.plainLanguage || '')
    .replace(/\r/g, '\n')
    .split(/\n+/)
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => /[.!?]$/.test(entry) ? entry : `${entry}.`)
    .join(' ');

  const trafficQa = statement.variant === 'traffic'
    ? Object.entries(statement.trafficAnswers || {})
        .filter(([, value]) => String(value || '').trim())
        .map(([key, value]) => `${key.toUpperCase()}: ${String(value).trim()}`)
        .join(' ')
    : '';

  return [lead, body, trafficQa].filter(Boolean).join('\n\n').trim();
}

