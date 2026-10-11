"""Кнопки REZAR: іконки з попередньої версії; бюджет — надійна ReplyKeyboardMarkup."""
from aiogram.types import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)

PICK = "🚘 Підібрати авто"
CALC = "🧮 Розрахувати під ключ"
KOREA = "🇰🇷 Чому авто з Кореї?"
MANAGER = "👨‍💼 Зв’язок з менеджером"
ACCESS = "🔐 Безкоштовні доступи до аукціонів"
MENU = "🏠 меню"
SHORT_MANAGER = "👨‍💼 менеджер"
ACCESS_SHORT = "🔐 доступи до аукціонів"
KOREA_SHORT = "🇰🇷 а чому з Кореї?"
CONTACT = "📱 поділитися контактом"
AUCTIONS = "🔨 аукціони"
DEALERS = "🏢 дилери"
CHAT = "💬 в чаті"
CALL = "📞 зателефонуйте"
BACK = "⬅️ назад"
NEXT = "далі ➡️"
GET_ACCESS = "🔓 отримати доступи"
WRITE_MANAGER = "💬 написати менеджеру"
WHY_REZAR = "🇰🇷 Чому саме Rezar?"

# Точні варіанти з нового ТЗ (без додаткових діапазонів), тільки іконки.
ACTIONS = ["💵 до 15 тис.", "💵 15–20 тис.", "💵 20–30 тис", 
           "💵 30–40 тис.", "💵 40+ тис.", "💵 безліміт"]


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
    # Залишено для сумісності з попередніми викликами.
    return r([[MENU, SHORT_MANAGER]])


def car_kb():
    return r([[MENU, SHORT_MANAGER], [ACCESS]], placeholder="напишіть марку, модель")


def year_kb():
    return r([[MENU, SHORT_MANAGER], [ACCESS]], placeholder="напишіть рік/роки виготовлення")


def budget_kb():
    # Надійно відображається саме під рядком вводу у Telegram, без edit_reply_markup.
    # 3+3 бюджети з ТЗ; нижче тільки «меню» та «менеджер».
    return r([ACTIONS[:3], ACTIONS[3:], [MENU, SHORT_MANAGER]])


def contact_kb():
    return r([[MENU, SHORT_MANAGER], [CONTACT]])


def preferred_kb():
    return r([[CHAT, CALL]])


def after_kb():
    return r([[MENU, KOREA_SHORT, SHORT_MANAGER]])


def after_access_buttons():
    return i([[(AUCTIONS, "open:auctions"), (DEALERS, "open:dealers")]])


def access_nav_kb():
    return r([[MENU, KOREA_SHORT, SHORT_MANAGER]])


def access_step_kb(n):
    if n == 1:
        return i([[(BACK, "access:0"), (NEXT, "access:2")]])
    if n == 2:
        return i([[(BACK, "access:1"), (NEXT, "access:3")]])
    return i([[(BACK, "access:2"), (GET_ACCESS, "access:get")]])


def korea_kb(last=False):
    if last:
        return r([[PICK, CALC], [MENU, AUCTIONS, SHORT_MANAGER]])
    return r([[PICK, CALC], [MENU, ACCESS_SHORT, SHORT_MANAGER]])


def korea_step_kb(n):
    if n == 1:
        return i([[(BACK, "korea:0"), (NEXT, "korea:2")]])
    if n == 2:
        return i([[(BACK, "korea:1"), (NEXT, "korea:3")]])
    return i([[(BACK, "korea:2"), (WHY_REZAR, "korea:4")]])


def manager_kb(has_contact=False):
    rows = [[MENU, ACCESS_SHORT]]
    if not has_contact:
        rows.append([CONTACT])
    return r(rows, placeholder="напишіть Ваш запит")


def manager_inline(username):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=WRITE_MANAGER, url=f"https://t.me/{username.lstrip('@')}")]
    ])


def bot_commands():
    return [
        BotCommand(command="start", description="🚀 Старт"),
        BotCommand(command="pick", description=PICK),
        BotCommand(command="calc", description=CALC),
        BotCommand(command="korea", description=KOREA),
        BotCommand(command="manager", description=MANAGER),
        BotCommand(command="access", description="🔐 Доступи до аукціонів"),
    ]
