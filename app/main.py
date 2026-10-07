import asyncio
import html
import os
import logging
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, FSInputFile, Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

from . import content
from .config import get_settings
from .keyboards import (
    access1_kb,
    access2_kb,
    access3_kb,
    after_contact_kb,
    auctions_kb,
    budget_kb,
    calc_kb,
    contact_request_kb,
    dealers_kb,
    home_kb,
    ik,
    korea1_kb,
    korea2_kb,
    korea3_kb,
    manager_inline_kb,
    pick_freeform_kb,
    purchase_kb,
)


class PickFlow(StatesGroup):
    freeform = State()
    budget = State()
    purchase_time = State()
    waiting_contact = State()


BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

PHOTO_MAP = {
    "PHOTO_WELCOME": "1.png",
    "PHOTO_HOME_INTRO": "2.png",
    "PHOTO_PRESENTATION": "3.png",
    "PHOTO_PICK": "4.png",
    "PHOTO_PICK_DONE": "5.png",
    "PHOTO_CONTACT_DONE": "6.png",
    "PHOTO_AUCTIONS": "7.png",
    "PHOTO_DEALERS": "8.png",
    "PHOTO_CALC": "9.png",
    "PHOTO_ACCESS_1": "10.png",
    "PHOTO_ACCESS_2": "11.png",
    "PHOTO_ACCESS_3": "12.png",
    "PHOTO_KOREA_1": "13.png",
    "PHOTO_KOREA_2": "14.png",
    "PHOTO_KOREA_3": "15.png",
    "PHOTO_MANAGER": "16.png",
}


def photo_path(photo_key: Optional[str]) -> Optional[Path]:
    if not photo_key:
        return None
    filename = PHOTO_MAP.get(photo_key)
    if not filename:
        return None
    path = ASSETS_DIR / filename
    return path if path.exists() else None


async def send_screen(message: Message, text: str, keyboard=None, photo_key: Optional[str] = None):
    """Send a screen and never break the scenario only because a local photo failed."""
    path = photo_path(photo_key)
    if path:
        try:
            # Telegram photo captions are shorter than normal messages.
            # If a future text becomes too long, send photo and text separately.
            if len(text) <= 1000:
                await message.answer_photo(photo=FSInputFile(path), caption=text, reply_markup=keyboard)
            else:
                await message.answer_photo(photo=FSInputFile(path))
                await message.answer(text, reply_markup=keyboard)
            return
        except Exception as exc:
            logging.exception("Failed to send photo %s: %s", path, exc)
    # Fallback: the flow must continue even when an image is missing/broken/too large.
    await message.answer(text, reply_markup=keyboard)


async def edit_or_send(query: CallbackQuery, text: str, keyboard=None, photo_key: Optional[str] = None):
    path = photo_path(photo_key)
    if path:
        await query.message.answer_photo(photo=FSInputFile(path), caption=text, reply_markup=keyboard)
    else:
        try:
            if query.message.photo:
                await query.message.answer(text, reply_markup=keyboard)
            else:
                await query.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await query.message.answer(text, reply_markup=keyboard)
    await query.answer()


async def show_home(message: Message):
    await message.answer(content.HOME_MENU_PROMPT, reply_markup=home_kb())


