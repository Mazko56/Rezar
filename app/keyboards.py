from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def ik(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
        for row in rows
    ])


def home_kb():
    return ik([
        [("🚘 Підібрати авто", "pick"), ("🧮 Розрахувати під ключ", "calc")],
        [("🔐 Карта доступів до аукціонів", "access1")],
        [("🇰🇷 Чому Корея?", "korea1"), ("👨‍💼 Менеджер", "manager")],
    ])


def pick_freeform_kb():
    return ik([[('⬅️ Назад', 'pick_intro'), ('Далі ➡️', 'budget')]])


def budget_kb():
    return ik([
        [('до 15.000', 'budget:до 15.000'), ('15.000–20.000', 'budget:15-20')],
        [('20.000–30.000', 'budget:20-30'), ('30.000–40.000', 'budget:30-40')],
        [('40.000+', 'budget:40+'), ('ще збираю', 'budget:collecting')],
        [('⬅️ Назад', 'pick_freeform'), ('🏠 На головну', 'home')],
    ])


def purchase_kb():
    return ik([
        [('Найближчим часом', 'time:soon'), ('Протягом 1–3 місяців', 'time:1-3')],
        [('Протягом року', 'time:year'), ('Планую на майбутнє', 'time:future')],
        [('⬅️ Назад', 'budget'), ('🏠 На головну', 'home')],
    ])


def contact_request_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='📱 Поділитися контактом', request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder='Натисніть, щоб передати номер телефону',
    )


def after_contact_kb():
    return ik([
        [('🔨 АУКЦІОНИ', 'auctions'), ('🏢 ДИЛЕРИ', 'dealers')],
        [('⬅️ Назад', 'pick_done'), ('🏠 На головну', 'home')],
    ])


def auctions_kb():
    return ik([[('⬅️ Назад', 'contact_done'), ('👨‍💼 Менеджер', 'manager')]])


def dealers_kb():
    return ik([[('⬅️ Назад', 'contact_done'), ('👨‍💼 Менеджер', 'manager')]])


def calc_kb():
    return ik([[('🚀 Почати', 'pick_intro')], [('⬅️ Назад', 'home'), ('🏠 На головну', 'home')]])


def access1_kb():
    return ik([[('⬅️ Назад', 'home'), ('Далі ➡️', 'access2')]])


def access2_kb():
    return ik([[('⬅️ Назад', 'access1'), ('Зрозуміло ➡️', 'access3')]])


def access3_kb():
    return ik([[('🏠 На головну', 'home'), ('⬅️ Назад', 'access2')], [('🔓 Отримати', 'pick_intro')]])


def korea1_kb():
    return ik([[('⬅️ Назад', 'home'), ('Ще переваги ➡️', 'korea2')]])


def korea2_kb():
    return ik([[('⬅️ Назад', 'korea1'), ('Ще переваги ➡️', 'korea3')]])


def korea3_kb():
    return ik([
        [('🚘 Підібрати авто', 'pick_intro'), ('🧮 Розрахувати під ключ', 'calc')],
        [('🏠 На головну', 'home'), ('⬅️ Назад', 'korea2')],
        [('👨‍💼 Менеджер', 'manager')],
    ])


def manager_inline_kb(manager_username: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💬 Написати менеджеру', url=f'https://t.me/{manager_username}')],
        [InlineKeyboardButton(text='🏠 На головну', callback_data='home')],
    ])
