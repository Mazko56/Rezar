"""Rezar bot. Сценарій і тексти: Вставлений текст markdown(5).md."""
import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from . import content, keyboards as kb, storage
from .config import get_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
ASSETS = Path(__file__).resolve().parent.parent / "assets"

PHOTOS = {
    "home": "2.png", "presentation": "3.png", "pick": "4.png", "quiz_ready": "9.png", "calc": "10.png",
    "access1": "6.png", "access2": "11.png", "access3": "12.png",
    "korea2": "13.png", "korea3": "14.png", "korea4": "15.png",
}


def photo_file(name: str):
    path = ASSETS / PHOTOS.get(name, "not-present")
    if not path.is_file():
        return None
    with path.open("rb") as f:
        first = f.read(12)
    if first.startswith(b"\xff\xd8"):
        return FSInputFile(path, filename=f"{name}.jpg")
    if first.startswith(b"\x89PNG\r\n\x1a\n"):
        return FSInputFile(path, filename=f"{name}.png")
    return None


def escape(value):
    return str(value or "")


def after_hours():
    h = datetime.now(ZoneInfo("Europe/Kyiv")).hour
    return h < 9 or h >= 19


async def send_screen(message: Message, text: str, *, photo: str | None = None, reply_markup=None):
    """Відправляє тільки текст із ТЗ; за наявності додасть передбачене фото."""
    media = photo_file(photo) if photo else None
    if media is not None:
        try:
            if len(text) <= 1024:
                return await message.answer_photo(media, caption=text, reply_markup=reply_markup)
            await message.answer_photo(media)
        except Exception as exc:
            log.warning("Could not send %s: %s", photo, exc)
    return await message.answer(text, reply_markup=reply_markup)


async def send_dual_controls(message: Message, text: str, bottom, inline, *, photo=None):
    """Telegram не дозволяє дві клавіатури у reply_markup одного повідомлення.

    Якщо фото є, прикріплюємо reply-клавіатуру до фото, inline — до тексту;
    якщо фото немає, міняємо inline-markup повідомлення, надісланого із reply-клавіатурою.
    Ніякого додаткового повідомлення з текстом не створюємо.
    """
    media = photo_file(photo) if photo else None
    if media:
        try:
            await message.answer_photo(media, reply_markup=bottom)
            return await message.answer(text, reply_markup=inline)
        except Exception as exc:
            log.warning("Photo missing or invalid %s: %s", photo, exc)
    # Якщо абзаців два або більше, розбиваємо ЛИШЕ наявний текст із ТЗ
    # між двома повідомленнями: нижня клавіатура з першого, inline з другого.
    # Це працює на всіх клієнтах Telegram без додаткових текстів-заглушок.
    if "\n\n" in text:
        a, _, b = text.partition("\n\n")
        await message.answer(a, reply_markup=bottom)
        return await message.answer(b, reply_markup=inline)
    # Одне речення бюджету технічно неможливо відправити з двома markup одночасно.
    # Надсилаємо один раз, після чого міняємо markup на inline (reply зберігається
    # у багатьох клієнтах; керування меню також доступне через синю кнопку Menu).
    m = await message.answer(text, reply_markup=bottom)
    try:
        await m.edit_reply_markup(reply_markup=inline)
    except Exception as exc:
        log.warning("Cannot combine reply and inline for this Telegram client: %s", exc)
    return m


async def send_presentation(message: Message):
    """Медіа надає замовник. Не вставляємо текст-заглушку, якого немає в ТЗ."""
    circle = ASSETS / "presentation_circle.mp4"
    if circle.exists():
        await message.answer_video_note(FSInputFile(circle, filename="presentation_circle.mp4"))
    notes = ASSETS / "presentation.txt"
    if notes.is_file():
        txt = notes.read_text(encoding="utf-8").strip()
        if txt:
            await message.answer(txt)
    video = ASSETS / "presentation_video.mp4"
    if video.exists():
        await message.answer_video(FSInputFile(video, filename="presentation_video.mp4"))
    # 3.png з вихідного архіву є HTML-документом, не зображенням.
    legacy_image = photo_file("presentation")
    if legacy_image:
        await message.answer_photo(legacy_image)


async def main_menu(message: Message):
    storage.update(message.chat.id, view="home")
    return await message.answer(content.HOME_MENU, reply_markup=kb.main_kb())


