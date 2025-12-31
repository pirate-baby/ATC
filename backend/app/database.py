from collections.abc import Generator
from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

T = TypeVar("T")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_or_404(db: Session, model: type[T], id: UUID, detail: str | None = None) -> T:
    obj = db.scalar(select(model).where(model.id == id))  # type: ignore[attr-defined]
    if not obj:
        raise HTTPException(status_code=404, detail=detail or f"{model.__name__} not found")
    return obj
