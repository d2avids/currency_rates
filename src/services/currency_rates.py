import asyncio
import decimal
import json
import logging
import traceback
from json import JSONDecodeError
from typing import Union, Optional

import aiohttp
from aiohttp import ClientSession
from fastapi import Depends

from core.settings import settings
from exceptions.currency_rates import MaxRatesExceededException
from repositories.currency_rates import (CurrencyRateRepo, ICurrencyRateRepo,
                                         get_currency_rates_repo)
from schemas.currency_rates import (CurrencyRateRequest, CurrencyRateResponse,
                                    CurrencyRatesResponse)

logger = logging.getLogger(__name__)


class CurrencyRateParser:
    """A utility class for parsing and fetching currency conversion rates via HTTP requests."""

    @staticmethod
    def _parse_currency_rate(text: str, currency_name: str) -> str:
        """Parses the currency rate for a given currency from the raw HTML text."""
        right_index = text.find(f'{settings.currency_parsing_settings.CURRENCY_RATE_START_PATTERN}"{currency_name}"')
        starting_index = right_index
        symbol = None
        while symbol != settings.currency_parsing_settings.CURRENCY_RATE_END_PATTERN:
            right_index += 1
            symbol = text[right_index]
        return text[starting_index:right_index + 1]

    @staticmethod
    async def fetch_rate(
            aiohttp_session: ClientSession,
            currency_rate_request: CurrencyRateRequest,
    ) -> CurrencyRateResponse:
        """Performs an HTTP GET request to fetch the conversion rate for the currency pair and returns the parsed rate.

        Args:
          aiohttp_session (ClientSession): The aiohttp client session to use for making the HTTP request.
          currency_rate_request (CurrencyRateRequest): The request object containing the currency pair and date.

        Returns:
          CurrencyRateResponse: The response object containing the conversion rate.
        """
        rate = decimal.Decimal('0.0')
        try:
            async with aiohttp_session.get(
                    url=f'{settings.currency_parsing_settings.CURRENCIES_URL}'
                        f'?from={currency_rate_request.from_cur}&date={currency_rate_request.date}',
                    timeout=settings.currency_parsing_settings.SESSION_TIMEOUT
            ) as response:
                text = await response.text()
                print(text)
            currency_rate_text = CurrencyRateParser._parse_currency_rate(
                text, currency_name=currency_rate_request.to_cur
            )
            currency_rate_json = json.loads(currency_rate_text)
            rate = decimal.Decimal(
                currency_rate_json.get(settings.currency_parsing_settings.RATE_KEY, decimal.Decimal('0.0'))
            )
        except IndexError:
            logger.critical(
                f'Failed to parse for {currency_rate_request.from_cur=}, '
                f'{currency_rate_request.to_cur=} {currency_rate_request.date=}. '
                f'Incorrect parsing strategy. '
                f'Potential access problems or significant change in the HTML markup of the page.'
            )
        except aiohttp.ClientConnectorError:
            trc = traceback.format_exc()
            logger.error(
                f'Failed to fetch for {currency_rate_request.from_cur=}, '
                f'{currency_rate_request.to_cur=} {currency_rate_request.date=}. {trc}'
            )
        except JSONDecodeError:
            trc = traceback.format_exc()
            logger.error(
                f'Could not parse for {currency_rate_request.from_cur=}, '
                f'{currency_rate_request.to_cur=} {currency_rate_request.date=}. '
                f'Potentially invalid date, currencies codes or lack of data. {trc}'
            )
        except Exception:
            trc = traceback.format_exc()
            logger.error(
                f'Unexpected error. Could not fetch or parse for {currency_rate_request.from_cur=}, '
                f'{currency_rate_request.to_cur=} {currency_rate_request.date=}. {trc}'
            )
        finally:
            if rate != decimal.Decimal('0.0'):
                rate = rate.quantize(
                    settings.currency_parsing_settings.DECIMAL_PLACES,
                    rounding=decimal.ROUND_HALF_UP
                )
            return CurrencyRateResponse(**currency_rate_request.model_dump(), rate=rate)


class CurrencyRatesService:
    """Service class responsible for handling currency rate requests and interacting with the repository."""
    def __init__(self, currency_rates_repo: ICurrencyRateRepo):
        self._currency_rates_repo = currency_rates_repo

    async def get(self, *args: CurrencyRateRequest) -> Union[CurrencyRateResponse, CurrencyRatesResponse]:
        """
        Retrieves currency rates for one or more currency pair requests. If the rate is not available
        in the database, it will be fetched from an external service and stored in the database.

        Args:
            *args (CurrencyRateRequest): One or more `CurrencyRateRequest` objects representing the
                currency pairs and dates for which rates are requested.

        Returns:
            Union[CurrencyRateResponse, CurrencyRatesResponse]:
                A single `CurrencyRateResponse` if only one request is made, or a `CurrencyRatesResponse`
                containing a list of responses for multiple requests.

        Raises:
            MaxRatesExceededException(HTTPException): If a number of args exceeds the limit specified
                in the MAX_RATES_PER_REQUEST config variable.
        """
        is_collection = False
        if isinstance(args[0], tuple):
            args = args[0][1]
            if len(args) > settings.currency_parsing_settings.MAX_RATES_PER_REQUEST:
                raise MaxRatesExceededException(settings.currency_parsing_settings.MAX_RATES_PER_REQUEST)
            is_collection = True

        results: list[Optional[CurrencyRateResponse]] = []

        # SEQUENTIAL calls to the db, since doing them all in quick succession has minimal overhead
        # compared to the complexity you’d add by parallelizing them.
        for currency_rate_request in args:
            db_obj = await self._currency_rates_repo.get(currency_rate_request)
            results.append(CurrencyRateResponse.model_validate(db_obj) if db_obj else None)

        missing_rates_indexes: list[int] = [i for i, result in enumerate(results) if not result]

        rates_to_create: list[CurrencyRateResponse] = []
        if missing_rates_indexes:
            async with aiohttp.ClientSession() as session:
                parse_tasks = [
                    asyncio.create_task(CurrencyRateParser.fetch_rate(session, args[i]))
                    for i in missing_rates_indexes
                ]
                parsed_rates = await asyncio.gather(*parse_tasks)

            for i, parsed_rate in zip(missing_rates_indexes, parsed_rates):
                results[i] = parsed_rate
                if parsed_rate.rate != decimal.Decimal('0.0'):
                    rates_to_create.append(parsed_rate)

        if rates_to_create:
            await self._currency_rates_repo.bulk_create_or_update(rates_to_create)

        return CurrencyRatesResponse(
            root=[result for result in results]
        ) if is_collection else results[0]


async def get_currency_rates_service(repo: CurrencyRateRepo = Depends(get_currency_rates_repo)) -> CurrencyRatesService:
    return CurrencyRatesService(repo)
