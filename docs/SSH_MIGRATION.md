# Переход проекта на SSH

## Когда это нужно
Эта инструкция нужна, если локальный клон или серверный checkout должны работать с GitHub по SSH, а не по HTTPS. Типовые симптомы: не удаётся клонировать приватный репозиторий, GitHub Desktop просит пароль/токен, `Permission denied (publickey)`, старый remote указывает на HTTPS.

## 1. Проверка существующих remote
На Windows PowerShell:

```powershell
clear
cd Y:\Мой диск\Git\ServerOrchestration
git remote -v
```

Нормальный SSH remote должен выглядеть так:

```text
origin  git@github.com:messireL/ServerOrchestration.git (fetch)
origin  git@github.com:messireL/ServerOrchestration.git (push)
```

## 2. Генерация SSH-ключа на Windows
Если ключа ещё нет:

```powershell
ssh-keygen -t ed25519 -C "your_email@example.com"
```

Обычно ключи будут здесь:
- приватный: `C:\Users\<USER>\.ssh\id_ed25519`
- публичный: `C:\Users\<USER>\.ssh\id_ed25519.pub`

## 3. Запуск ssh-agent и добавление ключа
В PowerShell:

```powershell
Get-Service ssh-agent | Set-Service -StartupType Automatic
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519
```

## 4. Добавление публичного ключа в GitHub
1. Открыть содержимое файла `id_ed25519.pub`.
2. В GitHub: **Settings → SSH and GPG keys → New SSH key**.
3. Вставить ключ и сохранить.

## 5. Проверка соединения с GitHub
```powershell
ssh -T git@github.com
```

Ожидаемый результат — приветствие от GitHub без ошибки `Permission denied (publickey)`.

## 6. Переключение уже существующего локального репозитория на SSH
```powershell
clear
cd Y:\Мой диск\Git\ServerOrchestration
git remote set-url origin git@github.com:messireL/ServerOrchestration.git
git remote -v
```

## 7. Клонирование заново по SSH
Если локальная папка была удалена:

```powershell
clear
cd Y:\Мой диск\Git
git clone git@github.com:messireL/ServerOrchestration.git
cd .\ServerOrchestration
git remote -v
```

## 8. GitHub Desktop
GitHub Desktop нормально работает с SSH-клонами, если:
- ключ добавлен в GitHub;
- `ssh-agent` запущен;
- remote уже указывает на `git@github.com:...`;
- Desktop открывает именно тот каталог, где remote уже SSH.

Если Desktop продолжает вести себя так, будто repo по HTTPS:
1. Закрыть репозиторий в Desktop.
2. Проверить `git remote -v` в консоли.
3. Открыть этот каталог заново в Desktop.

## 9. Серверный checkout по SSH
На сервере нужен отдельный SSH-ключ или deploy key. Базовый сценарий:

```bash
clear
cd /opt/ServerOrchestration
git remote -v
ssh -T git@github.com
```

Если сервер должен только читать приватный репозиторий, удобнее использовать deploy key, привязанный к одному репозиторию.

## 10. Типовые ошибки

### `Permission denied (publickey)`
Причины:
- ключ не добавлен в GitHub;
- не запущен `ssh-agent`;
- используется не тот ключ;
- сервер/ПК работает под другим пользователем.

### Клонирование идёт не в тот каталог
Сначала перейти в нужную родительскую папку и только потом делать `git clone`.

### Старый remote остался HTTPS
Нужно выполнить `git remote set-url origin git@github.com:messireL/ServerOrchestration.git`.

### Несколько ключей / несколько GitHub-аккаунтов
Использовать `~/.ssh/config` и отдельные host alias, если это потребуется.

## 11. Минимальная памятка после миграции
```powershell
clear
cd Y:\Мой диск\Git\ServerOrchestration
git remote -v
ssh -T git@github.com
git fetch origin --prune
```

Если все три шага проходят нормально — SSH-контур живой.
