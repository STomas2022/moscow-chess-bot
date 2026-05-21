import json
import logging
import asyncio
import httpx


OLLAMA_BASE_URL = "http://localhost:11434"
MODEL = "gemma3:latest"
TIMEOUT_SECONDS = 60

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — Конь, администратор шахматной школы Moscow Chess School (chess-mos.ru).

СТИЛЬ: кратко, красиво, конструктивно. 1-3 предложения. Без воды.

ИНФОРМАЦИЯ О ШКОЛЕ:
- Основана в 2018 году в Москве.
- Филиалы: Москва (8 филиалов), Химки, Дубай (2 филиала). Онлайн по всему миру.
- Возраст: дети от 5 лет и взрослые.
- Тренеры — гроссмейстеры и мастера FIDE. Главный тренер: МГ Сергей Тивяков (FIDE 2699).
- Часы работы: Пн-Сб 10:00–20:00. Вс — выходной.
- Длительность занятия: 55 минут (групповое), 55 минут (индивидуальное).
- Сайт: chess-mos.ru
- Телефон: +7 (903) 271-76-82
- Email: chess.mos@yandex.ru

ЦЕНЫ (групповые занятия):
- Пробное (55 мин) — 900 ₽
- Разовое (55 мин) — 1600 ₽
- Абонемент 4 занятия — 4800 ₽
- Абонемент 8 занятий — 7200 ₽
- Индивидуальное (55 мин) — 3500 ₽
- Онлайн (8 занятий/мес) — 4800 ₽
- Moscow Chess Club (взрослые) — 5600 ₽

ФИЛИАЛЫ МОСКВЫ:
• м. Автозаводская — ул. Восточная, 4А, ФОК Торпедо
• м. Академическая/Крымская — ул. Шверника, 13
• м. Дубровка — ул. Велозаводская, 11/1
• м. Калужская/Новаторская — ул. Обручева, 24
• Ленинский проспект — Ленинский пр-т, 37А
• м. Таганская — Новоспасский пер., д. 5
• м. Шаболовская — Серпуховский Вал, 24
• г. Химки — Юбилейный пр-т, 20

ДУБАЙ:
• Bluewaters, DRVN Porshe restaurant
• Al Jalila Cultural Centre for Children

ПРАВИЛА:
1. Общий вопрос → ответь кратко (1-2 предложения). extracted = {"name": null, "phone": null}.
2. Пользователь даёт имя/телефон → извлеки в name/phone. Имя может быть с маленькой буквы, с опечаткой — всё равно извлеки. В reply — следующий шаг.
3. Сбор данных: имя → "Ваш номер телефона?", телефон → "Отлично!". Страна/возраст/формат/филиал — через кнопки. Дату не спрашивай.
4. НЕ здоровайся. Просто отвечай на вопрос.

ОТВЕТ ТОЛЬКО В JSON:
{"extracted": {"name": null, "phone": null}, "reply": "твой ответ"}
"""


class OllamaService:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=TIMEOUT_SECONDS)

    def _build_prompt(self, user_message: str, current_data: dict) -> str:
        data_str = json.dumps(current_data, ensure_ascii=False, indent=2)
        return f"ТЕКУЩИЕ ДАННЫЕ О КЛИЕНТЕ:\n{data_str}\n\nСООБЩЕНИЕ КЛИЕНТА:\n{user_message}"

    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"):
            text = text.split("```json", 1)[1]
            if "```" in text:
                text = text.rsplit("```", 1)[0]
        elif text.startswith("```"):
            text = text.split("```", 1)[1]
            if "```" in text:
                text = text.rsplit("```", 1)[0]
        text = text.strip()
        return json.loads(text)

    async def generate(self, prompt: str) -> str:
        payload = {
            "model": MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3, "top_p": 0.95},
        }
        response = await self.client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    async def process_message(self, user_message: str, current_data: dict) -> dict:
        prompt = self._build_prompt(user_message, current_data)
        try:
            text = await asyncio.wait_for(self.generate(prompt), timeout=TIMEOUT_SECONDS)
            return self._extract_json(text)
        except asyncio.TimeoutError:
            logger.error("Ollama timeout (%ds)", TIMEOUT_SECONDS)
            return {"extracted": {}, "reply": "Извините, ответ занимает больше времени. Попробуйте ещё раз."}
        except json.JSONDecodeError as e:
            logger.error("Ollama JSON error: %s", e)
            logger.error("Ответ: %s", text[:300] if "text" in dir() else "пусто")
            return {"extracted": {}, "reply": "Извините, произошла ошибка. Повторите, пожалуйста."}
        except Exception as e:
            logger.error("Ollama error: %s", e)
            return {"extracted": {}, "reply": "Извините, техническая ошибка. Попробуйте позже."}

    async def process_audio(self, audio_bytes: bytes, current_data: dict) -> dict:
        return {"extracted": {}, "reply": "Извините, сейчас я принимаю только текстовые сообщения. Напишите, пожалуйста."}
