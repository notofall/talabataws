FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    uvicorn \
    sqlalchemy \
    asyncpg \
    psycopg2-binary \
    pydantic \
    pydantic-settings \
    python-jose \
    passlib \
    bcrypt \
    python-multipart \
    python-dotenv \
    alembic \
    openpyxl \
    httpx \
    psutil \
    email-validator

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/updates

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
