import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import get_or_create_conversation, update_conversation
from services.booking import create_booking

logger = logging.getLogger(__name__)

RUSSIA_BRANCHES = {
    "branch_avtozavod": ("м. Автозаводская", "ул. Восточная, 4А, с.4, ФОК Торпедо"),
    "branch_akademic": ("м. Академическая/Крымская", "ул. Шверника, 13, корп. 2, ЦКИД Академический"),
    "branch_dubrovka": ("м. Дубровка", "ул. Велозаводская, 11/1, Библиотека №124"),
    "branch_kaluzh": ("м. Калужская/Новаторская", "ул. Обручева, 24, Библиотека №188"),
    "branch_leninsky": ("Ленинский проспект", "Ленинский пр-т, 37А, Библиотека №166"),
    "branch_taganka": ("м. Таганская", "Новоспасский пер., д. 5, Библиотека №16"),
    "branch_shabolovka": ("м. Шаболовская", "Серпуховский Вал, 24"),
    "branch_khimki": ("г. Химки", "Юбилейный проспект 20, Библио-Холл"),
}

UAE_BRANCHES = {
    "branch_dubai_blue": ("Bluewaters", "DRVN Porshe restaurant, Dubai"),
    "branch_dubai_jalila": ("Al Jalila Centre", "Al Jalila Cultural Centre for Children, Dubai"),
}

PRICES_STANDARD = (
    "• Пробное занятие (55 мин, в группе) — 900 ₽\n"
    "• Разовое (55 мин, в группе) — 1600 ₽\n"
    "• Абонемент 4 занятия в группе — 4800 ₽\n"
    "• Абонемент 8 занятий в группе — 7200 ₽\n"
    "• Индивидуальное занятие (55 мин) — 3500 ₽"
)

PRICES_ONLINE = (
    "• Пробное онлайн — 900 ₽\n"
    "• Абонемент 8 занятий в группе — 4800 ₽/мес\n"
    "• Индивидуальное онлайн — от 3500 ₽"
)


def age_keyboard(back: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧒 Детский", callback_data="age_child"),
         InlineKeyboardButton("👨 Взрослый", callback_data="age_adult")],
        [InlineKeyboardButton("⬅ Назад", callback_data=back)],
    ])


def branch_keyboard(branches: dict, back: str | None = None):
    kb = [[InlineKeyboardButton(f"📍 {v[0]}", callback_data=k)] for k, v in branches.items()]
    if back:
        kb.append([InlineKeyboardButton("⬅ Назад", callback_data=back)])
    return InlineKeyboardMarkup(kb)


def format_keyboard(back: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💻 Онлайн", callback_data="format_online"),
         InlineKeyboardButton("🏫 В филиале", callback_data="format_offline")],
        [InlineKeyboardButton("⬅ Назад", callback_data=back)],
    ])


def edit_field_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Имя", callback_data="edit_name")],
        [InlineKeyboardButton("📞 Телефон", callback_data="edit_phone")],
        [InlineKeyboardButton("⬅ Назад", callback_data="edit_back")],
    ])


async def country_callback(query, context, user_id, username, first_name, data):
    country = "russia" if data == "country_russia" else "uae"
    context.user_data["country"] = country
    get_or_create_conversation(user_id, username, first_name)
    update_conversation(user_id, {"country": country})
    await query.edit_message_text(
        "Кто будет заниматься?",
        reply_markup=age_keyboard("back_country"),
    )


async def age_callback(query, context, user_id, data):
    age = "child" if data == "age_child" else "adult"
    context.user_data["age_group"] = age
    update_conversation(user_id, {"age_group": age})
    await query.edit_message_text(
        "Как хотите заниматься?",
        reply_markup=format_keyboard("back_age"),
    )


