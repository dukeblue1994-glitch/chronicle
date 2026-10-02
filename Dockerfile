FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system chronicle && adduser --system --ingroup chronicle chronicle
COPY . .
RUN pip install --no-cache-dir . && mkdir -p /app/data && chown -R chronicle:chronicle /app/data
ENV CHRONICLE_DB_PATH=/app/data/chronicle.db
USER chronicle
EXPOSE 8000
CMD ["chronicle-api"]
