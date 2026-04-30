import type { MobileStatement, StatementPagePreview } from '../types';

export type StatementReviewPageModel = {
  statement: MobileStatement;
  pages: StatementPagePreview[];
};

export function StatementReviewPage(model: StatementReviewPageModel): string {
  return `Statement review: ${model.statement.formTitle} / ${model.pages.length} pages`;
}

