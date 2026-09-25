FROM node:24-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
WORKDIR /app
COPY pyproject.toml README.md requirements-api.lock ./
COPY src ./src
COPY api ./api
RUN pip install --no-cache-dir --require-hashes -r requirements-api.lock \
    && pip install --no-cache-dir --no-deps . \
    && useradd --create-home --uid 10001 gridflex
COPY data ./data
COPY --from=frontend /build/frontend/dist ./frontend/dist
USER gridflex
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
