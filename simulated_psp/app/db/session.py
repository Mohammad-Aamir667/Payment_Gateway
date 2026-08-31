from fastapi import Depends

from app.infrastructure.database import SessionLocal

def get_db():
    db = SessionLocal()        # ← Do NOT accept any parameters here
    try:
        yield db
    finally:
        db.close()