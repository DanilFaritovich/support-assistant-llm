import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createMemoryHistory } from 'vue-router';

import { Root } from '../app';
import { createSupportRouter } from '../router';
import { ApiError, getDepartments, processTicket, routeTicket } from '../api/tickets';
import { DEMO_TEMPLATES, DEMO_TICKETS_BY_LOCALE } from '../demo';
import { LOCALE_STORAGE_KEY } from '../locale';
import type { Department } from '../types/ticket';

async function mountApp(path = '/') {
  const router = createSupportRouter(createMemoryHistory());
  await router.push(path);
  await router.isReady();
  const wrapper = mount(Root, { global: { plugins: [router] } });
  return { wrapper, router };
}

const DEMO_TEMPLATE = DEMO_TEMPLATES.ru;
const DEMO_TICKETS = DEMO_TICKETS_BY_LOCALE.ru;

vi.mock('../api/tickets', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/tickets')>()),
  getDepartments: vi.fn(),
  routeTicket: vi.fn(),
  processTicket: vi.fn(),
}));

const departments: Department[] = [
  { id: 101, name: 'Workplace & Devices', description: 'Device support.' },
  { id: 202, name: 'Identity & Access', description: 'Sign-in support.' },
];
const ticketText = 'A valid one-time code returns Session expired.';
const routingResponse = {
  title: 'Sign-in session expires',
  department_id: 202,
  department_name: 'Identity & Access',
  reasoning: 'The report describes a sign-in failure.',
};
const processingResponse = { description: 'Summary:\nSign-in session expires.' };

async function route(wrapper: ReturnType<typeof mount>): Promise<void> {
  await wrapper.find('#ticket-text').setValue(ticketText);
  await wrapper.find('#route-form').trigger('submit');
  await flushPromises();
}

describe('App', () => {
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    localStorage.setItem(LOCALE_STORAGE_KEY, 'ru');
    vi.mocked(getDepartments).mockResolvedValue(departments);
    vi.mocked(routeTicket).mockResolvedValue(routingResponse);
    vi.mocked(processTicket).mockResolvedValue(processingResponse);
  });

  it('loads departments and a complete fictional demo example', async () => {
    const { wrapper } = await mountApp();
    await flushPromises();

    await wrapper.find('#demo-ticket').setValue(DEMO_TICKETS[1]?.id);
    await wrapper.get('.demo-toolbar .secondary-button').trigger('click');

    expect(getDepartments).toHaveBeenCalledExactlyOnceWith();
    expect((wrapper.get('#ticket-text').element as HTMLTextAreaElement).value).toBe(
      DEMO_TICKETS[1]?.ticketText,
    );

    await wrapper.get('#route-form').trigger('submit');
    await flushPromises();
    await wrapper.get('#confirm-department').trigger('click');

    expect(
      (wrapper.get('#description-template').element as HTMLTextAreaElement).value,
    ).toBe(DEMO_TEMPLATE);
  });

  it('exposes the backend input limits in the text areas', async () => {
    const { wrapper } = await mountApp();
    await flushPromises();

    expect(wrapper.get('#ticket-text').attributes('maxlength')).toBe('4000');

    await route(wrapper);
    await wrapper.get('#confirm-department').trigger('click');

    expect(wrapper.get('#description-template').attributes('maxlength')).toBe('2000');
  });

  it('requires confirmation before showing description generation', async () => {
    const { wrapper } = await mountApp();
    await flushPromises();
    await route(wrapper);

    expect(wrapper.text()).toContain(routingResponse.department_name);
    expect(wrapper.text()).toContain(routingResponse.reasoning);
    expect(wrapper.find('#draft-form').exists()).toBe(false);

    await wrapper.get('#confirm-department').trigger('click');

    expect(wrapper.find('#draft-form').exists()).toBe(true);
    expect(wrapper.text()).toContain('Итоговый выбор');
  });

  it('generates a description with the confirmed suggested department', async () => {
    const { wrapper } = await mountApp();
    await flushPromises();
    await route(wrapper);
    await wrapper.get('#confirm-department').trigger('click');
    await wrapper.get('#description-template').setValue(DEMO_TEMPLATE);
    await wrapper.get('#draft-form').trigger('submit');
    await flushPromises();

    expect(processTicket).toHaveBeenCalledExactlyOnceWith({
      ticket_text: ticketText,
      department_id: 202,
      template: DEMO_TEMPLATE,
    });
    expect(wrapper.get('#draft-description').text()).toBe(
      processingResponse.description,
    );
  });

  it('changes department locally without another routing request', async () => {
    const { wrapper } = await mountApp();
    await flushPromises();
    await route(wrapper);

    await wrapper.get('#change-department').trigger('click');
    await wrapper.get('#department-select').setValue('101');
    await wrapper.get('#department-form').trigger('submit');
    await wrapper.get('#description-template').setValue(DEMO_TEMPLATE);
    await wrapper.get('#draft-form').trigger('submit');
    await flushPromises();

    expect(routeTicket).toHaveBeenCalledTimes(1);
    expect(processTicket).toHaveBeenCalledWith({
      ticket_text: ticketText,
      department_id: 101,
      template: DEMO_TEMPLATE,
    });
    expect(wrapper.text()).toContain('Workplace & Devices');
  });

  it('clears data and resets a completed workflow', async () => {
    const { wrapper } = await mountApp();
    await flushPromises();
    await route(wrapper);
    await wrapper.get('#confirm-department').trigger('click');
    await wrapper.get('.demo-toolbar .text-button').trigger('click');

    expect((wrapper.get('#ticket-text').element as HTMLTextAreaElement).value).toBe('');
    expect(wrapper.find('#draft-form').exists()).toBe(false);
    expect(wrapper.text()).not.toContain(routingResponse.title);
  });

  it('shows routing and drafting errors without losing recoverable state', async () => {
    vi.mocked(routeTicket).mockRejectedValueOnce(new Error('Free models unavailable.'));
    const { wrapper } = await mountApp();
    await flushPromises();
    await route(wrapper);
    expect(wrapper.get('#route-form [role="alert"]').text()).toContain(
      'Free models unavailable.',
    );

    vi.mocked(routeTicket).mockResolvedValueOnce(routingResponse);
    vi.mocked(processTicket).mockRejectedValueOnce(new Error('Drafting failed.'));
    await route(wrapper);
    await wrapper.get('#confirm-department').trigger('click');
    await wrapper.get('#description-template').setValue(DEMO_TEMPLATE);
    await wrapper.get('#draft-form').trigger('submit');
    await flushPromises();

    expect(wrapper.get('#draft-form [role="alert"]').text()).toContain(
      'Drafting failed.',
    );
    expect(wrapper.text()).toContain('Итоговый выбор');
  });
});

