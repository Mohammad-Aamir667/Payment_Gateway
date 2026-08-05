from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.merchant.models import Merchant
from app.security.constants import WEBHOOK_SECRET_PREFIX
from app.webhook.models import Webhook

from app.webhook.repository import WebhookRepository
from app.webhook.schemas import (
    WebhookCreateRequest,
    WebhookResponse,WebhookUpdateRequest,
    WebhookUpdateResponse,
)

from app.security.passwords import verify_password
from app.security.secrets import generate_secret


class WebhookService:

    def __init__(
        self,
        webhook_repository: WebhookRepository,
    ):
        self.webhook_repository = webhook_repository

    def create_webhook(
        self,
        merchant: Merchant,
        request: WebhookCreateRequest,
        db: Session,
    ) -> WebhookResponse:

        # Verify merchant password
        if not verify_password(
            request.password,
            merchant.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password.",
            )

        # Verify merchant does not already have a webhook
        existing_webhook = self.webhook_repository.get_by_merchant(
            db=db,
            merchant_id=merchant.merchant_id,
        )

        if existing_webhook is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Webhook configuration already exists.",
            )

        # Generate webhook secret
        webhook_secret = generate_secret(WEBHOOK_SECRET_PREFIX)

        # Create webhook
        webhook = Webhook(
            merchant_id=merchant.merchant_id,
            callback_url=str(request.callback_url),
            event_types=request.event_types,
            webhook_secret=webhook_secret,
        )

        self.webhook_repository.create(
            db=db,
            webhook=webhook,
        )

        db.commit()
        db.refresh(webhook)

        return WebhookResponse(
            webhook_id=webhook.webhook_id,
            callback_url=webhook.callback_url,
            event_types=webhook.event_types,
            is_active=webhook.is_active,
            webhook_secret=webhook_secret,
            created_at=webhook.created_at,
        )




    def update_webhook(
        self,
        merchant: Merchant,
        webhook_id: UUID,
        request: WebhookUpdateRequest,
        db: Session,
    ) -> WebhookUpdateResponse:

        # Verify merchant password
        if not verify_password(
            request.password,
            merchant.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect password.",
            )
        if (request.callback_url is None and request.event_types is None and request.is_active is None):
            raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="At least one field must be provided for update.",
    ) 
        # Retrieve webhook
        webhook = self.webhook_repository.get_by_id(
            db=db,
            webhook_id=webhook_id,
        )

        if webhook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook configuration does not exist.",
            )

        # Verify ownership
        if webhook.merchant_id != merchant.merchant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Webhook does not belong to the authenticated merchant.",
            )

        # Update callback URL
        if request.callback_url is not None:
            webhook.callback_url = str(request.callback_url)

        # Update subscribed event types
        if request.event_types is not None:
            webhook.event_types = request.event_types

        # Update active status
        if request.is_active is not None:
            webhook.is_active = request.is_active

        db.commit()
        db.refresh(webhook)

        return WebhookUpdateResponse(
            webhook_id=webhook.webhook_id,
            callback_url=webhook.callback_url,
            event_types=webhook.event_types,
            is_active=webhook.is_active,
            updated_at=webhook.updated_at,
        )