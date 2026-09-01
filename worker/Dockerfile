FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY worker/pyproject.toml .
RUN python -m pip install .
COPY worker/app ./app
COPY shared ./shared
CMD ["python", "-m", "app.main"]
