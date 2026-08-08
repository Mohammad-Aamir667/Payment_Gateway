import bcrypt


from app.core.settings import settings

def hash_password(secret: str) -> str:
    """
    Hash a plain-text secret using bcrypt.
    """

    secret_bytes = secret.encode("utf-8")

    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)

    hash_secret = bcrypt.hashpw(secret_bytes, salt)

    return hash_secret.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))