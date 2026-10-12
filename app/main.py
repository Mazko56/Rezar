"""Telegram REZAR bot: independent quiz drafts and photo administration.

User-facing text is taken from app/content.py (the supplied REZAR specification).
"""
import asyncio
import html
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message, InlineKeyboardButton, InlineKeyboardMarkup

from . import content, keyboards as kb, storage
from .config import get_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
ASSETS = Path(__file__).resolve().parent.parent / "assets"
ADMIN_IDS = {5138418509}

# Фото можна покласти до assets/ АБО встановити через /admin.
# Особливе: 11.png = ВАЖЛИВІСТЬ; 8.png/13.png/14.png/15.png = 4 екрани Кореї.
PHOTOS = {
    "home": "2.png", "presentation": "3.png", "pick": "4.png", "quiz_ready": "9.png", "calc": "10.png",
    "access1": "6.png", "access2": "11.png", "access3": "12.png",
    "korea1": "8.png", "korea2": "13.png", "korea3": "14.png", "korea4": "15.png",
    "auctions": "16.png", "dealers": "17.png", "manager": "18.png", "bonus": "19.png",
}
PHOTO_LABELS = {
    "home": "Головна / вступ", "presentation": "Мініпрезентація (фото)",
    "pick": "Підібрати авто / вступ", "quiz_ready": "Анкета сформована",
    "calc": "Розрахунок під ключ / вступ",
    "access1": "Доступи 1 — Секретність", "access2": "Доступи 2 — Важливість",
    "access3": "Доступи 3 — Ексклюзивність",
    "korea1": "Корея 1 — Вибір авто", "korea2": "Корея 2 — Вигода",
    "korea3": "Корея 3 — Перевага", "korea4": "Корея 4 — Rezar",
    "auctions": "Аукціони / логіни", "dealers": "Дилери / майданчики",
    "manager": "Зв’язок з менеджером", "bonus": "Бонус / доступи після анкети",
}


def local_photo(name: str):
    filename = PHOTOS.get(name)
    if not filename:
        return None
    path = ASSETS / filename
    if not path.is_file():
        return None
    with path.open("rb") as f:
        magic = f.read(12)
    if magic.startswith(b"\xff\xd8"):
        return FSInputFile(path, filename=f"{name}.jpg")
    if magic.startswith(b"\x89PNG\r\n\x1a\n"):
        return FSInputFile(path, filename=f"{name}.png")
    return None


async def send_screen(message: Message, text: str, *, photo: str | None = None,
                      reply_markup=None, parse_mode=None):
    """One Telegram message for photo+heading+body, when caption <= 1024 chars."""
    media_override = storage.get_photo_override(photo) if photo else None
    candidates = [media_override, local_photo(photo)] if photo else []
    for media in candidates:
        if not media:
            continue
        try:
            if len(text) <= 1024:
                return await message.answer_photo(media, caption=text,
                                                  reply_markup=reply_markup, parse_mode=parse_mode)
            # The Telegram Bot API caption limit is 1024 chars. This branch
            # affects only longer, unrelated screens; Korea/access fit in one.
            await message.answer_photo(media)
            return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as exc:
            log.warning("Photo for %s could not be sent, trying fallback: %s", photo, exc)
    return await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)


def screen_html(text: str) -> str:
    """Style only a screen's original heading; do not alter its wording."""
    first, separator, rest = text.partition("\n")
    return f"<b>{html.escape(first)}</b>{separator}{html.escape(rest)}"


async def send_presentation(message: Message):
    circle = ASSETS / "presentation_circle.mp4"
    if circle.exists():
        await message.answer_video_note(FSInputFile(circle))
    notes = ASSETS / "presentation.txt"
    if notes.exists():
        text = notes.read_text(encoding="utf-8").strip()
        if text:
            await message.answer(text)
    video = ASSETS / "presentation_video.mp4"
    if video.exists():
        await message.answer_video(FSInputFile(video))
    media_override = storage.get_photo_override("presentation")
    photo = local_photo("presentation")
    if media_override or photo:
        await send_screen(message, "", photo="presentation")


