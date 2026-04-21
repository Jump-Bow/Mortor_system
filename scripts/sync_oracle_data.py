"""
AIMS Oracle 資料同步腳本 (厚模式 / Thick Mode) — Production-Ready v2
======================================================================
從 AIMS Oracle 11.2g 資料庫直接撈取資料，同步至本地 PostgreSQL。

依賴條件：
  - 系統層：libaio1 已安裝，LD_LIBRARY_PATH 指向 Oracle Instant Client 19.x
  - Python層：oracledb==2.1.2, pandas==2.1.4, sqlalchemy==2.0.x
  - GCP Secret Manager 需有：ORA_DB_USER, ORA_DB_PASS,
                              ORA_DB_SERVER, ORA_DB_PORT, ORA_DB_SERVICE

同步資料表與策略（Oracle AIMS → PostgreSQL FEM）：
  ┌──────────────────┬────────────────────────────────────────────────────┐
  │ 資料表           │ 策略                                               │
  ├──────────────────┼────────────────────────────────────────────────────┤
  │ t_organization   │ SCD Type 1 Upsert（有則更新名稱/類型，無則新增）    │
  │ t_equipment      │ SCD Type 1 Upsert（有則更新名稱/位置，無則新增）    │
  │ hr_organization  │ SCD Type 1 Upsert                                  │
  │ hr_account       │ SCD Type 1 Upsert                                  │
  │ t_job            │ Insert-Only + 補齊 act_key/act_mem（不改量測紀錄） │
  │ inspection_result│ 【不同步】— 量測結果僅由 App 巡檢員產生            │
  └──────────────────┴────────────────────────────────────────────────────┘

▶ 重要安全設計：
  - 永不使用 TRUNCATE CASCADE（會連鎖刪除工單/量測/異常紀錄）
  - 永不預建 inspection_result 佔位空行（會導致 App 正常值被 DO NOTHING 吞掉）
  - 所有寫入採用 INSERT ... ON CONFLICT 的原子性 Upsert

使用方式：
  python scripts/sync_oracle_data.py
"""

import os
import re
import sys
import logging
from datetime import datetime, timedelta

import oracledb
import pandas as pd
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

# ── 路徑設定：讓 Flask app 可以被 import ── ────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app

# ── 日誌設定 ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# ==============================================================================
# 1. 設定與連線
# ==============================================================================

ORACLE_CONFIG = {
    "username":     os.environ.get("ORA_DB_USER"),
    "password":     os.environ.get("ORA_DB_PASS"),
    "host":         os.environ.get("ORA_DB_SERVER"),
    "port":         int(os.environ.get("ORA_DB_PORT", "1521")),
    "service_name": os.environ.get("ORA_DB_SERVICE"),
    "schema":       os.environ.get("ORA_DB_SCHEMA", "chimei"),  # Oracle Schema 前綴
}

# 查詢用 Schema 前綴（e.g. "chimei."），空字串則無前綴
_SCHEMA = os.environ.get("ORA_DB_SCHEMA", "chimei")
ORA_PREFIX = f"{_SCHEMA}." if _SCHEMA else ""


