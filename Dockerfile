# ──────────────────────────────────────────────────────────────
# Dockerfile — Medical Dictionary Trie API
# ──────────────────────────────────────────────────────────────
#
# Build:
#   docker build -t medical-trie .
#
# Run:
#   docker run -p 8000:8000 medical-trie
#
# Run with custom data file:
#   docker run -p 8000:8000 \
#     -v $(pwd)/data:/app/data \
#     -e MEDICAL_DATA_FILE=/app/data/your_terms.txt \
#     medical-trie
# ──────────────────────────────────────────────────────────────

# ── Stage 1: Builder ───────────────────────────────────────────
FROM python:3.11-slim AS builder

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ──────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    MEDICAL_DATA_FILE=/app/data/sample_medical_terms.txt \
    DEFAULT_TOP_K=10 \
    FUZZY_MAX_DISTANCE=2 \
    DEFAULT_SORT_BY=frequency

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy only necessary project files
COPY data/     ./data/
COPY src/      ./src/
COPY api/      ./api/

# Create __init__.py files for package resolution
RUN touch src/__init__.py api/__init__.py

# Set ownership
RUN chown -R appuser:appgroup /app

USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" \
    || exit 1

# Start the FastAPI server
CMD ["uvicorn", "api.app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
