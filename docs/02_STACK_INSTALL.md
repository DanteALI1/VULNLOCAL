# 02. Установка стека (PostgreSQL, Redis, Python, Nginx)

Выполняйте на РЕД ОС 8 под пользователем с `sudo`. Команды нумерованы — копируйте по порядку.

## 1. Базовые пакеты

```bash
sudo dnf -y install curl wget git vim tar unzip policycoreutils-python-utils
```

## 2. PostgreSQL

### 2.1. Установка сервера

Имена пакетов зависят от репозитория РЕД ОС. Типовой вариант:

```bash
sudo dnf -y install postgresql-server postgresql-contrib
```

Если пакет называется иначе (например `postgresql16-server`), подставьте имя из `dnf search postgresql`.

### 2.2. Инициализация и автозапуск

```bash
sudo postgresql-setup --initdb || sudo /usr/bin/postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo systemctl status postgresql --no-pager
```

Ожидаемо: `active (running)`.

### 2.3. Создание роли, БД и прав (ручной путь)

1. Сгенерируйте пароль УЗ БД и сохраните его:

```bash
openssl rand -base64 24
```

2. Создайте роль и базу (пароль подставьте свой):

```bash
sudo -u postgres psql <<'SQL'
CREATE USER novatip WITH PASSWORD 'ЗАМЕНИТЕ_ПАРОЛЬ';
CREATE DATABASE novatip OWNER novatip ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE novatip TO novatip;
\c novatip
GRANT ALL ON SCHEMA public TO novatip;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO novatip;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO novatip;
SQL
```

3. Проверьте вход:

```bash
psql "postgres://novatip:ЗАМЕНИТЕ_ПАРОЛЬ@127.0.0.1:5432/novatip" -c 'SELECT 1;'
```

Ожидаемо: `?column?` / `1`.

### 2.4. Доступ по TCP (если нужно)

Отредактируйте `pg_hba.conf` (путь часто `/var/lib/pgsql/data/pg_hba.conf`):

```bash
sudo vi /var/lib/pgsql/data/pg_hba.conf
```

Добавьте (для локали):

```text
host    novatip    novatip    127.0.0.1/32    scram-sha-256
```

Перезапуск:

```bash
sudo systemctl restart postgresql
```

> Альтернатива: мастер NovaTIP умеет режим **«Создать УЗ и БД»** (см. `04_WIZARD_AND_FIRST_LOGIN.md`). Суперпароль postgres туда вводится один раз и **не сохраняется**.

## 3. Redis

```bash
sudo dnf -y install redis
sudo systemctl enable --now redis
redis-cli ping
```

Ожидаемо: `PONG`.

## 4. Python 3.12+

```bash
sudo dnf -y install python3 python3-pip python3-devel gcc gcc-c++ make libffi-devel openssl-devel
python3 --version
```

Нужен **3.12+**. Если в репозитории старше — подключите модуль/репозиторий с 3.12 по документации РЕД ОС, затем:

```bash
python3.12 --version
```

## 5. Nginx

```bash
sudo dnf -y install nginx
sudo systemctl enable --now nginx
curl -I http://127.0.0.1/
```

Ожидаемо: HTTP-ответ от nginx (код 200/403/301 — главное, что сервис отвечает).

## 6. firewalld

```bash
sudo dnf -y install firewalld
sudo systemctl enable --now firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
```

Ожидаемо: в списке `ssh`, `http`, `https`.

PostgreSQL и Redis **не** открывайте наружу без необходимости (оставьте на `127.0.0.1`).

## 7. SELinux (базово)

1. Проверьте режим:

```bash
getenforce
```

`Enforcing` — норма для боя.

2. Разрешите nginx проксировать на бэкенд (типовые булевы):

```bash
sudo setsebool -P httpd_can_network_connect 1
```

3. Если позже появятся AVC-отказы для `/opt/novatip`:

```bash
sudo ausearch -m avc -ts recent | tail -n 50
```

и при необходимости разметьте каталоги (`semanage fcontext` + `restorecon`) — детали в `05_OPERATIONS.md`.

## 8. Что дальше

Переходите к [03_APP_INSTALL.md](03_APP_INSTALL.md).
