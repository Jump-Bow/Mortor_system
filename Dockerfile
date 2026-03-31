# Dockerfile for FEM Admin System

FROM python:3.10.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    PORT=5000

# Install system dependencies (PostgreSQL + Oracle Instant Client 19.x 系統依賴)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

# ─── Oracle Instant Client 19.x (相容 Oracle 11.2g) ───────────────────────────
# 請在專案根目錄準備 ./instantclient 目錄（來源：Oracle Instant Client 19.x Basic for Linux x86-64）
# 下載：https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html
# 解壓後將資料夾重新命名為 instantclient 放於專案根目錄（已加入 .gitignore）
COPY ./instantclient /opt/oracle/instantclient
ENV LD_LIBRARY_PATH="/opt/oracle/instantclient"
ENV ORACLE_HOME="/opt/oracle/instantclient"

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs uploads/photos

# Expose port
EXPOSE 5000

# Health check (Use dynamic port if possible, or stay at localhost:5000 for local check)
# In Cloud Run, health check is handled by GCP via the port. 
# This HEALTHCHECK is primarily for local docker-compose.
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/login || exit 1

# Run application with gunicorn using the dynamic PORT variable
CMD gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 60 --access-logfile - --error-logfile - "run:app"