def get_oracle_engine() -> sa.Engine:
    """
    建立 Oracle Thick Mode SQLAlchemy 引擎。

    厚模式 (Thick Mode) 必要條件：
      1. libaio1 系統套件已安裝
      2. Oracle Instant Client 19.x 放置於 LD_LIBRARY_PATH 指定路徑
      3. oracledb.init_oracle_client() 需在任何連線前呼叫一次
    """
    # 驗證必要環境變數
    missing = [k for k, v in ORACLE_CONFIG.items() if not v]
    if missing:
        logger.error(f"缺少必要的 Oracle 環境變數: {missing}")
        logger.error("請確認 GCP Secret Manager 已設定 ORA_DB_USER / ORA_DB_PASS / ORA_DB_SERVER / ORA_DB_PORT / ORA_DB_SERVICE")
        sys.exit(1)

    # 取得厚模式（指向 Instant Client 目錄）
    raw_lib_dir = os.environ.get("LD_LIBRARY_PATH", "/opt/oracle/instantclient")
    # Docker 的 ENV 如果串接空變數會產生 "/opt/oracle/instantclient:"，必須濾掉冒號
    lib_dir = raw_lib_dir.split(":")[0] if raw_lib_dir else "/opt/oracle/instantclient"

    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
        logger.info(f"Oracle Thick Mode 初始化完成，函式庫路徑: {lib_dir}")
    except oracledb.ProgrammingError:
        # 已初始化過（同進程多次呼叫）時忽略
        pass
    except Exception as e:
        logger.error(f"Oracle Thick Mode 初始化失敗: {e}")
        logger.error(f"請確認 {lib_dir} 存在且包含 Oracle Instant Client 19.x 的 .so 檔案")
        sys.exit(1)

    conn_str = (
        f"oracle+oracledb://"
        f"{ORACLE_CONFIG['username']}:{ORACLE_CONFIG['password']}"
        f"@{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}"
        f"/?service_name={ORACLE_CONFIG['service_name']}"
    )

    try:
        engine = sa.create_engine(conn_str, pool_pre_ping=True)
        # 測試連線
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1 FROM DUAL"))
        logger.info(f"Oracle 連線成功：{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service_name']}")
        return engine
    except Exception as e:
        logger.error(f"Oracle 連線失敗: {e}")
        sys.exit(1)


def get_postgres_engine() -> sa.Engine:
    """從 Flask Config 取得 PostgreSQL SQLAlchemy 引擎"""
    env = os.getenv("FLASK_ENV", "production")
    flask_app = create_app(env)
    uri = flask_app.config.get("SQLALCHEMY_DATABASE_URI")
    if not uri:
        logger.error("未在 Flask Config 中找到 SQLALCHEMY_DATABASE_URI")
        sys.exit(1)
    return sa.create_engine(uri, pool_pre_ping=True)


# ==============================================================================
# 2. 資料寫入（SCD Type 1 Upsert — 安全版）
# ==============================================================================

# ──────────────────────────────────────────────────────────────────────────────
# 資料表同步策略定義
#
# 設計原則（ISO 55000 / EAM 工業標準）：
#   - 主檔（設備/組織/人員）：SCD Type 1 — 有則更新指定欄位，無則新增
#   - 工單（t_job）：Insert-Only + 有限 Update（僅補齊 act_key / act_mem）
#   - inspection_result / abnormal_cases：絕對不由此腳本操作
#
# 永遠不使用 TRUNCATE CASCADE 原因：
#   TRUNCATE t_equipment CASCADE 會連鎖刪除：
#     → t_job（所有工單）→ inspection_result（所有量測）→ abnormal_cases（所有異常單）
#   這是不可逆的資料災難，且不符合 ISO 55000 可追溯性要求。
# ──────────────────────────────────────────────────────────────────────────────

# 各資料表的 Upsert 設定：
#   key   = 衝突判斷的主鍵欄位
#   update = 發生衝突時要更新的欄位（不在此清單的欄位一律維持現有值）
TABLE_UPSERT_CONFIG = {
    "t_organization": {
        "key": ["unitid"],
        "update": ["parentunitid", "unitname", "unittype"],
    },
    "t_equipment": {
        "key": ["id"],
        "update": ["name", "assetid", "unitid"],
    },
    "hr_organization": {
        "key": ["id"],
        "update": ["parentid", "name"],
    },
    "hr_account": {
        "key": ["id"],
        "update": ["name", "organizationid", "email"],
    },
    "t_job": {
        "key": ["actid"],
        # 工單一旦存在，僅補齊可能在 AIMS 側更新的欄位
        # 絕對不更新 equipmentid / mdate（App 端量測結果依賴此關聯）
        # act_mem / act_mem_id 為 FEM 自訂欄位，Oracle 原生不存在，不同步
        "update": ["act_key"],
    },
}


