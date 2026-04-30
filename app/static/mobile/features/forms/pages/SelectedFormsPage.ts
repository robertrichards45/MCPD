import type { MobileFormRecord } from '../formRegistry';

export type SelectedFormsPageModel = {
  title: string;
  recommendedForms: string[];
  optionalForms: string[];
  selectedForms: string[];
  records: MobileFormRecord[];
};

export function SelectedFormsPage(model: SelectedFormsPageModel): string {
  return `${model.title}: ${model.selectedForms.length} selected / ${model.records.length} catalog records`;
}
