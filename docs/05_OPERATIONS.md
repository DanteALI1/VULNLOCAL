# 05. Эксплуатация: бэкап, обновление, логи, ошибки

## 1. Резервное копирование

### 1.1. База PostgreSQL

```bash
sudo -u postgres pg_dump -Fc novatip > /var/backups/novatip-$(date +%F).dump
ls -lh /var/backups/novatip-*.dump
```

Восстановление (осторожно, перезапишет данные):

```bash
sudo -u postgres pg_restore -d novatip --clean --if-exists /var/backups/novatip-YYYY-MM-DD.dump
```

### 1.2. Файлы приложения

```bash
sudo tar -czf /var/backups/novatip-files-$(date +%F).tgz \
  /opt/novatip/.env /opt/novatip/media /opt/novatip/staticfiles
```

Храните бэкапы вне ВМ (СХД / другой хост).

## 2. Обновление NovaTIP

```bash
sudo systemctl stop novatip-web novatip-worker novatip-beat
sudo -u novatip -H bash -lc '
  cd /opt/novatip
  git pull   # или распакуйте новый релиз поверх
  . .venv/bin/activate
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py collectstatic --noinput
'
sudo systemctl start novatip-web novatip-worker novatip-beat
sudo systemctl status novatip-web --no-pager
```

Перед обновлением сделайте бэкап из §1.

## 3. Логи

```bash
sudo journalctl -u novatip-web -e --no-pager
sudo journalctl -u novatip-worker -e --no-pager
sudo journalctl -u novatip-beat -e --no-pager
sudo tail -n 100 /var/log/nginx/error.log
```

Следить в реальном времени:

```bash
sudo journalctl -u novatip-web -f
```

## 4. Проверка здоровья

```bash
curl -sS http://127.0.0.1:8000/healthz
curl -sS http://127.0.0.1:8000/readyz
redis-cli ping
sudo systemctl is-active postgresql redis novatip-web novatip-worker novatip-beat nginx
```

## 5. Типичные ошибки

| Симптом | Вероятная причина | Что сделать |
|---|---|---|
| 502 Bad Gateway | Gunicorn не запущен | `systemctl status novatip-web`, смотрите journalctl |
| Страница без CSS | Нет collectstatic / alias | `collectstatic`, проверьте `location /static/` |
| Ошибка БД при входе | Неверный `DATABASE_URL` | проверьте `.env`, `psql … -c 'SELECT 1'` |
| Celery не синкает | Redis down / worker stopped | `redis-cli ping`, `systemctl restart novatip-worker` |
| SELinux блокирует proxy | bool не выставлен | `setsebool -P httpd_can_network_connect 1` |
| firewall режет HTTPS | нет сервиса https | см. `02_STACK_INSTALL.md` §6 |
| Лицензия grace истекла | нет `.novalic` / offline | загрузите лицензию в UI `/licensing/` |
| Мастер циклит на шаге БД | нет прав УЗ | режим B или GRANT из `02` |

## 6. Перезапуск всего стека приложения

```bash
sudo systemctl restart postgresql redis nginx novatip-web novatip-worker novatip-beat
```

## 7. Ссылки

- Обзор: [00_OVERVIEW.md](00_OVERVIEW.md)
- Сводный чеклист РЕД ОС 8: [DEPLOY_REDOS8.md](DEPLOY_REDOS8.md)
- Docker для разработки: [DOCKER_DEV.md](DOCKER_DEV.md)
