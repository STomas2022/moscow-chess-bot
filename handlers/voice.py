import logging
import io
from telegram import Update
from telegram.ext import ContextTypes
from db import get_or_create_conversation, update_conversation
from services.gemini import GeminiService
from services.booking import create_booking

logger = logging.getLogger(__name__)
gemini = GeminiService()

REQUIRED_FIELDS = ["name", "phone", "branch", "lesson_type", "desired_date", "desired_time"]

def all_data_collected(data: dict) -> bool:
    return all(data.get(f) for f in REQUIRED_FIELDS)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    voice = update.message.voice

    file = await context.bot.get_file(voice.file_id)
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    audio_data = buf.getvalue()

    conversation = get_or_create_conversation(user.id, user.username or "", user.first_name or "")
    current_data = {k: conversation.get(k, "") for k in REQUIRED_FIELDS}
    current_data["price"] = conversation.get("price", "")

    result = await gemini.process_audio_async(audio_data, current_data)
    reply = result.get("reply", "Извините, не удалось распознать голосовое сообщение.")

    extracted = result.get("extracted", {})
    updates = {}
    for key in REQUIRED_FIELDS + ["price"]:
        if extracted.get(key):
            updates[key] = extracted[key].strip()

    if updates:
        updates["step"] = sum(1 for f in REQUIRED_FIELDS if (updates.get(f) or conversation.get(f)))
        update_conversation(user.id, updates)

    for key in REQUIRED_FIELDS:
        if updates.get(key):
            conversation[key] = updates[key]

    await update.message.reply_text(reply)

    if all_data_collected(conversation):
        booking_data = {
            "name": conversation.get("name", ""),
            "phone": conversation.get("phone", ""),
            "branch": conversation.get("branch", ""),
            "lesson_type": conversation.get("lesson_type", ""),
            "desired_date": conversation.get("desired_date", ""),
            "desired_time": conversation.get("desired_time", ""),
            "price": conversation.get("price", ""),
        }
        create_booking(booking_data)
