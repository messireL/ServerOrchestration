# Tests 0.1.4

## Базовые проверки
- открыть `/`
- проверить отображение summary cards
- проверить `GET /health`
- проверить `GET /version`
- проверить `GET /api/summary`
- проверить `GET /api/status/servers`
- проверить `GET /api/alerts`
- проверить `POST /api/probes/ping/run`

## Ожидаемое поведение на пустом inventory
- dashboard открывается
- список серверов пустой
- active alerts пустой
- ping probe завершает выполнение без ошибок и возвращает `processed=0`
