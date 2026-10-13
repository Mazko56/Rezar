"""REZAR: inline means under the screen; reply keyboard means under input."""
from aiogram.types import (
    BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
    ReplyKeyboardMarkup,
)

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

ACTIONS = ["до 15 тис.", "15–20 тис.", "20–30 тис.",
           "30–40 тис.", "40+ тис.", "безліміт"]


def r(rows, *, placeholder=None):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=s, request_contact=(s == CONTACT)) for s in row] for row in rows],
        resize_keyboard=True, is_persistent=True, input_field_placeholder=placeholder,
    )


def i(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback) for text, callback in row] for row in rows
    ])


def main_kb():
    return r([[PICK, CALC], [KOREA, MANAGER], [ACCESS]])


def car_kb():
    return r([[SHORT_MANAGER], [ACCESS]], placeholder="напишіть марку, модель")


def year_kb():
    return r([[SHORT_MANAGER], [ACCESS]], placeholder="рік виробництва")


def budget_kb():
    return i([[(label, f"budget:{n}") for n, label in enumerate(ACTIONS[:3])],
              [(label, f"budget:{n+3}") for n, label in enumerate(ACTIONS[3:])]])


def budget_nav_kb():
    return r([[SHORT_MANAGER]], placeholder="оберіть бюджет вище")


def contact_kb():
    return r([[CONTACT]])


def preferred_kb():
    return r([[CHAT, CALL]])


def after_kb():
    return r([[KOREA_SHORT, SHORT_MANAGER]])


def repeat_access_buttons():
    return i([[(AUCTIONS, "open:auctions")], [(DEALERS, "open:dealers")]])


def after_access_buttons():
    return i([[(AUCTIONS, "open:auctions"), (DEALERS, "open:dealers")]])


def access_nav_kb():
    # ONLY three buttons under the text-input field, not under access message.
    return r([[KOREA_SHORT, SHORT_MANAGER]])


def access_step_kb(n):
    if n == 1:
        return i([[(BACK, "access:0"), (NEXT, "access:2")]])
    if n == 2:
        return i([[(BACK, "access:1"), (NEXT, "access:3")]])
    return i([[(BACK, "access:2"), (GET_ACCESS, "access:get")]])


def korea_nav_kb():
    # All Korea screens: five buttons below input, in the exact 2 + 3 layout.
    return r([[PICK, CALC], [ACCESS_SHORT, SHORT_MANAGER]])


def korea_last_nav_kb():
    # Final Korea screen: same five bottom buttons and no inline controls.
    return korea_nav_kb()


def korea_step_kb(n):
    if n == 1:
        return i([[(BACK, "korea:0"), (NEXT, "korea:2")]])
    if n == 2:
        return i([[(BACK, "korea:1"), (NEXT, "korea:3")]])
    return i([[(BACK, "korea:2"), (WHY_REZAR, "korea:4")]])


def manager_kb(has_contact=False):
    rows = [[KOREA_SHORT, ACCESS_SHORT]]
    if not has_contact:
        rows.append([CONTACT])
    return r(rows, placeholder="напишіть Ваш запит")


def manager_inline(username):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=WRITE_MANAGER, url=f"https://t.me/{username.lstrip('@')}")]
    ])


def default_commands():
    # Telegram requires ASCII command names; descriptions are Ukrainian.
    return [
        BotCommand(command="start", description="🚀 Старт"),
        BotCommand(command="pick", description="🚘 Підібрати авто"),
        BotCommand(command="calc", description="🧮 Розрахувати під ключ"),
        BotCommand(command="korea", description="🇰🇷 Чому авто з Кореї?"),
        BotCommand(command="manager", description="👨‍💼 Зв’язок з менеджером"),
        BotCommand(command="access", description="🔐 Доступи до аукціонів"),
    ]


def admin_commands():
    return default_commands() + [BotCommand(command="admin", description="🛠 Адмінка")]