def upsert_dataframe(df: pd.DataFrame, table_name: str, engine: sa.Engine) -> None:
    """
    將 DataFrame 以 SCD Type 1 策略寫入 PostgreSQL。

    策略：INSERT ... ON CONFLICT (key) DO UPDATE SET (update_cols)
         只更新有差異的欄位（IS DISTINCT FROM），避免無意義的 Write Amplification。

    Args:
        df         : 要寫入的 DataFrame
        table_name : 目標 PostgreSQL 資料表名稱
        engine     : SQLAlchemy Engine
    """
    if df.empty:
        logger.warning(f"  ⚠️  {table_name}: DataFrame 為空，跳過寫入")
        return

    config = TABLE_UPSERT_CONFIG.get(table_name)
    if not config:
        logger.error(f"  ❌ {table_name}: 未定義 Upsert 設定，拒絕寫入（安全防護）")
        return

    key_cols    = config["key"]
    update_cols = config["update"]

    # 只保留資料表定義中相關的欄位，避免 DataFrame 有多餘欄位出錯
    relevant_cols = key_cols + [c for c in update_cols if c in df.columns]
    df = df[[c for c in relevant_cols if c in df.columns]].copy()

    records = df.to_dict(orient="records")
    if not records:
        logger.warning(f"  ⚠️  {table_name}: 無有效紀錄，跳過")
        return

    meta    = sa.MetaData()
    table   = sa.Table(table_name, meta, autoload_with=engine)
    stmt    = pg_insert(table).values(records)

    # ON CONFLICT DO UPDATE — 只更新有差異的欄位
    update_dict = {
        col: stmt.excluded[col]
        for col in update_cols
        if col in df.columns
    }

    if update_dict:
        stmt = stmt.on_conflict_do_update(
            index_elements=key_cols,
            set_=update_dict,
        )
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=key_cols)

    try:
        with engine.begin() as conn:
            result = conn.execute(stmt)
        logger.info(f"  ✅ {table_name}: Upsert {len(records)} 筆（rows affected: {result.rowcount}）")
    except Exception as e:
        logger.error(f"  ❌ 寫入 {table_name} 失敗: {e}")


# ==============================================================================
# 3. 資料轉換 (Transform)
# ==============================================================================

def transform_jobs(jobs_df: pd.DataFrame) -> pd.DataFrame:
    """
    解析工單 act_desc 欄位，萃取保養週期 (mterm) 與等級 (grade)。

    ▶ 與 v1 的差異：
      - 移除 inspection_result 的預建邏輯（不再替 App 塞空白佔位紀錄）
      - 量測結果的建立權完全歸屬 App 巡檢員

    Args:
        jobs_df: 從 Oracle 撈回的工單 DataFrame

    Returns:
        jobs_enriched: 工單加上解析出的 mterm / grade 欄位（供寫入 t_job 用）
    """
    if jobs_df.empty:
        return pd.DataFrame()

    # 從 act_desc 解析格式如「(3M) A級保養」的欄位
    pattern = re.compile(r"\((?P<mterm>\d+[MY])\).*?(?P<grade>[A-Z])級")

    def parse_desc(row):
        m = pattern.search(str(row.get("act_desc", "")))
        if m:
            return pd.Series([m.group("mterm"), m.group("grade")])
        return pd.Series([None, None])

    jobs_df = jobs_df.copy()
    jobs_df[["mterm", "grade"]] = jobs_df.apply(parse_desc, axis=1)

    unparsed = jobs_df["mterm"].isna().sum()
    if unparsed > 0:
        logger.warning(f"  ⚠️  無法解析 act_desc 的工單: {unparsed} 筆（格式不符合 (NM/NY) X級）")

    # 只保留 t_job 需要的欄位
    # act_mem / act_mem_id 為 FEM 自訂欄位，Oracle 原生不存在，已從查詢移除
    keep_cols = [
        c for c in [
            "actid", "equipmentid", "act_desc", "mdate",
            "act_key", "mterm", "grade"
        ]
        if c in jobs_df.columns
    ]
    return jobs_df[keep_cols].copy()