describe('language switching', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    vi.mocked(getDepartments).mockResolvedValue(departments);
  });
  afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('uses browser language and falls back to English for other languages', async () => {
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('ru-RU');
    const { wrapper: russian } = await mountApp();
    expect(russian.get('h1').text()).toBe('Обработка IT-заявок');
    russian.unmount();
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('de-DE');
    const { wrapper: english } = await mountApp();
    expect(english.get('h1').text()).toBe('IT ticket processing');
    expect(document.documentElement.lang).toBe('en');
    english.unmount();
  });

  it('preserves the workflow and custom input, persists the choice and loads localized examples', async () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'ru');
    vi.mocked(routeTicket).mockResolvedValue(routingResponse);
    const { wrapper } = await mountApp();
    await flushPromises();
    await route(wrapper);
    await wrapper.get('#confirm-department').trigger('click');
    await wrapper.get('#description-template').setValue('My custom template');
    await wrapper.get('a[lang="en"]').trigger('click');
    await flushPromises();
    expect(wrapper.get('h1').text()).toBe('IT ticket processing');
    expect(document.title).toContain('IT ticket processing');
    expect(document.documentElement.lang).toBe('en');
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('en');
    expect((wrapper.get('#ticket-text').element as HTMLTextAreaElement).value).toBe(
      ticketText,
    );
    expect(
      (wrapper.get('#description-template').element as HTMLTextAreaElement).value,
    ).toBe('My custom template');
    expect(wrapper.text()).toContain('Final selection');
    expect(wrapper.text()).toContain(routingResponse.reasoning);
    expect(routeTicket).toHaveBeenCalledTimes(1);
    await wrapper.get('.demo-toolbar .secondary-button').trigger('click');
    expect((wrapper.get('#ticket-text').element as HTMLTextAreaElement).value).toBe(
      DEMO_TICKETS_BY_LOCALE.en[0]?.ticketText,
    );
    await flushPromises();
    wrapper.unmount();
    const { wrapper: restored } = await mountApp();
    expect(restored.get('h1').text()).toBe('IT ticket processing');
    restored.unmount();
  });

  it('translates an existing API error when switching languages', async () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'ru');
    vi.mocked(routeTicket).mockRejectedValue(new ApiError(429));
    const { wrapper } = await mountApp();
    await flushPromises();
    await route(wrapper);
    expect(wrapper.get('[role="alert"]').text()).toContain('Слишком много запросов');
    await wrapper.get('a[lang="en"]').trigger('click');
    await flushPromises();
    expect(wrapper.get('[role="alert"]').text()).toContain('Too many requests');
    wrapper.unmount();
  });

  it('uses the URL over saved preferences and keeps the form through history navigation', async () => {
    localStorage.setItem(LOCALE_STORAGE_KEY, 'ru');
    const { wrapper, router } = await mountApp('/en/');
    expect(wrapper.get('h1').text()).toBe('IT ticket processing');
    expect(wrapper.get('a[lang="ru"]').attributes('href')).toBe('/ru/');
    await wrapper.get('#ticket-text').setValue('Keep this draft');
    await wrapper.get('a[lang="ru"]').trigger('click');
    await flushPromises();
    expect(router.currentRoute.value.path).toBe('/ru/');
    expect(
      document.head.querySelector('link[rel="canonical"]')?.getAttribute('href'),
    ).toBe('https://support.danil-miftakhov.dev/ru/');
    router.back();
    await flushPromises();
    expect(wrapper.get('h1').text()).toBe('IT ticket processing');
    expect((wrapper.get('#ticket-text').element as HTMLTextAreaElement).value).toBe(
      'Keep this draft',
    );
    expect(
      document.head.querySelector('link[rel="canonical"]')?.getAttribute('href'),
    ).toBe('https://support.danil-miftakhov.dev/en/');
    wrapper.unmount();
  });

  it('switches languages even when browser storage is disabled', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('disabled');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('disabled');
    });
    const { wrapper } = await mountApp();
    await wrapper.get('a[lang="ru"]').trigger('click');
    await flushPromises();
    expect(wrapper.get('h1').text()).toBe('Обработка IT-заявок');
    wrapper.unmount();
  });
});
