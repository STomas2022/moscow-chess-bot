from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    from db import reset_conversation, get_or_create_conversation
    reset_conversation(user.id)
    get_or_create_conversation(user.id, user.username or "", user.first_name or "")

    await update.message.reply_text(
        "Здравствуйте! Я Конь, администратор шахматной школы Moscow Chess School. Как я могу к вам обращаться?"
    )
