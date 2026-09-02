# 03. Установка приложения NovaTIP

Цель: пользователь `novatip`, код в `/opt/novatip`, venv, `.env`, systemd, Nginx+TLS.

## 1. Пользователь системы

```bash
sudo useradd -r -m -d /opt/novatip -s /bin/bash novatip
sudo mkdir -p /opt/novatip
sudo chown -R novatip:novatip /opt/novatip
```

## 2. Код приложения

Вариант A — git clone (подставьте ваш URL):

```bash
sudo -u novatip -H bash -lc 'cd /opt && git clone https://github.com/DanteALI1/VULNLOCAL.git novatip-src'
sudo rsync -a --delete /opt/novatip-src/ /opt/novatip/
sudo chown -R novatip:novatip /opt/novatip
```

Вариант B — скопируйте архив релиза в `/opt/novatip` и распакуйте от имени `novatip`.

Проверка:

```bash
ls /opt/novatip/manage.py /opt/novatip/requirements.txt /opt/novatip/.env.example
```

## 3. Виртуальное окружение Python

```bash
sudo -u novatip -H bash -lc '
  cd /opt/novatip
  python3 -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
'
```

Ожидаемо: в конце установки пакетов нет красных ошибок `ERROR`.

## 4. Файл `.env`

```bash
sudo -u novatip -H bash -lc 'cd /opt/novatip && cp .env.example .env && chmod 600 .env'
sudo -u novatip -H vi /opt/novatip/.env
```

Минимально заполните (пример):

```bash
DJANGO_SECRET_KEY=СГЕНЕРИРУЙТЕ_ДЛИННУЮ_СТРОКУ
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=novatip.example.local,IP_ВМ
DATABASE_URL=postgres://novatip:ПАРОЛЬ_УЗ_БД@127.0.0.1:5432/novatip
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
LICENSE_SERVER_URL=http://127.0.0.1:8100
```

Секрет:

```bash
openssl rand -hex 32
```

Полный список переменных — в `.env.example` в корне репозитория.

## 5. Миграции и статика

```bash
sudo -u novatip -H bash -lc '
  cd /opt/novatip
  . .venv/bin/activate
  python manage.py migrate
  python manage.py collectstatic --noinput
'
```

## 6. systemd-юниты

Создайте три файла.

### 6.1. Web (Gunicorn)

```bash
sudo tee /etc/systemd/system/novatip-web.service >/dev/null <<'EOF'
[Unit]
Description=NovaTIP Gunicorn
After=network.target postgresql.service redis.service

[Service]
User=novatip
Group=novatip
WorkingDirectory=/opt/novatip
EnvironmentFile=/opt/novatip/.env
ExecStart=/opt/novatip/.venv/bin/gunicorn novatip.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
```

### 6.2. Celery worker

```bash
sudo tee /etc/systemd/system/novatip-worker.service >/dev/null <<'EOF'
[Unit]
Description=NovaTIP Celery Worker
After=network.target redis.service postgresql.service

[Service]
User=novatip
Group=novatip
WorkingDirectory=/opt/novatip
EnvironmentFile=/opt/novatip/.env
ExecStart=/opt/novatip/.venv/bin/celery -A novatip worker -l info
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
```

### 6.3. Celery beat

```bash
sudo tee /etc/systemd/system/novatip-beat.service >/dev/null <<'EOF'
[Unit]
Description=NovaTIP Celery Beat
After=network.target redis.service

[Service]
User=novatip
Group=novatip
WorkingDirectory=/opt/novatip
EnvironmentFile=/opt/novatip/.env
ExecStart=/opt/novatip/.venv/bin/celery -A novatip beat -l info
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
```

Включение:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now novatip-web novatip-worker novatip-beat
sudo systemctl status novatip-web --no-pager
curl -s http://127.0.0.1:8000/healthz || true
```

## 7. Nginx + TLS

1. Сертификат (корпоративный CA или Let's Encrypt). Пример самоподписанного для стенда:

```bash
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/novatip.key \
  -out /etc/nginx/ssl/novatip.crt \
  -subj "/CN=novatip.example.local"
```

2. Конфиг сайта:

```bash
sudo tee /etc/nginx/conf.d/novatip.conf >/dev/null <<'EOF'
server {
    listen 443 ssl http2;
    server_name novatip.example.local;

    ssl_certificate     /etc/nginx/ssl/novatip.crt;
    ssl_certificate_key /etc/nginx/ssl/novatip.key;

    client_max_body_size 50m;

    location /static/ {
        alias /opt/novatip/staticfiles/;
    }
    location /media/ {
        alias /opt/novatip/media/;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
server {
    listen 80;
    server_name novatip.example.local;
    return 301 https://$host$request_uri;
}
EOF
```

3. Проверка и перезагрузка:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 8. Что дальше

Откройте `https://IP_или_имя/` и пройдите мастер: [04_WIZARD_AND_FIRST_LOGIN.md](04_WIZARD_AND_FIRST_LOGIN.md).
