import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db

from app.merchant.models import Merchant

from app.merchant.dependencies import get_current_merchant
from app.merchant_credentials.schemas import (
    APIKeyCreateRequest,
    APIKeyMetadataResponse,
    APIKeyResponse,
    APIKeyRevokeRequest,
)
from app.merchant_credentials.service import APIKeyService
from app.merchant_credentials.repository import APIKeyRepository
from app.merchant_credentials.schemas import APIKeyListResponse

router = APIRouter(
    prefix="/api-keys",
    tags=["Merchant API Keys"],
)

api_key_service = APIKeyService(
    api_key_repository=APIKeyRepository(),
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=APIKeyResponse,
)
def create_api_key(
    request: APIKeyCreateRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return api_key_service.create_api_key(
        merchant=merchant,
        request=request,
        db=db,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=APIKeyListResponse,
)
def get_api_keys(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return api_key_service.get_api_keys(
        merchant=merchant,
        db=db,
    )


@router.post(
    "/{api_key_id}/revoke",
    status_code=status.HTTP_200_OK,
    response_model=APIKeyMetadataResponse,
)
def revoke_api_key(
    api_key_id: UUID,
    request: APIKeyRevokeRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
):
    return api_key_service.revoke_api_key(
        api_key_id=api_key_id,
        merchant=merchant,
        request=request,
        db=db,
    )