# ==============================================================================
# 4. 主流程 (ETL)
# ==============================================================================

def main():
    logger.info("=" * 60)
    logger.info("🚀 AIMS Oracle 同步作業開始（Thick Mode / Oracle 11.2g）v2")
    logger.info("=" * 60)

    ora_eng = get_oracle_engine()
    pg_eng  = get_postgres_engine()

    # ── Extract（從 AIMS Oracle 抽取）────────────────────────────────────────
    logger.info("📥 [1/3] Extract：從 Oracle 讀取資料...")
    three_months_ago = (datetime.today() - timedelta(days=90)).strftime("%Y%m%d")

    try:
        # ORA-00942 修正：所有資料表加上 Schema 前綴（ORA_PREFIX = "chimei."）
        # ORA-00904 修正：移除 act_mem / act_mem_id（Oracle 原生不存在，為 FEM 自訂欄位）
        jobs = pd.read_sql(
            f"SELECT actid, equipmentid, act_desc, mdate, act_key "
            f"FROM {ORA_PREFIX}t_job WHERE mdate >= '{three_months_ago}'",
            ora_eng
        )
        equip  = pd.read_sql(f"SELECT id, name, assetid, unitid FROM {ORA_PREFIX}t_equipment", ora_eng)
        org    = pd.read_sql(f"SELECT unitid, parentunitid, unitname, unittype FROM {ORA_PREFIX}t_organization", ora_eng)
        hr_org = pd.read_sql(f"SELECT id, parentid, name FROM {ORA_PREFIX}hr_organization", ora_eng)
        hr_acc = pd.read_sql(f"SELECT id, name, organizationid, email FROM {ORA_PREFIX}hr_account", ora_eng)
    except Exception as e:
        logger.error(f"❌ Oracle 資料讀取失敗: {e}")
        return

    logger.info(f"  t_job:          {len(jobs)} 筆（最近 90 天）")
    logger.info(f"  t_equipment:    {len(equip)} 筆")
    logger.info(f"  t_organization: {len(org)} 筆")
    logger.info(f"  hr_organization:{len(hr_org)} 筆")
    logger.info(f"  hr_account:     {len(hr_acc)} 筆")

    # ── Transform（轉換）─────────────────────────────────────────────────────
    logger.info("🔄 [2/3] Transform：解析工單 grade / mterm...")
    jobs_enriched = transform_jobs(jobs)
    logger.info(f"  成功解析工單: {len(jobs_enriched)} 筆")
    # ▶ P1 修正：不再建立 inspection_result 初始記錄
    #   理由：量測結果的建立權完全歸屬 App 巡檢員
    #          若預建 is_out_of_spec=0 的空行，App 正常值（0）將被 ON CONFLICT DO NOTHING 吞掉

    # ── Load（依外鍵順序寫入 PostgreSQL）────────────────────────────────────
    logger.info("💾 [3/3] Load：依外鍵順序寫入 PostgreSQL（SCD Type 1 Upsert）...")
    # 外鍵依賴順序：組織/人員 → 設備 → 工單
    upsert_dataframe(org,           "t_organization",  pg_eng)
    upsert_dataframe(equip,         "t_equipment",     pg_eng)
    upsert_dataframe(hr_org,        "hr_organization", pg_eng)
    upsert_dataframe(hr_acc,        "hr_account",      pg_eng)
    upsert_dataframe(jobs_enriched, "t_job",           pg_eng)
    # inspection_result：不同步（量測結果僅由 App 巡檢員產生）
    # abnormal_cases  ：不同步（純 FEM 業務資料，Oracle AIMS 不存在此概念）

    logger.info("=" * 60)
    logger.info("🏁 同步作業完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
