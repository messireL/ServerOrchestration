# ServerOrchestration v0.1.33

## Что исправлено
- Исправлена несовместимость вызова `update_http_status(...)`: backend больше не падает на сохранении HTTP результата из-за аргументов `http_ok/http_status_code/http_response_ms`.
- Исправлена несовместимость вызова `update_ssl_status(...)`: backend принимает `source` и сохраняет его в payload SSL-проверки.
- Сохранена обратная совместимость сигнатур DB-helper функций, чтобы manual/scheduler-контур не ломался на разных местах вызова.
- Обновлены версия и docs.

## Что было симптомом
- В логах появлялось: `TypeError: update_http_status() got an unexpected keyword argument 'http_ok'`.
- Из-за этого HTTP/SSL/XUI выглядели как «не работают», хотя сами проверки запускались, но спотыкались на сохранении результата.

## Что проверить
1. После redeploy ручной запуск HTTP probe не даёт `TypeError`.
2. Ручной запуск SSL probe не даёт `unexpected keyword argument 'source'`.
3. При включённых флажках реально обновляются статусы HTTP / 3x-ui / SSL, а не только ping.
4. Для серверов без `web_url` HTTP probe корректно пропускается как skipped, а не как failed.
