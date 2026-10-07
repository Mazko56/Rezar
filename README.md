# REZAR Telegram Bot — Stage 1

Перший етап: оболонка Telegram-бота, усі основні розділи, кнопки, переходи та квізовий цикл.

## Що вже працює

- `/start` + приветствие
- главная
- «Підібрати авто»
- произвольные пожелания по авто
- бюджет
- срок покупки
- запрос контакта через Telegram
- экран после контакта
- «Аукціони»
- «Дилери»
- «Розрахувати під ключ»
- «Карта доступів»
- «Чому Корея?»
- «Менеджер»
- кнопки Назад / На главную
- подключаемые фото через переменные окружения

## Что намеренно пока НЕ включено

Это первый этап. Поэтому здесь пока нет:

- PostgreSQL
- CRM
- Graspil
- retry-очереди
- backup БД
- `/admin`

Они подключаются на следующих этапах, чтобы не смешивать оболочку с backend-интеграциями.

## Локальный запуск

1. Установить Python 3.12.
2. Создать виртуальное окружение:

```bash
python -m venv .venv
```

3. Активировать его.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

4. Установить зависимости:

```bash
pip install -r requirements.txt
```

5. Скопировать `.env.example` в `.env` и указать `BOT_TOKEN`.

6. Запустить:

```bash
python -m app.main
```

## Фото

Для каждого экрана можно указать Telegram `file_id` или HTTPS URL в Railway Variables / `.env`:

- PHOTO_WELCOME
- PHOTO_HOME
- PHOTO_PICK
- PHOTO_PICK_DONE
- PHOTO_CONTACT_DONE
- PHOTO_AUCTIONS
- PHOTO_DEALERS
- PHOTO_CALC
- PHOTO_ACCESS_1/2/3
- PHOTO_KOREA_1/2/3
- PHOTO_MANAGER

Если значение пустое — бот отправляет только текст.

## Доступы к аукционам

Логины и пароли специально не хранятся в GitHub. Заполнить переменные окружения:

- HAPPYCAR_ID / HAPPYCAR_PASSWORD
- DUOCAR_ID / DUOCAR_PASSWORD
- JENO_ID / JENO_PASSWORD
- GLOVIS_LOGIN / GLOVIS_PASSWORD

Это безопаснее, чем хранить рабочие пароли в исходном коде.
