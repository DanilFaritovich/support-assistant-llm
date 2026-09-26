<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { getDepartments, processTicket, routeTicket } from './api/tickets';
import { DEMO_TEMPLATE, DEMO_TICKETS } from './demo';
import type {
  Department,
  TicketProcessingResponse,
  TicketRoutingResponse,
} from './types/ticket';

const ticketText = ref('');
const template = ref('');
const selectedDemoId = ref(DEMO_TICKETS[0]?.id ?? '');

const MAX_TICKET_TEXT_LENGTH = 4000;
const MAX_TEMPLATE_LENGTH = 2000;

const departments = ref<Department[]>([]);
const departmentsLoading = ref(false);
const departmentsError = ref('');

const routing = ref(false);
const routingError = ref('');
const routingResult = ref<TicketRoutingResponse | null>(null);

const editingDepartment = ref(false);
const manualDepartmentId = ref<number | null>(null);
const confirmedDepartmentId = ref<number | null>(null);
const departmentSelectionError = ref('');

const processing = ref(false);
const processingError = ref('');
const processingResult = ref<TicketProcessingResponse | null>(null);

const confirmedDepartment = computed(() =>
  departments.value.find((department) => department.id === confirmedDepartmentId.value),
);

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Произошла неизвестная ошибка.';
}

function resetRouting(): void {
  routingResult.value = null;
  confirmedDepartmentId.value = null;
  manualDepartmentId.value = null;
  editingDepartment.value = false;
  processingResult.value = null;
  routingError.value = '';
  departmentSelectionError.value = '';
  processingError.value = '';
}

watch(ticketText, resetRouting);

async function loadDepartments(): Promise<void> {
  departmentsLoading.value = true;
  departmentsError.value = '';

  try {
    departments.value = await getDepartments();
  } catch (error: unknown) {
    departmentsError.value = getErrorMessage(error);
  } finally {
    departmentsLoading.value = false;
  }
}

function loadDemo(): void {
  const demo = DEMO_TICKETS.find((item) => item.id === selectedDemoId.value);
  if (demo) {
    ticketText.value = demo.ticketText;
    template.value = DEMO_TEMPLATE;
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
    routingError.value = 'Введите текст заявки.';
    return;
  }

  routing.value = true;
  try {
    routingResult.value = await routeTicket({ ticket_text: ticketText.value });
    manualDepartmentId.value = routingResult.value.department_id;
  } catch (error: unknown) {
    routingError.value = getErrorMessage(error);
  } finally {
    routing.value = false;
  }
}

function confirmSuggestedDepartment(): void {
  if (!routingResult.value) return;
  confirmedDepartmentId.value = routingResult.value.department_id;
  editingDepartment.value = false;
  departmentSelectionError.value = '';
  processingResult.value = null;
}

function startDepartmentChange(): void {
  if (!routingResult.value) return;
  manualDepartmentId.value =
    confirmedDepartmentId.value ?? routingResult.value.department_id;
  editingDepartment.value = true;
  confirmedDepartmentId.value = null;
  processingResult.value = null;
  processingError.value = '';
}

function confirmManualDepartment(): void {
  const exists = departments.value.some(
    (department) => department.id === manualDepartmentId.value,
  );
  if (!exists || manualDepartmentId.value === null) {
    departmentSelectionError.value = 'Выберите доступный IT-департамент.';
    return;
  }

  confirmedDepartmentId.value = manualDepartmentId.value;
  editingDepartment.value = false;
  departmentSelectionError.value = '';
  processingResult.value = null;
}