async def show_auctions(message: Message):
    manager = get_settings().manager_username
    happy_id = os.getenv("HAPPYCAR_ID", "—") or "—"
    happy_pw = os.getenv("HAPPYCAR_PASSWORD", "—") or "—"
    duo_id = os.getenv("DUOCAR_ID", "—") or "—"
    duo_pw = os.getenv("DUOCAR_PASSWORD", "—") or "—"
    jeno_id = os.getenv("JENO_ID", "—") or "—"
    jeno_pw = os.getenv("JENO_PASSWORD", "—") or "—"
    glovis_id = os.getenv("GLOVIS_LOGIN", "—") or "—"
    glovis_pw = os.getenv("GLOVIS_PASSWORD", "—") or "—"
    text = (
        f"🔨 <b>АУКЦІОНИ</b>\n\n"
        f"Принципи торгівлі, правила участі в аукціоні, як зробити ставку та відповіді "
        f"на інші питання отримуйте у менеджера @{manager}.\n"
        f"Права доступів назавжди збережені для Вас у цьому боті.\n\n"
        f"<b>ХЕПІКАР</b>\nhttps://happycarservice.com/member/login.html\n"
        f"ID: <code>{html.escape(happy_id)}</code>\nPassword: <code>{html.escape(happy_pw)}</code>\n\n"
        f"<b>ДУОКАР</b>\nhttps://duocar.co.kr/\n"
        f"ID: <code>{html.escape(duo_id)}</code>\nPassword: <code>{html.escape(duo_pw)}</code>\n\n"
        f"<b>ДЖЕНО-МОТОРС</b>\nhttp://jenomotors.com/main/main.php\n"
        f"ID: <code>{html.escape(jeno_id)}</code>\nPassword: <code>{html.escape(jeno_pw)}</code>\n\n"
        f"<b>ГЛОВІС</b>\nhttps://auction.autobell.co.kr/info/programDown.do\n"
        f"Login: <code>{html.escape(glovis_id)}</code>\nPassword: <code>{html.escape(glovis_pw)}</code>\n\n"
        f"Доставимо авто у Ваше місто. Фіксуємо вартість у договорі. Оплата в 4 етапи. "
        f"Пряма угода без посередників. Морський фрахт — орієнтовно 2 місяці."
    )
    await send_screen(message, text, auctions_kb(), "PHOTO_AUCTIONS")


