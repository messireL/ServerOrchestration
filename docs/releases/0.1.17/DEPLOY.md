# Deploy 0.1.17

1. Распаковать релиз поверх локального репозитория.
2. Commit + push в GitHub.
3. Дождаться GitHub Actions для image `0.1.17`.
4. В Portainer сделать Redeploy stack из Git-репозитория.
5. После старта backend проверить, что startup сам выполнил schema-sync без ручных SQL-правок.
