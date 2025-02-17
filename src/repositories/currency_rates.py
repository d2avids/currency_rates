from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db_session
from domain.currency_rates import CurrencyRate
from schemas.currency_rates import CurrencyRateRequest, CurrencyRateResponse


class ICurrencyRateRepo(ABC):
    """Abstract base class for the repository that handles currency rate operations."""

    @abstractmethod
    async def get(self, currency_rate_request: CurrencyRateRequest) -> Optional[CurrencyRate]:
        """
        Retrieves the currency rate for a specific currency pair and date.

        Args:
            currency_rate_request (CurrencyRateRequest): The request object containing the source currency,
                target currency, and the date for the conversion rate.

        Returns:
            Optional[CurrencyRate]: Database object or `None` if no currency rate was found.
        """

    @abstractmethod
    async def create_or_update(self, currency_rate: CurrencyRateResponse) -> CurrencyRate:
        """
        Creates or updates a currency rate entry in the repository.

        If a rate entry already exists for the specified currency pair and date, it will be updated with
        the new rate. Otherwise, a new entry will be created.

        Args:
            currency_rate (CurrencyRateResponse): The response object containing the currency pair, date,
                and the rate to be stored.

        Returns:
            CurrencyRate: The newly created or updated currency rate object.
        """

    @abstractmethod
    async def bulk_create_or_update(self, currency_rates: list[CurrencyRateResponse]) -> None:
        """
        Performs a bulk insert or update of the provided list of currency rates in the repository.

        Args:
            currency_rates (list[CurrencyRateResponse]): A list of currency rate response objects to be inserted
                or updated in the database.
        """


class CurrencyRateRepo(ICurrencyRateRepo):
    def __init__(self, db: AsyncSession) -> None:
        self._db: AsyncSession = db

    async def get(self, currency_rate_request: CurrencyRateRequest) -> Optional[CurrencyRate]:
        result = await self._db.execute(
            select(CurrencyRate).where(
                CurrencyRate.from_cur == currency_rate_request.from_cur,  # type: ignore
                CurrencyRate.to_cur == currency_rate_request.to_cur,  # type: ignore
                CurrencyRate.date == currency_rate_request.date  # type: ignore
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update(self, currency_rate: CurrencyRateResponse) -> CurrencyRate:
        result = await self._db.execute(
            select(CurrencyRate).where(
                CurrencyRate.from_cur == currency_rate.from_cur,  # type: ignore
                CurrencyRate.to_cur == currency_rate.to_cur,  # type: ignore
                CurrencyRate.date == currency_rate.date  # type: ignore
            )
        )
        currency_rate_obj = result.scalar_one_or_none()

        if currency_rate_obj:
            currency_rate_obj.rate = currency_rate.rate
            await self._db.commit()
            return currency_rate_obj

        currency_rate_obj = CurrencyRate(
            from_cur=currency_rate.from_cur,
            to_cur=currency_rate.to_cur,
            date=currency_rate.date,
            rate=currency_rate.rate
        )
        self._db.add(currency_rate_obj)
        await self._db.commit()
        await self._db.refresh(currency_rate_obj)
        return currency_rate_obj

    async def bulk_create_or_update(self, currency_rates: list[CurrencyRateResponse]) -> None:
        deduped: dict[tuple[str, str, date], CurrencyRateResponse] = {}
        for rate in currency_rates:
            key = (rate.from_cur, rate.to_cur, rate.date)
            deduped[key] = rate

        rates_dicts = [r.model_dump() for r in deduped.values()]

        stmt = insert(CurrencyRate).values(rates_dicts)
        stmt = stmt.on_conflict_do_update(
            index_elements=["from_cur", "to_cur", "date"],
            set_={"rate": stmt.excluded.rate},
        )
        await self._db.execute(stmt)
        await self._db.commit()


async def get_currency_rates_repo(db: AsyncSession = Depends(get_db_session)) -> CurrencyRateRepo:
    return CurrencyRateRepo(db)