async def format_callback(query, context, user_id, data):
    fmt = "online" if data == "format_online" else "offline"
    context.user_data["format"] = fmt
    update_conversation(user_id, {"format": fmt})

    if fmt == "online":
        branch = "Онлайн"
        context.user_data["branch"] = branch
        update_conversation(user_id, {"branch": branch})
        await query.edit_message_text(
            f"💻 Онлайн-обучение по всему миру\n\n{PRICES_ONLINE}\n\nКак вас зовут?"
        )
    else:
        conv = get_or_create_conversation(user_id)
        if conv.get("country") == "uae":
            await query.edit_message_text(
                "🇦🇪 Выберите филиал в Дубае:",
                reply_markup=branch_keyboard(UAE_BRANCHES, back="back_age"),
            )
        else:
            await query.edit_message_text(
                "🇷🇺 Выберите филиал в Москве или Подмосковье:",
                reply_markup=branch_keyboard(RUSSIA_BRANCHES, back="back_age"),
            )


async def branch_callback(query, context, user_id, data):
    all_branches = {**RUSSIA_BRANCHES, **UAE_BRANCHES}
    if data not in all_branches:
        await query.edit_message_text("Ошибка. Попробуйте /start")
        return

    name, address = all_branches[data]
    branch_str = f"{name} — {address}"
    context.user_data["branch"] = branch_str
    update_conversation(user_id, {"branch": branch_str})

    await query.edit_message_text(
        f"📍 {branch_str}\n\n{PRICES_STANDARD}\n\nКак вас зовут?"
    )


async def confirm_yes_callback(query, context, user_id, data):
    booking_data = context.user_data.get("pending_booking")
    if not booking_data:
        await query.edit_message_text("Ошибка: данные не найдены. Начните с /start.")
        return
    await create_booking(booking_data)
    context.user_data.pop("pending_booking", None)
    await query.edit_message_text(
        "Спасибо! С вами в ближайшее время свяжется администратор и сообщит подробности занятия. 🏁"
    )


async def confirm_edit_callback(query, context, user_id, data):
    await query.edit_message_text(
        "Что хотите исправить?",
        reply_markup=edit_field_keyboard(),
    )


async def edit_field_callback(query, context, user_id, data):
    field_map = {"edit_name": "name", "edit_phone": "phone"}
    field = field_map.get(data)
    if not field:
        return
    labels = {"name": "имя", "phone": "номер телефона"}
    context.user_data["editing_field"] = field
    await query.edit_message_text(
        f"Введите новое {labels.get(field, field)}:"
    )


async def edit_back_callback(query, context, user_id, data):
    from handlers.message import _summary_text, confirm_keyboard
    pending = context.user_data.get("pending_booking")
    if pending:
        await query.edit_message_text(
            _summary_text(pending), reply_markup=confirm_keyboard()
        )
    else:
        await query.edit_message_text("Ошибка. Начните с /start.")


BACK_HANDLERS = {
    "back_country": lambda query, uid: query.edit_message_text(
        "В какой стране вы находитесь?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Россия", callback_data="country_russia")],
            [InlineKeyboardButton("🇦🇪 ОАЭ (Дубай)", callback_data="country_uae")],
        ]),
    ),
    "back_age": lambda query, uid: query.edit_message_text(
        "Кто будет заниматься?",
        reply_markup=age_keyboard("back_country"),
    ),
    "back_format": lambda query, uid: query.edit_message_text(
        "Как хотите заниматься?",
        reply_markup=format_keyboard("back_age"),
    ),
}


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    uid = user.id
    username = user.username or ""
    first_name = user.first_name or ""

    if data in BACK_HANDLERS:
        await BACK_HANDLERS[data](query, uid)
        return

    if data.startswith("country_"):
        await country_callback(query, context, uid, username, first_name, data)

    elif data.startswith("age_"):
        await age_callback(query, context, uid, data)

    elif data.startswith("format_"):
        await format_callback(query, context, uid, data)

    elif data.startswith("branch_"):
        await branch_callback(query, context, uid, data)

    elif data.startswith("confirm_yes"):
        await confirm_yes_callback(query, context, uid, data)

    elif data == "confirm_edit":
        await confirm_edit_callback(query, context, uid, data)

    elif data.startswith("edit_name") or data.startswith("edit_phone"):
        await edit_field_callback(query, context, uid, data)

    elif data == "edit_back":
        await edit_back_callback(query, context, uid, data)
