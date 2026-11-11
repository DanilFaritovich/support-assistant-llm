import { flushPromises } from '@vue/test-utils';
import { afterEach, expect, it, vi } from 'vitest';
import { createMemoryHistory } from 'vue-router';

import { createApplication } from '../app';
import { demoWorkspace } from './fixtures/workspace';
import { render } from '../entry-server';

vi.mock('../api/tickets', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/tickets')>()),
  getDepartments: vi.fn().mockResolvedValue([]),
}));

vi.mock('../api/workspace', () => ({
  getWorkspace: vi.fn().mockImplementation(async () => demoWorkspace()),
}));

afterEach(() => {
  document.body.innerHTML = '';
  vi.restoreAllMocks();
});

it('hydrates prerendered Russian content without replacing it or losing interactivity', async () => {
  const { html } = await render('ru');
  document.body.innerHTML = `<div id="app" data-prerendered>${html}</div>`;
  const heading = document.querySelector('h1');
  expect(heading?.textContent).toBe('Обработка IT-заявок');
  const warnings = vi.spyOn(console, 'warn');
  const errors = vi.spyOn(console, 'error');
  const { app, router } = createApplication(createMemoryHistory());
  try {
    await router.push('/ru/');
    await router.isReady();
    app.mount('#app');
    await flushPromises();
    expect(document.querySelector('h1')).toBe(heading);
    document.querySelector<HTMLAnchorElement>('a[lang="en"]')?.click();
    await flushPromises();
    expect(document.querySelector('h1')?.textContent).toBe('IT ticket processing');
    expect(router.currentRoute.value.path).toBe('/en/');
    expect(warnings).not.toHaveBeenCalled();
    expect(errors).not.toHaveBeenCalled();
  } finally {
    app.unmount();
  }
});
