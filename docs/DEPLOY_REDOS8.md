# Чеклист деплоя NovaTIP на РЕД ОС 8

Отмечайте пункты по мере выполнения. Детали — в связанных документах.

## A. Подготовка ВМ и ОС — [01_VM_AND_OS.md](01_VM_AND_OS.md)

- [ ] 1. Создана ВМ (CPU/RAM/диск по таблице).
- [ ] 2. Подключён ISO РЕД ОС 8, установка завершена.
- [ ] 3. Задан hostname, пароль root, пользователь с sudo.
- [ ] 4. Выполнен `dnf update`, работает `chronyd`.
- [ ] 5. SSH с рабочей станции открывается.
- [ ] 6. Ping шлюза и DNS работают.

## B. Стек — [02_STACK_INSTALL.md](02_STACK_INSTALL.md)

- [ ] 7. Установлен и запущен PostgreSQL.
- [ ] 8. Созданы роль/БД `novatip` и выданы GRANT **или** запланирован режим мастера «Создать УЗ и БД».
- [ ] 9. `psql … -c 'SELECT 1'` успешен (если создавали вручную).
- [ ] 10. Redis установлен, `redis-cli ping` → `PONG`.
- [ ] 11. Python 3.12+ доступен.
- [ ] 12. Nginx установлен и отвечает локально.
- [ ] 13. firewalld: открыты ssh/http/https.
- [ ] 14. SELinux: `httpd_can_network_connect` включён при Enforcing.

## C. Приложение — [03_APP_INSTALL.md](03_APP_INSTALL.md)

- [ ] 15. Пользователь ОС `novatip`, код в `/opt/novatip`.
- [ ] 16. Создан `.venv`, установлен `requirements.txt`.
- [ ] 17. Скопирован и заполнен `.env` из `.env.example`.
- [ ] 18. Выполнены `migrate` и `collectstatic`.
- [ ] 19. Включены `novatip-web`, `novatip-worker`, `novatip-beat`.
- [ ] 20. Nginx проксирует на `127.0.0.1:8000` по HTTPS.

## D. Мастер и вход — [04_WIZARD_AND_FIRST_LOGIN.md](04_WIZARD_AND_FIRST_LOGIN.md)

- [ ] 21. Открыт `/setup/`, пройдены шаги 1–9.
- [ ] 22. На шаге БД выбран режим A или B, подключение проверено.
- [ ] 23. Создан администратор веб-интерфейса.
- [ ] 24. Выполнен вход на `/accounts/login/` без саморегистрации.
- [ ] 25. В меню видны Дашборд, Уязвимости, Заявки, Настройки (Wiki нет).
- [ ] 26. Sync находится в Настройки → Источники / Sync.

## E. Эксплуатация — [05_OPERATIONS.md](05_OPERATIONS.md)

- [ ] 27. Настроен каталог бэкапов и первый `pg_dump`.
- [ ] 28. Известны команды `journalctl` для web/worker/beat.
- [ ] 29. `healthz` / `readyz` отвечают.

## Быстрые команды статуса

```bash
sudo systemctl is-active postgresql redis nginx novatip-web novatip-worker novatip-beat
curl -sS http://127.0.0.1:8000/healthz
curl -sS http://127.0.0.1:8000/readyz
```
