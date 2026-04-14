# Проверка релиза v0.1.29

1. Открывается главная панель без регрессии.
2. Запуск HTTP/All probes не приводит к `TypeError` в backend logs.
3. В таблице/сводке HTTP-статусы и время ответа сохраняются после проверки.
4. Backend image использует канал `stable`; `APP_RELEASE_VERSION`/`BACKEND_RELEASE_VERSION` проверяем только если включён опциональный release marker.
