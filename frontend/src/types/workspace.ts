import type { Department } from './ticket';
import type { Locale } from '../locale';

export interface WorkspaceItem {
  id: string;
  name: string;
  text: string;
  locale: Locale | null;
}

export interface WorkspaceData {
  format_version: 1;
  departments: Department[];
  examples: WorkspaceItem[];
  templates: WorkspaceItem[];
  default_template_id: string | null;
}

export interface WorkspaceState {
  retention_days: number;
  data: WorkspaceData;
  revision: number;
  personalized: boolean;
}
