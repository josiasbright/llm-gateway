from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.config import sqlalchemy_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(sqlalchemy_url(), pool_pre_ping=True)
