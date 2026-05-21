from telegram import Update
from telegram.ext import ContextTypes
from db import reset_conversation, get_or_create_conversation

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    reset_conversation(user.id)
    get_or_create_conversation(user.id, user.username or "", user.first_name or "")

    if args and args[0] == "booking":
        await update.message.reply_text(
            "Здравствуйте! Я Конь, администратор шахматной школы Moscow Chess School. "
            "Хотите записаться на занятие? Как я могу к вам обращаться?"
        )
    else:
        await update.message.reply_text(
            "Здравствуйте! Я Конь, администратор шахматной школы Moscow Chess School. "
            "Как я могу к вам обращаться?"
        )
