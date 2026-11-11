<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue';
import { RouterLink } from 'vue-router';

import { ApiError, getDepartments, processTicket, routeTicket } from './api/tickets';
import { getWorkspace } from './api/workspace';
import WorkspaceManager from './components/WorkspaceManager.vue';
import type { WorkspaceState } from './types/workspace';
import { DEMO_TEMPLATES, DEMO_TICKETS_BY_LOCALE } from './demo';
import { useLocale } from './locale';
import type {
  Department,
  TicketProcessingResponse,
  TicketRoutingResponse,
} from './types/ticket';

const { locale, text, rememberLocale } = useLocale();
const workspace = ref<WorkspaceState | null>(null);
const workspaceError = shallowRef<unknown>(null);
const savedTemplates = computed(
  () =>
    workspace.value?.data.templates.filter(
      (item) =>
        item.locale === null ||
        item.locale === locale.value ||
        item.id === workspace.value?.data.default_template_id,
    ) ?? [],
);
const selectedTemplateId = ref('');
const demoTickets = computed(() =>
  workspace.value
    ? workspace.value.data.examples
        .filter((item) => item.locale === null || item.locale === locale.value)
        .map((item) => ({ id: item.id, label: item.name, ticketText: item.text }))
    : DEMO_TICKETS_BY_LOCALE[locale.value],
);
const demoTemplate = computed(() => {
  const data = workspace.value?.data;
  return (
    data?.templates.find((item) => item.id === data.default_template_id)?.text ??
    savedTemplates.value[0]?.text ??
    data?.templates[0]?.text ??
    DEMO_TEMPLATES[locale.value]
  );
});

const ticketText = ref('');
const template = ref(demoTemplate.value);
const selectedDemoId = ref(demoTickets.value[0]?.id ?? '');

const MAX_TICKET_TEXT_LENGTH = 4000;
const MAX_TEMPLATE_LENGTH = 2000;

const departments = ref<Department[]>([]);
const departmentsLoading = ref(false);
const departmentsError = shallowRef<unknown>(null);

const routing = ref(false);
const routingError = shallowRef<unknown>(null);
const routingResult = ref<TicketRoutingResponse | null>(null);

const editingDepartment = ref(false);
const manualDepartmentId = ref<number | null>(null);
const confirmedDepartmentId = ref<number | null>(null);
const departmentSelectionError = shallowRef<unknown>(null);

const processing = ref(false);
const processingError = shallowRef<unknown>(null);
const processingResult = ref<TicketProcessingResponse | null>(null);

const confirmedDepartment = computed(() =>
  departments.value.find((department) => department.id === confirmedDepartmentId.value),
);

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 422) return text.value.validationError;
    if (error.status === 429) return text.value.quotaError;
    if (error.status === 413) return text.value.largeRequestError;
    if (error.status === 404) return text.value.notFoundError;
    if (error.status >= 500) return text.value.unavailableError;
    return `${text.value.apiError} ${error.status}`;
  }
  if (typeof error === 'string' && error in text.value) {
    return text.value[error as keyof typeof text.value];
  }
  if (error instanceof TypeError) return text.value.networkError;
  return error instanceof Error ? error.message : text.value.unknownError;
}

function resetRouting(): void {
  routingResult.value = null;
  confirmedDepartmentId.value = null;
  manualDepartmentId.value = null;
  editingDepartment.value = false;
  processingResult.value = null;
  routingError.value = null;
  departmentSelectionError.value = null;
  processingError.value = null;
}

watch(ticketText, resetRouting);
watch(template, () => {
  processingResult.value = null;
});
watch(demoTickets, (items) => {
  if (!items.some((item) => item.id === selectedDemoId.value))
    selectedDemoId.value = items[0]?.id ?? '';
});
watch(savedTemplates, (items) => {
  if (!items.some((item) => item.id === selectedTemplateId.value))
    selectedTemplateId.value = items[0]?.id ?? '';
});

function applyWorkspace(state: WorkspaceState): void {
  const previousDefault = demoTemplate.value;
  workspace.value = state;
  selectedTemplateId.value =
    state.data.default_template_id ?? savedTemplates.value[0]?.id ?? '';
  if (!template.value || template.value === previousDefault)
    template.value = demoTemplate.value;
  departments.value = state.data.departments;
  resetRouting();
}

