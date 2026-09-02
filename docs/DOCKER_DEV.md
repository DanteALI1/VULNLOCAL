# Docker Compose — локальная разработка

Документ для разработчика. Боевой контур на РЕД ОС 8 — см. [DEPLOY_REDOS8.md](DEPLOY_REDOS8.md).

## 1. Требования

1. Docker Engine + Docker Compose plugin.
2. Git.
3. Свободные порты: `8000` (web), `5432` (Postgres), `6379` (Redis), `8100` (license_server).

Проверка:

```bash
docker --version
docker compose version
```

## 2. Быстрый старт

Из корня репозитория:

```bash
cp .env.example .env
```

Отредактируйте пароли в `.env` при необходимости (`POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY`).

```bash
docker compose up --build -d
docker compose ps
```

Ожидаемо: сервисы `db`, `redis`, `web`, `worker`, `beat`, `license_server` в состоянии running/healthy.

Откройте в браузере: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## 3. Что поднимает Compose

| Сервис | Назначение |
|---|---|
| `db` | PostgreSQL 16, init из `docker/init-db.sql` |
| `redis` | брокер/результаты Celery |
| `web` | Django/Gunicorn (или dev-сервер по entrypoint) |
| `worker` | Celery worker |
| `beat` | Celery beat |
| `license_server` | лёгкий сервис лицензий на `:8100` |

Роль и БД `novatip` создаются init-скриптом. В мастере на шаге БД достаточно режима **Подключиться**.

## 4. Логи и оболочка

```bash
docker compose logs -f web
docker compose logs -f worker
docker compose exec web bash
docker compose exec web python manage.py migrate
```

## 5. Остановка и сброс данных

```bash
docker compose down
```

Удалить тома БД (полная очистка):

```bash
docker compose down -v
```

## 6. Статика и прототипы UI

1. Рабочие стили: `static/css/tip-console.css`, `static/js/tip-ui.js`.
2. HTML-прототипы для сверки вёрстки: `design/novatip-ui/` (откройте `login.html` и др. локально в браузере).
3. CDN не используется: alpine-lite поведение в `tip-ui.js`, confirm-stub в `htmx-lite.js`.

## 7. Wiki

Модуль Wiki / NovaWIKI **вне скоупа** продукта — не включайте его в Compose и меню.
