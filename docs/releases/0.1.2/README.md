# Release 0.1.2

## Что сделано
- Исправлен Portainer stack: теперь у `backend` есть безопасное значение `BACKEND_IMAGE` по умолчанию.
- Убран обязательный `APP_VERSION` из Portainer stack variables.
- Добавлены значения по умолчанию для `APP_NAME`, `APP_TZ`, `POSTGRES_DB`, `POSTGRES_USER`, `BACKEND_BIND_IP`, `BACKEND_PORT`.
- Версия релиза вынесена в файл `VERSION`.
- GitHub Actions теперь читает версию из `VERSION` и публикует image с тегом релиза.
- Dockerfile backend теперь встраивает версию в image на этапе сборки.
- Обновлены deploy и release docs.

## Что не входит в этот релиз
- GUI frontend
- scheduler/worker
- ping probe
- alerts
- Ansible runner
- 3x-ui / SSL / UFW проверки
