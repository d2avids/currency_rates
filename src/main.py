import uvicorn
import logging.config
from fastapi import FastAPI, Security, Depends
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from api.v1.currency_rates import router as currency_rates_router
from core.settings import settings
from core.dependencies import verify_api_key, rate_limiter_dependency
from core.logging import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=settings.OPENAPI_URL,
    docs_url=settings.DOCS_URL,
    default_response_class=ORJSONResponse,
    dependencies=[
        Security(verify_api_key),
        Depends(rate_limiter_dependency),
    ],
)
app.include_router(currency_rates_router)

if not settings.DEBUG:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.security.ALLOWED_HOSTS,
)

if __name__ == "__main__":
    uvicorn.run(
        'main:app',
        host=settings.HOST,
        port=settings.PORT,
        log_config=None
    )
