# Release 0.1.17

Ping/probe schema-sync hotfix after v0.1.16.

## Что исправлено
- в startup добавлен schema-sync legacy-колонок `servers` и `server_status`;
- отдельно добавлена миграция `server_status.summary_json`, из-за отсутствия которой ping probe мог падать `Internal Server Error` на старой БД;
- ping / ssh / http probe-endpoints обёрнуты так, чтобы ошибка по отдельному серверу или при записи результата не роняла весь API endpoint;
- выровнены версии релиза в `VERSION`, backend `APP_VERSION`, Dockerfile и compose-файлах;
- документация и roadmap обновлены под фактический следующий порядок релизов.