async def start(message: Message):
    storage.read(message.from_user.id)
    storage.update(message.from_user.id, view="home")
    await send_screen(message, content.HOME, photo="home")
    await asyncio.sleep(2)
    await send_presentation(message)
    await message.answer(content.HOME_MENU, reply_markup=kb.main_kb())


async def quiz_question(message: Message, person: dict):
    stage = person.get("stage") or "car"
    if stage == "car":
        await message.answer(content.CAR_QUESTION, reply_markup=kb.car_kb())
    elif stage == "year":
        await message.answer(content.YEAR_QUESTION, reply_markup=kb.year_kb())
    elif stage == "budget":
        await send_dual_controls(message, content.BUDGET_QUESTION, kb.budget_bottom_kb(), kb.budget_kb())
    elif stage == "contact":
        if person.get("phone"):
            storage.update(message.chat.id, stage="preferred")
            await message.answer(content.PREFERRED_CONTACT, reply_markup=kb.preferred_kb())
        else:
            await send_screen(message, content.QUIZ_READY, photo="quiz_ready", reply_markup=kb.contact_kb())
    elif stage == "preferred":
        await message.answer(content.PREFERRED_CONTACT, reply_markup=kb.preferred_kb())


async def begin_quiz(message: Message, person_id: int, origin: str, *, actor=None):
    person = storage.read(person_id)
    # Не стираємо незакінчену анкету при переході між вкладками.
    if person["completed"] or (person["phone"] and person["car"] and person["year"] and person["budget"]):
        storage.update(person_id, view="result")
        if origin == "access":
            await send_completed_access_choices(message)
        else:
            await send_quiz_result(message)
        return
    if person["stage"]:
        storage.update(person_id, view="quiz")
        await quiz_question(message, person)
        return
    storage.update(person_id, stage="car", view="quiz", source=origin)
    if origin == "calc":
        await send_screen(message, content.CALC_INTRO, photo="calc")
    else:
        user = actor or message.from_user
        username = "@" + escape(user.username) if user and user.username else escape(user.first_name if user else "")
        await send_screen(message, content.PICK_INTRO.format(username=username), photo="pick")
    await quiz_question(message, storage.read(person_id))


async def send_completed_access_choices(message: Message):
    await send_dual_controls(message, "Доступи до аукціонів в Південній Кореї", kb.after_kb(), kb.after_access_buttons())


async def send_quiz_result(message: Message):
    settings = get_settings()
    result = content.QUIZ_FINISHED.format(channel=settings.channel_invite, chat=settings.chat_invite)
    await send_dual_controls(message, result, kb.after_kb(), kb.after_access_buttons())


async def show_auctions(message: Message, person_id: int):
    storage.update(person_id, view="auctions")
    variables = {
        "happy_id": os.getenv("HAPPYCAR_ID", ""),
        "happy_pw": os.getenv("HAPPYCAR_PASSWORD", ""),
        "duo_id": os.getenv("DUOCAR_ID", ""),
        "duo_pw": os.getenv("DUOCAR_PASSWORD", ""),
        "jeno_id": os.getenv("JENO_ID", ""),
        "jeno_pw": os.getenv("JENO_PASSWORD", ""),
        "glovis_id": os.getenv("GLOVIS_LOGIN", ""),
        "glovis_pw": os.getenv("GLOVIS_PASSWORD", ""),
    }
    await message.answer(content.AUCTIONS.format(**{k: escape(v) for k, v in variables.items()}), reply_markup=kb.after_kb())


async def show_dealers(message: Message, person_id: int):
    storage.update(person_id, view="dealers")
    await message.answer(content.DEALERS, reply_markup=kb.after_kb())


async def show_access(message: Message, person_id: int, n: int):
    storage.update(person_id, view="access")
    text = {1: content.ACCESS_1, 2: content.ACCESS_2, 3: content.ACCESS_3}[n]
    await send_dual_controls(message, text, kb.access_nav_kb(), kb.access_step_kb(n), photo=f"access{n}")


async def open_access(message: Message, person_id: int):
    person = storage.read(person_id)
    if person["phone"] and person["car"] and person["year"] and person["budget"]:
        await show_auctions(message, person_id)
    else:
        await show_access(message, person_id, 1)


async def show_korea(message: Message, person_id: int, n: int):
    storage.update(person_id, view="korea")
    text = {1: content.KOREA_1, 2: content.KOREA_2, 3: content.KOREA_3, 4: content.KOREA_4}[n]
    nav = kb.korea_step_kb(n) if n < 4 else None
    bottom = kb.korea_kb(last=(n == 4))
    if nav:
        await send_dual_controls(message, text, bottom, nav, photo=(f"korea{n}" if n > 1 else None))
    else:
        await send_screen(message, text, photo="korea4", reply_markup=bottom)


