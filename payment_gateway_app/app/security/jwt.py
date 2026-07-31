from datetime import datetime, timedelta, timezone

import jwt

from app.core.settings import settings
from fastapi import HTTPException, status
from jwt import ExpiredSignatureError, PyJWTError

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