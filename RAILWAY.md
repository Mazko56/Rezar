# Railway — REZAR Bot

## Обновление проекта

После замены файлов в `C:\REZAR`:

```bat
cd /d C:\REZAR
git add .
git commit -m "Fix start flow and presentation"
git push
```

Railway автоматически сделает новый deploy.

## Start Command

```bash
python -m app.main
```

## Variables

```text
BOT_TOKEN=...
MANAGER_USERNAME=rezar_auto1
CHANNEL_INVITE=https://t.me/+Lr5L8xRGZa9kZGRi
CHAT_INVITE=https://t.me/+YuRmEjW__dplMTZi
MISE_PYTHON_GITHUB_ATTESTATIONS=false
NIXPACKS_PYTHON_VERSION=3.12
```

## Фото

`2.png`-`16.png` должны лежать в репозитории в папке `assets/`.

`1.png` используется для стартового Intro до нажатия «Розпочати» и устанавливается через BotFather → `/mybots` → бот → Edit Bot → Edit Description Picture / Edit Intro Media.

## Проверка

После deploy открыть новый тестовый аккаунт Telegram, который ещё не запускал бота:

1. до Start должен отображаться Intro с `1.png`;
2. после Start приходит `2.png` + текст;
3. через 3 секунды приходит `3.png` + презентация;
4. затем сразу приходит отдельное сообщение с главным меню и кнопками.