def after_hours():
    hour = datetime.now(ZoneInfo("Europe/Kyiv")).hour
    return hour < 9 or hour >= 19


async def main_menu(message: Message, user_id: int):
    storage.update(user_id, view="home")
    return await message.answer(content.HOME_MENU, reply_markup=kb.main_kb())


async def start(message: Message):
    user_id = message.from_user.id
    storage.read(user_id)
    storage.update(user_id, view="home")
    await send_screen(message, content.HOME, photo="home")
    await asyncio.sleep(2)
    await send_presentation(message)
    await message.answer(content.HOME_MENU, reply_markup=kb.main_kb())


async def quiz_question(message: Message, user_id: int, origin: str):
    q = storage.read_quiz(user_id, origin)
    stage = q["stage"]
    p = storage.read(user_id)
    if stage == "car":
        await message.answer(content.CAR_QUESTION, reply_markup=kb.car_kb())
    elif stage == "year":
        await message.answer(content.YEAR_QUESTION, reply_markup=kb.year_kb())
    elif stage == "budget":
        await message.answer(content.BUDGET_QUESTION, reply_markup=kb.budget_kb())
    elif stage == "contact":
        if p["phone"]:
            storage.update_quiz(user_id, origin, stage="preferred")
            await message.answer(content.PREFERRED_CONTACT, reply_markup=kb.preferred_kb())
        else:
            await send_screen(message, content.QUIZ_READY, photo="quiz_ready", reply_markup=kb.contact_kb())
    elif stage == "preferred":
        await message.answer(content.PREFERRED_CONTACT, reply_markup=kb.preferred_kb())


async def begin_quiz(message: Message, user_id: int, origin: str, *, actor=None):
    """Each section has its own session; completed -> new, unfinished -> resume."""
    previous = storage.read_quiz(user_id, origin)
    q = storage.begin_quiz(user_id, origin)
    is_new = bool(previous["completed"] or (previous["stage"] == "car" and not previous["car"]))
    if is_new:
        if origin == "calc":
            await send_screen(message, content.CALC_INTRO, photo="calc")
        elif origin in {"pick", "access"}:
            user = actor or message.from_user
            username = f"@{html.escape(user.username)}" if user and user.username else html.escape(user.first_name or "") if user else ""
            await send_screen(message, content.PICK_INTRO.format(username=username), photo="pick")
    await quiz_question(message, user_id, origin)


async def send_completed_access_choices(message: Message):
    await send_screen(message, content.BONUS_ACCESS, photo="bonus",
                      reply_markup=kb.after_access_buttons(), parse_mode="HTML")


async def send_quiz_result(message: Message):
    settings = get_settings()
    await message.answer(content.QUIZ_FINISHED.format(channel=settings.channel_invite, chat=settings.chat_invite),
                         reply_markup=kb.after_kb())
    await send_screen(message, content.BONUS_ACCESS, photo="bonus",
                      reply_markup=kb.after_access_buttons(), parse_mode="HTML")


async def show_auctions(message: Message, user_id: int):
    storage.update(user_id, view="auctions")
    keys = {
        "happy_id": "HAPPYCAR_ID", "happy_pw": "HAPPYCAR_PASSWORD",
        "duo_id": "DUOCAR_ID", "duo_pw": "DUOCAR_PASSWORD",
        "jeno_id": "JENO_ID", "jeno_pw": "JENO_PASSWORD",
        "glovis_id": "GLOVIS_LOGIN", "glovis_pw": "GLOVIS_PASSWORD",
    }
    await send_screen(message, content.AUCTIONS.format(**{
        key: os.getenv(env, "") for key, env in keys.items()
    }), photo="auctions", reply_markup=kb.after_kb())


async def show_dealers(message: Message, user_id: int):
    storage.update(user_id, view="dealers")
    await send_screen(message, content.DEALERS, photo="dealers", reply_markup=kb.after_kb())


