import type {
  Department,
  TicketProcessingRequest,
  TicketProcessingResponse,
  TicketRoutingRequest,
  TicketRoutingResponse,
} from '../types/ticket';

const API_BASE_URL = '/api';

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`API request failed: HTTP ${status}`);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function readResponse<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status);
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
