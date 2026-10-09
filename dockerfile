
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY scraper/ ./scraper/
COPY schema.sql ./

RUN pip install --no-cache-dir .

USER 10001:10001

ENTRYPOINT ["python", "-m", "scraper.cli"]
