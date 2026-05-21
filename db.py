from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from typing import Optional

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ⚠️ Перед запуском создай таблицу в Supabase SQL Editor:
#
# CREATE TABLE IF NOT EXISTS conversations (
#   id BIGSERIAL PRIMARY KEY,
#   user_id BIGINT NOT NULL UNIQUE,
#   username TEXT,
#   first_name TEXT,
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

def get_or_create_conversation(user_id: int, username: str = "", first_name: str = "") -> dict:
    if supabase:
        result = supabase.table("conversations").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
        data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "name": "",
            "phone": "",
            "branch": "",
            "lesson_type": "",
            "desired_date": "",
            "desired_time": "",
            "price": "",
            "step": 0,
        }
        supabase.table("conversations").insert(data).execute()
        return data
    return {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "name": "",
        "phone": "",
        "branch": "",
        "lesson_type": "",
        "desired_date": "",
        "desired_time": "",
        "price": "",
        "step": 0,
    }

def update_conversation(user_id: int, updates: dict) -> dict:
    if "updated_at" not in updates:
        import datetime
        updates["updated_at"] = datetime.datetime.now().isoformat()
    if supabase:
        result = supabase.table("conversations").update(updates).eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
    return {}

def get_conversation(user_id: int) -> Optional[dict]:
    if supabase:
        result = supabase.table("conversations").select("*").eq("user_id", user_id).execute()
        if result.data:
            return result.data[0]
    return None

def reset_conversation(user_id: int):
    if supabase:
        supabase.table("conversations").delete().eq("user_id", user_id).execute()
