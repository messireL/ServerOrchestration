# Результат deploy/update v0.1.26

Ожидаемый результат после выкладки:
- backend стартует без ошибок импорта/compile;
- scheduler продолжает циклы без `NameError`;
- в `/api/probes/history` появляются новые `xui` записи от `scheduler`;
- ручной запуск connectivity/http probes не ломает API 500-ошибкой.
