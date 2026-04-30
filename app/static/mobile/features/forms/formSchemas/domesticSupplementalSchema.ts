import type { MobileFormSectionSchema } from './sharedTypes';

export const domesticSupplementalSectionOrder: MobileFormSectionSchema[] = [
  {
    title: 'Dispatch And Parties',
    fields: [
      { key: 'SupInitial.1', label: "Supervisor's Initial", type: 'initial' },
      { key: 'VicName', label: 'Victim Name', type: 'text' },
      { key: 'SponsorSSN', label: "Sponsor's SSN", type: 'text' },
      { key: 'CCN', label: 'CCN', type: 'text' },
      { key: 'RespTime', label: 'Time Of Response', type: 'text' },
      { key: 'ResponseDate', label: 'Date Of Response', type: 'date' },
      { key: 'Reported', label: 'Initial Incident / Violation Reported', type: 'text' },
    ],
  },
  {
    title: 'Victim Condition And Statements',
    fields: [
      { key: 'SupInitial.2', label: "Supervisor's Initial", type: 'initial' },
      { key: 'Victim', label: 'Victim', type: 'checkbox', conditionalGroup: 'RadioButtonList' },
      { key: 'Suspect', label: 'Suspect', type: 'checkbox', conditionalGroup: 'RadioButtonList' },
      { key: 'Child', label: 'Child In Family', type: 'checkbox', conditionalGroup: 'RadioButtonList' },
      { key: 'Who', label: 'By Whom', type: 'text' },
      { key: 'Describe', label: 'Describe Each Item Checked Above', type: 'textarea' },
      { key: 'Said', label: "Victim's Excited Utterances", type: 'textarea' },
    ],
  },
  {
    title: 'Suspect Condition And Statements',
    fields: [
      { key: 'Angry1', label: 'Angry', type: 'checkbox' },
      { key: 'Alcohol1', label: 'Consumed Alcohol', type: 'checkbox' },
      { key: 'Describe1', label: 'Describe Each Item Checked Above', type: 'textarea' },
      { key: 'Said1', label: "Suspect's Spontaneous Admissions", type: 'textarea' },
    ],
  },
  {
    title: 'Scene, Relationship, And Prior Violence',
    fields: [
      { key: 'FQ', label: 'Family Quarters', type: 'checkbox', conditionalGroup: 'RadioButtonList' },
      { key: 'Where', label: 'Where', type: 'text' },
      { key: 'Details', label: 'Scene Details', type: 'textarea' },
      { key: 'Years', label: 'Years', type: 'text' },
      { key: 'Months', label: 'Months', type: 'text' },
      { key: 'Escalating', label: 'Escalating Violence', type: 'checkbox' },
      { key: 'IssCourt', label: 'Issuing Court', type: 'text' },
    ],
  },
  {
    title: 'Witnesses, Evidence, And Victim Services',
    fields: [
      { key: 'SupInitial.4', label: "Supervisor's Initial", type: 'initial' },
      { key: 'AdultWit', label: 'Adult Witnesses', type: 'checkbox' },
      { key: 'ChildWit', label: 'Child Witnesses', type: 'checkbox' },
      { key: 'Statement', label: 'Statement Taken', type: 'checkbox' },
      { key: 'TakenBy', label: 'Photographs Taken By', type: 'text' },
      { key: 'OtherDesc', label: 'Other Evidence Description', type: 'textarea' },
      { key: 'DVIP', label: 'Domestic Violence Pamphlet', type: 'checkbox' },
      { key: 'VAIC', label: 'Victim Advocate Information Card', type: 'checkbox' },
      { key: 'FVUIC', label: 'Family Violence Unit Card', type: 'checkbox' },
    ],
  },
  {
    title: 'Medical Response And Injury Documentation',
    fields: [
      { key: 'SupInitial.7', label: "Supervisor's Initial", type: 'initial' },
      { key: 'FirstAidBy.1', label: 'Victim First Aid By', type: 'text' },
      { key: 'Facility.1', label: 'Victim Treatment Facility', type: 'text' },
      { key: 'FirstAidBy.2', label: 'Suspect First Aid By', type: 'text' },
      { key: 'Facility.2', label: 'Suspect Treatment Facility', type: 'text' },
      { key: 'SupInitial.9', label: "Supervisor's Final Initial", type: 'initial' },
      { key: 'InjName', label: 'Injured Party Name', type: 'text' },
      { key: 'InjExplain', label: 'Injury Explanation', type: 'textarea' },
      { key: 'InjName1', label: 'Second Injured Party Name', type: 'text' },
      { key: 'InjExplain1', label: 'Second Injury Explanation', type: 'textarea' },
    ],
  },
];
