from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/simulated_psp"


engine = create_engine(DATABASE_URL)


class Base(DeclarativeBase):
    pass