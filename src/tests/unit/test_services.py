import decimal

import aiohttp
import pytest

from core.settings import settings
from exceptions.currency_rates import MaxRatesExceededException
from schemas.currency_rates import CurrencyRateRequest, CurrencyRatesRequest
from services.currency_rates import CurrencyRateParser, CurrencyRatesService
from tests.helpers import make_fake_parsing_response, FakeCurrencyRepo


class TestCurrencyParser:
    @staticmethod
    async def test_fetch_rate_success(monkeypatch):
        success_rate = '1.2345'
        currency = 'USD'
        monkeypatch.setattr(
            'aiohttp.ClientSession.get', make_fake_parsing_response(rate=success_rate, currency=currency)
        )
        request = CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2025-01-01')
        async with aiohttp.ClientSession() as session:
            response = await CurrencyRateParser.fetch_rate(session, request)
            expected_rate = decimal.Decimal(success_rate).quantize(settings.currency_parsing_settings.DECIMAL_PLACES)
            assert response.rate == expected_rate, f'Expected fetched rate to be {expected_rate}, got {response.rate}'

    @staticmethod
    async def test_fetch_incorrect_rate(monkeypatch):
        rate = 'symbols'
        currency = 'USD'
        monkeypatch.setattr(
            'aiohttp.ClientSession.get', make_fake_parsing_response(rate=rate, currency=currency)
        )
        request = CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2025-01-01')
        async with aiohttp.ClientSession() as session:
            response = await CurrencyRateParser.fetch_rate(session, request)
            expected_rate = decimal.Decimal('0.0')
            assert response.rate == expected_rate, (
                f'For an incorrect rate input, expected {expected_rate}, got {response.rate}'
            )

    @staticmethod
    async def test_fetch_incorrect_text(monkeypatch):
        rate = '0.0'
        expected_rate = decimal.Decimal(rate)
        text = 'FORBIDDEN'
        currency = 'USD'
        monkeypatch.setattr(
            'aiohttp.ClientSession.get', make_fake_parsing_response(rate=rate, text=text, currency=currency)
        )
        request = CurrencyRateRequest(from_cur='EUR', to_cur='USD', date='2025-01-01')
        async with aiohttp.ClientSession() as session:
            response = await CurrencyRateParser.fetch_rate(session, request)
            assert response.rate == expected_rate, (
                f'When response text is {text}, expected rate {expected_rate}, got {response.rate}'
            )


class TestCurrencyRatesService:
    @staticmethod
    async def test_get_single_request(monkeypatch):
        currency = 'USD'
        monkeypatch.setattr(
            'aiohttp.ClientSession.get',
            make_fake_parsing_response(rate='1.2345', currency=currency)
        )
        service = CurrencyRatesService(FakeCurrencyRepo('fake_arg'))
        request = CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2025-01-01')
        result = await service.get(request)
        assert result.date == request.date, f'Expected date {request.date}, got {result.date}'
        assert result.from_cur == request.from_cur, f'Expected from_cur {request.from_cur}, got {result.from_cur}'
        assert result.to_cur == request.to_cur, f'Expected to_cur {request.to_cur}, got {result.to_cur}'
        assert isinstance(result.rate, decimal.Decimal), (
            f'Expected rate type Decimal, got {result.rate} of type {type(result.rate)}'
        )
        assert result.rate != decimal.Decimal('0.0'), f'Expected a non-zero rate, got {result.rate}'

    @staticmethod
    async def test_get_multiple_requests(monkeypatch):
        currency = 'USD'
        monkeypatch.setattr(
            'aiohttp.ClientSession.get',
            make_fake_parsing_response(rate='1.2345', currency=currency)
        )
        service = CurrencyRatesService(FakeCurrencyRepo('fake_arg'))
        requests = CurrencyRatesRequest(root=[
            CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2025-01-01'),
            CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2024-02-02'),
            CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2023-02-02'),
        ])
        results = await service.get(*requests)
        assert len(results.root) == len(requests.root), (
            f'Expected {len(requests.root)} results, got {len(results.root)}'
        )

        for req, res in zip(requests.root, results.root):
            assert res.date == req.date, f'For request with date {req.date}, expected date {req.date}, got {res.date}'
            assert res.from_cur == req.from_cur, (
                f'For request with from_cur {req.from_cur}, expected {req.from_cur}, got {res.from_cur}'
            )
            assert res.to_cur == req.to_cur, (
                f'For request with to_cur {req.to_cur}, expected {req.to_cur}, got {res.to_cur}'
            )
            assert isinstance(res.rate, decimal.Decimal), (
                f'Expected rate to be a Decimal, got {res.rate} of type {type(res.rate)}'
            )
            assert res.rate != decimal.Decimal('0.0'), f'Expected a non-zero rate, got {res.rate}'

    @staticmethod
    async def test_get_too_many_requests(monkeypatch):
        currency = 'USD'
        monkeypatch.setattr(
            'aiohttp.ClientSession.get',
            make_fake_parsing_response(rate='1.2345', currency=currency)
        )
        settings.currency_parsing_settings.MAX_RATES_PER_REQUEST = 2
        service = CurrencyRatesService(FakeCurrencyRepo('fake_arg'))
        requests = CurrencyRatesRequest(root=[
            CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2025-01-01'),
            CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2024-02-02'),
            CurrencyRateRequest(from_cur='EUR', to_cur=currency, date='2023-02-02'),
        ])
        with pytest.raises(MaxRatesExceededException):
            await service.get(*requests)
