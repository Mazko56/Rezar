from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_GET = "🚘 Отримати варіанти\nавто"
BTN_CALC = "🧮 Розрахувати\nпід ключ"
BTN_KOREA = "🇰🇷 Чому авто\nз Кореї?"
BTN_MANAGER = "👨‍💼 Зв’язок з\nменеджером"
BTN_ACCESS = "🔐 Безкоштовні доступи\nдо аукціонів"

BTN_MENU = "🏠 Меню"
BTN_BACK = "⬅️ Назад"
BTN_CONSULT = "👨‍💼 Консультація"
BTN_AUCTIONS = "🔨 Аукціони"
BTN_DEALERS = "🏢 Дилери"
BTN_CHAT = "💬 В чаті"
BTN_CALL = "📞 Зателефонуйте мені"
BTN_SHARE_CONTACT = "📱 Поділитися контактом"


def _reply(rows, placeholder: str | None = None, resize: bool = True, one_time: bool = False):
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=resize,
        is_persistent=True,
        one_time_keyboard=one_time,
        input_field_placeholder=placeholder,
    )


def inline_rows(rows):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
            for row in rows
        ]
    )


def main_menu_kb():
    return _reply([
        [KeyboardButton(text=BTN_GET), KeyboardButton(text=BTN_CALC)],
        [KeyboardButton(text=BTN_KOREA), KeyboardButton(text=BTN_MANAGER)],
        [KeyboardButton(text=BTN_ACCESS)],
    ])


def intro_prompt_kb():
    return _reply([
        [KeyboardButton(text="🇰🇷 А чому Корея?"), KeyboardButton(text="👨‍💼 Зв'язок з менеджером")],
        [KeyboardButton(text="🔐 Безкоштовні доступи до аукціонів")],
    ], placeholder="Напишіть свої побажання по авто...")


def quiz_nav_kb():
    return _reply([
        [KeyboardButton(text=BTN_MENU), KeyboardButton(text=BTN_BACK), KeyboardButton(text="👨‍💼 Менеджер")],
    ])


def manager_contact_kb():
    return _reply([
        [KeyboardButton(text=BTN_SHARE_CONTACT, request_contact=True)],
        [KeyboardButton(text=BTN_MENU)],
    ])


def response_method_kb():
    return _reply([
        [KeyboardButton(text=BTN_CHAT), KeyboardButton(text=BTN_CALL)],
    ])


def access_nav_kb():
    return _reply([
        [KeyboardButton(text=BTN_MENU), KeyboardButton(text=BTN_CONSULT)],
    ])


def result_nav_kb():
    return _reply([
        [KeyboardButton(text=BTN_AUCTIONS), KeyboardButton(text=BTN_DEALERS)],
        [KeyboardButton(text=BTN_MENU), KeyboardButton(text="👨‍💼 Менеджер")],
    ])


def korea_bottom_kb():
    return _reply([
        [KeyboardButton(text=BTN_GET), KeyboardButton(text=BTN_CALC)],
        [KeyboardButton(text="🔐 Доступи до аукціонів"), KeyboardButton(text="👨‍💼 Менеджер")],
    ])


def korea_last_bottom_kb():
    return _reply([
        [KeyboardButton(text=BTN_GET), KeyboardButton(text=BTN_CALC)],
        [KeyboardButton(text=BTN_MENU), KeyboardButton(text="👨‍💼 Менеджер")],
    ])


def budget_kb():
    return _reply([
        [KeyboardButton(text="до 15.000"), KeyboardButton(text="15.000–20.000")],
        [KeyboardButton(text="20.000–30.000"), KeyboardButton(text="30.000–40.000")],
        [KeyboardButton(text="40.000–50.000"), KeyboardButton(text="50.000+")],
        [KeyboardButton(text=BTN_MENU), KeyboardButton(text=BTN_BACK), KeyboardButton(text="👨‍💼 Менеджер")],
    ])


def purchase_kb():
    return _reply([
        [KeyboardButton(text="Вже готовий розглянути")],
        [KeyboardButton(text="Протягом 1–3 міс.")],
        [KeyboardButton(text="Протягом року")],
        [KeyboardButton(text="Через рік")],
        [KeyboardButton(text=BTN_MENU), KeyboardButton(text=BTN_BACK), KeyboardButton(text="👨‍💼 Менеджер")],
    ])


def korea_page1_kb():
    return inline_rows([
        [("⬅️ Назад", "korea:home"), ("Дізнатись більше ➡️", "korea:2")],
    ])


def korea_page2_kb():
    return inline_rows([
        [("⬅️ Назад", "korea:home"), ("Дізнатись більше ➡️", "korea:3")],
    ])


def korea_page3_kb():
    return inline_rows([
        [("⬅️ Назад", "korea:home"), ("Чому саме Rezar? ➡️", "korea:4")],
    ])
