import asyncio
import html
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, FSInputFile, Message

from . import content
from .config import get_settings
from .keyboards import (
    BTN_ACCESS,
    BTN_AUCTIONS,
    BTN_BACK,
    BTN_CALC,
    BTN_CHAT,
    BTN_CONSULT,
    BTN_DEALERS,
    BTN_GET,
    BTN_KOREA,
    BTN_MANAGER,
    BTN_MENU,
    BTN_CALL,
    access_nav_kb,
    budget_kb,
    intro_prompt_kb,
    korea_bottom_kb,
    korea_last_bottom_kb,
    korea_page1_kb,
    korea_page2_kb,
    korea_page3_kb,
    main_menu_kb,
    manager_contact_kb,
    purchase_kb,
    quiz_nav_kb,
    response_method_kb,
    result_nav_kb,
)


class QuizFlow(StatesGroup):
    freeform = State()
    budget = State()
    purchase_time = State()
    city = State()
    waiting_contact = State()
    waiting_response = State()


BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
USER_FLAGS: dict[int, dict] = {}

PHOTO_FILES = {
    "home_intro": "2.png",
    "presentation": "3.png",
    "pick_intro": "4.png",
    "manager": "5.png",
    "access": "6.png",
    "dealers": "7.png",
    "korea1": "8.png",
    "korea2": "9.png",
    "korea3": "10.png",
    "korea4": "11.png",
}


def flag(user_id: int) -> dict:
    return USER_FLAGS.setdefault(user_id, {"contact_shared": False})


def get_photo(name: str):
    filename = PHOTO_FILES.get(name)
    if not filename:
        return None
    path = ASSETS_DIR / filename
    return path if path.exists() else None


async def send_with_optional_photo(message: Message, text: str, photo_name: str | None = None, reply_markup=None):
    photo = get_photo(photo_name) if photo_name else None
    if photo:
        try:
            await message.answer_photo(FSInputFile(photo), caption=text, reply_markup=reply_markup)
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=reply_markup)


def current_is_after_hours() -> bool:
    now = datetime.now(ZoneInfo("Europe/Kyiv"))
    return now.hour >= 20 or now.hour < 8


async def show_home(message: Message, state: FSMContext | None = None):
    if state:
        await state.clear()
    await message.answer(content.HOME_MENU_PROMPT, reply_markup=main_menu_kb())


async def start_quiz(message: Message, state: FSMContext, source: str):
    await state.clear()
    await state.set_state(QuizFlow.freeform)
    await state.update_data(source=source)
    name = message.from_user.username and f"@{html.escape(message.from_user.username)}" or html.escape(message.from_user.first_name or "користувач")
    await send_with_optional_photo(message, content.PICK_INTRO.format(name=name), "pick_intro")
    await message.answer(content.FREEFORM_PROMPT, reply_markup=intro_prompt_kb())


