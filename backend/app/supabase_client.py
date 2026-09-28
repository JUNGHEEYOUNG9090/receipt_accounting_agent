import os

from dotenv import load_dotenv
from supabase import create_client, Client


BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

load_dotenv(os.path.join(BASE_DIR, ".env"))


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다."
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
)