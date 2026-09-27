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
- Общие rolling quota в Redis для LLM-операций и anti-flood API на Nginx.
- Коррелированные JSON-логи приложения, пригодные для внешней отправки в Loki.
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
| Хранение | SQLite в постоянном Docker volume; временное quota-состояние в Redis |
| Запуск | Docker Compose, Nginx, healthcheck контейнеров |

## Архитектура

Браузер обращается только к относительным адресам `/api`. Nginx раздаёт собранный SPA и проксирует API-запросы в FastAPI по приватной сети Compose. FastAPI вызывает прикладные сервисы через порты маршрутизации и генерации. Адаптеры OpenRouter реализуют эти порты и проверяют каждый ответ модели. Репозиторий SQLAlchemy изолирует хранение департаментов.

```text
Браузер -> Nginx/Vue -> FastAPI -> прикладные сервисы
                               |-> репозиторий -> SQLite
                               |-> LLM-порты -> бесплатные модели OpenRouter
                               `-> quota-порт -> Redis
```

Nginx применяет общий IP anti-flood и ограничение тела запроса 16 КиБ для
`/api/`. Отдельная общая LLM quota хранится в Redis. Именованную сеть
`support-assistant-network` можно подключить к внешнему reverse proxy. В
production используются отдельная внутренняя сеть приложения и явно заданная
внешняя proxy-сеть; сам proxy остаётся инфраструктурой VDS.

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

Backend и Redis не публикуют порты хоста. SQLite хранится в именованном volume
`support-assistant-data`; quota-счётчики Redis намеренно не сохраняются.
Миграции выполняются перед запуском API, а отсутствующие демонстрационные
департаменты добавляются без дубликатов.

## Конфигурация

| Переменная | Обязательна | По умолчанию | Назначение |
| --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | Да для LLM-функций | — | Ключ OpenRouter только для backend |
| `OPENROUTER_MODELS` | Нет | `openrouter/free` | Модели в порядке fallback; разрешены только `openrouter/free` и ID с `:free` |
| `OPENROUTER_TIMEOUT_SECONDS` | Нет | `60` | Таймаут запроса от 1 до 180 секунд |
| `OPENROUTER_MAX_RETRIES` | Нет | `2` | Повторы SDK при временных ошибках, от 0 до 3 |
| `OPENROUTER_SITE_URL` | Нет | пусто | Необязательный URL проекта для атрибуции OpenRouter |
| `LLM_RATE_LIMIT_PER_MINUTE` | Нет | `10` | Общий IP-лимит двух LLM-endpoint'ов за 60 секунд |
| `LLM_RATE_LIMIT_PER_DAY` | Нет | `20` | Общий IP-лимит двух LLM-endpoint'ов за 24 часа |
| `REDIS_URL` | Нет | `redis://localhost:6379/0` | Backend-only хранилище общей quota; Compose задаёт внутренний URL |
| `LOG_LEVEL` | Нет | `INFO` | Уровень логирования backend |
| `LOG_FORMAT` | Нет | `json` | `json` для structured output или `text` для локального запуска |
| `SERVICE_NAME` | Нет | `support-assistant-backend` | Поле service в structured logs |
| `ENVIRONMENT` | Нет | `development` | Поле environment в structured logs |
| `FORWARDED_ALLOW_IPS` | Нет | только loopback | Точные доверенные IP/CIDR reverse proxy для Uvicorn |
| `DATABASE_URL` | Нет | задаётся Compose | URL SQLAlchemy для запуска без Compose |

Не добавляйте настоящий ключ в отслеживаемые Git-файлы. Ключ не попадает в frontend bundle.

Два LLM-endpoint'а используют общие атомарные rolling quota Redis для всех
workers и backend-инстансов. Persistence Redis отключён, поскольку счётчики не
являются бизнес-данными. Для публичного деплоя укажите в
`FORWARDED_ALLOW_IPS` точные адреса или сети Nginx/Caddy, чтобы Uvicorn
безопасно определял IP клиента; не используйте `*`. Если перед Nginx появится
ещё один proxy, сначала настройте доверенную обработку real IP в Nginx.

