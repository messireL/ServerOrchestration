# Tests v0.1.32

1. Backend поднимается без crash loop.
2. Web UI открывается.
3. Кнопка «Добавить сервер» открывает форму.
4. Сохранение нового сервера проходит успешно.
5. Ручная проверка 3x-ui идёт по `subscription_3xui_url`.
6. Ручная проверка SSL идёт по хосту и порту `subscription_3xui_url`.
7. В логах backend нет `run_xui_check` / `Dict is not defined`.