async function submitDraft(): Promise<void> {
  if (processing.value || routing.value || confirmedDepartmentId.value === null) {
    return;
  }

  processingError.value = '';
  processingResult.value = null;
  if (!ticketText.value.trim() || !template.value.trim()) {
    processingError.value = 'Заполните текст заявки и шаблон.';
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
    processingError.value = getErrorMessage(error);
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
        <h1>Обработка IT-заявок</h1>
        <p class="subtitle">
          Определите подходящий департамент, подтвердите или измените выбор и создайте
          структурированное описание заявки.
        </p>
      </div>
      <span class="status-label">Демонстрационная версия</span>
    </header>

    <main class="layout">
      <section class="panel editor-panel">
        <div class="section-heading">
          <span class="step">01</span>
          <div>
            <h2>Исходная заявка</h2>
            <p>Загрузите вымышленный пример или введите собственный текст.</p>
          </div>
        </div>

        <div class="demo-toolbar">
          <label for="demo-ticket">Готовый пример</label>
          <select id="demo-ticket" v-model="selectedDemoId" :disabled="routing">
            <option v-for="demo in DEMO_TICKETS" :key="demo.id" :value="demo.id">
              {{ demo.label }}
            </option>
          </select>
          <button
            class="secondary-button"
            type="button"
            :disabled="routing"
            @click="loadDemo"
          >
            Загрузить пример
          </button>
          <button
            class="text-button"
            type="button"
            :disabled="routing || processing"
            @click="clearForm"
          >
            Очистить
          </button>
        </div>

        <form id="route-form" class="ticket-form" @submit.prevent="submitRouting">
          <label for="ticket-text">Текст заявки</label>
          <textarea
            id="ticket-text"
            v-model="ticketText"
            rows="9"
            :maxlength="MAX_TICKET_TEXT_LENGTH"
            placeholder="Опишите проблему, наблюдаемый и ожидаемый результат..."
            :disabled="routing || processing"
          />
          <p v-if="routingError" class="message error" role="alert">
            {{ routingError }}
          </p>
          <button
            class="primary-button"
            type="submit"
            :disabled="routing || processing || !ticketText.trim()"
          >
            {{ routing ? 'Определяем департамент…' : 'Определить департамент' }}
          </button>
        </form>

        <section v-if="routingResult" class="workflow-section" aria-live="polite">
          <div class="section-heading">
            <span class="step">02</span>
            <div>
              <h2>Предложенная маршрутизация</h2>
              <p>Проверьте предложение модели перед генерацией описания.</p>
            </div>
          </div>

          <div class="result-content">
            <div class="result-field">
              <span class="field-label">Название</span>
              <h3>{{ routingResult.title }}</h3>
            </div>
            <div class="result-field">
              <span class="field-label">Предложенный IT-департамент</span>
              <strong>{{ routingResult.department_name }}</strong>
              <span class="muted">ID: {{ routingResult.department_id }}</span>
            </div>
            <div class="result-field">
              <span class="field-label">Обоснование выбора</span>
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
              Подтвердить
            </button>
            <button
              id="change-department"
              class="secondary-button"
              type="button"
              :disabled="departmentsLoading || departments.length === 0"
              @click="startDepartmentChange"
            >
              Изменить
            </button>
          </div>

          <form
            v-if="editingDepartment"
            id="department-form"
            class="ticket-form department-form"
            @submit.prevent="confirmManualDepartment"
          >
            <label for="department-select">IT-департамент</label>
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
              {{ departmentSelectionError }}
            </p>
            <button
              class="primary-button"
              type="submit"
              :disabled="processing || manualDepartmentId === null"
            >
              Подтвердить выбор
            </button>
          </form>

          <div v-if="confirmedDepartmentId !== null" class="confirmation-card">
            <div>
              <span class="field-label">Итоговый выбор</span>
              <strong>{{
                confirmedDepartment?.name ?? `Department #${confirmedDepartmentId}`
              }}</strong>
            </div>
            <button
              class="text-button"
              type="button"
              :disabled="processing"
              @click="startDepartmentChange"
            >
              Изменить
            </button>
          </div>
        </section>

        <section v-if="confirmedDepartmentId !== null" class="workflow-section">
          <div class="section-heading">
            <span class="step">03</span>
            <div>
              <h2>Шаблон описания</h2>
              <p>Используйте демонстрационный шаблон или измените его.</p>
            </div>
          </div>
          <div class="template-toolbar">
            <button
              class="text-button"
              type="button"
              :disabled="processing"
              @click="template = DEMO_TEMPLATE"
            >
              Загрузить шаблон
            </button>
            <button
              class="text-button"
              type="button"
              :disabled="processing || !template"
              @click="template = ''"
            >
              Очистить шаблон
            </button>
          </div>
          <form id="draft-form" class="ticket-form" @submit.prevent="submitDraft">
            <label for="description-template">Шаблон</label>
            <textarea
              id="description-template"
              v-model="template"
              rows="8"
              :maxlength="MAX_TEMPLATE_LENGTH"
              placeholder="Введите структуру будущего описания..."
              :disabled="routing || processing"
            />
            <p v-if="processingError" class="message error" role="alert">
              {{ processingError }}
            </p>
            <button
              class="primary-button"
              type="submit"
              :disabled="routing || processing || !template.trim()"
            >
              {{ processing ? 'Генерируем описание…' : 'Сгенерировать описание' }}
            </button>
          </form>
        </section>

        <section v-if="processingResult" class="workflow-section" aria-live="polite">
          <div class="section-heading">
            <span class="step">04</span>
            <div>
              <h2>Готовое описание</h2>
              <p>Результат с учётом итогового департамента.</p>
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
              <h2>Демонстрационные департаменты</h2>
              <p>Справочник, доступный для ручного выбора.</p>
            </div>
          </div>
          <div class="departments-toolbar">
            <span>{{ departments.length }} доступно</span>
            <button
              class="text-button"
              type="button"
              :disabled="departmentsLoading"
              @click="loadDepartments"
            >
              {{ departmentsLoading ? 'Загрузка…' : 'Обновить' }}
            </button>
          </div>
          <p v-if="departmentsError" class="message error" role="alert">
            {{ departmentsError }}
          </p>
          <p v-else-if="departmentsLoading" class="muted">Загружаем департаменты…</p>
          <p v-else-if="departments.length === 0" class="muted">
            В справочнике пока нет департаментов.
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
