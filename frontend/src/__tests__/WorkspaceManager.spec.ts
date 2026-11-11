import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createMemoryHistory } from 'vue-router';
import WorkspaceManager from '../components/WorkspaceManager.vue';
import { createSupportRouter } from '../router';
import { ApiError } from '../api/tickets';
import { getWorkspace, getWorkspaceDefaults, saveWorkspace } from '../api/workspace';
import { demoWorkspace } from './fixtures/workspace';

vi.mock('../api/workspace', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/workspace')>()),
  getWorkspace: vi.fn(),
  getWorkspaceDefaults: vi.fn(),
  saveWorkspace: vi.fn(),
}));

async function editor() {
  const router = createSupportRouter(createMemoryHistory());
  await router.push('/en/');
  await router.isReady();
  const wrapper = mount(WorkspaceManager, {
    props: { state: demoWorkspace(), disabled: false },
    global: { plugins: [router] },
  });
  await wrapper.get('summary').trigger('click');
  return wrapper;
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getWorkspace).mockResolvedValue(demoWorkspace());
  vi.mocked(getWorkspaceDefaults).mockResolvedValue(demoWorkspace());
  vi.mocked(saveWorkspace).mockImplementation(async (data, revision) => ({
    data,
    revision: revision + 1,
    personalized: true,
    retention_days: 90,
  }));
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it('saves departments, examples and a selected default template', async () => {
  const wrapper = await editor();
  await wrapper.get('#department-name-101').setValue('My IT');
  await wrapper.get('#add-examples').trigger('click');
  const names = wrapper.findAll('input[id^="examples-name-"]');
  const texts = wrapper.findAll('textarea[id^="examples-text-"]');
  await names.at(-1)?.setValue('My example');
  await texts.at(-1)?.setValue('A fictional support request');
  await wrapper.get('#default-template').setValue('en-default');
  await wrapper.get('#workspace-form').trigger('submit');
  await flushPromises();
  expect(saveWorkspace).toHaveBeenCalledWith(
    expect.objectContaining({
      departments: expect.arrayContaining([expect.objectContaining({ name: 'My IT' })]),
      examples: expect.arrayContaining([
        expect.objectContaining({ name: 'My example' }),
      ]),
      default_template_id: 'en-default',
    }),
    0,
  );
  expect(wrapper.emitted('saved')).toHaveLength(1);
  expect(wrapper.get('[role="status"]').text()).toBe('Workspace saved.');
});

it('preserves unsaved edits on conflict and reloads only on explicit action', async () => {
  vi.mocked(saveWorkspace).mockRejectedValueOnce(new ApiError(409));
  const wrapper = await editor();
  await wrapper.get('#department-name-101').setValue('Unsaved IT');
  await wrapper.get('#workspace-form').trigger('submit');
  await flushPromises();
  expect(wrapper.get('[role="alert"]').text()).toContain('another tab');
  expect((wrapper.get('#department-name-101').element as HTMLInputElement).value).toBe(
    'Unsaved IT',
  );
  expect(wrapper.emitted('saved')).toBeUndefined();
  await wrapper.get('#reload-workspace').trigger('click');
  await flushPromises();
  expect((wrapper.get('#department-name-101').element as HTMLInputElement).value).toBe(
    'Workplace & Devices',
  );
});

it('restores defaults only after confirmation and retains saved revision', async () => {
  const wrapper = await editor();
  await wrapper.setProps({
    state: { ...demoWorkspace(), revision: 4, personalized: true },
  });
  await wrapper.get('#restore-workspace').trigger('click');
  expect(saveWorkspace).not.toHaveBeenCalled();
  await wrapper.get('#confirm-workspace-replace').trigger('click');
  await flushPromises();
  expect(saveWorkspace).toHaveBeenCalledWith(demoWorkspace().data, 4);
});

it('imports an export only after confirmation and reports invalid files', async () => {
  const wrapper = await editor();
  const input = wrapper.get('#import-workspace');
  const imported = demoWorkspace().data;
  imported.departments[0]!.name = 'Imported IT';
  Object.defineProperty(input.element, 'files', {
    configurable: true,
    value: [{ size: 100, text: async () => JSON.stringify(imported) }],
  });
  await input.trigger('change');
  await flushPromises();
  expect(saveWorkspace).not.toHaveBeenCalled();
  await wrapper.get('#confirm-workspace-replace').trigger('click');
  await flushPromises();
  expect(saveWorkspace).toHaveBeenCalledWith(imported, 0);
  Object.defineProperty(input.element, 'files', {
    configurable: true,
    value: [{ size: 17000, text: async () => '{}' }],
  });
  await input.trigger('change');
  await flushPromises();
  expect(wrapper.get('[role="alert"]').text()).toContain('Unable to read');
});

it('exports saved settings and disables writes during ticket processing', async () => {
  const wrapper = await editor();
  const create = vi.fn().mockReturnValue('blob:export');
  const revoke = vi.fn();
  vi.stubGlobal('URL', { createObjectURL: create, revokeObjectURL: revoke });
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
  await wrapper.get('#department-name-101').setValue('Unsaved');
  await wrapper.get('#export-workspace').trigger('click');
  const blob = create.mock.calls[0]?.[0] as Blob;
  expect(blob.type).toBe('application/json');
  expect(revoke).toHaveBeenCalledWith('blob:export');
  await wrapper.setProps({ disabled: true });
  expect(wrapper.get('#save-workspace').attributes('disabled')).toBeDefined();
});
