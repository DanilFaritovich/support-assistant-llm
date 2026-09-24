import { afterEach, describe, expect, it, vi } from 'vitest';

import { getDepartments, processTicket, routeTicket } from '../api/tickets';

describe('ticket API client', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('sends routing and processing payloads to the backend API', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            title: 'Title',
            department_id: 2,
            department_name: 'Identity & Access',
            reasoning: 'Reason',
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ description: 'Description' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    await routeTicket({ ticket_text: 'Ticket' });
    await processTicket({ ticket_text: 'Ticket', department_id: 2, template: 'T' });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/tickets/route',
      expect.objectContaining({ method: 'POST', body: '{"ticket_text":"Ticket"}' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/tickets/process',
      expect.objectContaining({
        method: 'POST',
        body: '{"ticket_text":"Ticket","department_id":2,"template":"T"}',
      }),
    );
  });

  it('surfaces API detail messages and fallback HTTP errors', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'OpenRouter unavailable.' }), {
          status: 502,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(new Response('bad gateway', { status: 502 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(getDepartments()).rejects.toThrow('OpenRouter unavailable.');
    await expect(getDepartments()).rejects.toThrow('API request failed: HTTP 502');
  });
});
