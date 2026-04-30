export type InitialsPadProps = {
  captured: boolean;
};

export function InitialsPad(props: InitialsPadProps): string {
  return `InitialsPad: ${props.captured ? 'captured' : 'pending'}`;
}

