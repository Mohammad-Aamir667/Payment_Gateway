from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import UUID
from sqlalchemy.orm import Session

from app.merchant_credentials.models import APIKey
from app.merchant.models import Merchant

from app.merchant_credentials.schemas import (
    APIKeyCreateRequest,
    APIKeyResponse,APIKeyListResponse,APIKeyMetadataResponse,
    APIKeyRevokeRequest,
    KeyStatus
)
from app.merchant_credentials.repository import APIKeyRepository

from app.security.constants import API_KEY_PREFIX
from app.security.passwords import verify_password
from app.security.hashing import hash_secret
from app.security.secrets import generate_secret


class APIKeyService:

    def __init__(
        self,
        api_key_repository: APIKeyRepository,
    ):
        self.api_key_repository = api_key_repository

    def create_api_key(
        self,
        merchant: Merchant,
        request: APIKeyCreateRequest,
        db: Session,
    ) -> APIKeyResponse:

        # Step 1: Verify merchant password
        if not verify_password(
            request.password,
            merchant.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password.",
            )

        # Step 2: Ensure key name is unique for this merchant
        existing_key = (
            self.api_key_repository.get_by_merchant_and_key_name(
                db=db,
                merchant_id=merchant.merchant_id,
                key_name=request.key_name,
            )
        )

        if existing_key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="API key name already exists.",
            )

        # Step 3: Generate plaintext API key
        plain_api_key = generate_secret(API_KEY_PREFIX)

        # Step 4: Hash API key
        api_key_hash = hash_secret(plain_api_key)

        # Step 5: Create ORM object
        api_key = APIKey(
            merchant_id=merchant.merchant_id,
            api_key_hash=api_key_hash,
            key_name=request.key_name,
        )

        # Step 6: Persist
        self.api_key_repository.create(
            db=db,
            api_key=api_key,
        )

        # Step 7: Commit transaction
        db.commit()

        # Step 8: Refresh ORM object
        db.refresh(api_key)

        # Step 9: Return plaintext API key (shown only once)
        return APIKeyResponse(
            key_name=api_key.key_name,
            api_key=plain_api_key,
            created_at=api_key.created_at,
        )

    def get_api_keys(
        self,
        merchant: Merchant,
        db: Session,
    ) -> APIKeyListResponse:

        api_keys = self.api_key_repository.get_by_merchant_id(
            db=db,
            merchant_id=merchant.merchant_id,
        )

        return APIKeyListResponse(
            api_keys=[
                APIKeyMetadataResponse(
                    api_key_id=api_key.api_key_id,
                    key_name=api_key.key_name,
                    key_status=api_key.key_status,
                    created_at=api_key.created_at,
                    revoked_at=api_key.revoked_at,
                )
                for api_key in api_keys
            ]
        )

    def revoke_api_key(
        self,
        api_key_id: UUID,
        merchant: Merchant,
        request: APIKeyRevokeRequest,
        db: Session,
    ) -> APIKeyMetadataResponse:

        # Step 1: Verify password
        if not verify_password(
            request.password,
            merchant.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password.",
            )

        # Step 2: Retrieve API Key
        api_key = self.api_key_repository.get_by_id(
            db=db,
            api_key_id=api_key_id,
        )

        if api_key is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found.",
            )

        # Step 3: Verify ownership
        if api_key.merchant_id != merchant.merchant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to revoke this API key.",
            )

        # Step 4: Verify current state
        if api_key.key_status == KeyStatus.REVOKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="API key is already revoked.",
            )

        # Step 5: Revoke
        api_key.key_status = KeyStatus.REVOKED
        api_key.revoked_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(api_key)

        return APIKeyMetadataResponse(
            api_key_id=api_key.api_key_id,
            key_name=api_key.key_name,
            key_status=api_key.key_status,
            created_at=api_key.created_at,
            revoked_at=api_key.revoked_at,
        )
    