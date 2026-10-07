# REZAR Bot — Railway

## 1. Загрузка фото

Фото складывать в папку:

```text
assets/
```

с именами `1.png`, `2.png`, `3.png` ... `16.png`.

После добавления фото сделать:

```bash
git add .
git commit -m "Add bot images"
git push
```

## 2. Deploy на Railway

1. `New Project`
2. `Deploy from GitHub Repo`
3. выбрать репозиторий `Mazko56/Rezar`
4. дождаться первой сборки

## 3. Variables

Добавить минимум:

```text
BOT_TOKEN=ваш_токен_бота
MANAGER_USERNAME=rezar_auto1
CHANNEL_INVITE=https://t.me/+Lr5L8xRGZa9kZGRi
CHAT_INVITE=https://t.me/+YuRmEjW__dplMTZi
MISE_PYTHON_GITHUB_ATTESTATIONS=false
NIXPACKS_PYTHON_VERSION=3.12
```

## 4. Start Command

Если Railway не определит сам, указать:

```bash
python -m app.main
```

## 5. Важно про экран до Start

То, что пользователь видит до нажатия `Розпочати`, задаётся не кодом, а через BotFather:

- `/setdescription`
- `/setabouttext`
- `/setuserpic`

## 6. Обновления

После любых изменений:

```bash
git add .
git commit -m "Update REZAR bot"
git push
```

Railway сам сделает redeploy.
