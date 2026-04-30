export type VoiceInputControlState = {
  supported: boolean;
  active: boolean;
};

export const defaultVoiceInputControlState: VoiceInputControlState = {
  supported: false,
  active: false,
};
