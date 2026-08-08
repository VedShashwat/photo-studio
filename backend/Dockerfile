FROM python:3.12-slim
WORKDIR /app
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir .
COPY backend/app ./app
COPY backend/alembic.ini .
COPY backend/migrations ./migrations
COPY shared ./shared
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
