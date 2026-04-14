# Release v0.1.29

## Что вошло
- hotfix: исправлен рассинхрон kwargs между `main.py` и `db.update_http_status()`;
- HTTP probe reset/save path снова корректно сохраняет `http_ok`, `http_status_code`, `http_response_ms`;
- release docs и stack docs уточнены: `BACKEND_RELEASE_VERSION` для stable-канала опционален и не обязателен для обычного deploy.

## Главный смысл релиза
Закрыть регрессию HTTP-monitoring после рефакторинга db-слоя и зафиксировать более практичный runtime-подход: deploy через `stable` без обязательной ручной смены release marker в env.
