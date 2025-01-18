from fastapi import APIRouter, Depends

from schemas.currency_rates import (CurrencyRateRequest, CurrencyRateResponse,
                                    CurrencyRatesRequest,
                                    CurrencyRatesResponse)
from services.currency_rates import (CurrencyRatesService,
                                     get_currency_rates_service)

router = APIRouter(
    prefix='/v1/currency-rates',
)


@router.post('/get-rate', response_model=CurrencyRateResponse)
async def get_rate(
        currency_rate: CurrencyRateRequest,
        service: CurrencyRatesService = Depends(get_currency_rates_service),
):
    """
    Retrieve the conversion rate for a single currency pair.

    This endpoint accepts a single `CurrencyRateRequest` object and returns a corresponding
    `CurrencyRateResponse`. A conversion rate of `0.0` indicates that the conversion failed,
    which typically means that no data was available for the specified currencies or date.
    """
    result = await service.get(currency_rate)
    return result


@router.post('/get-rates', response_model=CurrencyRatesResponse)
async def get_rates(
        currency_rates: CurrencyRatesRequest,
        service: CurrencyRatesService = Depends(get_currency_rates_service),
):
    """
    Retrieve conversion rates for multiple currency pairs.

    Accepts a list of `CurrencyRateRequest` objects encapsulated in a
    `CurrencyRatesRequest` and returns a `CurrencyRatesResponse` containing the conversion rates in original order.

    A conversion rate of `0.0` for any entry indicates that the conversion for that request failed,
    likely due to missing data for the specified currencies or date.

    The number of currency pairs per request is limited.
    """
    results = await service.get(*currency_rates)
    return results
