import logging
from datetime import datetime
from config import ADMIN_CHAT_ID, TG_BOT_TOKEN

logger = logging.getLogger(__name__)

def create_booking(data: dict) -> bool:
    logger.info("=== НОВАЯ ЗАПИСЬ ===")
    logger.info("Имя: %s", data.get("name"))
    logger.info("Телефон: %s", data.get("phone"))
    logger.info("Филиал: %s", data.get("branch"))
    logger.info("Тип занятия: %s", data.get("lesson_type"))
    logger.info("Дата: %s", data.get("desired_date"))
    logger.info("Время: %s", data.get("desired_time"))
    logger.info("Цена: %s", data.get("price"))
    logger.info("Создано: %s", datetime.now().isoformat())
    logger.info("===================")

    if ADMIN_CHAT_ID:
        try:
            from telegram import Bot
            bot = Bot(token=TG_BOT_TOKEN)
            message = (
                f"✅ Новая запись!\n\n"
                f"• Имя: {data.get('name')}\n"
                f"• Телефон: {data.get('phone')}\n"
                f"• Филиал: {data.get('branch')}\n"
                f"• Тип занятия: {data.get('lesson_type')}\n"
                f"• Дата: {data.get('desired_date')}\n"
                f"• Время: {data.get('desired_time')}\n"
                f"• Цена: {data.get('price')}"
            )
            bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)
        except Exception as e:
            logger.error("Не удалось отправить уведомление админу: %s", e)

    return True
