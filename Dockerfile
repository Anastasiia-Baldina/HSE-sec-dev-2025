# Build stage (install dev deps + run tests)
FROM python:3.11-slim AS build

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./

# Dev dependencies are needed only for tests in the build stage
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .

RUN pytest -q


# Runtime stage (production deps only)
FROM python:3.11-slim AS runtime

WORKDIR /app

# Non-root user
RUN useradd --create-home --uid 10001 appuser

# Install only production dependencies to avoid shipping dev/test packages
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
