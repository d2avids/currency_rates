import datetime as dt
import decimal
from string import ascii_letters
from typing import Annotated

from pydantic import BaseModel, Field, RootModel, field_validator
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from schemas.base import BaseRequestModel, BaseResponseModel


class CurrencyDetails(BaseModel):
    """
    Represents currency conversion details.

    Attributes:
        from_cur (str): The source currency code (ISO 4217 format).
        to_cur (str): The target currency code (ISO 4217 format).
        date (datetime.date): The date of the currency rate.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    from_cur: Annotated[
        str,
        Field(
            ...,
            title='Source Currency Code',
            description='The source currency code (ISO 4217 format)',
            min_length=3,
            max_length=3,
            examples=['USD']
        )
    ]
    to_cur: Annotated[
        str,
        Field(
            ...,
            title='Target Currency Code',
            description='The target currency code (ISO 4217 format)',
            min_length=3,
            max_length=3,
            examples=['EUR']
        )
    ]
    date: Annotated[
        dt.date,
        Field(
            ...,
            title='Date of Currency Rate',
            description='The date of the currency rate',
            examples=['2019-02-01']
        )
    ]

    @field_validator('from_cur', 'to_cur')
    @classmethod
    def validate_currency(cls, v: str):
        v = v.strip()
        if not set(v).issubset(ascii_letters):
            raise ValueError('Currency must be 3 latin letters')
        return v.upper()

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: dt.date):
        if v > dt.date.today():
            raise ValueError("Invalid date %(date)s. Date can't be in the future", v)
        return v


class CurrencyRateRequest(BaseRequestModel, CurrencyDetails):
    ...


class CurrencyRatesRequest(RootModel, BaseRequestModel):
    root: Annotated[
        list[CurrencyRateRequest],
        Field(..., title='List of Currency Rate Requests', description='List of Currency Rate Requests')
    ]


class CurrencyRateResponse(BaseResponseModel, CurrencyDetails):
    rate: Annotated[
        decimal.Decimal,
        Field(..., title="Exchange Rate", description="The exchange rate between currencies")
    ]


class CurrencyRatesResponse(RootModel, BaseResponseModel):
    root: Annotated[
        list[CurrencyRateResponse],
        Field(..., title='List of Currency Rate Responses', description='List of Currency Rate Responses')
    ]
