# Система мониторинга

Система мониторинга — проект оркестрации управления Ubuntu-серверами с web GUI, PostgreSQL, inventory, status/probe-слоем, alerts и будущим operational-контуром через Ansible.

## Базовые принципы
- GitHub — основной источник кода.
- Portainer — основной способ deploy/update.
- Docker Compose — обязательный формат поставки стека.
- Прямой `docker compose` на сервере — только fallback/диагностика.
- Контейнеры приложения работают non-root.
- Каждый релиз имеет собственную версию и папку `docs/releases/<version>/`.

## Текущий релиз
- Версия: `0.1.24`

## Что входит в v0.1.24

- добавлены `alert_settings` и `alert_delivery_log` для правил уведомлений и журнала отправок;
- появились настройки alerting: включение уведомлений, new/resolved alerts, stale threshold и reminder interval;
- реализована доставка уведомлений через Telegram и SMTP email по env-конфигурации;
- активные alerts теперь хранят `notify_count`, `last_notified_at`, `last_delivery_status`, `last_delivery_error`;
- background loop дополнительно оценивает stale-monitoring и reminder-уведомления;
- в API появились endpoints `/api/alerts/settings`, `/api/alerts/deliveries`, `/api/alerts/test`;
- экран `Оповещения` теперь показывает настройки alerting, активные alerts и журнал доставок;
- scheduler/history из `0.1.23` сохранены без отката.

## Что уже можно делать через веб-интерфейс
- смотреть summary и dashboard;
- создавать, редактировать и удалять серверы;
- создавать, редактировать и удалять группы;
- создавать и удалять связи сервер ↔ группа;
- запускать ping / SSH / HTTP/HTTPS проверки вручную;
- включать и выключать scheduler мониторинга;
- задавать интервалы и таймауты ping / SSH / HTTP;
- смотреть историю ручных и фоновых прогонов;
- фильтровать inventory по состоянию и типу мониторинга;
- смотреть alerts и статусы по разделам;
- смотреть ping diagnostics через API.

## Роль Ansible
- Быстрые проверки (`ping`, `SSH`, `HTTP/HTTPS`) остаются в собственном probe-слое проекта.
- Ansible не используется как GUI и не используется для частого мониторинга.
- Ansible будет подключаться как исполнительный слой для apt, timezone, reboot, 3x-ui и operational-задач.