async def show_manager(message: Message, person_id: int):
    person = storage.read(person_id)
    storage.update(person_id, view="manager")
    await send_dual_controls(
        message, content.MANAGER, kb.manager_kb(bool(person["phone"])),
        kb.manager_inline(get_settings().manager_username)
    )


async def handle_text(message: Message):
    if not message.from_user or not message.text:
        return
    user_id = message.from_user.id
    p = storage.read(user_id)
    text = message.text.strip()

    # Константні кнопки під СВ працюють у всіх розділах.
    if text in (kb.MENU,):
        await main_menu(message)
        return
    if text in (kb.PICK,):
        await begin_quiz(message, user_id, "pick")
        return
    if text in (kb.CALC,):
        await begin_quiz(message, user_id, "calc")
        return
    if text in (kb.KOREA, kb.KOREA_SHORT):
        await show_korea(message, user_id, 1)
        return
    if text in (kb.MANAGER, kb.SHORT_MANAGER):
        await show_manager(message, user_id)
        return
    if text in (kb.ACCESS, kb.ACCESS_SHORT, "аукціони"):
        await open_access(message, user_id)
        return
    if text == "дилери":
        await show_dealers(message, user_id)
        return

    if p["view"] == "quiz":
        if p["stage"] == "car":
            storage.update(user_id, car=text, stage="year")
            await quiz_question(message, storage.read(user_id))
            return
        if p["stage"] == "year":
            storage.update(user_id, year=text, stage="budget")
            await quiz_question(message, storage.read(user_id))
            return
        if p["stage"] == "preferred" and text in ("в чаті", "зателефонуйте"):
            storage.update(user_id, contact_method=text)
            storage.close_quiz(user_id)
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
    p = storage.read(user_id)
    storage.update(user_id, phone=message.contact.phone_number)
    if p["view"] == "manager":
        reply = content.MANAGER_OFF_HOURS if after_hours() else content.MANAGER_CONTACT
        await message.answer(reply, reply_markup=kb.manager_kb(True))
        return
    if p["view"] == "quiz" and p["stage"] in ("contact", "preferred"):
        storage.update(user_id, stage="preferred")
        await message.answer(content.PREFERRED_CONTACT, reply_markup=kb.preferred_kb())


async def main():
    bot = Bot(get_settings().bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def on_start(message: Message):
        await start(message)

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

    @dp.callback_query(F.data.startswith("budget:"))
    async def on_budget(q: CallbackQuery):
        await q.answer()
        p = storage.read(q.from_user.id)
        if p["view"] != "quiz" or p["stage"] != "budget":
            return
        number = int(q.data.split(":", 1)[1])
        if 0 <= number < len(kb.ACTIONS):
            storage.update(q.from_user.id, budget=kb.ACTIONS[number], stage="contact")
            await quiz_question(q.message, storage.read(q.from_user.id))

    @dp.callback_query(F.data.startswith("access:"))
    async def on_access(q: CallbackQuery):
        await q.answer()
        choice = q.data.partition(":")[2]
        if choice == "0":
            await main_menu(q.message)
        elif choice == "get":
            await begin_quiz(q.message, q.from_user.id, "access", actor=q.from_user)
        elif choice in ("1", "2", "3"):
            await show_access(q.message, q.from_user.id, int(choice))

    @dp.callback_query(F.data.startswith("korea:"))
    async def on_korea(q: CallbackQuery):
        await q.answer()
        choice = q.data.partition(":")[2]
        if choice == "0":
            await main_menu(q.message)
        elif choice in ("1", "2", "3", "4"):
            await show_korea(q.message, q.from_user.id, int(choice))

    @dp.callback_query(F.data.startswith("open:"))
    async def on_open(q: CallbackQuery):
        await q.answer()
        name = q.data.partition(":")[2]
        if name == "auctions":
            await show_auctions(q.message, q.from_user.id)
        elif name == "dealers":
            await show_dealers(q.message, q.from_user.id)

    @dp.message(F.text)
    async def on_text(message: Message):
        await handle_text(message)

    # Синє «Меню» Telegram з шістьма командами — як у ТЗ.
    await bot.set_my_commands(kb.bot_commands())
    try:
        await bot.set_my_description(description=content.BOT_INTRO)
    except Exception as exc:
        log.warning("Set bot intro description in BotFather if needed: %s", exc)
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
