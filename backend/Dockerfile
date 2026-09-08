# Lightweight official Python 3.11 image for Cloud Run
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered container logging
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set container working directory
WORKDIR /app

# Install dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code into the backend package directory
COPY . /app/backend/

# Ensure the /app directory is in PYTHONPATH so backend.* imports resolve cleanly
ENV PYTHONPATH=/app

# Default documentation port (Cloud Run will inject PORT at runtime)
EXPOSE 8000

# Start uvicorn server binding to 0.0.0.0 and dynamic Cloud Run PORT
# 'exec' ensures uvicorn runs as PID 1 to gracefully handle Cloud Run SIGTERM signals
CMD ["sh", "-c", "exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
