from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/simulated_psp"


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,

    autocommit=False,
)


class Base(DeclarativeBase):
    pass