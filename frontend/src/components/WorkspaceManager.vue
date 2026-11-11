<script setup lang="ts">
import { ref, watch } from 'vue';
import { ApiError } from '../api/tickets';
import {
  getWorkspace,
  getWorkspaceDefaults,
  MAX_WORKSPACE_BYTES,
  parseWorkspaceImport,
  saveWorkspace,
} from '../api/workspace';
import { useLocale } from '../locale';
import type { WorkspaceData, WorkspaceState } from '../types/workspace';

const props = defineProps<{ state: WorkspaceState | null; disabled: boolean }>();
const emit = defineEmits<{ saved: [state: WorkspaceState] }>();
const { text } = useLocale();
const draft = ref<WorkspaceData | null>(null);
const revision = ref(0);
const busy = ref(false);
const errorKey = ref('');
const saved = ref(false);
const confirmation = ref<'restore' | 'import' | null>(null);
const importText = ref('');
const downloadUrl = ref('');

function replaceDraft(state: WorkspaceState): void {
  draft.value = JSON.parse(JSON.stringify(state.data)) as WorkspaceData;
  revision.value = state.revision;
  errorKey.value = '';
  confirmation.value = null;
}
watch(
  () => props.state,
  (state) => {
    if (state) replaceDraft(state);
  },
  { immediate: true },
);

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) return 'workspaceConflict';
    if (error.status === 413) return 'largeRequestError';
    if (error.status === 422) return 'validationError';
    if (error.status === 429) return 'quotaError';
    return 'unavailableError';
  }
  if (error instanceof TypeError) return 'networkError';
  return 'unknownError';
}

async function persist(data: WorkspaceData): Promise<void> {
  if (busy.value || props.disabled) return;
  busy.value = true;
  errorKey.value = '';
  saved.value = false;
  try {
    const bytes = new TextEncoder().encode(JSON.stringify(data)).length;
    if (bytes > MAX_WORKSPACE_BYTES) {
      errorKey.value = 'workspaceTooLarge';
      return;
    }
    const state = await saveWorkspace(data, revision.value);
    emit('saved', state);
    replaceDraft(state);
    saved.value = true;
  } catch (error: unknown) {
    errorKey.value = errorMessage(error);
  } finally {
    busy.value = false;
  }
}

async function save(): Promise<void> {
  if (draft.value) await persist(draft.value);
}

async function reload(): Promise<void> {
  if (busy.value || props.disabled) return;
  busy.value = true;
  try {
    const state = await getWorkspace();
    replaceDraft(state);
    emit('saved', state);
  } catch (error: unknown) {
    errorKey.value = errorMessage(error);
  } finally {
    busy.value = false;
    saved.value = false;
  }
}

function addDepartment(): void {
  if (!draft.value) return;
  const id = Math.max(0, ...draft.value.departments.map((item) => item.id)) + 1;
  draft.value.departments.push({ id, name: '', description: '' });
}

function addItem(kind: 'examples' | 'templates'): void {
  draft.value?.[kind].push({
    id: crypto.randomUUID(),
    name: '',
    text: '',
    locale: null,
  });
}

function removeTemplate(id: string): void {
  if (!draft.value) return;
  draft.value.templates = draft.value.templates.filter((item) => item.id !== id);
  if (draft.value.default_template_id === id) draft.value.default_template_id = null;
}

function exportSettings(): void {
  if (!props.state) return;
  if (downloadUrl.value) URL.revokeObjectURL(downloadUrl.value);
  downloadUrl.value = URL.createObjectURL(
    new Blob([JSON.stringify(props.state.data)], { type: 'application/json' }),
  );
  const link = document.createElement('a');
  link.href = downloadUrl.value;
  link.download = 'support-assistant-workspace.json';
  link.click();
  URL.revokeObjectURL(downloadUrl.value);
  downloadUrl.value = '';
}

async function readImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  errorKey.value = '';
  saved.value = false;
  try {
    if (file.size > 16384) throw new Error('invalidImport');
    importText.value = await file.text();
    parseWorkspaceImport(importText.value);
    confirmation.value = 'import';
  } catch {
    errorKey.value = 'invalidImport';
  }
}

async function confirmReplace(): Promise<void> {
  const action = confirmation.value;
  confirmation.value = null;
  if (action === 'import') {
    try {
      await persist(parseWorkspaceImport(importText.value));
    } catch {
      errorKey.value = 'invalidImport';
    }
    importText.value = '';
  } else if (action === 'restore') {
    busy.value = true;
    let defaults: WorkspaceState;
    try {
      defaults = await getWorkspaceDefaults();
    } catch (error: unknown) {
      errorKey.value = errorMessage(error);
      return;
    } finally {
      busy.value = false;
    }
    await persist(defaults.data);
  }
}
</script>

