export type MobileFormFieldType = 'text' | 'textarea' | 'number' | 'date' | 'checkbox' | 'select' | 'signature' | 'initial';

export type MobileFormFieldSchema = {
  key: string;
  label: string;
  type: MobileFormFieldType;
  required?: boolean;
  conditionalGroup?: string;
};

export type MobileFormSectionSchema = {
  title: string;
  fields: MobileFormFieldSchema[];
};
