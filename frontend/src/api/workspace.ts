import { ApiError } from './tickets';
import type { WorkspaceData, WorkspaceState } from '../types/workspace';

async function read(response: Response): Promise<WorkspaceState> {
  if (!response.ok) throw new ApiError(response.status);
  return (await response.json()) as WorkspaceState;
}

export async function getWorkspace(): Promise<WorkspaceState> {
  return read(await fetch('/api/workspace', { cache: 'no-store' }));
}

export async function getWorkspaceDefaults(): Promise<WorkspaceState> {
  return read(await fetch('/api/workspace/defaults', { cache: 'no-store' }));
}

export async function saveWorkspace(
  data: WorkspaceData,
  revision: number,
): Promise<WorkspaceState> {
  return read(
    await fetch('/api/workspace', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Workspace-Request': '1' },
      body: JSON.stringify({ data, revision }),
    }),
  );
}

export const MAX_WORKSPACE_BYTES = 15000;

export function parseWorkspaceImport(content: string): WorkspaceData {
  if (new TextEncoder().encode(content).length > 16384)
    throw new Error('invalidImport');
  const data: unknown = JSON.parse(content);
  if (
    typeof data !== 'object' ||
    data === null ||
    !('format_version' in data) ||
    data.format_version !== 1 ||
    !('departments' in data) ||
    !Array.isArray(data.departments) ||
    !('examples' in data) ||
    !Array.isArray(data.examples) ||
    !('templates' in data) ||
    !Array.isArray(data.templates)
  )
    throw new Error('invalidImport');
  // Full field, collection, and cross-reference validation remains server-owned.
  return data as WorkspaceData;
}
