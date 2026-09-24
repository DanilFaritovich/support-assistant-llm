import type {
  Department,
  TicketProcessingRequest,
  TicketProcessingResponse,
  TicketRoutingRequest,
  TicketRoutingResponse,
} from '../types/ticket';

const API_BASE_URL = '/api';

async function readResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);

    if (
      body !== null &&
      typeof body === 'object' &&
      'detail' in body &&
      typeof body.detail === 'string'
    ) {
      throw new Error(body.detail);
    }

    if (response.status === 422) {
      throw new Error('Проверьте введённые данные.');
    }

    throw new Error(`API request failed: HTTP ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function getDepartments(): Promise<Department[]> {
  const response = await fetch(`${API_BASE_URL}/departments`);

  return readResponse<Department[]>(response);
}

export async function routeTicket(
  payload: TicketRoutingRequest,
): Promise<TicketRoutingResponse> {
  const response = await fetch(`${API_BASE_URL}/tickets/route`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return readResponse<TicketRoutingResponse>(response);
}

export async function processTicket(
  payload: TicketProcessingRequest,
): Promise<TicketProcessingResponse> {
  const response = await fetch(`${API_BASE_URL}/tickets/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return readResponse<TicketProcessingResponse>(response);
}
