# ServerOrchestration

Web-панель мониторинга и операционного управления Ubuntu/Linux-серверами.

Текущий подготовленный релиз: **v0.1.48**.
Последний подтверждённый пользователем рабочий релиз: **v0.1.38**.

## Что уже есть в v0.1.48
- починен контур сохранения результатов 3x-ui probes и устранён crash на `update_3xui_status(...)`;
- 3x-ui subscription probe теперь вытаскивает traffic / total / expiry / profile metadata из HTTP headers и payload;
- SSL probe сохраняет и показывает сертификатные детали понятнее, включая self-signed сценарий;
- история прогонов получила полезные details по SSL и 3x-ui вместо пустого `—`;
- ping / SSH / HTTP / 3x-ui / SSL мониторинг продолжают работать через единый monitoring screen.

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
- **v0.1.48** — стабилизация persisted probe details для 3x-ui/SSL и возврат к функциональному контуру;
- дальше: операционные действия по серверам, Ansible inventory/runner, apt/update flows, reboot/maintenance windows, audit trail действий оператора.

### Monitoring hotfix notes
Current next build after v0.1.48 focuses on persisted 3x-ui subscription details, SSL certificate metadata, and richer probe history output for monitoring.