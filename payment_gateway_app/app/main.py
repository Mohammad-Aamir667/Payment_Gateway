from fastapi import FastAPI
from app.auth.router import router as auth_router
app = FastAPI()
app.include_router(auth_router)
from app.merchant.router import router as merchant_router
app.include_router(merchant_router)
@app.get("/")
def root():
    return {"message":"Hello from server"}