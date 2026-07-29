import bcrypt
from datetime import datetime, timedelta, timezone

import jwt

from app.core.settings import settings
import hashlib
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, PyJWTError

def hash_password(secret: str) -> str:
    """
    Hash a plain-text secret using bcrypt.
    """

    secret_bytes = secret.encode("utf-8")

    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)

    hash_secret = bcrypt.hashpw(secret_bytes, salt)

    return hash_secret.decode("utf-8")



def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

def create_access_token(merchant_id: str) -> str:
    payload = {
        "sub": merchant_id,
        "type": "access",
        "exp": datetime.now(timezone.utc)
        + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    


def create_refresh_token(merchant_id: str) -> str:
    payload = {
        "sub": merchant_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
   
def verify_token(
    token: str,
    verify_exp: bool = True,
) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={
                "verify_exp": verify_exp,
            },
        )

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )

    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token."
        )