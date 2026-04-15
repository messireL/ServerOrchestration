- `v0.1.50`: backend-парсинг subscription HTML как браузерной страницы (table/text/script fallback) для 3x-ui profile.

# ServerOrchestration

Web-панель мониторинга и операционного управления Ubuntu/Linux-серверами.

Текущий подготовленный релиз: **v0.1.50**.
Последний подтверждённый пользователем рабочий релиз: **v0.1.38**.

## Что уже есть в v0.1.50
- принудительный cache-bust для frontend-ассетов `styles.css` и `app.js` через `?v=0.1.50`;
- для `/` и `/static/*` выставлены no-store/no-cache headers, чтобы браузер не держал старый фронтенд после релиза;
- добавлен явный перехват frontend-ошибок и unhandled promise rejection с видимым сообщением на экране;
- это релиз стабилизации фронтового bootstrap-контура, чтобы кнопки не умирали молча после откатов/горячих фиксов.

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
- **v0.1.50** — cache-bust/no-cache для frontend и видимая диагностика bootstrap-ошибок;
- дальше: операционные действия по серверам, Ansible inventory/runner, apt/update flows, reboot/maintenance windows, audit trail действий оператора.

### Monitoring hotfix notes
Current next build after v0.1.50 focuses on persisted 3x-ui subscription details, SSL certificate metadata, and richer probe history output for monitoring.