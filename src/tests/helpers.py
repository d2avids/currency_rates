import decimal
import random as rd
from typing import Optional, Union, Any

from core.settings import settings
from domain import CurrencyRate
from repositories.currency_rates import ICurrencyRateRepo
from schemas.currency_rates import CurrencyRateRequest, CurrencyRateResponse


class FakeCurrencyRepo(ICurrencyRateRepo):
    def __init__(self, fake_arg: Any):
        fake_arg = fake_arg

    async def get(self, currency_rate_request: CurrencyRateRequest) -> Optional[CurrencyRate]:
        to_return = rd.randint(0, 1)
        if not to_return:
            return
        return CurrencyRate(
            from_cur=currency_rate_request.from_cur,
            to_cur=currency_rate_request.to_cur,
            date=currency_rate_request.date,
            rate=rd.randint(10, 1000) / 100
        )

    async def create_or_update(self, currency_rate: CurrencyRateResponse) -> CurrencyRate:
        return CurrencyRate(
            from_cur=currency_rate.from_cur,
            to_cur=currency_rate.to_cur,
            date=currency_rate.date,
            rate=currency_rate.rate
        )

    async def bulk_create_or_update(self, currency_rates: list[CurrencyRateResponse]) -> None:
        return


class FakeParsingResponse:
    def __init__(self, rate: str, currency: str, text: str = None):
        self.rate = rate
        self.currency = currency
        self._text = text

    async def text(self) -> str:
        if self._text:
            return self._text
        return (
            f'{settings.currency_parsing_settings.CURRENCY_RATE_START_PATTERN}'
            f'"{self.currency}", "rate": "{self.rate}"{settings.currency_parsing_settings.CURRENCY_RATE_END_PATTERN}'
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


def make_fake_parsing_response(rate: str, currency: str, text: str = None):

    def fake_parsing_response(self, url, timeout, **kwargs):
        return FakeParsingResponse(rate=rate, currency=currency, text=text)

    return fake_parsing_response
