# Docker Configuration
# Container image definition for the backend application
# Instructions for building and running the app in Docker

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# --- EKLEMEN GEREKEN KISIM ---
# Playwright ve tarayıcı bağımlılıklarını kur
RUN pip install playwright
RUN playwright install --with-deps chromium
# -----------------------------

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-tur \
    libtesseract-dev \
    poppler-utils \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \  
    && rm -rf /var/lib/apt/lists/*

# Copy application code
# Copy everything (agents, app, configs etc.)
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