async function loadWorkspace(): Promise<void> {
  workspaceError.value = null;
  try {
    applyWorkspace(await getWorkspace());
  } catch (error: unknown) {
    workspaceError.value = error;
  }
}

function loadSavedTemplate(): void {
  const selected = savedTemplates.value.find(
    (item) => item.id === selectedTemplateId.value,
  );
  if (selected) template.value = selected.text;
}

async function loadDepartments(): Promise<void> {
  departmentsLoading.value = true;
  departmentsError.value = null;

  try {
    const loaded = await getDepartments();
    if (JSON.stringify(loaded) !== JSON.stringify(departments.value)) resetRouting();
    departments.value = loaded;
  } catch (error: unknown) {
    departmentsError.value = error;
  } finally {
    departmentsLoading.value = false;
  }
}

function loadDemo(): void {
  const demo = demoTickets.value.find((item) => item.id === selectedDemoId.value);
  if (demo) {
    ticketText.value = demo.ticketText;
    template.value = demoTemplate.value;
  }
}

function clearForm(): void {
  ticketText.value = '';
  template.value = '';
  resetRouting();
}

async function submitRouting(): Promise<void> {
  if (routing.value || processing.value) return;

  resetRouting();
  if (!ticketText.value.trim()) {
    routingError.value = 'enterTicket';
    return;
  }

  routing.value = true;
  try {
    routingResult.value = await routeTicket({ ticket_text: ticketText.value });
    manualDepartmentId.value = routingResult.value.department_id;
  } catch (error: unknown) {
    routingError.value = error;
  } finally {
    routing.value = false;
  }
}

function confirmSuggestedDepartment(): void {
  if (!routingResult.value) return;
  confirmedDepartmentId.value = routingResult.value.department_id;
  editingDepartment.value = false;
  departmentSelectionError.value = null;
  processingResult.value = null;
}

function startDepartmentChange(): void {
  if (!routingResult.value) return;
  manualDepartmentId.value =
    confirmedDepartmentId.value ?? routingResult.value.department_id;
  editingDepartment.value = true;
  confirmedDepartmentId.value = null;
  processingResult.value = null;
  processingError.value = null;
}

function confirmManualDepartment(): void {
  const exists = departments.value.some(
    (department) => department.id === manualDepartmentId.value,
  );
  if (!exists || manualDepartmentId.value === null) {
    departmentSelectionError.value = 'selectDepartment';
    return;
  }

  confirmedDepartmentId.value = manualDepartmentId.value;
  editingDepartment.value = false;
  departmentSelectionError.value = null;
  processingResult.value = null;
}

async function submitDraft(): Promise<void> {
  if (processing.value || routing.value || confirmedDepartmentId.value === null) {
    return;
  }

  processingError.value = null;
  processingResult.value = null;
  if (!ticketText.value.trim() || !template.value.trim()) {
    processingError.value = 'fillFields';
    return;
  }

  processing.value = true;
  try {
    processingResult.value = await processTicket({
      ticket_text: ticketText.value,
      department_id: confirmedDepartmentId.value,
      template: template.value,
    });
  } catch (error: unknown) {
    processingError.value = error;
  } finally {
    processing.value = false;
  }
}

