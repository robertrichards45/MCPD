import type { MobileStatement, StatementPagePreview } from '../types';

export type SignatureCapturePageModel = {
  statement: MobileStatement;
  pages: StatementPagePreview[];
};

export function SignatureCapturePage(model: SignatureCapturePageModel): string {
  return `Signature capture: ${model.statement.formTitle} / ${model.pages.length} pages`;
}
