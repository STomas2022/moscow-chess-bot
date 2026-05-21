import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from typing import Optional

logger = logging.getLogger(__name__)

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ⚠️ Запусти в Supabase SQL Editor:
#
# CREATE TABLE IF NOT EXISTS conversations (
#   id BIGSERIAL PRIMARY KEY,
#   user_id BIGINT NOT NULL UNIQUE,
#   username TEXT,
#   first_name TEXT,
#   country TEXT DEFAULT '',
#   age_group TEXT DEFAULT '',
#   format TEXT DEFAULT '',
#   name TEXT,
#   phone TEXT,
#   branch TEXT,
#   lesson_type TEXT,
#   desired_date TEXT,
#   desired_time TEXT,
#   price TEXT,
#   step INTEGER DEFAULT 0,
#   created_at TIMESTAMPTZ DEFAULT NOW(),
#   updated_at TIMESTAMPTZ DEFAULT NOW()
# );
#
# CREATE TABLE IF NOT EXISTS bookings (
#   id BIGSERIAL PRIMARY KEY,
#   created_at TIMESTAMPTZ DEFAULT NOW(),
#   country TEXT DEFAULT '',
#   age_group TEXT DEFAULT '',
#   format TEXT DEFAULT '',
#   name TEXT DEFAULT '',
#   phone TEXT DEFAULT '',
#   branch TEXT DEFAULT ''
# );
#
# -- Если таблицы уже есть — добавь колонки:
# ALTER TABLE conversations ADD COLUMN IF NOT EXISTS country TEXT DEFAULT '';
# ALTER TABLE conversations ADD COLUMN IF NOT EXISTS age_group TEXT DEFAULT '';
# ALTER TABLE conversations ADD COLUMN IF NOT EXISTS format TEXT DEFAULT '';

EMPTY_CONVERSATION = {
    "country": "",
    "age_group": "",
    "format": "",
    "name": "",
    "phone": "",
    "branch": "",
    "lesson_type": "",
    "desired_date": "",
    "desired_time": "",
    "price": "",
    "step": 0,
}

REQUIRED_FIELDS = ["name", "phone", "branch", "age_group"]

def get_or_create_conversation(user_id: int, username: str = "", first_name: str = "") -> dict:
    base = dict(EMPTY_CONVERSATION)
    base.update({"user_id": user_id, "username": username, "first_name": first_name})

    if supabase:
        try:
            result = supabase.table("conversations").select("*").eq("user_id", user_id).execute()
            if result.data:
                row = dict(result.data[0])
                for k in EMPTY_CONVERSATION:
                    row.setdefault(k, "")
                return row
            supabase.table("conversations").insert(base).execute()
        except Exception:
            pass
    return dict(base)

def update_conversation(user_id: int, updates: dict) -> dict:
    if "updated_at" not in updates:
        import datetime
        updates["updated_at"] = datetime.datetime.now().isoformat()
    if supabase:
        try:
            result = supabase.table("conversations").update(updates).eq("user_id", user_id).execute()
            if result.data:
                return result.data[0]
        except Exception:
            pass
    return {}

def get_conversation(user_id: int) -> Optional[dict]:
    if supabase:
        try:
            result = supabase.table("conversations").select("*").eq("user_id", user_id).execute()
            if result.data:
                return result.data[0]
        except Exception:
            pass
    return None

def reset_conversation(user_id: int):
    if supabase:
        try:
            supabase.table("conversations").delete().eq("user_id", user_id).execute()
        except Exception:
            pass

def all_data_collected(data: dict) -> bool:
    return all(data.get(f) for f in REQUIRED_FIELDS)


def save_booking(data: dict) -> bool:
    if not supabase:
        return False
    try:
        row = {
            "country": data.get("country", ""),
            "age_group": data.get("age_group", ""),
            "format": data.get("format", ""),
            "name": data.get("name", ""),
            "phone": data.get("phone", ""),
            "branch": data.get("branch", ""),
        }
        supabase.table("bookings").insert(row).execute()
        logger.info("✅ Заявка сохранена в Supabase bookings")
        return True
    except Exception as e:
        logger.error("Ошибка сохранения заявки: %s", e)
        return False
