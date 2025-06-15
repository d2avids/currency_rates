import datetime as dt
import decimal

from fastapi.testclient import TestClient

from api.v1.currency_rates import router
from core.settings import settings
from schemas.currency_rates import CurrencyRateResponse
from services.currency_rates import CurrencyRateParser
from tests.helpers import make_fake_parsing_response, FakeCurrencyRepo

UNAUTHORIZED_HEADERS = {
    'Host': settings.security.ALLOWED_HOSTS[0],
}
INVALID_API_KEY_HEADERS = {
    'Host': settings.security.ALLOWED_HOSTS[0],
    settings.API_KEY_NAME: 'fake123',
}
LIMITED_API_KEY_HEADERS = {
    'Host': settings.security.ALLOWED_HOSTS[0],
    settings.API_KEY_NAME: settings.API_KEYS[0],
}
HEADERS = {
    'Host': settings.security.ALLOWED_HOSTS[0],
    settings.API_KEY_NAME: settings.UNLIMITED_API_KEYS[0],
}


def test_get_rate_incorrect_date_format(test_client: TestClient):
    """Test that the get-rate endpoint returns a 422 status code for an incorrect date format."""
    body = {
        'from_cur': 'USD',
        'to_cur': 'EUR',
        'date': '2023/21/21'
    }
    response = test_client.post(
        url=f'api{router.prefix}/get-rate',
        json=body,
        headers=HEADERS
    )
    status_code = response.status_code
    assert status_code == 422


def test_get_rate_date_in_future(test_client: TestClient):
    """Test that the get-rate endpoint returns a 422 status code when the provided date is in the future."""
    body = {
        'from_cur': 'USD',
        'to_cur': 'EUR',
        'date': '2999-01-01'
    }
    response = test_client.post(
        url=f'api{router.prefix}/get-rate',
        json=body,
        headers=HEADERS
    )
    status_code = response.status_code
    assert status_code == 422


def test_get_rate_incorrect_currencies(monkeypatch, test_client: TestClient):
    """
    Test that the get-rate endpoint returns 422 status codes for those currency codes that violates ISO4217 format.
    """
    body = {
        'from_cur': '123',
        'to_cur': 'BBB',
        'date': '2020-01-01'
    }
    response = test_client.post(
        url=f'api{router.prefix}/get-rate',
        json=body,
        headers=HEADERS
    )
    assert response.status_code == 422


def test_get_rate_unauthorized(test_client: TestClient):
    """Test that the get-rate endpoint returns a 403 status code when unauthorized headers are provided."""
    body = {
        'from_cur': 'EUR',
        'to_cur': 'USD',
        'date': '2015-01-01'
    }
    response = test_client.post(
        url=f'api{router.prefix}/get-rate',
        json=body,
        headers=UNAUTHORIZED_HEADERS
    )
    status_code = response.status_code
    assert status_code == 403


def test_get_rate_invalid_api_key(test_client: TestClient):
    """Test that the get-rate endpoint returns a 403 status code when invalid API key is provided."""
    body = {
        'from_cur': 'EUR',
        'to_cur': 'USD',
        'date': '2015-01-01'
    }
    response = test_client.post(
        url=f'api{router.prefix}/get-rate',
        json=body,
        headers=INVALID_API_KEY_HEADERS
    )
    status_code = response.status_code
    assert status_code == 403


def test_get_rate_limited_api_key(monkeypatch, test_client: TestClient):
    """
    Test that the get-rate endpoint returns a 429 status code
    when too many requests with a limited API key are made.
    """
    monkeypatch.setattr(
        'aiohttp.ClientSession.get',
        make_fake_parsing_response(rate='0.65', currency='USD')
    )
    monkeypatch.setattr(
        'repositories.currency_rates.CurrencyRateRepo',
        FakeCurrencyRepo
    )
    body = {
        'from_cur': 'EUR',
        'to_cur': 'USD',
        'date': '2015-01-01'
    }
    for _ in range(settings.security.RATE_LIMIT+1):
        response = test_client.post(
            url=f'api{router.prefix}/get-rate',
            json=body,
            headers=LIMITED_API_KEY_HEADERS
        )
    status_code = response.status_code
    assert status_code == 429


def test_get_rate_correct(monkeypatch, test_client: TestClient):
    """Test that the get-rate endpoint returns the correct conversion rate for valid input."""
    from_cur = 'EUR'
    to_cur = 'USD'
    date = '2015-01-01'
    monkeypatch.setattr(
        'aiohttp.ClientSession.get',
        make_fake_parsing_response(rate='0.65', currency=to_cur)
    )
    monkeypatch.setattr(
        'repositories.currency_rates.CurrencyRateRepo',
        FakeCurrencyRepo
    )
    body = {
        'from_cur': from_cur,
        'to_cur': to_cur,
        'date': date
    }
    response = test_client.post(
        url=f'api{router.prefix}/get-rate',
        json=body,
        headers=HEADERS
    )
    status_code = response.status_code
    response_json = response.json()
    assert status_code == 200
    assert response_json['fromCur'] == from_cur
    assert response_json['toCur'] == to_cur


async def fake_fetch_rate(session, req):
    """Fake async fetch_rate function to simulate external conversion rate fetching."""
    if req.from_cur == 'EUR':
        return CurrencyRateResponse(
            from_cur='EUR',
            to_cur='USD',
            date=dt.date.fromisoformat('2015-01-01'),
            rate=decimal.Decimal('0.65')
        )
    elif req.from_cur == 'AAA':
        return CurrencyRateResponse(
            from_cur='AAA',
            to_cur='BBB',
            date=dt.date.fromisoformat('2020-01-01'),
            rate=decimal.Decimal('0.0')
        )
    # Default fallback.
    return CurrencyRateResponse(
        from_cur=req.from_cur,
        to_cur=req.to_cur,
        date=dt.date.fromisoformat(req.date) if isinstance(req.date, str) else req.date,
        rate=decimal.Decimal('0.0')
    )


def test_get_rates_multiple(monkeypatch, test_client: TestClient):
    """Test the get-rates endpoint with multiple conversion rate requests, verifying order and values."""
    valid_request = {
        'from_cur': 'EUR',
        'to_cur': 'USD',
        'date': '2015-01-01'
    }
    invalid_request = {
        'from_cur': 'AAA',
        'to_cur': 'BBB',
        'date': '2020-01-01'
    }

    monkeypatch.setattr(CurrencyRateParser, 'fetch_rate', fake_fetch_rate)
    monkeypatch.setattr('repositories.currency_rates.CurrencyRateRepo', FakeCurrencyRepo)

    payload = [valid_request, invalid_request]

    response = test_client.post(
        url=f'api{router.prefix}/get-rates',
        json=payload,
        headers=HEADERS
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 2

    first_response = data[0]
    assert first_response['fromCur'] == 'EUR'
    assert first_response['toCur'] == 'USD'

    second_response = data[1]
    assert second_response['fromCur'] == 'AAA'
    assert second_response['toCur'] == 'BBB'


def test_get_rates_exceeds_max(test_client: TestClient):
    """Test that the get-rates endpoint returns an error when the number of requests exceeds the maximum allowed."""
    max_requests = settings.currency_parsing_settings.MAX_RATES_PER_REQUEST
    payload = [
        {'from_cur': 'EUR', 'to_cur': 'USD', 'date': '2015-01-01'}
        for _ in range(max_requests + 1)
    ]

    response = test_client.post(
        url=f'api{router.prefix}/get-rates',
        json=payload,
        headers=HEADERS
    )

    assert response.status_code == 400, response.text
    detail = response.json().get('detail', '')
    assert str(max_requests) in detail
