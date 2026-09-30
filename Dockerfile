FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system chronicle && adduser --system --ingroup chronicle chronicle

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=chronicle:chronicle . .

ENV CHRONICLE_DB_PATH=/app/data/chronicle.db
RUN mkdir -p /app/data && chown -R chronicle:chronicle /app/data

USER chronicle

EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
