import hashlib

def hash_secret(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()