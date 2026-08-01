import secrets
API_KEY_PREFIX = "pg_live_"

def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"