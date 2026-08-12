from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.merchant.models import Merchant, MerchantStatus
from app.merchant.repository import MerchantRepository
from app.merchant_credentials.models import APIKey, KeyStatus
from app.merchant_credentials.repository import APIKeyRepository
from datetime import datetime, timezone
from app.security.hashing import hash_secret
api_key_repository = APIKeyRepository()
merchant_repository = MerchantRepository()

security = HTTPBearer()


async def get_authenticated_merchant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Merchant:
    api_key = credentials.credentials
    
    api_key_hash = hash_secret(api_key)

    

    stored_key: APIKey | None = api_key_repository.get_by_hash(db, api_key_hash)
    if stored_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key.",
        )

    if stored_key.key_status != KeyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key has been revoked.",
        )

    merchant = merchant_repository.get_by_id(db, stored_key.merchant_id)

    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Merchant not found.",
        )

    if merchant.merchant_status != MerchantStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant is not active.",
        )

    stored_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return merchant