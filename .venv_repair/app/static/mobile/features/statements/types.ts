export type StatementVariant = 'standard' | 'traffic';

export type MobileStatement = {
  id: string;
  variant: StatementVariant;
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

export type StatementPagePreview = {
  pageNumber: number;
  title: string;
  lines: string[];
  initialField: string;
  signatureField?: string;
  witnessSignatureField?: string;
};

