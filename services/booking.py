import logging
from datetime import datetime
from config import ADMIN_CHAT_ID, TG_BOT_TOKEN
from db import save_booking

logger = logging.getLogger(__name__)


async def create_booking(data: dict) -> bool:
    logger.info("=== НОВАЯ ЗАПИСЬ ===")
    logger.info("Страна: %s", data.get("country"))
    logger.info("Возраст: %s", data.get("age_group"))
    logger.info("Формат: %s", data.get("format"))
    logger.info("Имя: %s", data.get("name"))
    logger.info("Телефон: %s", data.get("phone"))
    logger.info("Филиал: %s", data.get("branch"))
    logger.info("Создано: %s", datetime.now().isoformat())
    logger.info("===================")

    save_booking(data)

    try:
        admin_id = int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID else None
    except (ValueError, TypeError):
        admin_id = None

    if admin_id:
        try:
            from telegram import Bot
            bot = Bot(token=TG_BOT_TOKEN)
            country_flag = "🇷🇺" if data.get("country") == "russia" else "🇦🇪"
            fmt_icon = "💻" if data.get("format") == "online" else "🏫"
            age_label = "🧒 Детский" if data.get("age_group") == "child" else "👨 Взрослый"
            message = (
                f"✅ Новая заявка!\n\n"
                f"{country_flag} {data.get('country', '').upper()}\n"
                f"{age_label}\n"
                f"{fmt_icon} {data.get('format', '')}\n"
                f"• Имя: {data.get('name')}\n"
                f"• Телефон: {data.get('phone')}\n"
                f"• Филиал: {data.get('branch')}"
            )
            await bot.send_message(chat_id=admin_id, text=message)
        except Exception as e:
            logger.error("Не удалось отправить уведомление админу: %s", e)
            return False

    return True
