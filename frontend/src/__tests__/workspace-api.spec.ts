import { afterEach, expect, it, vi } from 'vitest';
import { getWorkspace, parseWorkspaceImport, saveWorkspace } from '../api/workspace';
import { demoWorkspace } from './fixtures/workspace';

afterEach(() => vi.unstubAllGlobals());

it('uses same-origin settings endpoints with a CSRF header and revision', async () => {
  const state = demoWorkspace();
  const fetchMock = vi
    .fn()
    .mockImplementation(async () => new Response(JSON.stringify(state)));
  vi.stubGlobal('fetch', fetchMock);
  expect(await getWorkspace()).toEqual(state);
  await saveWorkspace(state.data, 7);
  expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/workspace', { cache: 'no-store' });
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    '/api/workspace',
    expect.objectContaining({
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Workspace-Request': '1' },
      body: JSON.stringify({ data: state.data, revision: 7 }),
    }),
  );
});

it('rejects failed saves without reading internal error details', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response('Internal details', { status: 409 })),
  );
  await expect(saveWorkspace(demoWorkspace().data, 1)).rejects.toMatchObject({
    status: 409,
  });
});

it('accepts versioned exports and rejects invalid, unsupported, or oversized files', () => {
  const data = demoWorkspace().data;
  expect(parseWorkspaceImport(JSON.stringify(data))).toEqual(data);
  for (const content of [
    'not-json',
    '{}',
    JSON.stringify({ ...data, format_version: 2 }),
    ' '.repeat(16385),
  ]) {
    expect(() => parseWorkspaceImport(content)).toThrow();
  }
});