<template>
  <section class="panel workspace-panel" aria-labelledby="workspace-title">
    <h2 id="workspace-title">{{ text.workspaceTitle }}</h2>
    <p>{{ text.workspaceHelp }}</p>
    <p v-if="state" class="muted">
      {{ text.workspaceRetention.replace('{days}', String(state.retention_days)) }}
    </p>
    <p v-if="!state" class="muted">{{ text.loading }}</p>
    <details v-if="draft && state">
      <summary>{{ text.workspaceManage }}</summary>
      <form
        id="workspace-form"
        class="ticket-form"
        @submit.prevent="save"
        @input="saved = false"
      >
        <fieldset :disabled="busy || disabled">
          <legend>
            {{ text.departmentsTitle }} ({{ draft.departments.length }}/20)
          </legend>
          <div
            v-for="(item, index) in draft.departments"
            :key="item.id"
            class="workspace-item"
          >
            <label :for="`department-name-${item.id}`">{{ text.itemName }}</label>
            <input
              :id="`department-name-${item.id}`"
              v-model="item.name"
              required
              maxlength="100"
            />
            <label :for="`department-description-${item.id}`">{{
              text.itemDescription
            }}</label>
            <textarea
              :id="`department-description-${item.id}`"
              v-model="item.description"
              rows="2"
              maxlength="1000"
            />
            <button
              type="button"
              class="text-button"
              :disabled="draft.departments.length <= 1"
              @click="draft.departments.splice(index, 1)"
            >
              {{ text.remove }}
            </button>
          </div>
          <button
            id="add-department"
            type="button"
            class="secondary-button"
            :disabled="draft.departments.length >= 20"
            @click="addDepartment"
          >
            {{ text.addDepartment }}
          </button>
        </fieldset>
        <fieldset
          v-for="kind in ['examples', 'templates'] as const"
          :key="kind"
          :disabled="busy || disabled"
        >
          <legend>
            {{ kind === 'examples' ? text.savedExamples : text.savedTemplates }} ({{
              draft[kind].length
            }}/{{ kind === 'examples' ? 20 : 10 }})
          </legend>
          <div
            v-for="(item, index) in draft[kind]"
            :key="item.id"
            class="workspace-item"
          >
            <label :for="`${kind}-name-${item.id}`">{{ text.itemName }}</label>
            <input
              :id="`${kind}-name-${item.id}`"
              v-model="item.name"
              required
              maxlength="100"
            />
            <label :for="`${kind}-text-${item.id}`">{{
              kind === 'examples' ? text.ticketText : text.template
            }}</label>
            <textarea
              :id="`${kind}-text-${item.id}`"
              v-model="item.text"
              required
              rows="4"
              :maxlength="kind === 'examples' ? 4000 : 2000"
            />
            <label :for="`${kind}-locale-${item.id}`">{{ text.itemLanguage }}</label>
            <select :id="`${kind}-locale-${item.id}`" v-model="item.locale">
              <option :value="null">{{ text.allLanguages }}</option>
              <option value="en">English</option>
              <option value="ru">Русский</option>
            </select>
            <button
              type="button"
              class="text-button"
              :disabled="kind === 'templates' && draft.templates.length <= 1"
              @click="
                kind === 'templates'
                  ? removeTemplate(item.id)
                  : draft.examples.splice(index, 1)
              "
            >
              {{ text.remove }}
            </button>
          </div>
          <button
            :id="`add-${kind}`"
            type="button"
            class="secondary-button"
            :disabled="draft[kind].length >= (kind === 'examples' ? 20 : 10)"
            @click="addItem(kind)"
          >
            {{ kind === 'examples' ? text.addExample : text.addTemplate }}
          </button>
        </fieldset>
        <label for="default-template">{{ text.defaultTemplate }}</label>
        <select
          id="default-template"
          v-model="draft.default_template_id"
          :disabled="busy || disabled"
        >
          <option :value="null">{{ text.localeDefaultTemplate }}</option>
          <option v-for="item in draft.templates" :key="item.id" :value="item.id">
            {{ item.name }}
          </option>
        </select>
        <div class="action-row">
          <button
            id="save-workspace"
            class="primary-button"
            :disabled="busy || disabled"
          >
            {{ busy ? text.saving : text.saveWorkspace }}
          </button>
          <button
            type="button"
            class="text-button"
            :disabled="busy || disabled"
            @click="replaceDraft(state)"
          >
            {{ text.cancel }}
          </button>
        </div>
      </form>
      <div class="workspace-actions">
        <button
          id="export-workspace"
          type="button"
          class="secondary-button"
          :disabled="busy || disabled"
          @click="exportSettings"
        >
          {{ text.exportWorkspace }}
        </button>
        <label for="import-workspace">{{ text.importWorkspace }}</label>
        <input
          id="import-workspace"
          type="file"
          accept="application/json,.json"
          :disabled="busy || disabled"
          @change="readImport"
        />
        <button
          id="restore-workspace"
          type="button"
          class="text-button"
          :disabled="busy || disabled"
          @click="confirmation = 'restore'"
        >
          {{ text.restoreWorkspace }}
        </button>
        <button
          id="reload-workspace"
          type="button"
          class="text-button"
          :disabled="busy || disabled"
          @click="reload"
        >
          {{ text.reloadWorkspace }}
        </button>
      </div>
      <div
        v-if="confirmation"
        class="confirmation-card"
        role="group"
        :aria-label="text.replaceWorkspace"
      >
        <p>{{ text.replaceWorkspace }}</p>
        <button
          id="confirm-workspace-replace"
          class="primary-button"
          type="button"
          :disabled="busy || disabled"
          @click="confirmReplace"
        >
          {{ text.confirm }}
        </button>
        <button type="button" class="text-button" @click="confirmation = null">
          {{ text.cancel }}
        </button>
      </div>
    </details>
    <p v-if="errorKey" class="message error" role="alert">
      {{ text[errorKey as keyof typeof text] }}
    </p>
    <p v-if="saved" class="message" role="status">{{ text.workspaceSaved }}</p>
  </section>
</template>
