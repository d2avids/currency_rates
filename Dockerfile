FROM python:3.12-alpine

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PYTHONPATH="${PYTHONPATH}:/app"

WORKDIR /app

RUN pip install poetry==1.8.3 && \
    addgroup -S web && \
    adduser -S -G web -h /app web && \
    chown web:web -R /app

USER web

COPY --chown=web:web poetry.lock pyproject.toml ./

RUN poetry install --without dev && rm -rf $POETRY_CACHE_DIR

COPY --chown=web:web src .

EXPOSE 8080

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
