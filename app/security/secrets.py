import secrets

def generate_secret(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(32)}"