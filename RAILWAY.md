# Railway: REZAR bot 11.10.2026

1. В GitHub оновити репозиторій `Mazko56/Rezar` файлами з архіву, не видаляти власну `.git`.
2. У Railway відкрити сервіс Telegram-бота і встановити змінні з `.env.example` (`BOT_TOKEN` — із BotFather; зберігати секретно).
3. Start Command: `python -m app.main`.
4. Для стійкого збереження анкети у Railway сервісі додати **Volume**, монтувати в `/app/data`. У Variables можна додати `BOT_DATA_DIR=/app/data`. Без Volume дані можуть втратитися після оновлення контейнера.
5. Боту потрібен лише **один активний worker** при використанні polling. Для production/staging — окремі токени Telegram-ботів.
6. Перевірити Logs і команду `/start`, три питання квізу, контакт, доступи, чотири екрани Кореї й розділ менеджера.
7. `assets/3.png` із попереднього архіву не є справжнім PNG; його треба замінити власною презентацією (`presentation_circle.mp4`, `presentation.txt`, `presentation_video.mp4`) — без файлів бот не додає жодного тексту-заглушки.
8. Медіа до Start налаштовується в BotFather як Description Picture / Intro Media, текст опису ставиться через Telegram Bot API.

Наступні оновлення з `C:\\REZAR` (у CMD):

```bat
cd /d C:\REZAR
git add .
git commit -m "REZAR exact new specification 11 Oct"
git push origin main
```