async def main():
    settings = get_settings()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    @dp.message(CommandStart())
    async def start(message: Message, state: FSMContext):
        await state.clear()

        # IMPORTANT: WELCOME + 1.png belong to Telegram Bot Intro and are configured
        # in BotFather. They are intentionally NOT sent again after /start.
        await send_screen(message, content.HOME_INTRO, photo_key="PHOTO_HOME_INTRO")

        await asyncio.sleep(3)
        try:
            await send_screen(message, content.MINI_PRESENTATION, photo_key="PHOTO_PRESENTATION")
        finally:
            # Even if presentation media has a problem, always show the main menu.
            await show_home(message)

    @dp.callback_query(F.data == "home")
    async def cb_home(q: CallbackQuery, state: FSMContext):
        await state.clear()
        await edit_or_send(q, content.HOME_MENU_PROMPT, home_kb())

    @dp.callback_query(F.data.in_({"pick", "pick_intro"}))
    async def cb_pick_intro(q: CallbackQuery, state: FSMContext):
        await state.clear()
        name = q.from_user.username and f"@{html.escape(q.from_user.username)}" or html.escape(q.from_user.first_name or "користувач")
        await edit_or_send(
            q,
            content.PICK_INTRO.format(name=name),
            ik([[ ("Поїхали 🚀", "pick_freeform") ], [ ("🏠 На головну", "home") ]]),
            "PHOTO_PICK",
        )

    @dp.callback_query(F.data == "pick_freeform")
    async def cb_pick_freeform(q: CallbackQuery, state: FSMContext):
        await state.set_state(PickFlow.freeform)
        await edit_or_send(q, content.PICK_FREEFORM, pick_freeform_kb())

    @dp.message(PickFlow.freeform)
    async def save_freeform(message: Message, state: FSMContext):
        if not message.text:
            await message.answer("Будь ласка, надішліть побажання текстом.")
            return
        await state.update_data(freeform=message.text)
        await state.set_state(PickFlow.budget)
        await message.answer("✅ Побажання збережено.")
        await message.answer(content.BUDGET, reply_markup=budget_kb())

    @dp.callback_query(F.data == "budget")
    async def cb_budget(q: CallbackQuery, state: FSMContext):
        await state.set_state(PickFlow.budget)
        await edit_or_send(q, content.BUDGET, budget_kb())

    @dp.callback_query(F.data.startswith("budget:"))
    async def cb_budget_value(q: CallbackQuery, state: FSMContext):
        await state.update_data(budget=q.data.split(":", 1)[1])
        await state.set_state(PickFlow.purchase_time)
        await edit_or_send(q, content.PURCHASE_TIME, purchase_kb())

    @dp.callback_query(F.data.startswith("time:"))
    async def cb_time(q: CallbackQuery, state: FSMContext):
        await state.update_data(purchase_time=q.data.split(":", 1)[1])
        await state.set_state(PickFlow.waiting_contact)
        await q.answer()
        await send_screen(q.message, content.PICK_DONE, photo_key="PHOTO_PICK_DONE")
        await q.message.answer("Для передачі запиту менеджеру поділіться номером телефону:", reply_markup=contact_request_kb())

    @dp.callback_query(F.data == "pick_done")
    async def cb_pick_done(q: CallbackQuery, state: FSMContext):
        await state.set_state(PickFlow.waiting_contact)
        await q.answer()
        await send_screen(q.message, content.PICK_DONE, photo_key="PHOTO_PICK_DONE")
        await q.message.answer("Для передачі запиту менеджеру поділіться номером телефону:", reply_markup=contact_request_kb())

    @dp.message(F.contact)
    async def receive_contact(message: Message, state: FSMContext):
        await state.update_data(phone=message.contact.phone_number)
        settings2 = get_settings()
        await message.answer("✅ Контакт отримано.", reply_markup=ReplyKeyboardRemove())
        await send_screen(
            message,
            content.CONTACT_DONE.format(manager=html.escape(settings2.manager_username)),
            after_contact_kb(),
            "PHOTO_CONTACT_DONE",
        )
        await message.answer(
            "Корисні посилання:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Офіційний канал", url=settings2.channel_invite)],
                [InlineKeyboardButton(text="💬 Чат", url=settings2.chat_invite)],
            ])
        )

    @dp.callback_query(F.data == "contact_done")
    async def cb_contact_done(q: CallbackQuery):
        s = get_settings()
        await edit_or_send(q, content.CONTACT_DONE.format(manager=html.escape(s.manager_username)), after_contact_kb(), "PHOTO_CONTACT_DONE")

    @dp.callback_query(F.data == "auctions")
    async def cb_auctions(q: CallbackQuery):
        await q.answer()
        await show_auctions(q.message)

    @dp.callback_query(F.data == "dealers")
    async def cb_dealers(q: CallbackQuery):
        await edit_or_send(q, content.DEALERS, dealers_kb(), "PHOTO_DEALERS")

    @dp.callback_query(F.data == "calc")
    async def cb_calc(q: CallbackQuery):
        await edit_or_send(q, content.CALC, calc_kb(), "PHOTO_CALC")

    @dp.callback_query(F.data == "access1")
    async def cb_access1(q: CallbackQuery):
        await edit_or_send(q, content.ACCESS_1, access1_kb(), "PHOTO_ACCESS_1")

    @dp.callback_query(F.data == "access2")
    async def cb_access2(q: CallbackQuery):
        await edit_or_send(q, content.ACCESS_2, access2_kb(), "PHOTO_ACCESS_2")

    @dp.callback_query(F.data == "access3")
    async def cb_access3(q: CallbackQuery):
        await edit_or_send(q, content.ACCESS_3, access3_kb(), "PHOTO_ACCESS_3")

    @dp.callback_query(F.data == "korea1")
    async def cb_korea1(q: CallbackQuery):
        await edit_or_send(q, content.KOREA_1, korea1_kb(), "PHOTO_KOREA_1")

    @dp.callback_query(F.data == "korea2")
    async def cb_korea2(q: CallbackQuery):
        await edit_or_send(q, content.KOREA_2, korea2_kb(), "PHOTO_KOREA_2")

    @dp.callback_query(F.data == "korea3")
    async def cb_korea3(q: CallbackQuery):
        await edit_or_send(q, content.KOREA_3, korea3_kb(), "PHOTO_KOREA_3")

    @dp.callback_query(F.data == "manager")
    async def cb_manager(q: CallbackQuery):
        s = get_settings()
        await q.answer()
        await send_screen(q.message, content.MANAGER, manager_inline_kb(s.manager_username), "PHOTO_MANAGER")
        await q.message.answer("Або передайте номер телефону:", reply_markup=contact_request_kb())

    @dp.message()
    async def fallback(message: Message):
        await message.answer("Оберіть потрібний розділ у меню 👇", reply_markup=home_kb())

    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
