from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.security import verify_token
from app.merchant.repository import MerchantRepository
from app.merchant.models import MerchantStatus
from app.merchant.models import Merchant
merchant_repository = MerchantRepository()


def get_current_merchant(
    request: Request,
    db: Session = Depends(get_db),
)->Merchant:
    access_token = request.cookies.get("access_token")

    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    payload = verify_token(access_token)

    merchant = merchant_repository.get_by_id(
        db=db,
        merchant_id=payload["sub"],
    )

    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Merchant not found.",
        )

    if merchant.merchant_status != MerchantStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant account is not active.",
        )

    return merchant