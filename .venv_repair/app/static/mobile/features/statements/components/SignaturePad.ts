export type SignaturePadProps = {
  label: string;
  captured: boolean;
};

export function SignaturePad(props: SignaturePadProps): string {
  return `${props.label}: ${props.captured ? 'captured' : 'pending'}`;
}

