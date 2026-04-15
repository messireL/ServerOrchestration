- `v0.1.50`: backend-парсинг subscription HTML как браузерной страницы (table/text/script fallback) для 3x-ui profile.
- `v0.1.51`: усилен парсинг subscription HTML/JS, убран захват кусков страницы вместо реальных данных подписки, добавлены unit-тесты parser fallback.

# ServerOrchestration

Web-панель мониторинга и операционного управления Ubuntu/Linux-серверами.

Текущий подготовленный релиз: **v0.1.51**.
Последний подтверждённый пользователем рабочий релиз: **v0.1.38**.

## Что уже есть в v0.1.51
- всё из v0.1.50 по cache-bust/no-cache и диагностике frontend-bootstrap;
- усиленный парсинг HTML-страниц подписок 3x-ui без захвата мусорного куска страницы как `profile_title`;
- дополнительный line/script fallback для случаев, когда subscription profile лежит в JS-объекте страницы;
- unit-тесты backend-парсера подписок на реальные проблемные сценарии.

## Архитектурный стек
- FastAPI backend
- PostgreSQL
- статический frontend внутри backend
- Docker / Docker Compose
- Portainer как основной путь deploy/update
- Ansible как будущий исполнительный слой для операций изменения состояния сервера

## Документация
- ТЗ: `docs/TZ.md`
- Архитектура: `docs/ARCHITECTURE.md`
- Регламент релизов: `docs/RELEASE_POLICY.md`
- Перенос в новый чат: `docs/TRANSFER_TO_NEW_CHAT.md`
- Материалы по релизам: `docs/releases/<version>/`

## Ближайший следующий блок
- **v0.1.51** — добивка парсинга HTML/JS подписок 3x-ui, чтобы в мониторинге показывались реальные download/upload/limit/expire вместо куска страницы;
- дальше: добить оставшиеся живые шаблоны 3x-ui по реальному HTML, разгрузить экран диагностики и расширять operational-контур мониторинга/действий по серверам.
