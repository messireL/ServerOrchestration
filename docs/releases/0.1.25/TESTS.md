# Проверка релиза v0.1.25

## Обязательный минимум после выкладки
1. Открыть `Инвентарь -> Серверы`.
2. Создать или отредактировать сервер с заполнением:
   - `web_url`
   - `console_3xui_url`
   - `subscription_3xui_url`
3. Убедиться, что сервер сохраняется без 500/traceback.
4. Открыть `Проверки` и убедиться, что видны поля:
   - `HTTP interval`
   - `3x-ui interval`
   - `HTTP timeout`
   - `3x-ui timeout`
5. Выполнить ручной запуск проверок.
6. Проверить, что `/api/status/servers` и UI показывают:
   - `console_3xui_ok`
   - `console_3xui_http_status`
   - `console_3xui_response_ms`
   - `subscription_3xui_ok`
   - `subscription_3xui_http_status`
   - `subscription_3xui_response_ms`
7. Проверить, что backend стартует на старой БД без ручных SQL-команд.
8. Проверить, что через некоторое время scheduler сам добавляет history-записи для 3x-ui.

## Что считать успешным результатом
- форма сервера не ломается;
- настройки мониторинга сохраняются;
- ручные прогоны не падают;
- старый инстанс БД не требует ручной доработки;
- в status/history видны данные по 3x-ui.
