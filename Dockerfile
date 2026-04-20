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
# 策略（方案 B）：zip 存放於 GCS，由 cloudbuild-main.yaml 步驟 0 在 build 前下載到
# build context，再由此 COPY 指令打包進映像。
# 大型二進位檔不放入 Git，確保 repo 乾淨且符合 VPC-SC 限制。
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
