# Bugs 0.1.1

## Выявленные баги
1. Portainer Git stack падал с ошибкой `service "backend" has neither an image nor a build context specified`, если не был задан `BACKEND_IMAGE`.
2. Неудобно было требовать ручное указание `APP_VERSION` в Portainer stack variables на каждом релизе.

## Статус
Исправлено в релизе 0.1.2.
