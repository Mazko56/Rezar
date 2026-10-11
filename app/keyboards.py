"""Кнопки з нового ТЗ: reply-клавіатура під СВ, inline-кнопки на повідомленнях."""
from aiogram.types import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)

PICK = "Підібрати авто"
CALC = "Розрахувати під ключ"
KOREA = "Чому авто з Кореї?"
MANAGER = "Зв’язок з менеджером"
ACCESS = "Безкоштовні доступи до аукціонів"
MENU = "меню"
SHORT_MANAGER = "менеджер"
ACCESS_SHORT = "доступи до аукціонів"
KOREA_SHORT = "а чому з Кореї?"
CONTACT = "поділитися контактом"
ACTIONS = ["до 15 тис.", "15–20 тис.", "20–30 тис", "30–40 тис.", "40+ тис.", "безліміт"]


def r(rows, *, placeholder=None):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=text, request_contact=(text == CONTACT)) for text in row]
        for row in rows
    ], resize_keyboard=True, is_persistent=True, input_field_placeholder=placeholder)


def i(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=text, callback_data=callback) for text, callback in row
    ] for row in rows])


def main_kb():
    return r([[PICK, CALC], [KOREA, MANAGER], [ACCESS]])


def quiz_kb():
    return r([[MENU, SHORT_MANAGER], [ACCESS]])


def budget_bottom_kb():
    return r([[MENU, SHORT_MANAGER]], placeholder="оберіть бюджет вище")


def car_kb():
    return r([[MENU, SHORT_MANAGER], [ACCESS]], placeholder="напишіть марку, модель")


def year_kb():
    return r([[MENU, SHORT_MANAGER], [ACCESS]], placeholder="напишіть рік/роки виготовлення")


def budget_kb():
    # Повністю згідно ТЗ: три кнопки в першому та три у другому ряду, над СВ.
    return i([
        [(ACTIONS[0], "budget:0"), (ACTIONS[1], "budget:1"), (ACTIONS[2], "budget:2")],
        [(ACTIONS[3], "budget:3"), (ACTIONS[4], "budget:4"), (ACTIONS[5], "budget:5")],
    ])


def contact_kb():
    return r([[MENU, SHORT_MANAGER], [CONTACT]])


def preferred_kb():
    return r([["в чаті", "зателефонуйте"]])


def after_kb():
    return r([[MENU, KOREA_SHORT, SHORT_MANAGER]])


def after_access_buttons():
    return i([[ ("аукціони", "open:auctions"), ("дилери", "open:dealers") ]])


def access_nav_kb():
    return r([[MENU, KOREA_SHORT, SHORT_MANAGER]])


def access_step_kb(n):
    if n == 1:
        return i([[ ("назад", "access:0"), ("далі", "access:2") ]])
    if n == 2:
        return i([[ ("назад", "access:1"), ("далі", "access:3") ]])
    return i([[ ("назад", "access:2"), ("отримати доступи", "access:get") ]])


def korea_kb(last=False):
    if last:
        return r([[PICK, CALC], [MENU, "аукціони", SHORT_MANAGER]])
    return r([[PICK, CALC], [MENU, ACCESS_SHORT, SHORT_MANAGER]])


def korea_step_kb(n):
    if n == 1:
        return i([[ ("назад", "korea:0"), ("далі", "korea:2") ]])
    if n == 2:
        return i([[ ("назад", "korea:1"), ("далі", "korea:3") ]])
    return i([[ ("назад", "korea:2"), ("Чому саме Rezar?", "korea:4") ]])


def manager_kb(has_contact=False):
    rows = [[MENU, ACCESS_SHORT]]
    if not has_contact:
        rows.append([CONTACT])
    return r(rows, placeholder="напишіть Ваш запит")


def manager_inline(username):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="написати менеджеру", url=f"https://t.me/{username.lstrip('@')}")]
    ])


def bot_commands():
    return [
        BotCommand(command="start", description="Старт"),
        BotCommand(command="pick", description=PICK),
        BotCommand(command="calc", description=CALC),
        BotCommand(command="korea", description=KOREA),
        BotCommand(command="manager", description=MANAGER),
        BotCommand(command="access", description="Доступи до аукціонів"),
    ]
