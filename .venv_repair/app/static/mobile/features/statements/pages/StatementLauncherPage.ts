import type { MobileStatement } from '../types';

export type StatementLauncherPageModel = {
  statements: MobileStatement[];
};

export function StatementLauncherPage(model: StatementLauncherPageModel): string {
  return `Statement launcher: ${model.statements.length} statements`;
}

