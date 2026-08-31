from fastapi import FastAPI

from app.api.payments import router as payments_router


app = FastAPI(
    title="Simulated Payment Service Provider",
    version="1.0.0",
)

app.include_router(payments_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}