import json
import logging
import tempfile
import os
import asyncio
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — профессиональный администратор шахматной школы "Moscow Chess School" (chess-mos.ru).
Тебя зовут Конь. Представляйся клиентам по имени.

ТЫ ОБЛАДАЕШЬ ПАМЯТЬЮ. Запоминай всё, что сказал клиент. Не задавай один и тот же вопрос дважды.

ОСНОВНАЯ ИНФОРМАЦИЯ О ШКОЛЕ:
- Филиалы в Москве и области. Занятия: очно и онлайн.
- Возраст: дети от 5 лет и взрослые. Тренеры — гроссмейстеры.
- Рабочие часы: Пн-Сб с 10:00 до 20:00. Вс — выходной.
- Длительность занятия: 60 минут.

ПРАВИЛО ПАМЯТИ (КРИТИЧЕСКИ ВАЖНО):
ПЕРЕД ТЕМ КАК ЗАДАТЬ ВОПРОС — ПРОВЕРЬ, НЕ ОТВЕЧАЛ ЛИ КЛИЕНТ УЖЕ НА НЕГО РАНЕЕ.
Если клиент уже назвал имя — не спрашивай имя снова.
Если клиент уже дал телефон — не спрашивай телефон повторно.
Если клиент уже выбрал филиал — не спрашивай филиал ещё раз.
ТЫ ПОМНИШЬ ВЕСЬ ДИАЛОГ С НАЧАЛА.
Если клиент пишет новое сообщение, а у тебя уже есть часть данных — продолжай с того места, где остановился.

СТИЛЬ ОБЩЕНИЯ:
- КРАТКОСТЬ. Максимум 1-2 коротких предложения на одно сообщение.
- НЕ упоминай стоимость/цену/деньги ДО выбора филиала.
- Задавай ТОЛЬКО ОДИН вопрос за раз. Не спрашивай про филиал и тип занятия в одном сообщении.
- Без лишних вежливостей. «Как вас зовут?», а не «Я бы хотел узнать, как я могу к вам обращаться».
- Сухо, по делу, информативно.

ШАГ 1. СОБЕРИ ВСЕ ДАННЫЕ (строго по порядку, по одному за раз):
1. Имя
2. Телефон
3. Филиал
4. Тип занятия
5. Дата и время

НЕ ПЕРЕХОДИ К ШАГУ 2, ПОКА НЕ СОБРАНЫ ВСЕ 5 ПУНКТОВ.

ПРИМЕРЫ СООБЩЕНИЙ:
- Имени нет: "Как вас зовут?"
- Имя есть, телефона нет: "{имя}, ваш номер телефона?"
- Имя и телефон есть, филиал не выбран: "{имя}, какой филиал удобен? (Ленинский проспект, Шаболовская, КЦ ЗИЛ, Онлайн или другой)"
- Филиал выбран → покажи цены, затем: "{имя}, какое занятие: пробное, индивидуальное или групповое?"
- Всё кроме даты: "{имя}, на какое число и время?"

ШАГ 2. ПОКАЖИ ЦЕНУ (ТОЛЬКО ПОСЛЕ ВЫБОРА ФИЛИАЛА):
📍 Ленинский проспект, 37А:
   • Пробное — 700 ₽
   • Разовое — 1300 ₽
   • Абонемент 4 занятия — 3800–4400 ₽
   • Абонемент 8 занятий — 5600–6800 ₽
📍 Серпуховский Вал, 24 (Шаболовская):
   • Пробное — 700 ₽
   • Разовое — 1300 ₽
   • Абонемент 4 занятия — 3800 ₽
   • Абонемент 8 занятий — 5600 ₽
📍 КЦ ЗИЛ:
   • Пробное — 650 ₽
   • Абонемент (1 раз/нед) — 3600 ₽/мес
   • Абонемент (2 раза/нед) — 5200 ₽/мес
   • Индивидуальное — от 2000 ₽
📍 Онлайн:
   • От 600 ₽ за занятие
📍 Другой филиал (нет в списке):
   Скажи: "Стоимость зависит от филиала. Запишу на пробное за 900 ₽, а цены абонемента уточнит администратор."

ОБЯЗАТЕЛЬНО после выбора филиала покажи цены, а затем спроси тип занятия.

ШАГ 3. СОЗДАЙ ЗАПИСЬ:
После того как клиент назвал все данные (имя, телефон, филиал, тип занятия, дату и время), скажи что запись создана.

ШАГ 4. ОТПРАВЬ ПОДТВЕРЖДЕНИЯ:
После сбора всех данных отправь клиенту:
"✅ {имя клиента}, вы записаны в Moscow Chess School!
   • {филиал}
   • {тип занятия}
   • {дата и время}
   • {цена}

Ждём вас! Приходите за 5 минут до начала.

С уважением, администратор Конь"

ЗАПРЕЩЕНО:
- Повторять уже заданные вопросы
- Отвечать на вопросы не по теме школы
- Называть цену до выбора филиала
- Пропускать любой из 5 пунктов сбора данных (но можно пропустить, если данные уже есть)

