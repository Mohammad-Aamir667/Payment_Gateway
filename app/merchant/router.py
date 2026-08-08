from fastapi import APIRouter, Depends
router = APIRouter(prefix="/merchant", tags=["Merchant"])
from app.merchant.models import Merchant
from app.merchant.dependencies import get_current_merchant
from app.auth.schemas import MerchantResponse
@router.get("/me")

def get_profile(
    merchant: Merchant = Depends(get_current_merchant),
):
    return MerchantResponse.model_validate(merchant)