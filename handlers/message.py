import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import get_or_create_conversation, update_conversation
from services.ollama_service import OllamaService
from services.booking import create_booking
from handlers.callbacks import age_keyboard, format_keyboard
from utils.validation import validate_phone, PHONE_EXAMPLES

logger = logging.getLogger(__name__)
ollama = OllamaService()

REQUIRED = ["name", "phone", "branch", "age_group"]


def confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Исправить", callback_data="confirm_edit")],
    ])


def _summary_text(data: dict) -> str:
    age_label = "👨 Взрослый" if data.get("age_group") == "adult" else "🧒 Детский"
    fmt_icon = "💻 Онлайн" if data.get("format") == "online" else "🏫 В филиале"
    country_flag = "🇷🇺" if data.get("country") == "russia" else "🇦🇪"
    return (
        f"Проверьте данные:\n\n"
        f"• {country_flag} {data.get('country', '').upper()}\n"
        f"• {age_label}\n"
        f"• {fmt_icon}\n"
        f"• Имя: {data.get('name')}\n"
        f"• Телефон: {data.get('phone')}\n"
        f"• Филиал: {data.get('branch')}\n\n"
        f"Всё верно?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    editing_field = context.user_data.get("editing_field")
    if editing_field:
        pending = context.user_data.get("pending_booking", {})
        if editing_field == "phone":
            valid, phone = validate_phone(text)
            if not valid:
                country = pending.get("country", "russia")
                example = PHONE_EXAMPLES.get(country, PHONE_EXAMPLES["russia"])
                await update.message.reply_text(
                    f"Номер неверный. Пример: {example}\nПожалуйста, введите ещё раз."
                )
                return
            pending["phone"] = phone
        else:
            pending["name"] = text.strip()

        context.user_data["pending_booking"] = pending
        context.user_data.pop("editing_field", None)
        await update.message.reply_text(
            _summary_text(pending), reply_markup=confirm_keyboard()
        )
        return

    conversation = get_or_create_conversation(user.id, user.username or "", user.first_name or "")

    for field in REQUIRED + ["country", "format"]:
        conversation[field] = conversation.get(field) or context.user_data.get(field, "")

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

    result = await ollama.process_message(text, current_data)
    reply = result.get("reply", "Извините, не могу обработать сообщение.")
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
        context.user_data.update(updates)
        for k in REQUIRED:
            if k in updates:
                conversation[k] = updates[k]

    if updates.get("phone"):
        merged = {**conversation, **updates}
        booking_data = {k: merged.get(k, "") for k in REQUIRED + ["country", "format"]}
        context.user_data["pending_booking"] = booking_data
        await update.message.reply_text(
            _summary_text(booking_data), reply_markup=confirm_keyboard()
        )
    else:
        await update.message.reply_text(reply)
