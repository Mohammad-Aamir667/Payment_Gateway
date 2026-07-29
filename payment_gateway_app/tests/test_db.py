from sqlalchemy import text

from app.infrastructure.database import SessionLocal

def test_connection():
    session = SessionLocal()

    try:
        result = session.execute(text("SELECT version();"))

        print(result.scalar())

    finally:
        session.close()


if __name__ == "__main__":
    test_connection()