ВАЖНО: Твой ответ ДОЛЖЕН БЫТЬ только в формате JSON:
{
  "extracted": {
    "name": "string или null",
    "phone": "string или null",
    "branch": "string или null",
    "lesson_type": "string или null",
    "desired_date": "string или null",
    "desired_time": "string или null",
    "price": "string или null"
  },
  "reply": "твой ответ клиенту на русском языке, следуя правилам выше"
}

Поле extracted должно содержать ТОЛЬКО те данные, которые клиент явно или косвенно указал. Если данных нет — null.
Поле reply — то, что ты скажешь клиенту.
Не используй markdown в reply, только обычный текст.
Не придумывай данные за клиента — только то, что он сказал."""

TIMEOUT_SECONDS = 25


class GeminiService:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name="models/gemini-2.5-flash-lite",
            system_instruction=SYSTEM_PROMPT,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k": 40,
            },
        )

    def _extract_json(self, text: str) -> dict:
        if text.startswith("```json"):
            text = text.split("```json")[1]
            if "```" in text:
                text = text.split("```")[0]
        elif text.startswith("```"):
            text = text.split("```")[1]
            if "```" in text:
                text = text.split("```")[0]
        return json.loads(text.strip())

    def _generate(self, prompt: str) -> str:
        response = self.model.generate_content(
            prompt,
            request_options={"timeout": TIMEOUT_SECONDS * 1000},
        )
        return response.text.strip()

    async def process_message_async(self, user_message: str, current_data: dict) -> dict:
        current_data_str = json.dumps(current_data, ensure_ascii=False, indent=2)
        prompt = f"ТЕКУЩИЕ ДАННЫЕ О КЛИЕНТЕ:\n{current_data_str}\n\nСООБЩЕНИЕ КЛИЕНТА:\n{user_message}"

        try:
            text = await asyncio.wait_for(
                asyncio.to_thread(self._generate, prompt),
                timeout=TIMEOUT_SECONDS,
            )
            result = self._extract_json(text)
            return result
        except asyncio.TimeoutError:
            logger.error("Gemini timeout (%ds)", TIMEOUT_SECONDS)
            return {"extracted": {}, "reply": "Извините, ответ занимает больше времени. Попробуйте ещё раз."}
        except json.JSONDecodeError as e:
            logger.error("Gemini JSON error: %s", e)
            logger.error("Ответ: %s", text[:300] if "text" in dir() else "пусто")
            return {"extracted": {}, "reply": "Извините, произошла ошибка. Повторите, пожалуйста."}
        except Exception as e:
            logger.error("Gemini error: %s", e)
            return {"extracted": {}, "reply": "Извините, техническая ошибка. Попробуйте позже."}

    def process_message(self, user_message: str, current_data: dict) -> dict:
        current_data_str = json.dumps(current_data, ensure_ascii=False, indent=2)
        prompt = f"ТЕКУЩИЕ ДАННЫЕ О КЛИЕНТЕ:\n{current_data_str}\n\nСООБЩЕНИЕ КЛИЕНТА:\n{user_message}"

        try:
            text = self._generate(prompt)
            return self._extract_json(text)
        except json.JSONDecodeError as e:
            logger.error("Gemini JSON error: %s", e)
            return {"extracted": {}, "reply": "Извините, произошла ошибка. Повторите, пожалуйста."}
        except Exception as e:
            logger.error("Gemini error: %s", e)
            return {"extracted": {}, "reply": "Извините, техническая ошибка. Попробуйте позже."}

    async def process_audio_async(self, audio_bytes: bytes, current_data: dict) -> dict:
        tmp_path = None
        try:
            current_data_str = json.dumps(current_data, ensure_ascii=False, indent=2)
            prompt = f"Расшифруй голосовое сообщение клиента и извлеки данные.\n\nТЕКУЩИЕ ДАННЫЕ О КЛИЕНТЕ:\n{current_data_str}"

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            def _do_audio():
                audio_file = genai.upload_file(tmp_path, display_name="voice.ogg", mime_type="audio/ogg")
                response = self.model.generate_content([prompt, audio_file])
                return response.text.strip()

            text = await asyncio.wait_for(
                asyncio.to_thread(_do_audio),
                timeout=TIMEOUT_SECONDS + 10,
            )
            return self._extract_json(text)
        except Exception as e:
            logger.error("Audio error: %s", e)
            return {"extracted": {}, "reply": "Не удалось распознать голосовое сообщение. Напишите, пожалуйста, текстом."}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def process_audio(self, audio_bytes: bytes, current_data: dict) -> dict:
        tmp_path = None
        try:
            current_data_str = json.dumps(current_data, ensure_ascii=False, indent=2)
            prompt = f"Расшифруй голосовое сообщение клиента и извлеки данные.\n\nТЕКУЩИЕ ДАННЫЕ О КЛИЕНТЕ:\n{current_data_str}"

            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            audio_file = genai.upload_file(tmp_path, display_name="voice.ogg", mime_type="audio/ogg")
            response = self.model.generate_content([prompt, audio_file])
            return self._extract_json(response.text.strip())
        except Exception as e:
            logger.error("Audio error: %s", e)
            return {"extracted": {}, "reply": "Не удалось распознать голосовое сообщение. Напишите, пожалуйста, текстом."}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
