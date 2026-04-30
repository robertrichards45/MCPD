export type NarrativeFactSection = {
  key: string;
  label: string;
  value: string;
};

export type BuildNarrativeDraftInput = {
  callType?: string | null;
  basics?: {
    occurredDate?: string;
    occurredTime?: string;
    location?: string;
  };
  facts?: NarrativeFactSection[];
};

export function buildNarrativeDraft(input: BuildNarrativeDraftInput): string {
  const facts = Array.isArray(input.facts) ? input.facts : [];
  const factMap = Object.fromEntries(
    facts
      .filter((entry) => entry && entry.key && String(entry.value || '').trim())
      .map((entry) => [entry.key, String(entry.value || '').trim()])
  );

  const lines: string[] = [];
  const date = input.basics?.occurredDate?.trim() || '';
  const time = input.basics?.occurredTime?.trim() || '';
  const location = input.basics?.location?.trim() || '';
  const callType = (input.callType || '').trim();

  const introParts = [
    date ? `On ${date}` : '',
    time ? `at ${time}` : '',
    location ? `at ${location}` : '',
  ].filter(Boolean);

  if (introParts.length || callType) {
    const intro = [introParts.join(' '), callType ? `MCPD responded to a ${callType}.` : 'MCPD responded to the incident.']
      .filter(Boolean)
      .join(' ');
    lines.push(intro.trim());
  }

  const orderedSections = [
    ['what_happened', 'What happened'],
    ['complainant', 'Complainant'],
    ['victim', 'Victim'],
    ['suspect', 'Suspect'],
    ['officer_actions', 'Officer actions'],
    ['disposition', 'Disposition'],
  ];

  orderedSections.forEach(([key, label]) => {
    const value = factMap[key];
    if (!value) return;
    lines.push(`${label}: ${value}`);
  });

  return lines.join('\n\n').trim();
}
