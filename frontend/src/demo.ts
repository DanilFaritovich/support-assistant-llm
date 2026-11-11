import type { Locale } from './locale';

export interface DemoTicket {
  id: string;
  label: string;
  ticketText: string;
}

const EN_TEMPLATE = `Summary:

Environment:

Steps to reproduce:

Actual result:

Expected result:

Additional information:`;

const EN_TICKETS: DemoTicket[] = [
  {
    id: 'login',
    label: 'Sign-in problem',
    ticketText:
      'After entering a valid one-time code in the employee portal, the page shows “Session expired” and returns to the sign-in screen. The issue started this morning and affects two test accounts.',
  },
  {
    id: 'laptop',
    label: 'Laptop docking issue',
    ticketText:
      'A demo user’s laptop no longer detects either external monitor after reconnecting to the USB-C dock. The keyboard and network connection through the same dock still work.',
  },
  {
    id: 'deployment',
    label: 'Deployment unavailable',
    ticketText:
      'The staging deployment for the demo catalog service has been pending for 25 minutes. The deployment dashboard reports that no runner is available; the previous deployment completed successfully.',
  },
];

export const DEMO_TEMPLATES: Record<Locale, string> = {
  en: EN_TEMPLATE,
  ru: `Краткое описание:

Окружение:

Шаги воспроизведения:

Фактический результат:

Ожидаемый результат:

Дополнительная информация:`,
};

export const DEMO_TICKETS_BY_LOCALE: Record<Locale, DemoTicket[]> = {
  en: EN_TICKETS,
  ru: [
    {
      id: 'login',
      label: 'Проблема со входом',
      ticketText:
        'После ввода правильного одноразового кода на портале сотрудников появляется сообщение «Сессия истекла» и снова открывается экран входа. Проблема возникла сегодня утром и воспроизводится на двух тестовых учётных записях.',
    },
    {
      id: 'laptop',
      label: 'Проблема с док-станцией',
      ticketText:
        'После повторного подключения ноутбука демонстрационного пользователя к док-станции USB-C оба внешних монитора перестали определяться. Клавиатура и сетевое подключение через ту же док-станцию работают.',
    },
    {
      id: 'deployment',
      label: 'Развёртывание недоступно',
      ticketText:
        'Развёртывание демонстрационного сервиса каталога в тестовой среде ожидает запуска уже 25 минут. Панель развёртывания сообщает, что нет доступного runner. Предыдущее развёртывание завершилось успешно.',
    },
  ],
};
