import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from '../App.vue';
import { getDepartments, processTicket, routeTicket } from '../api/tickets';
import { DEMO_TEMPLATE, DEMO_TICKETS } from '../demo';
import type { Department } from '../types/ticket';

vi.mock('../api/tickets', () => ({
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
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(getDepartments).mockResolvedValue(departments);
    vi.mocked(routeTicket).mockResolvedValue(routingResponse);
    vi.mocked(processTicket).mockResolvedValue(processingResponse);
  });

  it('loads departments and a complete fictional demo example', async () => {
    const wrapper = mount(App);
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
    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.get('#ticket-text').attributes('maxlength')).toBe('4000');

    await route(wrapper);
    await wrapper.get('#confirm-department').trigger('click');

    expect(wrapper.get('#description-template').attributes('maxlength')).toBe('2000');
  });

  it('requires confirmation before showing description generation', async () => {
    const wrapper = mount(App);
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
    const wrapper = mount(App);
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
    const wrapper = mount(App);
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
    const wrapper = mount(App);
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
    const wrapper = mount(App);
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
