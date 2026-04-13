# Tests for 0.1.23

- `/version` возвращает `0.1.23`;
- `/api/monitor/settings` отдаёт scheduler-настройки;
- `/api/probes/history` возвращает историю прогонов;
- после старта backend без ручной кнопки появляются scheduler-run записи в history;
- ручной запуск ping / SSH / HTTP добавляет записи с source=`manual`;
- экран `Проверки` показывает scheduler state, интервалы, таймауты и таблицу history.
