# Release 0.1.4

## Что добавлено
- read-only web dashboard на `/`
- API `GET /api/status/servers`
- API `GET /api/alerts`
- API `POST /api/probes/ping/run`
- таблица `alerts`
- поля `ping_latency_ms` и `last_error` в `server_status`
- сохранение результата ping в БД
- создание/разрешение alert типа `ping_down`
- установка `iputils-ping` в backend image

## Что не делаем в этом релизе
- пока не вводим серверы через API/curl как основной рабочий процесс
- отдельную web-форму добавления серверов перенесли на следующий релиз