# Inline rows contain both the step navigation and the context actions.
# Telegram cannot attach an inline and a persistent reply keyboard to the
# same message; embedding all required actions avoids extra/split messages.
def access_buttons(page: int):
    step = kb.access_step_kb(page).inline_keyboard
    context = kb.access_nav_kb().keyboard[0]
    return InlineKeyboardMarkup(inline_keyboard=step + [
        [InlineKeyboardButton(text=context[0].text, callback_data="go:menu"),
         InlineKeyboardButton(text=context[2].text, callback_data="go:manager")],
        [InlineKeyboardButton(text=context[1].text, callback_data="go:korea")],
    ])


def korea_buttons(page: int):
    nav = kb.korea_step_kb(page).inline_keyboard if page < 4 else []
    if page < 4:
        return InlineKeyboardMarkup(inline_keyboard=nav + [
            [InlineKeyboardButton(text=kb.PICK, callback_data="go:pick"),
             InlineKeyboardButton(text=kb.CALC, callback_data="go:calc")],
            [InlineKeyboardButton(text=kb.MENU, callback_data="go:menu"),
             InlineKeyboardButton(text=kb.SHORT_MANAGER, callback_data="go:manager")],
            [InlineKeyboardButton(text=kb.ACCESS_SHORT, callback_data="go:access")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=kb.PICK, callback_data="go:pick"),
         InlineKeyboardButton(text=kb.CALC, callback_data="go:calc")],
        [InlineKeyboardButton(text=kb.MENU, callback_data="go:menu"),
         InlineKeyboardButton(text=kb.SHORT_MANAGER, callback_data="go:manager")],
        [InlineKeyboardButton(text=kb.AUCTIONS, callback_data="go:auctions")],
    ])


async def show_access(message: Message, user_id: int, page: int):
    storage.update(user_id, view="access")
    text = {1: content.ACCESS_1, 2: content.ACCESS_2, 3: content.ACCESS_3}[page]
    await send_screen(message, screen_html(text), photo=f"access{page}",
                      reply_markup=access_buttons(page), parse_mode="HTML")


async def open_access(message: Message, user_id: int):
    person = storage.read(user_id)
    if person["phone"] and storage.has_completed_quiz(user_id):
        await show_auctions(message, user_id)
    else:
        await show_access(message, user_id, 1)


async def show_korea(message: Message, user_id: int, page: int):
    storage.update(user_id, view="korea")
    text = {1: content.KOREA_1, 2: content.KOREA_2,
            3: content.KOREA_3, 4: content.KOREA_4}[page]
    await send_screen(message, screen_html(text), photo=f"korea{page}",
                      reply_markup=korea_buttons(page), parse_mode="HTML")


async def show_manager(message: Message, user_id: int):
    person = storage.read(user_id)
    storage.update(user_id, view="manager")
    # Keep the original direct-message URL button and the contact-sharing keyboard.
    # Telegram supports only one markup type per message, so the manager section
    # retains the prior two-part layout (the Korea/access screens do NOT split).
    first, sep, second = content.MANAGER.partition("\n\n")
    await send_screen(message, first, photo="manager", reply_markup=kb.manager_kb(bool(person["phone"])))
    if sep:
        await message.answer(second, reply_markup=kb.manager_inline(get_settings().manager_username))


