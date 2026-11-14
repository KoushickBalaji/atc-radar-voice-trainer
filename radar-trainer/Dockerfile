FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY data/traffic/ /build/data/traffic/
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 ATC_APP_HOST=0.0.0.0 PORT=10000 MPLBACKEND=Agg
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-hosted.txt ./
RUN pip install --no-cache-dir -r requirements-hosted.txt
# Bake static navigation data once; each visitor still gets its own writable copy.
RUN python -c "import bluesky; bluesky.init(mode='sim', detached=True, workdir='/opt/atc-nav')"
ENV ATC_NAV_CACHE=/opt/atc-nav/cache
COPY src/ ./src/
COPY data/ ./data/
COPY run_hosted.py ./
COPY scripts/check_hosted_sessions.py ./scripts/check_hosted_sessions.py
COPY --from=frontend /build/frontend/dist ./frontend/dist/
RUN useradd --create-home trainer && chown -R trainer:trainer /app
USER trainer
EXPOSE 10000
CMD ["python", "run_hosted.py"]
