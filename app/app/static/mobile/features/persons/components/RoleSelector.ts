export const PERSON_ROLE_OPTIONS = [
  'Victim',
  'Suspect',
  'Witness',
  'Reporting Party',
  'Subject',
  'Driver',
  'Passenger',
  'Other',
] as const;

export type PersonRole = (typeof PERSON_ROLE_OPTIONS)[number];
