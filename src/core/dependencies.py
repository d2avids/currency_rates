import datetime
from dataclasses import dataclass, field

from fastapi import Security, HTTPException, Depends, status
from fastapi.security import APIKeyHeader

from core.settings import settings

api_key_header = APIKeyHeader(name=settings.API_KEY_NAME, auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key not in [*settings.UNLIMITED_API_KEYS, *settings.API_KEYS]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Invalid API Key')
    return api_key


@dataclass
class RateLimitRecord:
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    count: int = 0


class RateLimiter:
    def __init__(self, limit: int, interval_minutes: int):
        self.limit = limit
        self.interval_minutes = datetime.timedelta(minutes=interval_minutes)
        self._usages: dict[str, RateLimitRecord] = {}

    def _reset_if_expired(self, api_key: str) -> None:
        record = self._usages.get(api_key)
        if record is None or datetime.datetime.now() > record.timestamp + self.interval_minutes:
            self._usages[api_key] = RateLimitRecord()

    def get_current_usage(self, api_key: str) -> int:
        self._reset_if_expired(api_key)
        return self._usages[api_key].count

    def increment_usage(self, api_key: str) -> None:
        self._usages[api_key].count += 1

    def get_limit_expiration_datetime(self, api_key: str) -> datetime.datetime:
        self._reset_if_expired(api_key)
        return self._usages[api_key].timestamp + self.interval_minutes

    async def check_limit(self, api_key: str) -> None:
        current_usage = self.get_current_usage(api_key)
        if current_usage >= self.limit and api_key not in settings.UNLIMITED_API_KEYS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    'message': f'Rate limit of {self.limit} requests per '
                               f'{int(self.interval_minutes.total_seconds() // 60)} minutes reached',
                    'limit_expires': self.get_limit_expiration_datetime(api_key).strftime('%Y-%m-%d %H:%M:%S')
                }
            )
        self.increment_usage(api_key)


rate_limiter = RateLimiter(
    limit=settings.security.RATE_LIMIT,
    interval_minutes=settings.security.RATE_LIMIT_INTERVAL_MINUTES
)


async def rate_limiter_dependency(api_key: str = Depends(verify_api_key)):
    await rate_limiter.check_limit(api_key)
