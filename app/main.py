from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.merchant.router import router as merchant_router
from app.merchant_credentials.router import router as api_key_router
from app.merchant_payment_methods.router import router as merchant_payment_method_router
from app.webhook.router import router as webhook_router
from app.payment.router import router as payment_router
app = FastAPI()
app.include_router(auth_router)
app.include_router(merchant_router)
app.include_router(api_key_router)
app.include_router(merchant_payment_method_router)
app.include_router(webhook_router)
app.include_router(payment_router)
@app.get("/")
def root():
    return {"message":"Hello from server"}