FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including build tools for bcrypt
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libffi-dev \
    cargo \
    rustc \
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
    python-jose[cryptography] \
    "passlib[bcrypt]" \
    bcrypt==4.0.1 \
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
