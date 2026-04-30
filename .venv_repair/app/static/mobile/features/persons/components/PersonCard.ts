export type PersonCardModel = {
  id: string;
  name: string;
  role: string;
  dob: string;
  state: string;
  phone: string;
};

export function PersonCard(person: PersonCardModel): string {
  return `${person.name} (${person.role})`;
}
