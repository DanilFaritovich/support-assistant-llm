import { computed, ref, watch } from 'vue';

export type Locale = 'en' | 'ru';
export const LOCALE_STORAGE_KEY = 'support-assistant.locale';

export const messages = {
  en: {
    title: 'IT ticket processing',
    subtitle:
      'Find the right department, confirm or change the selection, and create a structured ticket description.',
    demoVersion: 'Demo version',
    sourceTicket: 'Original ticket',
    sourceHelp: 'Load a fictional example or enter your own text.',
    example: 'Example ticket',
    loadExample: 'Load example',
    clear: 'Clear',
    ticketText: 'Ticket text',
    ticketPlaceholder: 'Describe the issue, actual and expected results...',
    routing: 'Finding a department…',
    route: 'Find department',
    routingTitle: 'Suggested routing',
    routingHelp: 'Review the suggestion before generating a description.',
    ticketTitle: 'Title',
    suggestedDepartment: 'Suggested IT department',
    reasoning: 'Reasoning',
    confirm: 'Confirm',
    change: 'Change',
    department: 'IT department',
    confirmSelection: 'Confirm selection',
    finalSelection: 'Final selection',
    departmentFallback: 'Department',
    templateTitle: 'Description template',
    templateHelp: 'Use the demo template or customize it.',
    loadTemplate: 'Load template',
    clearTemplate: 'Clear template',
    template: 'Template',
    templatePlaceholder: 'Enter the structure for the description...',
    processing: 'Generating description…',
    process: 'Generate description',
    resultTitle: 'Generated description',
    resultHelp: 'Result based on the confirmed department.',
    departmentsTitle: 'Demo departments',
    departmentsHelp: 'Directory available for manual selection.',
    available: 'available',
    loading: 'Loading…',
    refresh: 'Refresh',
    loadingDepartments: 'Loading departments…',
    noDepartments: 'No departments are available yet.',
    enterTicket: 'Enter the ticket text.',
    selectDepartment: 'Select an available IT department.',
    fillFields: 'Enter the ticket text and template.',
    unknownError: 'An unexpected error occurred.',
    networkError: 'Unable to reach the server. Check your connection.',
    validationError: 'Check the entered data.',
    quotaError: 'Too many requests. Please try again later.',
    unavailableError: 'The service is temporarily unavailable. Please try again later.',
    largeRequestError: 'The request is too large. Shorten the text.',
    notFoundError: 'The requested data was not found.',
    apiError: 'Request failed. HTTP',
    language: 'Interface language',
  },
  ru: {
    title: 'Обработка IT-заявок',
    subtitle:
      'Определите подходящий департамент, подтвердите или измените выбор и создайте структурированное описание заявки.',
    demoVersion: 'Демонстрационная версия',
    sourceTicket: 'Исходная заявка',
    sourceHelp: 'Загрузите вымышленный пример или введите собственный текст.',
    example: 'Готовый пример',
    loadExample: 'Загрузить пример',
    clear: 'Очистить',
    ticketText: 'Текст заявки',
    ticketPlaceholder: 'Опишите проблему, наблюдаемый и ожидаемый результат...',
    routing: 'Определяем департамент…',
    route: 'Определить департамент',
    routingTitle: 'Предложенная маршрутизация',
    routingHelp: 'Проверьте предложение модели перед генерацией описания.',
    ticketTitle: 'Название',
    suggestedDepartment: 'Предложенный IT-департамент',
    reasoning: 'Обоснование выбора',
    confirm: 'Подтвердить',
    change: 'Изменить',
    department: 'IT-департамент',
    confirmSelection: 'Подтвердить выбор',
    finalSelection: 'Итоговый выбор',
    departmentFallback: 'Департамент',
    templateTitle: 'Шаблон описания',
    templateHelp: 'Используйте демонстрационный шаблон или измените его.',
    loadTemplate: 'Загрузить шаблон',
    clearTemplate: 'Очистить шаблон',
    template: 'Шаблон',
    templatePlaceholder: 'Введите структуру будущего описания...',
    processing: 'Генерируем описание…',
    process: 'Сгенерировать описание',
    resultTitle: 'Готовое описание',
    resultHelp: 'Результат с учётом итогового департамента.',
    departmentsTitle: 'Демонстрационные департаменты',
    departmentsHelp: 'Справочник, доступный для ручного выбора.',
    available: 'доступно',
    loading: 'Загрузка…',
    refresh: 'Обновить',
    loadingDepartments: 'Загружаем департаменты…',
    noDepartments: 'В справочнике пока нет департаментов.',
    enterTicket: 'Введите текст заявки.',
    selectDepartment: 'Выберите доступный IT-департамент.',
    fillFields: 'Заполните текст заявки и шаблон.',
    unknownError: 'Произошла неизвестная ошибка.',
    networkError: 'Не удалось связаться с сервером. Проверьте соединение.',
    validationError: 'Проверьте введённые данные.',
    quotaError: 'Слишком много запросов. Повторите попытку позже.',
    unavailableError: 'Сервис временно недоступен. Повторите попытку позже.',
    largeRequestError: 'Запрос слишком большой. Сократите текст.',
    notFoundError: 'Запрошенные данные не найдены.',
    apiError: 'Ошибка запроса. HTTP',
    language: 'Язык интерфейса',
  },
} satisfies Record<Locale, Record<string, string>>;

export function getInitialLocale(): Locale {
  try {
    const saved = localStorage.getItem(LOCALE_STORAGE_KEY);
    if (saved === 'en' || saved === 'ru') return saved;
  } catch {
    // Browser privacy settings may disable storage.
  }
  return navigator.language.toLowerCase().startsWith('ru') ? 'ru' : 'en';
}

export function useLocale() {
  const locale = ref<Locale>(getInitialLocale());
  const text = computed(() => messages[locale.value]);
  watch(
    locale,
    (value) => {
      document.documentElement.lang = value;
      document.title = `${messages[value].title} · Support Assistant`;
    },
    { immediate: true },
  );

  function setLocale(value: Locale): void {
    locale.value = value;
    try {
      localStorage.setItem(LOCALE_STORAGE_KEY, value);
    } catch {
      // Language switching still works when storage is unavailable.
    }
  }
  return { locale, text, setLocale };
}
