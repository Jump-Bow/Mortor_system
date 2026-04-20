# ============================================================
# Dockerfile for FEM Admin System — Multi-stage Build
# ============================================================
# Stage 1 (builder): 安裝編譯工具、解壓 Oracle Client、pip install
# Stage 2 (final):   複製成品，不含 gcc/g++，最小化攻擊面與 Image 大小
# ============================================================

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.10.13-slim AS builder

WORKDIR /build

# 安裝編譯期系統依賴（僅在 Builder Stage 存在）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# ─── Oracle Instant Client 19.x (相容 Oracle 11.2g+) ─────────────────────────
# zip (33MB) 直接由 git 追蹤，Git CLI 最高支援 100MB，安全無虞。
COPY ./instantclient-basiclite-linux.x64-19.24.0.0.0dbru.zip /tmp/instantclient.zip
RUN unzip -q /tmp/instantclient.zip -d /opt/oracle \
    && mv /opt/oracle/instantclient_19_24 /opt/oracle/instantclient \
    && rm /tmp/instantclient.zip

# 安裝 Production Python 依賴（排除測試/開發工具）
COPY requirements.prod.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.prod.txt \
    && pip install --no-cache-dir gunicorn

# ── Stage 2: Final (Production Image) ────────────────────────────────────────
FROM python:3.10.13-slim AS final

WORKDIR /app

# 僅安裝執行期最低系統依賴（無 gcc / g++ / unzip）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libaio1 \
    && rm -rf /var/lib/apt/lists/*

# 從 Builder 複製已安裝好的 Python packages（避免重新編譯）
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# 從 Builder 複製 Oracle Instant Client 函式庫（只要 .so 庫，不需 zip）
COPY --from=builder /opt/oracle/instantclient /opt/oracle/instantclient

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    PORT=5000 \
    LD_LIBRARY_PATH=/opt/oracle/instantclient

# 複製應用程式碼
COPY . .

# 建立必要目錄
RUN mkdir -p logs uploads/photos

# 對外開放 Port
EXPOSE 5000

# Health check（主要供本地 docker-compose 使用；Cloud Run 由 GCP 自行檢查 Port）
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/login || exit 1

# 以 gunicorn 啟動應用（動態讀取 PORT 環境變數）
CMD gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 2 --timeout 60 --access-logfile - --error-logfile - "run:app"