async def handle_text(message: Message):
    if not message.from_user or not message.text:
        return
    user_id = message.from_user.id
    p = storage.read(user_id)
    text = message.text.strip()

    if text in (kb.MENU, "меню"):
        await main_menu(message, user_id)
        return
    if text in (kb.PICK, "Підібрати авто"):
        await begin_quiz(message, user_id, "pick")
        return
    if text in (kb.CALC, "Розрахувати під ключ"):
        await begin_quiz(message, user_id, "calc")
        return
    if text in (kb.KOREA, kb.KOREA_SHORT, "Чому авто з Кореї?", "а чому з Кореї?"):
        await show_korea(message, user_id, 1)
        return
    if text in (kb.MANAGER, kb.SHORT_MANAGER, "Зв’язок з менеджером", "менеджер"):
        await show_manager(message, user_id)
        return
    if text in (kb.ACCESS, kb.ACCESS_SHORT, kb.AUCTIONS,
                "аукціони", "Безкоштовні доступи до аукціонів", "доступи до аукціонів"):
        await open_access(message, user_id)
        return
    if text in (kb.DEALERS, "дилери"):
        await show_dealers(message, user_id)
        return

    if p["view"] == "quiz" and p["source"] in storage.ORIGINS:
        origin = p["source"]
        q = storage.read_quiz(user_id, origin)
        if q["stage"] == "budget" and text in kb.ACTIONS:
            storage.update_quiz(user_id, origin, budget=text, stage="contact")
            await quiz_question(message, user_id, origin)
            return
        if q["stage"] == "car":
            storage.update_quiz(user_id, origin, car=text, stage="year")
            await quiz_question(message, user_id, origin)
            return
        if q["stage"] == "year":
            storage.update_quiz(user_id, origin, year=text, stage="budget")
            await quiz_question(message, user_id, origin)
            return
        if q["stage"] == "preferred" and text in (kb.CHAT, kb.CALL, "в чаті", "зателефонуйте"):
            storage.update_quiz(user_id, origin, contact_method=text)
            storage.complete_quiz(user_id, origin)
            storage.update(user_id, view="result")
            await send_quiz_result(message)
            return

    if p["view"] == "manager":
        storage.update(user_id, manager_request=text)
        if not p["phone"]:
            await message.answer(content.MANAGER_TYPED, reply_markup=kb.manager_kb(False))
        return
    if p["view"] in ("auctions", "dealers"):
        await message.answer(content.OTHER_TEXT, reply_markup=kb.after_kb())
        return
    if p["view"] == "access":
        await message.answer(content.ACCESS_INPUT_RESPONSE, reply_markup=kb.access_nav_kb())
        return


async def handle_contact(message: Message):
    if not message.from_user or not message.contact:
        return
    user_id = message.from_user.id
    if message.contact.user_id and message.contact.user_id != user_id:
        return
    person = storage.read(user_id)
    storage.update(user_id, phone=message.contact.phone_number)
    if person["view"] == "manager":
        answer = content.MANAGER_OFF_HOURS if after_hours() else content.MANAGER_CONTACT
        await message.answer(answer, reply_markup=kb.manager_kb(True))
        return
    if person["view"] == "quiz" and person["source"] in storage.ORIGINS:
        origin = person["source"]
        q = storage.read_quiz(user_id, origin)
        if q["stage"] in ("contact", "preferred"):
            storage.update_quiz(user_id, origin, stage="preferred")
            await message.answer(content.PREFERRED_CONTACT, reply_markup=kb.preferred_kb())


def admin_menu_markup():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=title, callback_data=f"admin:select:{key}")]
        for key, title in PHOTO_LABELS.items()
    ])


async def admin_menu(message: Message):
    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Оберіть повідомлення, для якого потрібно додати або замінити фото:",
                         reply_markup=admin_menu_markup())


async def handle_admin_photo(message: Message):
    if not message.from_user or message.from_user.id not in ADMIN_IDS:
        return False
    key = storage.get_admin_pending(message.from_user.id)
    if not key or key not in PHOTO_LABELS:
        return False
    if not message.photo:
        await message.answer("Надішліть зображення як фото, а не як файл.")
        return True
    storage.set_photo_override(key, message.photo[-1].file_id)
    storage.set_admin_pending(message.from_user.id, None)
    await message.answer(f"Фото збережено для «{PHOTO_LABELS[key]}». Воно з'явиться в цьому блоці бота.",
                         reply_markup=admin_menu_markup())
    return True


