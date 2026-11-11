import { DEMO_TEMPLATES, DEMO_TICKETS_BY_LOCALE } from '../../demo';
import type { WorkspaceState } from '../../types/workspace';

export function demoWorkspace(): WorkspaceState {
  return {
    revision: 0,
    retention_days: 90,
    personalized: false,
    data: {
      format_version: 1,
      departments: [
        { id: 101, name: 'Workplace & Devices', description: 'Device support.' },
        { id: 202, name: 'Identity & Access', description: 'Sign-in support.' },
      ],
      examples: (['en', 'ru'] as const).flatMap((locale) =>
        DEMO_TICKETS_BY_LOCALE[locale].map((item) => ({
          id: `${locale}-${item.id}`,
          name: item.label,
          text: item.ticketText,
          locale,
        })),
      ),
      templates: (['en', 'ru'] as const).map((locale) => ({
        id: `${locale}-default`,
        name: 'Default',
        text: DEMO_TEMPLATES[locale],
        locale,
      })),
      default_template_id: null,
    },
  };
}
