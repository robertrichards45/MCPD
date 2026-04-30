import { INCIDENT_STORE_KEY } from '../../store/useIncidentStore';

export function clearSessionAfterSend(): void {
  window.sessionStorage.removeItem(INCIDENT_STORE_KEY);
}
