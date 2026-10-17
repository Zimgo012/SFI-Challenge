# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/simulator
COPY sfi_challenge/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY sfi_challenge/app ./app
COPY docker/healthcheck.py /app/docker/healthcheck.py
RUN mkdir -p /app/simulator/data /var/lib/sfi
EXPOSE 8087
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8087", "--workers", "1"]
