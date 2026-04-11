# Deploy 0.1.19

1. Загрузить изменения в GitHub.
2. Дождаться GitHub Actions для image `0.1.19` в GHCR.
3. В Portainer выполнить redeploy существующего stack из Git/registry.
4. После redeploy проверить `/version` и `/api/probes/ping/diagnostics`.
5. Запустить ping probe из UI и убедиться, что появляется latency, а не только `failed=1`.
