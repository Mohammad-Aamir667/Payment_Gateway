from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy.orm import Session
from uuid import UUID
from app.common.schemas import PasswordRequest
from app.webhook.schemas import (
    WebhookCreateRequest,
    WebhookResponse, WebhookUpdateRequest,
    WebhookUpdateResponse,WebhookDetailsResponse

)
from app.webhook.service import WebhookService
from app.webhook.repository import WebhookRepository

from app.merchant.dependencies import get_current_merchant

from app.db.session import get_db

from app.merchant.models import Merchant
webhook_service = WebhookService(
    webhook_repository=WebhookRepository(),
)

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=WebhookResponse,
)
def create_webhook(
    request: WebhookCreateRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
) -> WebhookResponse:

    return webhook_service.create_webhook(
        merchant=merchant,
        request=request,
        db=db,
    )


@router.patch(
    "/{webhook_id}",
    status_code=status.HTTP_200_OK,
    response_model=WebhookUpdateResponse,
)
def update_webhook(
    webhook_id: UUID,
    request: WebhookUpdateRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
) -> WebhookUpdateResponse:

    return webhook_service.update_webhook(
        merchant=merchant,
        webhook_id=webhook_id,
        request=request,
        db=db,
    )


@router.patch(
    "/{webhook_id}/disable",
    status_code=status.HTTP_200_OK,
    response_model=WebhookUpdateResponse,
)
def disable_webhook(
    webhook_id: UUID,
    request: PasswordRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
) -> WebhookUpdateResponse:

    return webhook_service.disable_webhook(
        merchant=merchant,
        webhook_id=webhook_id,
        request=request,
        db=db,
    )



@router.patch(
    "/{webhook_id}/enable",
    status_code=status.HTTP_200_OK,
    response_model=WebhookUpdateResponse,
)
def enable_webhook(
    webhook_id: UUID,
    request: PasswordRequest,
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
) -> WebhookUpdateResponse:

    return webhook_service.enable_webhook(
        merchant=merchant,
        webhook_id=webhook_id,
        request=request,
        db=db,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=WebhookDetailsResponse,
)
def get_webhook(
    merchant: Merchant = Depends(get_current_merchant),
    db: Session = Depends(get_db),
) -> WebhookDetailsResponse:

    return webhook_service.get_webhook(
        merchant=merchant,
        db=db, 
    )