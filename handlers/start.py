from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import reset_conversation, get_or_create_conversation

MSK = timezone(timedelta(hours=3))


def greeting() -> str:
    hour = datetime.now(MSK).hour
    if 6 <= hour < 12:
        return "Доброе утро"
    if 12 <= hour < 18:
        return "Добрый день"
    if 18 <= hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"


def country_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Россия", callback_data="country_russia")],
        [InlineKeyboardButton("🇦🇪 ОАЭ (Дубай)", callback_data="country_uae")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reset_conversation(user.id)
    context.user_data.clear()
    get_or_create_conversation(user.id, user.username or "", user.first_name or "")

    await update.message.reply_text(
        f"{greeting()}! Я Конь, администратор Moscow Chess School.\n\n"
        "В какой стране вы находитесь?",
        reply_markup=country_keyboard(),
    )
