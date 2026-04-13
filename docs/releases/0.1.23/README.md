# Release 0.1.23

- добавлен background scheduler для ping / SSH / HTTP;
- scheduler хранит интервалы и таймауты в `monitor_settings`;
- добавлена таблица `probe_history` для manual/scheduler прогонов;
- в API появились `/api/monitor/settings` и `/api/probes/history`;
- экран `Проверки` теперь показывает состояние scheduler, последние scheduler-run и историю прогонов.
