export interface Department {
  id: number;
  name: string;
  description: string | null;
}

export interface TicketRoutingRequest {
  ticket_text: string;
}

export interface TicketRoutingResponse {
  title: string;
  department_id: number;
  department_name: string;
  reasoning: string;
}

export interface TicketProcessingRequest {
  ticket_text: string;
  department_id: number;
  template: string;
}

export interface TicketProcessingResponse {
  description: string;
}
