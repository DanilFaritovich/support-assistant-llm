<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue';

import { ApiError, getDepartments, processTicket, routeTicket } from './api/tickets';
import { DEMO_TEMPLATES, DEMO_TICKETS_BY_LOCALE } from './demo';
import { useLocale } from './locale';
import type {
  Department,
  TicketProcessingResponse,
  TicketRoutingResponse,
} from './types/ticket';

const { locale, text, setLocale } = useLocale();
const demoTickets = computed(() => DEMO_TICKETS_BY_LOCALE[locale.value]);
const demoTemplate = computed(() => DEMO_TEMPLATES[locale.value]);

const ticketText = ref('');
const template = ref('');
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

async function loadDepartments(): Promise<void> {
  departmentsLoading.value = true;
  departmentsError.value = null;

  try {
    departments.value = await getDepartments();
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

onMounted(() => void loadDepartments());
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
        <div class="language-switch" role="group" :aria-label="text.language">
          <button
            type="button"
            lang="en"
            :aria-pressed="locale === 'en'"
            @click="setLocale('en')"
          >
            English
          </button>
          <button
            type="button"
            lang="ru"
            :aria-pressed="locale === 'ru'"
            @click="setLocale('ru')"
          >
            Русский
          </button>
        </div>
      </div>
    </header>

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
          <select id="demo-ticket" v-model="selectedDemoId" :disabled="routing">
            <option v-for="demo in demoTickets" :key="demo.id" :value="demo.id">
              {{ demo.label }}
            </option>
          </select>
          <button
            class="secondary-button"
            type="button"
            :disabled="routing"
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
