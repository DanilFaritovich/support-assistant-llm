# Support Assistant

[English](README.md) · [Русский](README.ru.md)

> **Статус: в разработке** — активная разработка ведётся в ветке [`develop`](../../tree/develop).

Support Assistant — публичное демонстрационное приложение, которое превращает неструктурированную IT-заявку в маршрутизированную, проверенную пользователем и оформленную по шаблону задачу. Приложение использует бесплатные модели OpenRouter, при этом API-ключ и весь обмен с LLM остаются только на backend.

## Решаемая проблема

Заявки часто поступают в свободной форме. Специалисту поддержки приходится определять ответственную команду, проверять выбор и переписывать обращение по принятому шаблону. Support Assistant ускоряет эти действия, не убирая контроль человека: LLM предлагает департамент и объясняет решение, а пользователь подтверждает или меняет итоговый выбор до генерации описания.

## Возможности

- Генерация названия заявки и предложение IT-департамента через LLM.
- Отображение обоснования и обязательное подтверждение выбора.
- Ручная смена департамента без повторного запроса к LLM.
- Генерация описания с итоговым `department_id`, выбранным пользователем.
- Три вымышленных примера, редактируемый шаблон и очистка формы.
- Идемпотентная инициализация шести демонстрационных департаментов.
- OpenRouter с ограничением на `openrouter/free` и модели с суффиксом `:free`.
- Structured outputs по JSON Schema, проверка Pydantic, таймауты, повторы и безопасные ошибки API.
- Адаптивный интерфейс Vue, FastAPI, SQLite, миграции и healthcheck.
- Единый Docker Compose; наружу на localhost опубликован только frontend.

## Демонстрация

![Интерфейс Support Assistant с вымышленными департаментами](docs/images/application-overview.png)

Сценарий работы:

1. Загрузить вымышленную заявку или ввести собственную.
2. Получить предложение по департаменту.
3. Проверить департамент и обоснование.
4. Подтвердить выбор или указать другой департамент из справочника.
5. Изменить шаблон и сгенерировать итоговое описание.

Скриншот получен из приложения, запущенного через Docker Compose, и содержит только демонстрационные данные.

## Технологии

| Область | Технологии |
| --- | --- |
| Frontend | Vue 3, TypeScript, Vite, Vitest, Vue Test Utils, ESLint, Prettier |
| Backend | Python 3.14, FastAPI, Pydantic, асинхронный SQLAlchemy, Alembic, OpenAI-совместимый SDK |
| LLM | Маршрутизатор бесплатных моделей OpenRouter, structured outputs по JSON Schema |
| Хранение | SQLite в постоянном Docker volume |
| Запуск | Docker Compose, Nginx, healthcheck контейнеров |

## Архитектура

Браузер обращается только к относительным адресам `/api`. Nginx раздаёт собранный SPA и проксирует API-запросы в FastAPI по приватной сети Compose. FastAPI вызывает прикладные сервисы через порты маршрутизации и генерации. Адаптеры OpenRouter реализуют эти порты и проверяют каждый ответ модели. Репозиторий SQLAlchemy изолирует хранение департаментов.

```text
Браузер -> Nginx/Vue -> FastAPI -> прикладные сервисы
                               |-> репозиторий -> SQLite
                               `-> LLM-порты -> бесплатные модели OpenRouter
```

Именованную сеть `support-assistant-network` впоследствии можно подключить к внешнему reverse proxy. Интеграция с ProjectRouter и Caddy пока не реализована.

## Запуск через Docker Compose

Потребуются Docker с Compose v2 и [API-ключ OpenRouter](https://openrouter.ai/keys).

```bash
cp .env.example .env
# Укажите OPENROUTER_API_KEY в .env
docker compose up --build -d
```

Откройте <http://127.0.0.1:8080>. Проверка состояния:

```bash
docker compose ps
curl http://127.0.0.1:8080/api/health
```

Остановка без удаления данных:

```bash
docker compose down
```

Backend не публикует отдельный порт хоста. SQLite хранится в именованном volume `support-assistant-data`. Миграции выполняются перед запуском API, а отсутствующие демонстрационные департаменты добавляются без дубликатов.

## Конфигурация

| Переменная | Обязательна | По умолчанию | Назначение |
| --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | Да для LLM-функций | — | Ключ OpenRouter только для backend |
| `OPENROUTER_MODELS` | Нет | `openrouter/free` | Модели в порядке fallback; разрешены только `openrouter/free` и ID с `:free` |
| `OPENROUTER_TIMEOUT_SECONDS` | Нет | `60` | Таймаут запроса от 1 до 180 секунд |
| `OPENROUTER_MAX_RETRIES` | Нет | `2` | Повторы SDK при временных ошибках, от 0 до 3 |
| `OPENROUTER_SITE_URL` | Нет | пусто | Необязательный URL проекта для атрибуции OpenRouter |
| `DATABASE_URL` | Нет | задаётся Compose | URL SQLAlchemy для запуска без Compose |

Не добавляйте настоящий ключ в отслеживаемые Git-файлы. Ключ не попадает в frontend bundle.

## API

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `GET` | `/api/health` | Проверка состояния контейнера и reverse proxy |
| `GET` | `/api/departments` | Список департаментов |
| `POST` | `/api/tickets/route` | Название, предложенный департамент и обоснование |
| `POST` | `/api/tickets/process` | Описание для переданного итогового департамента |

Интерактивная документация OpenAPI доступна по `/docs` при прямом обращении к backend в режиме разработки.

## Разработка и тестирование

Backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.dev.txt
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy app
.venv/bin/python -m pytest
```

Frontend:

```bash
cd frontend
npm ci
npm run check
npm run build
```

Автоматические тесты используют моки и локальные транспорты и не обращаются к OpenRouter.

## Документация компонентов

- [Техническая документация frontend](frontend/README.md)
- [Техническая документация backend](backend/README.md)

## Лицензия

Проект распространяется по [лицензии MIT](LICENSE).
