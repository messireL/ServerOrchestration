# Release 0.1.1

## Что сделано
- Переведён базовый релиз в нормальный режим GitHub + Portainer.
- Добавлен backend API на FastAPI.
- Добавлены таблицы:
  - `servers`
  - `server_groups`
  - `server_group_members`
  - `server_status`
- Добавлены endpoints:
  - `/health`
  - `/version`
  - `/api/summary`
  - `/api/servers`
  - `/api/groups`
  - `/api/groups/{group_id}/servers/{server_id}`
- Добавлен non-root Dockerfile для backend.
- Добавлен `docker-compose.portainer.yml` для deploy из Portainer.
- Добавлен fallback `docker-compose.local.yml` для диагностики/локальной проверки.
- Добавлен GitHub Actions workflow для публикации backend image в GHCR.

## Что не входит в этот релиз
- GUI frontend
- scheduler/worker
- ping probe
- alerts
- Ansible runner
- 3x-ui / SSL / UFW проверки
