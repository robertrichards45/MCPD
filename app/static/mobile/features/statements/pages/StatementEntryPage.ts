import type { MobileStatement } from '../types';

export type StatementEntryPageModel = {
  statement: MobileStatement;
};

export function StatementEntryPage(model: StatementEntryPageModel): string {
  return `Statement entry: ${model.statement.formTitle}`;
}