async def main():
    settings = get_settings()
    bot = Bot(settings.bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def on_start(message: Message):
        await start(message)

    @dp.message(Command("admin"))
    async def on_admin(message: Message):
        await admin_menu(message)

    @dp.message(F.photo)
    async def on_photo(message: Message):
        await handle_admin_photo(message)

    @dp.callback_query(F.data.startswith("admin:"))
    async def on_admin_action(q: CallbackQuery):
        if q.from_user.id not in ADMIN_IDS:
            await q.answer()
            return
        parts = q.data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        key = parts[2] if len(parts) > 2 else ""
        if action == "select" and key in PHOTO_LABELS:
            storage.set_admin_pending(q.from_user.id, key)
            filename = PHOTOS[key]
            await q.message.answer(f"«{PHOTO_LABELS[key]}» — надішліть сюди фото. "
                                   f"Стандартний файл: assets/{filename}",
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                       [InlineKeyboardButton(text="🗑 Скинути фото з адмінки", callback_data=f"admin:reset:{key}")],
                                       [InlineKeyboardButton(text="⬅️ Список фото", callback_data="admin:list")],
                                   ]))
        elif action == "reset" and key in PHOTO_LABELS:
            storage.remove_photo_override(key)
            storage.set_admin_pending(q.from_user.id, None)
            await q.message.answer(f"Фото «{PHOTO_LABELS[key]}» скинуто. Тепер використовується assets/{PHOTOS[key]}, якщо файл є.",
                                   reply_markup=admin_menu_markup())
        elif action == "list":
            storage.set_admin_pending(q.from_user.id, None)
            await q.message.answer("Оберіть повідомлення:", reply_markup=admin_menu_markup())
        await q.answer()

    @dp.message(Command("pick"))
    async def command_pick(message: Message):
        await begin_quiz(message, message.from_user.id, "pick")

    @dp.message(Command("calc"))
    async def command_calc(message: Message):
        await begin_quiz(message, message.from_user.id, "calc")

    @dp.message(Command("korea"))
    async def command_korea(message: Message):
        await show_korea(message, message.from_user.id, 1)

    @dp.message(Command("access"))
    async def command_access(message: Message):
        await open_access(message, message.from_user.id)

    @dp.message(Command("manager"))
    async def command_manager(message: Message):
        await show_manager(message, message.from_user.id)

    @dp.message(F.contact)
    async def on_contact(message: Message):
        await handle_contact(message)

    @dp.callback_query(F.data.startswith("access:"))
    async def on_access(q: CallbackQuery):
        await q.answer()
        choice = q.data.partition(":")[2]
        if choice == "0":
            await main_menu(q.message, q.from_user.id)
        elif choice == "get":
            if storage.read(q.from_user.id)["phone"] and storage.has_completed_quiz(q.from_user.id):
                await send_completed_access_choices(q.message)
            else:
                await begin_quiz(q.message, q.from_user.id, "access", actor=q.from_user)
        elif choice in {"1", "2", "3"}:
            await show_access(q.message, q.from_user.id, int(choice))

    @dp.callback_query(F.data.startswith("korea:"))
    async def on_korea(q: CallbackQuery):
        await q.answer()
        choice = q.data.partition(":")[2]
        if choice == "0":
            await main_menu(q.message, q.from_user.id)
        elif choice in {"1", "2", "3", "4"}:
            await show_korea(q.message, q.from_user.id, int(choice))

    @dp.callback_query(F.data.startswith("go:"))
    async def on_go(q: CallbackQuery):
        await q.answer()
        where = q.data.partition(":")[2]
        uid = q.from_user.id
        if where == "menu":
            await main_menu(q.message, uid)
        elif where == "korea":
            await show_korea(q.message, uid, 1)
        elif where == "manager":
            await show_manager(q.message, uid)
        elif where == "pick":
            await begin_quiz(q.message, uid, "pick", actor=q.from_user)
        elif where == "calc":
            await begin_quiz(q.message, uid, "calc", actor=q.from_user)
        elif where == "access":
            await open_access(q.message, uid)
        elif where == "auctions":
            await show_auctions(q.message, uid)

    @dp.callback_query(F.data.startswith("open:"))
    async def on_open(q: CallbackQuery):
        await q.answer()
        where = q.data.partition(":")[2]
        if where == "auctions":
            await show_auctions(q.message, q.from_user.id)
        elif where == "dealers":
            await show_dealers(q.message, q.from_user.id)

    @dp.message(F.text)
    async def on_text(message: Message):
        await handle_text(message)

    await bot.set_my_commands(kb.bot_commands())
    try:
        await bot.set_my_description(description=content.BOT_INTRO)
    except Exception as exc:
        log.warning("Could not set bot description: %s", exc)
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
