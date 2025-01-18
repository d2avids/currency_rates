from sqlalchemy import Column, Date, String, Integer, UniqueConstraint
from sqlalchemy.types import DECIMAL

from domain.base import Base


class CurrencyRate(Base):
    __tablename__ = 'currency_rates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_cur = Column(String(3), nullable=False)
    to_cur = Column(String(3), nullable=False)
    date = Column(Date, nullable=False)
    rate = Column(DECIMAL(15, 8))

    __table_args__ = (
        UniqueConstraint('from_cur', 'to_cur', 'date', name='currency_date_uc'),
    )
