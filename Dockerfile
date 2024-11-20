FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY README.md .
COPY wpstac ./wpstac

RUN pip install --no-cache-dir -e ".[dev]"

ENV STAC_FASTAPI_TITLE="WorldPop STAC API"
ENV STAC_FASTAPI_DESCRIPTION="WorldPop STAC API with Swagger UI"
ENV APP_HOST="0.0.0.0"
ENV APP_PORT=8000
ENV DOCS_URL="/docs"
ENV OPENAPI_URL="/openapi.json"

EXPOSE 8000

CMD ["uvicorn", "wpstac.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/_mgmt/ping || exit 1