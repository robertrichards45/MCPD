export type IdScanLauncherState = {
  enabled: boolean;
  mode: 'manual_only' | 'future_id_scan';
};

export const defaultIdScanLauncherState: IdScanLauncherState = {
  enabled: false,
  mode: 'future_id_scan',
};
