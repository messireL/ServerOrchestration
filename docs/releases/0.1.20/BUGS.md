# Bugs / notes for 0.1.20

## Закрыто
- PostgreSQL ошибка `could not determine data type of parameter` при записи `summary_json` в `server_status`.

## Риски
- если на стенде останутся старые stopped containers/images после redeploy, их нужно чистить отдельно через Portainer prune / Docker prune; это не баг приложения, а обычный хвост redeploy-механики.
