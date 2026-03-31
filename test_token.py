import os

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_EMAIL = os.getenv("SUPABASE_EMAIL")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD")

if not all([SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_EMAIL, SUPABASE_PASSWORD]):
    raise RuntimeError(
        "Defina SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_EMAIL e SUPABASE_PASSWORD no .env"
    )

url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Content-Type": "application/json",
}
data = {
    "email": SUPABASE_EMAIL,
    "password": SUPABASE_PASSWORD,
}

response = requests.post(url, json=data, headers=headers, timeout=20)
print(response.status_code)
print(response.json())