onMounted(() => void loadWorkspace());
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Support Assistant</p>
        <h1>{{ text.title }}</h1>
        <p class="subtitle">
          {{ text.subtitle }}
        </p>
      </div>
      <div class="header-controls">
        <span class="status-label">{{ text.demoVersion }}</span>
        <nav class="language-switch" :aria-label="text.language">
          <RouterLink
            to="/en/"
            lang="en"
            hreflang="en"
            :aria-current="locale === 'en' ? 'page' : undefined"
            @click="rememberLocale('en')"
          >
            English
          </RouterLink>
          <RouterLink
            to="/ru/"
            lang="ru"
            hreflang="ru"
            :aria-current="locale === 'ru' ? 'page' : undefined"
            @click="rememberLocale('ru')"
          >
            Русский
          </RouterLink>
        </nav>
      </div>
    </header>

    <section class="panel about-panel" aria-labelledby="about-title">
      <h2 id="about-title">{{ text.aboutTitle }}</h2>
      <p>{{ text.aboutText }}</p>
      <p>{{ text.privacyNote }}</p>
    </section>

    <main class="layout">
      <section class="panel editor-panel">
        <div class="section-heading">
          <span class="step">01</span>
          <div>
            <h2>{{ text.sourceTicket }}</h2>
            <p>{{ text.sourceHelp }}</p>
          </div>
        </div>

        <div class="demo-toolbar">
          <label for="demo-ticket">{{ text.example }}</label>
          <select
            id="demo-ticket"
            v-model="selectedDemoId"
            :disabled="routing || processing"
          >
            <option v-for="demo in demoTickets" :key="demo.id" :value="demo.id">
              {{ demo.label }}
            </option>
          </select>
          <button
            class="secondary-button"
            type="button"
            :disabled="routing || processing"
            @click="loadDemo"
          >
            {{ text.loadExample }}
          </button>
          <button
            class="text-button"
            type="button"
            :disabled="routing || processing"
            @click="clearForm"
          >
            {{ text.clear }}
          </button>
        </div>

        <form id="route-form" class="ticket-form" @submit.prevent="submitRouting">
          <label for="ticket-text">{{ text.ticketText }}</label>
          <textarea
            id="ticket-text"
            v-model="ticketText"
            rows="9"
            :maxlength="MAX_TICKET_TEXT_LENGTH"
            :placeholder="text.ticketPlaceholder"
            :disabled="routing || processing"
          />
          <p v-if="routingError" class="message error" role="alert">
            {{ getErrorMessage(routingError) }}
          </p>
          <button
            class="primary-button"
            type="submit"
            :disabled="routing || processing || !ticketText.trim()"
          >
            {{ routing ? text.routing : text.route }}
          </button>
        </form>

        <section v-if="routingResult" class="workflow-section" aria-live="polite">
          <div class="section-heading">
            <span class="step">02</span>
            <div>
              <h2>{{ text.routingTitle }}</h2>
              <p>{{ text.routingHelp }}</p>
            </div>
          </div>

          <div class="result-content">
            <div class="result-field">
              <span class="field-label">{{ text.ticketTitle }}</span>
              <h3>{{ routingResult.title }}</h3>
            </div>
            <div class="result-field">
              <span class="field-label">{{ text.suggestedDepartment }}</span>
              <strong>{{ routingResult.department_name }}</strong>
              <span class="muted">ID: {{ routingResult.department_id }}</span>
            </div>
            <div class="result-field">
              <span class="field-label">{{ text.reasoning }}</span>
              <p class="preserve-lines">{{ routingResult.reasoning }}</p>
            </div>
          </div>

          <div
            v-if="!editingDepartment && confirmedDepartmentId === null"
            class="action-row"
          >
            <button
              id="confirm-department"
              class="primary-button"
              type="button"
              @click="confirmSuggestedDepartment"
            >
              {{ text.confirm }}
            </button>
            <button
              id="change-department"
              class="secondary-button"
              type="button"
              :disabled="departmentsLoading || departments.length === 0"
              @click="startDepartmentChange"
            >
              {{ text.change }}
            </button>
          </div>

          <form
            v-if="editingDepartment"
            id="department-form"
            class="ticket-form department-form"
            @submit.prevent="confirmManualDepartment"
          >
            <label for="department-select">{{ text.department }}</label>
            <select
              id="department-select"
              v-model="manualDepartmentId"
              :disabled="processing"
            >
              <option
                v-for="department in departments"
                :key="department.id"
                :value="department.id"
              >
                {{ department.name }}
              </option>
            </select>
            <p v-if="departmentSelectionError" class="message error" role="alert">
              {{ getErrorMessage(departmentSelectionError) }}
            </p>
            <button
              class="primary-button"
              type="submit"
              :disabled="processing || manualDepartmentId === null"
            >
              {{ text.confirmSelection }}
            </button>
          </form>

          <div v-if="confirmedDepartmentId !== null" class="confirmation-card">
            <div>
              <span class="field-label">{{ text.finalSelection }}</span>
              <strong>{{
                confirmedDepartment?.name ??
                `${text.departmentFallback} #${confirmedDepartmentId}`
              }}</strong>
            </div>
            <button
              class="text-button"
              type="button"
              :disabled="processing"
              @click="startDepartmentChange"
            >
              {{ text.change }}
            </button>
          </div>
        </section>

        <section v-if="confirmedDepartmentId !== null" class="workflow-section">
          <div class="section-heading">
            <span class="step">03</span>
            <div>
              <h2>{{ text.templateTitle }}</h2>
              <p>{{ text.templateHelp }}</p>
            </div>
          </div>
          <div class="template-toolbar">
            <label v-if="savedTemplates.length" for="saved-template">{{
              text.savedTemplates
            }}</label>
            <select
              v-if="savedTemplates.length"
              id="saved-template"
              v-model="selectedTemplateId"
              :disabled="processing || routing"
            >
              <option v-for="item in savedTemplates" :key="item.id" :value="item.id">
                {{ item.name }}
              </option>
            </select>
            <button
              v-if="savedTemplates.length"
              id="load-saved-template"
              class="secondary-button"
              type="button"
              :disabled="processing || routing"
              @click="loadSavedTemplate"
            >
              {{ text.loadSavedTemplate }}
            </button>
            <button
              class="text-button"
              type="button"
              :disabled="processing"
              @click="template = demoTemplate"
            >
              {{ text.loadTemplate }}
            </button>
            <button
              class="text-button"
              type="button"
              :disabled="processing || !template"
              @click="template = ''"
            >
              {{ text.clearTemplate }}
            </button>
          </div>
          <form id="draft-form" class="ticket-form" @submit.prevent="submitDraft">
            <label for="description-template">{{ text.template }}</label>
            <textarea
              id="description-template"
              v-model="template"
              rows="8"
              :maxlength="MAX_TEMPLATE_LENGTH"
              :placeholder="text.templatePlaceholder"
              :disabled="routing || processing"
            />
            <p v-if="processingError" class="message error" role="alert">
              {{ getErrorMessage(processingError) }}
            </p>
            <button
              class="primary-button"
              type="submit"
              :disabled="routing || processing || !template.trim()"
            >
              {{ processing ? text.processing : text.process }}
            </button>
          </form>
        </section>

        <section v-if="processingResult" class="workflow-section" aria-live="polite">
          <div class="section-heading">
            <span class="step">04</span>
            <div>
              <h2>{{ text.resultTitle }}</h2>
              <p>{{ text.resultHelp }}</p>
            </div>
          </div>
          <pre id="draft-description" class="description-output">{{
            processingResult.description
          }}</pre>
        </section>
      </section>

      <aside class="right-column">
        <WorkspaceManager
          :state="workspace"
          :disabled="routing || processing"
          @saved="applyWorkspace"
        />
        <p v-if="workspaceError" class="message error" role="alert">
          {{ getErrorMessage(workspaceError) }}
        </p>
        <button
          v-if="workspaceError"
          class="text-button"
          type="button"
          @click="loadWorkspace"
        >
          {{ text.refresh }}
        </button>
        <section class="panel departments-panel">
          <div class="section-heading">
            <span class="step">IT</span>
            <div>
              <h2>{{ text.departmentsTitle }}</h2>
              <p>{{ text.departmentsHelp }}</p>
            </div>
          </div>
          <div class="departments-toolbar">
            <span>{{ departments.length }} {{ text.available }}</span>
            <button
              class="text-button"
              type="button"
              :disabled="departmentsLoading"
              @click="loadDepartments"
            >
              {{ departmentsLoading ? text.loading : text.refresh }}
            </button>
          </div>
          <p v-if="departmentsError" class="message error" role="alert">
            {{ getErrorMessage(departmentsError) }}
          </p>
          <p v-else-if="departmentsLoading" class="muted">
            {{ text.loadingDepartments }}
          </p>
          <p v-else-if="departments.length === 0" class="muted">
            {{ text.noDepartments }}
          </p>
          <ul v-else class="department-list">
            <li
              v-for="department in departments"
              :key="department.id"
              class="department-item"
            >
              <div class="department-topline">
                <strong>{{ department.name }}</strong
                ><span class="department-id">#{{ department.id }}</span>
              </div>
              <p v-if="department.description">{{ department.description }}</p>
            </li>
          </ul>
        </section>
      </aside>
    </main>
  </div>
</template>
