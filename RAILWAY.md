# Как развернуть REZAR Bot на Railway

Docker не нужен.

## 1. Создать GitHub-репозиторий

Создайте пустой репозиторий, например `rezar-telegram-bot`.

В папке проекта выполните:

```bash
git init
git add .
git commit -m "REZAR bot stage 1"
git branch -M main
git remote add origin https://github.com/USERNAME/rezar-telegram-bot.git
git push -u origin main
```

## 2. Создать проект Railway

1. Войти в Railway.
2. `New Project`.
3. `Deploy from GitHub repo`.
4. Выбрать `rezar-telegram-bot`.
5. Railway определит Python-проект по `requirements.txt`.

## 3. Добавить Variables

В Railway откройте сервис бота → `Variables`.

Обязательно:

```text
BOT_TOKEN=токен_бота_из_BotFather
MANAGER_USERNAME=rezar_auto1
CHANNEL_INVITE=https://t.me/+Lr5L8xRGZa9kZGRi
CHAT_INVITE=https://t.me/+YuRmEjW__dplMTZi
```

При необходимости добавьте PHOTO_* и доступы к аукционам из `.env.example`.

ВАЖНО: не добавляйте `.env` в GitHub.

## 4. Команда запуска

В проекте уже есть `Procfile`:

```text
worker: python -m app.main
```

Если Railway не подхватит его автоматически, в `Settings` → `Deploy` → `Start Command` укажите:

```bash
python -m app.main
```

## 5. Проверка

После успешного deploy:

1. открыть Telegram;
2. написать боту `/start`;
3. пройти все кнопки;
4. проверить запрос контакта;
5. проверить разделы аукционов и дилеров;
6. проверить возврат на главную.

## 6. Обновления

После изменений в коде:

```bash
git add .
git commit -m "update bot"
git push
```

Railway автоматически выполнит новый deploy.

## 7. PostgreSQL — на следующем этапе

Когда начнётся backend-этап:

1. в том же Railway Project добавить `PostgreSQL`;
2. Railway создаст `DATABASE_URL`;
3. backend подключится к этой переменной;
4. после этого будут добавлены users/events/leads/retry jobs и CRM/Graspil.

На первом этапе PostgreSQL намеренно не используется, потому что задача этапа — полностью проверить интерфейс и все переходы бота.
