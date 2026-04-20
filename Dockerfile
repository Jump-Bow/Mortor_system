# Dockerfile for FEM Admin System

FROM python:3.10.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    PORT=5000

# Install system dependencies (PostgreSQL client libraries)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    unzip \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

# ─── Oracle Instant Client 19.x (相容 Oracle 11.2g+) ──────────────────────────────
# zip (33MB) 直接由 git 追蹤，Git CLI 最高支援 100MB，安全無虞。
# GitHub 網頁上傳限 25MB 不能用；本 repo 使用 git push 方式推送。
COPY ./instantclient-basiclite-linux.x64-19.24.0.0.0dbru.zip /tmp/instantclient.zip
RUN unzip -q /tmp/instantclient.zip -d /opt/oracle \
    && mv /opt/oracle/instantclient_19_24 /opt/oracle/instantclient \
    && rm /tmp/instantclient.zip

# 設定 OS linker 路徑，讓 libnnz19.so 等函式庫能被系統直接找到
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient:$LD_LIBRARY_PATH

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
