import decimal
from datetime import date

from core.settings import settings
from repositories.currency_rates import CurrencyRateRepo
from schemas.currency_rates import CurrencyRateRequest, CurrencyRateResponse


async def test_create_or_update_new(currency_rate_repo: CurrencyRateRepo, db_session):
    """Test creating a new currency rate when it does not yet exist."""
    original_rate = 1.10
    rate_to_check = decimal.Decimal(original_rate).quantize(
        settings.currency_parsing_settings.DECIMAL_PLACES,
        rounding=decimal.ROUND_HALF_UP,
    )

    request_data = CurrencyRateResponse(
        from_cur='USD',
        to_cur='EUR',
        date=date(2023, 1, 1),
        rate=original_rate
    )

    created_rate = await currency_rate_repo.create_or_update(request_data)

    assert created_rate is not None
    assert created_rate.from_cur == 'USD'
    assert created_rate.to_cur == 'EUR'
    assert created_rate.date == date(2023, 1, 1)
    assert created_rate.rate == rate_to_check


async def test_create_or_update_existing(currency_rate_repo: CurrencyRateRepo):
    """Test updating an existing currency rate."""
    original_rate = 0.75
    rate_to_check = decimal.Decimal(original_rate).quantize(
        settings.currency_parsing_settings.DECIMAL_PLACES,
        rounding=decimal.ROUND_HALF_UP,
    )
    existing_data = CurrencyRateResponse(
        from_cur='USD',
        to_cur='GBP',
        date=date(2023, 1, 2),
        rate=original_rate
    )
    existing_obj = await currency_rate_repo.create_or_update(existing_data)
    assert existing_obj.rate == rate_to_check

    original_rate = 0.75
    rate_to_check = decimal.Decimal(original_rate).quantize(
        settings.currency_parsing_settings.DECIMAL_PLACES,
        rounding=decimal.ROUND_HALF_UP,
    )
    updated_data = CurrencyRateResponse(
        from_cur='USD',
        to_cur='GBP',
        date=date(2023, 1, 2),
        rate=original_rate
    )
    updated_obj = await currency_rate_repo.create_or_update(updated_data)

    assert updated_obj.id == existing_obj.id
    assert updated_obj.rate == rate_to_check


async def test_get_currency_rate(currency_rate_repo: CurrencyRateRepo):
    """Test retrieving a currency rate that was already inserted."""
    insert_data = CurrencyRateResponse(
        from_cur='USD',
        to_cur='JPY',
        date=date(2023, 1, 3),
        rate=130.0
    )
    await currency_rate_repo.create_or_update(insert_data)

    request = CurrencyRateRequest(
        from_cur='USD',
        to_cur='JPY',
        date=date(2023, 1, 3)
    )

    retrieved = await currency_rate_repo.get(request)
    assert retrieved is not None
    assert retrieved.from_cur == 'USD'
    assert retrieved.to_cur == 'JPY'
    assert retrieved.date == date(2023, 1, 3)
    assert retrieved.rate == 130.0


async def test_get_non_existing_currency_rate(currency_rate_repo: CurrencyRateRepo):
    """Test retrieving a non-existing currency rate returns None."""
    request = CurrencyRateRequest(
        from_cur='AAA',
        to_cur='BBB',
        date=date(2023, 1, 4)
    )
    retrieved = await currency_rate_repo.get(request)
    assert retrieved is None


async def test_bulk_create_or_update(currency_rate_repo: CurrencyRateRepo):
    """Test the bulk insert or update of currency rates."""
    original_rate_1 = 1.07
    original_rate_2 = 1.06
    rate_to_check_1 = decimal.Decimal(original_rate_1).quantize(
        settings.currency_parsing_settings.DECIMAL_PLACES,
        rounding=decimal.ROUND_HALF_UP,
    )
    rate_to_check_2 = decimal.Decimal(original_rate_2).quantize(
        settings.currency_parsing_settings.DECIMAL_PLACES,
        rounding=decimal.ROUND_HALF_UP,
    )
    rates = [
        CurrencyRateResponse(
            from_cur='EUR', to_cur='USD', date=date(2023, 1, 5), rate=1.05
        ),
        CurrencyRateResponse(
            from_cur='EUR', to_cur='USD', date=date(2023, 1, 6), rate=original_rate_2
        ),
        # Duplicate date/currency pair: should update the existing rate
        CurrencyRateResponse(
            from_cur='EUR', to_cur='USD', date=date(2023, 1, 5), rate=original_rate_1
        ),
    ]
    await currency_rate_repo.bulk_create_or_update(rates)

    # Check that the records exist and the first one (2023-01-05) was updated to 1.07
    req1 = CurrencyRateRequest(from_cur='EUR', to_cur='USD', date=date(2023, 1, 5))
    req2 = CurrencyRateRequest(from_cur='EUR', to_cur='USD', date=date(2023, 1, 6))

    rate1 = await currency_rate_repo.get(req1)
    rate2 = await currency_rate_repo.get(req2)

    assert rate1 is not None
    assert rate1.rate == rate_to_check_1  # Updated
    assert rate2 is not None
    assert rate2.rate == rate_to_check_2  # Inserted


async def test_on_conflict_update(currency_rate_repo):
    """
    Verifies that when inserting a new record with the same unique key
    (from_cur, to_cur, date), the existing row is updated instead of duplicated.
    """
    original_rate = 1.10
    original_rate_decimal = decimal.Decimal(original_rate).quantize(
        settings.currency_parsing_settings.DECIMAL_PLACES,
        rounding=decimal.ROUND_HALF_UP,
    )
    new_rate = 1.25
    new_rate_decimal = decimal.Decimal(new_rate).quantize(
        settings.currency_parsing_settings.DECIMAL_PLACES,
        rounding=decimal.ROUND_HALF_UP,
    )

    initial_rate = CurrencyRateResponse(
        from_cur='EUR', to_cur='USD', date=date(2023, 2, 1), rate=original_rate
    )
    await currency_rate_repo.bulk_create_or_update([initial_rate])

    updated_rate = CurrencyRateResponse(
        from_cur='EUR', to_cur='USD', date=date(2023, 2, 1), rate=new_rate
    )
    await currency_rate_repo.bulk_create_or_update([updated_rate])

    request = CurrencyRateRequest(
        from_cur='EUR', to_cur='USD', date=date(2023, 2, 1)
    )
    result = await currency_rate_repo.get(request)
    assert result is not None, 'Expected a currency rate to be retrieved.'
    assert result.rate == new_rate_decimal, (
        f'Expected rate to be updated to {new_rate_decimal}, '
        f'but got {result.rate} instead.'
    )

    assert result.rate != original_rate_decimal, (
        f'Rate should no longer be {original_rate_decimal}, '
        f'but got {result.rate}.'
    )
