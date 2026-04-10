# Tests 0.1.2

## Что проверить после deploy
1. Stack в Portainer должен создаться без ошибки про пустой `image` у `backend`.
2. Контейнер `server-orchestration-postgres` должен быть healthy.
3. Контейнер `server-orchestration-backend` должен быть running.
4. `GET /health` должен вернуть:
   - status = ok
   - database = true
   - version = 0.1.2
5. `GET /version` должен вернуть:
   - service = server-orchestration
   - version = 0.1.2
6. `GET /api/summary` должен вернуть нулевые счётчики на чистой БД.