async def show_manager(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(QuizFlow.waiting_contact)
    await state.update_data(source="manager")
    if flag(message.from_user.id).get("contact_shared"):
        await message.answer(content.RESPONSE_METHOD_PROMPT, reply_markup=response_method_kb())
        await state.set_state(QuizFlow.waiting_response)
    else:
        await send_with_optional_photo(message, content.MANAGER_SECTION, "manager", manager_contact_kb())


async def show_access(message: Message):
    happy_id = os.getenv("HAPPYCAR_ID", "—") or "—"
    happy_pw = os.getenv("HAPPYCAR_PASSWORD", "—") or "—"
    duo_id = os.getenv("DUOCAR_ID", "—") or "—"
    duo_pw = os.getenv("DUOCAR_PASSWORD", "—") or "—"
    jeno_id = os.getenv("JENO_ID", "—") or "—"
    jeno_pw = os.getenv("JENO_PASSWORD", "—") or "—"
    glovis_id = os.getenv("GLOVIS_LOGIN", "—") or "—"
    glovis_pw = os.getenv("GLOVIS_PASSWORD", "—") or "—"
    text = (
        f"<b>ХЕПІКАР</b>\nhttps://happycarservice.com/member/login.html\n"
        f"ID: <code>{html.escape(happy_id)}</code>\nPassword: <code>{html.escape(happy_pw)}</code>\n\n"
        f"<b>ДУОКАР</b>\nhttps://duocar.co.kr/\n"
        f"ID: <code>{html.escape(duo_id)}</code>\nPassword: <code>{html.escape(duo_pw)}</code>\n\n"
        f"<b>ДЖЕНО-МОТОРС</b>\nhttp://jenomotors.com/main/main.php\n"
        f"ID: <code>{html.escape(jeno_id)}</code>\nPassword: <code>{html.escape(jeno_pw)}</code>\n\n"
        f"<b>ГЛОВІС</b>\nhttps://auction.autobell.co.kr/info/programDown.do\n"
        f"Login: <code>{html.escape(glovis_id)}</code>\nPassword: <code>{html.escape(glovis_pw)}</code>\n\n"
        f"{content.ACCESS_FOOTER}"
    )
    await send_with_optional_photo(message, text, "access", access_nav_kb())


async def show_korea_page(message: Message, page: int):
    if page == 1:
        await send_with_optional_photo(message, content.KOREA_1, "korea1", korea_page1_kb())
        await message.answer("Оберіть наступний крок у меню нижче 👇", reply_markup=korea_bottom_kb())
    elif page == 2:
        await send_with_optional_photo(message, content.KOREA_2, "korea2", korea_page2_kb())
        await message.answer("Оберіть наступний крок у меню нижче 👇", reply_markup=korea_bottom_kb())
    elif page == 3:
        await send_with_optional_photo(message, content.KOREA_3, "korea3", korea_page3_kb())
        await message.answer("Оберіть наступний крок у меню нижче 👇", reply_markup=korea_bottom_kb())
    else:
        await send_with_optional_photo(message, content.KOREA_4, "korea4", korea_last_bottom_kb())


async def finish_contact_flow(message: Message, state: FSMContext):
    data = await state.get_data()
    source = data.get("source", "quiz")
    if source == "manager":
        text = content.MANAGER_AFTER_HOURS if current_is_after_hours() else content.MANAGER_WORK_HOURS
        await message.answer(text, reply_markup=access_nav_kb())
        await state.clear()
        return

    text = content.AFTER_HOURS_RESULT if current_is_after_hours() else content.WORK_HOURS_RESULT
    await message.answer(text, reply_markup=result_nav_kb())
    await state.clear()


async def main():
    settings = get_settings()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    @dp.message(CommandStart())
    async def start(message: Message, state: FSMContext):
        await state.clear()
        await send_with_optional_photo(message, content.HOME_INTRO, "home_intro")
        await asyncio.sleep(3)
        await send_with_optional_photo(message, content.MINI_PRESENTATION, "presentation")
        await message.answer(content.HOME_MENU_PROMPT, reply_markup=main_menu_kb())

    @dp.message(F.text == BTN_MENU)
    async def menu_handler(message: Message, state: FSMContext):
        await show_home(message, state)

    @dp.message(F.text.in_({BTN_GET, BTN_CALC}))
    async def main_quiz_sections(message: Message, state: FSMContext):
        source = "calc" if message.text == BTN_CALC else "pick"
        await start_quiz(message, state, source)

    @dp.message(F.text.in_({BTN_KOREA, "🇰🇷 А чому Корея?"}))
    async def korea_entry(message: Message, state: FSMContext):
        await state.clear()
        await show_korea_page(message, 1)

    @dp.message(F.text.in_({BTN_MANAGER, "👨‍💼 Менеджер", "👨‍💼 Зв'язок з менеджером", BTN_CONSULT}))
    async def manager_entry(message: Message, state: FSMContext):
        await show_manager(message, state)

    @dp.message(F.text.in_({BTN_ACCESS, "🔐 Безкоштовні доступи до аукціонів", "🔐 Доступи до аукціонів", BTN_AUCTIONS}))
    async def access_entry(message: Message, state: FSMContext):
        await state.clear()
        await show_access(message)

    @dp.message(F.text == BTN_DEALERS)
    async def dealers_entry(message: Message, state: FSMContext):
        await state.clear()
        await send_with_optional_photo(message, content.DEALERS, "dealers", access_nav_kb())

    @dp.message(QuizFlow.freeform)
    async def freeform_input(message: Message, state: FSMContext):
        if not message.text:
            return
        await state.update_data(freeform=message.text)
        await state.set_state(QuizFlow.budget)
        await message.answer(content.BUDGET_PROMPT, reply_markup=budget_kb())
        

    @dp.message(QuizFlow.budget, F.text.in_({"до 15.000", "15.000–20.000", "20.000–30.000", "30.000–40.000", "40.000–50.000", "50.000+"}))
    async def budget_selected(message: Message, state: FSMContext):
        await state.update_data(budget=message.text)
        await state.set_state(QuizFlow.purchase_time)
        await message.answer(content.TIME_PROMPT, reply_markup=purchase_kb())

    @dp.message(QuizFlow.purchase_time, F.text.in_({"Вже готовий розглянути", "Протягом 1–3 міс.", "Протягом року", "Через рік"}))
    async def time_selected(message: Message, state: FSMContext):
        await state.update_data(purchase_time=message.text)
        await state.set_state(QuizFlow.city)
        await message.answer(content.CITY_PROMPT, reply_markup=quiz_nav_kb())

    @dp.message(QuizFlow.city)
    async def city_input(message: Message, state: FSMContext):
        if not message.text:
            return
        await state.update_data(city=message.text)
        await state.set_state(QuizFlow.waiting_contact)
        if flag(message.from_user.id).get("contact_shared"):
            await message.answer(content.RESPONSE_METHOD_PROMPT, reply_markup=response_method_kb())
            await state.set_state(QuizFlow.waiting_response)
        else:
            await message.answer(content.CONTACT_PROMPT, reply_markup=manager_contact_kb())

    @dp.message(F.contact)
    async def contact_received(message: Message, state: FSMContext):
        flag(message.from_user.id)["contact_shared"] = True
        await state.update_data(phone=message.contact.phone_number)
        await state.set_state(QuizFlow.waiting_response)
        await message.answer(content.RESPONSE_METHOD_PROMPT, reply_markup=response_method_kb())

    @dp.message(QuizFlow.waiting_response, F.text.in_({BTN_CHAT, BTN_CALL}))
    async def response_method_selected(message: Message, state: FSMContext):
        await state.update_data(response_method=message.text)
        await finish_contact_flow(message, state)

    @dp.message(F.text == BTN_BACK)
    async def back_handler(message: Message, state: FSMContext):
        current = await state.get_state()
        if current == QuizFlow.budget.state:
            await state.set_state(QuizFlow.freeform)
            await message.answer(content.FREEFORM_PROMPT, reply_markup=intro_prompt_kb())
        elif current == QuizFlow.purchase_time.state:
            await state.set_state(QuizFlow.budget)
            await message.answer(content.BUDGET_PROMPT, reply_markup=budget_kb())
            
        elif current == QuizFlow.city.state:
            await state.set_state(QuizFlow.purchase_time)
            await message.answer(content.TIME_PROMPT, reply_markup=purchase_kb())
            
        elif current == QuizFlow.waiting_contact.state:
            await state.set_state(QuizFlow.city)
            await message.answer(content.CITY_PROMPT, reply_markup=quiz_nav_kb())
        elif current == QuizFlow.waiting_response.state:
            await state.set_state(QuizFlow.waiting_contact)
            await message.answer(content.CONTACT_PROMPT, reply_markup=manager_contact_kb())
        else:
            await show_home(message, state)

    @dp.callback_query(F.data == "korea:home")
    async def korea_home(query: CallbackQuery, state: FSMContext):
        await query.answer()
        await show_home(query.message, state)

    @dp.callback_query(F.data == "korea:2")
    async def korea_2(query: CallbackQuery):
        await query.answer()
        await show_korea_page(query.message, 2)

    @dp.callback_query(F.data == "korea:3")
    async def korea_3(query: CallbackQuery):
        await query.answer()
        await show_korea_page(query.message, 3)

    @dp.callback_query(F.data == "korea:4")
    async def korea_4(query: CallbackQuery):
        await query.answer()
        await show_korea_page(query.message, 4)

    @dp.message()
    async def fallback(message: Message, state: FSMContext):
        current = await state.get_state()
        if current == QuizFlow.waiting_response.state:
            await message.answer(content.RESPONSE_METHOD_PROMPT, reply_markup=response_method_kb())
        elif current == QuizFlow.waiting_contact.state and not flag(message.from_user.id).get("contact_shared"):
            await message.answer(content.CONTACT_PROMPT, reply_markup=manager_contact_kb())
        else:
            await message.answer(content.HOME_MENU_PROMPT, reply_markup=main_menu_kb())

    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
