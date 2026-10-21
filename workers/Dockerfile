FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src
WORKDIR /app
COPY requirements-cloud.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY src/ ./src/
USER 10001:10001
ENTRYPOINT ["python", "-m", "classic_hubble_pipeline.cloud_run"]
