"""
AIMS Oracle 資料同步腳本 (厚模式 / Thick Mode)
=================================================
從 AIMS Oracle 11.2g 資料庫直接撈取資料，同步至本地 PostgreSQL。

依賴條件：
  - 系統層：libaio1 已安裝，LD_LIBRARY_PATH 指向 Oracle Instant Client 19.x
  - Python層：oracledb==2.1.2, pandas==2.1.4, sqlalchemy==2.0.x
  - GCP Secret Manager 需有：ORA_DB_USER, ORA_DB_PASS,
                              ORA_DB_SERVER, ORA_DB_PORT, ORA_DB_SERVICE

同步資料表（Oracle AIMS → PostgreSQL FEM）：
  t_organization   → 設施組織資料
  t_equipment      → 設備資料
  hr_organization  → HR 組織資料
  hr_account       → 人員帳號資料
  t_job            → 巡檢工單（最近 90 天）
  inspection_result→ 巡檢項目明細（初始化空值）

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
}


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

    # 啟用厚模式（指向 Instant Client 目錄）
    lib_dir = os.environ.get("LD_LIBRARY_PATH", "/opt/oracle/instantclient")
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
# 2. 資料寫入（Upsert）
# ==============================================================================

def upsert_dataframe(df: pd.DataFrame, table_name: str, engine: sa.Engine, constraint_cols: list) -> None:
    """
    將 DataFrame 寫入 PostgreSQL 資料表。

    策略：
    - 主參考資料表（org / equip / hr 等）使用 TRUNCATE + INSERT（全量覆寫）
    - 交易式資料表（t_job / inspection_result）使用 ON CONFLICT DO NOTHING（增量）
    """
    if df.empty:
        logger.warning(f"  ⚠️  {table_name}: DataFrame 為空，跳過寫入")
        return

    FULL_OVERWRITE_TABLES = {"t_organization", "t_equipment", "hr_organization", "hr_account"}

    try:
        with engine.begin() as conn:
            if table_name in FULL_OVERWRITE_TABLES:
                conn.execute(sa.text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))
                df.to_sql(table_name, conn, if_exists="append", index=False)
                logger.info(f"  ✅ {table_name}: 全量覆寫 {len(df)} 筆")
            else:
                temp_table = f"_temp_{table_name}"
                df.to_sql(temp_table, conn, if_exists="replace", index=False)
                cols = ", ".join([f'"{c}"' for c in df.columns])
                constraints = ", ".join([f'"{c}"' for c in constraint_cols])
                upsert_sql = f"""
                    INSERT INTO "{table_name}" ({cols})
                    SELECT {cols} FROM "{temp_table}"
                    ON CONFLICT ({constraints}) DO NOTHING
                """
                conn.execute(sa.text(upsert_sql))
                conn.execute(sa.text(f'DROP TABLE IF EXISTS "{temp_table}"'))
                logger.info(f"  ✅ {table_name}: Upsert 嘗試 {len(df)} 筆")
    except Exception as e:
        logger.error(f"  ❌ 寫入 {table_name} 失敗: {e}")


# ==============================================================================
# 3. 資料轉換 (Transform)
# ==============================================================================

def transform_jobs(jobs_df: pd.DataFrame, pg_engine: sa.Engine):
    """
    解析工單 act_desc 欄位，萃取保養週期 (mterm) 與等級 (grade)，
    並與 PostgreSQL 中的 equit_check_item 對應，產生 inspection_result 初始記錄。

    Returns:
        jobs_enriched (pd.DataFrame): 原工單加上 mterm / grade 欄位（寫入 t_job 用）
        result_df     (pd.DataFrame): 對應的 inspection_result 初始記錄
    """
    if jobs_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # 從 act_desc 解析格式如「(3M) A級保養」的欄位
    pattern = re.compile(r"\((?P<mterm>\d+[MY])\).*?(?P<grade>[A-Z])級")

    def parse_desc(row):
        m = pattern.search(str(row.get("act_desc", "")))
        if m:
            return pd.Series([m.group("mterm"), m.group("grade"), True])
        return pd.Series([None, None, False])

    jobs_df = jobs_df.copy()
    jobs_df[["mterm", "grade", "is_parsed"]] = jobs_df.apply(parse_desc, axis=1)

    parsed_df = jobs_df[jobs_df["is_parsed"]].copy()
    unparsed = len(jobs_df) - len(parsed_df)
    if unparsed > 0:
        logger.warning(f"  ⚠️  無法解析 act_desc 的工單: {unparsed} 筆（格式不符合 (NM/NY) X級）")

    # 與 equit_check_item 對應，找出 item_id
    try:
        specs_df = pd.read_sql("SELECT item_id, grade, mterm FROM equit_check_item", pg_engine)
    except Exception as e:
        logger.error(f"  ❌ 無法讀取 equit_check_item: {e}")
        return jobs_df, pd.DataFrame()

    expanded = pd.merge(parsed_df, specs_df, on=["grade", "mterm"], how="inner")

    if expanded.empty:
        logger.warning("  ⚠️  工單與 equit_check_item 無任何匹配，inspection_result 將不會有新記錄")

    # 組建 inspection_result 的初始記錄
    result_df = expanded[["actid", "equipmentid", "item_id"]].copy()
    result_df["measured_value"] = ""
    result_df["act_mem_id"]     = expanded.get("act_mem_id", pd.Series("", index=expanded.index))
    result_df["act_time"]       = pd.Timestamp.now()
    result_df["is_out_of_spec"] = 0  # 初始狀態：未量測

    # jobs_enriched：原工單加上解析出的 grade / mterm（供寫入 t_job）
    keep_cols = [c for c in ["actid", "equipmentid", "act_desc", "mdate", "act_mem_id", "mterm", "grade"] if c in jobs_df.columns]
    jobs_enriched = jobs_df[keep_cols].copy()

    return jobs_enriched, result_df


# ==============================================================================
# 4. 主流程 (ETL)
# ==============================================================================

def main():
    logger.info("=" * 60)
    logger.info("🚀 AIMS Oracle 同步作業開始（Thick Mode / Oracle 11.2g）")
    logger.info("=" * 60)

    ora_eng = get_oracle_engine()
    pg_eng  = get_postgres_engine()

    # ── Extract（從 AIMS Oracle 抽取）────────────────────────────────────────
    logger.info("📥 [1/3] Extract：從 Oracle 讀取資料...")
    three_months_ago = (datetime.today() - timedelta(days=90)).strftime("%Y%m%d")

    try:
        jobs   = pd.read_sql(
            f"SELECT actid, equipmentid, act_desc, mdate, act_mem_id "
            f"FROM t_job WHERE mdate >= '{three_months_ago}'",
            ora_eng
        )
        equip  = pd.read_sql("SELECT id, name, assetid, unitid FROM t_equipment", ora_eng)
        org    = pd.read_sql("SELECT unitid, parentunitid, unitname, unittype FROM t_organization", ora_eng)
        hr_org = pd.read_sql("SELECT id, parentid, name FROM hr_organization", ora_eng)
        hr_acc = pd.read_sql("SELECT id, name, organizationid, email FROM hr_account", ora_eng)
    except Exception as e:
        logger.error(f"❌ Oracle 資料讀取失敗: {e}")
        return

    logger.info(f"  t_job:          {len(jobs)} 筆（最近 90 天）")
    logger.info(f"  t_equipment:    {len(equip)} 筆")
    logger.info(f"  t_organization: {len(org)} 筆")
    logger.info(f"  hr_organization:{len(hr_org)} 筆")
    logger.info(f"  hr_account:     {len(hr_acc)} 筆")

    # ── Transform（轉換）────────────────────────────────────────────────────
    logger.info("🔄 [2/3] Transform：解析工單並對應巡檢項目...")
    jobs_enriched, result_df = transform_jobs(jobs, pg_eng)
    logger.info(f"  成功解析工單: {len(jobs_enriched)} 筆，inspection_result 初始記錄: {len(result_df)} 筆")

    # ── Load（依外鍵順序寫入 PostgreSQL）───────────────────────────────────
    logger.info("💾 [3/3] Load：寫入 PostgreSQL...")
    upsert_dataframe(org,           "t_organization",   pg_eng, ["unitid"])
    upsert_dataframe(equip,         "t_equipment",       pg_eng, ["id"])
    upsert_dataframe(hr_org,        "hr_organization",   pg_eng, ["id"])
    upsert_dataframe(hr_acc,        "hr_account",        pg_eng, ["id"])
    upsert_dataframe(jobs_enriched, "t_job",             pg_eng, ["actid"])
    upsert_dataframe(result_df,     "inspection_result", pg_eng, ["actid", "item_id", "equipmentid"])

    logger.info("=" * 60)
    logger.info("🏁 同步作業完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
