import logging
import io
from telegram import Update
from telegram.ext import ContextTypes
from db import get_or_create_conversation, update_conversation
from services.ollama_service import OllamaService
from services.booking import create_booking
from handlers.callbacks import age_keyboard, format_keyboard
from utils.validation import validate_phone, PHONE_EXAMPLES

logger = logging.getLogger(__name__)
ollama = OllamaService()

REQUIRED = ["name", "phone", "branch", "age_group"]

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    voice = update.message.voice

    file = await context.bot.get_file(voice.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)

    conversation = get_or_create_conversation(user.id, user.username or "", user.first_name or "")
    conversation["country"] = conversation.get("country") or context.user_data.get("country", "")
    conversation["age_group"] = conversation.get("age_group") or context.user_data.get("age_group", "")
    conversation["format"] = conversation.get("format") or context.user_data.get("format", "")
    conversation["branch"] = conversation.get("branch") or context.user_data.get("branch", "")

    if not conversation.get("country"):
        from handlers.start import country_keyboard
        await update.message.reply_text(
            "В какой стране вы находитесь?",
            reply_markup=country_keyboard(),
        )
        return

    if not conversation.get("age_group"):
        await update.message.reply_text(
            "Кто будет заниматься?",
            reply_markup=age_keyboard("back_country"),
        )
        return

    if not conversation.get("format"):
        await update.message.reply_text(
            "Как хотите заниматься?",
            reply_markup=format_keyboard("back_age"),
        )
        return

    current_data = {k: conversation.get(k, "") for k in REQUIRED}

    result = await ollama.process_audio(buf.getvalue(), current_data)
    reply = result.get("reply", "Извините, не удалось распознать голосовое сообщение.")
    extracted = result.get("extracted", {})

    updates = {}
    for key in REQUIRED:
        if extracted.get(key) and str(extracted[key]).strip():
            updates[key] = str(extracted[key]).strip()

    if "phone" in updates:
        valid, phone = validate_phone(updates["phone"])
        if not valid:
            country = conversation.get("country", "russia")
            example = PHONE_EXAMPLES.get(country, PHONE_EXAMPLES["russia"])
            await update.message.reply_text(
                f"Номер неверный. Пример: {example}\nПожалуйста, введите ещё раз."
            )
            return
        updates["phone"] = phone

    if updates:
        update_conversation(user.id, updates)
        for k in REQUIRED:
            if k in updates:
                conversation[k] = updates[k]

    if updates.get("phone"):
        merged = {**conversation, **updates}
        booking_data = {k: merged.get(k, "") for k in REQUIRED + ["country", "format"]}
        await create_booking(booking_data)
        await update.message.reply_text(
            "Спасибо! С вами в ближайшее время свяжется администратор и сообщит подробности занятия. 🏁"
        )
    else:
        await update.message.reply_text(reply)
