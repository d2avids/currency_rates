import datetime as dt

from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.sqltypes import TIMESTAMP


class Base(DeclarativeBase):
    __abstract__ = True
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=dt.datetime.now(dt.UTC)
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=dt.datetime.now(dt.UTC),
        onupdate=dt.datetime.now(dt.UTC)
    )
