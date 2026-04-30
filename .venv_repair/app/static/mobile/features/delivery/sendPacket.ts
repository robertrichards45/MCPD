import type { IncidentState } from '../../store/useIncidentStore';

export type SendPacketResponse = {
  ok: boolean;
  errors?: Array<{ field: string; message: string }>;
  warnings?: Array<{ field: string; message: string }>;
  recipient?: string;
  ccList?: string[];
  attachmentCount?: number;
  subject?: string;
};

export async function sendPacket(endpoint: string, incident: IncidentState): Promise<SendPacketResponse> {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'same-origin',
    body: JSON.stringify({ incident }),
  });

  const payload = (await response.json()) as SendPacketResponse;
  if (!response.ok) {
    return {
      ok: false,
      errors: payload.errors || [{ field: 'Delivery', message: 'Packet delivery failed.' }],
      warnings: payload.warnings || [],
      recipient: payload.recipient,
      ccList: payload.ccList || [],
    };
  }
  return payload;
}
