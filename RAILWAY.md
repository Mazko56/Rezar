# Railway deploy

## 1. Репозиторий

Проект пушится в GitHub, потом подключается в Railway через `Deploy from GitHub Repo`.

## 2. Variables

Добавить в Railway:

```text
BOT_TOKEN=ваш_токен_бота
MANAGER_USERNAME=rezar_auto1
CHANNEL_INVITE=https://t.me/+Lr5L8xRGZa9kZGRi
CHAT_INVITE=https://t.me/+YuRmEjW__dplMTZi
MISE_PYTHON_GITHUB_ATTESTATIONS=false
NIXPACKS_PYTHON_VERSION=3.12
HAPPYCAR_ID=
HAPPYCAR_PASSWORD=
DUOCAR_ID=
DUOCAR_PASSWORD=
JENO_ID=
JENO_PASSWORD=
GLOVIS_LOGIN=
GLOVIS_PASSWORD=
```

## 3. Start Command

Если Railway не определит автоматически:

```bash
python -m app.main
```

## 4. Фото

Фото загружать в папку `assets/`, потом делать push в GitHub.

## 5. Экран до Start

Экран до `Розпочати` задаётся через `@BotFather`, а не кодом.
Использовать `assets/1.png`.