Backend пишет JSON Lines в stdout и добавляет сгенерированный request ID,
который также возвращается в `X-Request-ID`. Сбор логов (например, в Loki
через Grafana Alloy) остаётся задачей deployment и не добавляется в Compose.

## API

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `GET` | `/api/health` | Проверка состояния контейнера и reverse proxy |
| `GET` | `/api/departments` | Список департаментов |
| `POST` | `/api/tickets/route` | Название, предложенный департамент и обоснование |
| `POST` | `/api/tickets/process` | Описание для переданного итогового департамента |

Максимальная длина `ticket_text` — 4 000 символов, пользовательского
`template` — 2 000 символов.

Интерактивная документация OpenAPI доступна по `/docs` при прямом обращении к backend в режиме разработки.

## Разработка и тестирование

Корневой Makefile — единый стабильный интерфейс проекта:

| Команда | Назначение |
| --- | --- |
| `make fix` | Безопасные автоисправления lint и форматирования backend/frontend |
| `make check` | Быстрые lint, format, type и unit-проверки backend/frontend |
| `make verify` | Integration/E2E-тесты, build frontend и детерминированные deployment-проверки |
| `make test` | Все существующие тесты backend и frontend |
| `make build` | Production build frontend |
| `make docker-build` | Проверка Compose и сборка образов |
| `make docker-check` | Сборка, запуск, health/smoke-check и cleanup Compose |
| `make production-config` | Проверка production Compose без настоящих secrets |
| `make deployment-check` | Pinned `actionlint`, `shellcheck` и проверка production Compose |
| `make production-deploy` | Деплой переданных immutable GHCR digest на настроенный VDS |
| `make production-migrate` | Явный запуск production-миграции Alembic |
| `make production-health` | Проверка health-маршрута gateway и backend |
| `make production-restore-images` | Восстановление last-known-good image references без изменения services |
| `make ci` | Полный путь `check + verify + docker-check` для GitHub Actions |

Перед read-only проверками выполняйте `make fix`, затем в обычном цикле
разработки используйте `make check`. Если изменения затрагивают интеграцию,
E2E-сценарии, сборку или CI, после него выполните `make verify`.
Более тяжёлый `make ci` предназначен прежде всего для GitHub Actions.

Backend:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.dev.txt
make check PYTHON=.venv/bin/python
```

Frontend:

```bash
cd frontend
make install
make check
make build
```

Автоматические тесты используют моки и локальные транспорты и не обращаются к
OpenRouter. Redis integration tests используют `TEST_REDIS_URL`; GitHub
Actions автоматически предоставляет изолированный Redis service.

GitHub Actions выполняет полный CI для Pull Request и push в `develop` и
`main`. Новая работа начинается от `develop` в task-ветке и возвращается
через Pull Request; перенос изменений из `develop` в `main` выполняется
отдельным Pull Request.

## Основа Continuous Delivery

В репозитории подготовлены production Compose, публикация immutable-образов в
GHCR, явные migration/health hooks и контракт защищённого GitHub Environment
`production`. Workflow запускается вручную только для `main`, сначала выполняет
переиспользуемый CI для точного commit, а затем сможет собрать два application
image и развернуть их точные digest после настройки внешнего VDS и Environment.

Это только repository foundation: сервер, production credentials и runtime
secrets не добавлены, реальный production deployment не проверялся. Требуемые
GitHub inputs, одноразовая настройка VDS, порядок деплоя и границы recovery
описаны в [production deployment contract](docs/deployment.md).

## Документация компонентов

- [Инструкции для Codex](AGENTS.md)
- [Описание архитектуры](ARCHITECTURE.md)
- [Контракт production deployment](docs/deployment.md)
- [Техническая документация frontend](frontend/README.md)
- [Техническая документация backend](backend/README.md)

## Лицензия

Проект распространяется по [лицензии MIT](LICENSE).
