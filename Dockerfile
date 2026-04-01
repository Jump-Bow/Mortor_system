# Dockerfile for FEM Admin System

FROM python:3.10.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    PORT=5000

# Install system dependencies
# - libaio1 : Oracle Instant Client 厚模式必要（libclntsh.so 依賴）
# - unzip   : 解壓縮 Oracle Instant Client zip
# - curl    : HEALTHCHECK 使用
# - libpq-dev: psycopg2-binary 已預先編譯，不需要此項，故移除
RUN apt-get update && apt-get install -y \
    libaio1 \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*


# ─── Oracle Instant Client 19.x (相容 Oracle 11.2g+) ──────────────────────────────
# 將本地 33MB 的 zip 檔複製進 Docker 內解壓縮（避免 VPC 防火牆擋住外部下載）
# 前提：請務必將 instantclient-basiclite-linux.x64-19.24.0.0.0dbru.zip 放在專案根目錄
COPY ./instantclient-basiclite-linux.x64-19.24.0.0.0dbru.zip /tmp/instantclient.zip
RUN unzip -q /tmp/instantclient.zip -d /opt/oracle \
    && mv /opt/oracle/instantclient_19_24 /opt/oracle/instantclient \
    && rm /tmp/instantclient.zip

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
