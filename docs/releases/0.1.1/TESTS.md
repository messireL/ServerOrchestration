# Tests 0.1.1

## Что проверить после deploy
1. Stack в Portainer должен подняться без ошибок.
2. Контейнер `server-orchestration-postgres` должен быть healthy.
3. Контейнер `server-orchestration-backend` должен быть running.
4. `GET /health` должен вернуть:
   - status = ok
   - database = true
   - version = 0.1.1
5. `GET /version` должен вернуть:
   - service = server-orchestration
   - version = 0.1.1
6. `GET /api/summary` должен вернуть нулевые счётчики на чистой БД.
7. Должно получаться:
   - создать группу
   - создать сервер
   - привязать сервер к группе
   - увидеть данные в `GET /api/groups` и `GET /api/servers`
