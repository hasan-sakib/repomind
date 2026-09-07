from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models. Import all models in db/migrations/env.py
    so Alembic autogenerate can discover them via Base.metadata."""
