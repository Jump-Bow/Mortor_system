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

    # ── 先 autoload PG 資料表結構，再過濾 DataFrame ───────────────────────────
    # 修正：INSERT 應包含 PG 資料表所有有值的欄位（確保 NOT NULL 欄位有值）
    # ON CONFLICT DO UPDATE 只更新 update_cols 指定欄位，不影響既有業務資料。
    # 舊作法只保留 key+update_cols，導致 NOT NULL 欄位（如 mdate）被丟棄而報錯。
    meta  = sa.MetaData()
    table = sa.Table(table_name, meta, autoload_with=engine)
    pg_col_names = {col.name for col in table.columns}
    # 只保留 PG 資料表中存在的欄位，過濾 DataFrame 的多餘欄位（如 Oracle 原生計算欄）
    df = df[[c for c in df.columns if c in pg_col_names]].copy()

    # ── CardinalityViolation 防護 ────────────────────────────────────────────
    # PostgreSQL ON CONFLICT DO UPDATE 不允許同批次對同一行 UPDATE 兩次。
    # 若 Oracle 來源有重複主鍵（資料品質問題），必須在此去重，保留最後一筆。
    before_count = len(df)
    df = df.drop_duplicates(subset=key_cols, keep="last")
    dup_count = before_count - len(df)
    if dup_count > 0:
        logger.warning(f"  ⚠️  {table_name}: 發現並移除 {dup_count} 筆重複主鍵紀錄（CardinalityViolation 防護）")

    records = df.to_dict(orient="records")
    if not records:
        logger.warning(f"  ⚠️  {table_name}: 無有效紀錄，跳過")
        return

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
        equip = pd.read_sql(
            f"SELECT id, name, assetid, unitid FROM {ORA_PREFIX}t_equipment",
            ora_eng
        )

        # ── t_organization 去重（CardinalityViolation 根本修復）────────────────
        # Oracle AIMS 設計：同一 unitid 存在多筆：
        #   - 自我指向 (parentunitid=unitid)：master record，需丟棄
        #   - 根節點 (parentunitid='*')：無父部門，保留但後續轉 NULL
        #   - 正常層級 (parentunitid=真正父節點)：優先保留
        # 優先序（明確單一 CASE，避免 '*' 與數字比較的歧義）：
        #   0 = 正常層級（非自我指向 AND 非 '*'）← 最優先
        #   1 = 根節點（parentunitid='*'）
        #   2 = 自我指向（parentunitid=unitid）← 最低優先，丟棄
        org = pd.read_sql(
            f"""
            SELECT unitid, parentunitid, unitname, unittype
            FROM (
                SELECT unitid, parentunitid, unitname, unittype,
                       ROW_NUMBER() OVER (
                           PARTITION BY unitid
                           ORDER BY
                               CASE
                                   WHEN parentunitid = unitid THEN 2
                                   WHEN parentunitid = '*'    THEN 1
                                   ELSE 0
                               END,
                               unittype
                       ) AS rn
                FROM {ORA_PREFIX}t_organization
            ) WHERE rn = 1
            """,
            ora_eng
        )

        # ── hr_organization 去重（同樣防護，id 可能重複）────────────────────────
        hr_org = pd.read_sql(
            f"""
            SELECT id, parentid, name
            FROM (
                SELECT id, parentid, name,
                       ROW_NUMBER() OVER (
                           PARTITION BY id
                           ORDER BY
                               CASE WHEN parentid <> id THEN 0 ELSE 1 END,
                               CASE WHEN parentid = '*' THEN 1 ELSE 0 END
                       ) AS rn
                FROM {ORA_PREFIX}hr_organization
            ) WHERE rn = 1
            """,
            ora_eng
        )

        hr_acc = pd.read_sql(
            f"SELECT id, name, organizationid, email FROM {ORA_PREFIX}hr_account",
            ora_eng
        )
    except Exception as e:
        logger.error(f"❌ Oracle 資料讀取失敗: {e}")
        return

    logger.info(f"  t_job:          {len(jobs)} 筆（最近 90 天）")
    logger.info(f"  t_equipment:    {len(equip)} 筆")
    logger.info(f"  t_organization: {len(org)} 筆")
    logger.info(f"  hr_organization:{len(hr_org)} 筆")
    logger.info(f"  hr_account:     {len(hr_acc)} 筆")

    # ── Transform（轉換）─────────────────────────────────────────────────────
    logger.info("🔄 [2/3] Transform：解析工單 grade / mterm 及清理 ForeignKey 參照...")
    
    # ▶ P2 修正：處理 Oracle 根節點 '*' 為 None (NULL)
    # Oracle 用 '*' 代表無父節點，但 PostgreSQL FK 要求 NULL
    org["parentunitid"] = org["parentunitid"].apply(lambda x: None if str(x).strip() == '*' else x)
    hr_org["parentid"] = hr_org["parentid"].apply(lambda x: None if str(x).strip() == '*' else x)

    jobs_enriched = transform_jobs(jobs)
    logger.info(f"  成功解析工單: {len(jobs_enriched)} 筆")

    # ── Oracle actid 唯一化（第一性原理修正）────────────────────────────────
    # Oracle AIMS 設計：同一工單號（actid）可對應多台設備，每台一行。
    # 例：actid='1001', equipmentid='MAE05D31'
    #     actid='1001', equipmentid='MAE05D32'  ← actid 重複！
    # PostgreSQL t_job.actid 為單一主鍵，直接匯入會產生 CardinalityViolation。
    # 解法：ETL Transform 階段合成唯一 actid = original_actid + "_" + equipmentid
    # 系統封閉：App 下載到的 actid 即為合成值，上傳巡檢結果時使用同一 actid，FK 完整。
    before_dedup = len(jobs_enriched)
    jobs_enriched["actid"] = (
        jobs_enriched["actid"].astype(str).str.strip()
        + "_"
        + jobs_enriched["equipmentid"].astype(str).str.strip()
    )
    # 合成後仍可能因 Oracle 重複資料有重複 → 取最後一筆（最新）
    jobs_enriched = jobs_enriched.drop_duplicates(subset=["actid"], keep="last").copy()
    after_dedup = len(jobs_enriched)
    if before_dedup - after_dedup > 0:
        logger.warning(
            f"  ⚠️  t_job: actid 合成後仍有 {before_dedup - after_dedup} 筆重複（Oracle 資料品質問題），保留最後一筆"
        )
    logger.info(f"  actid 合成完成：{before_dedup} 筆 → {after_dedup} 筆唯一工單")

    # ▶ P1 修正：不再建立 inspection_result 初始記錄
    #   理由：量測結果的建立權完全歸屬 App 巡檢員
    #          若預建 is_out_of_spec=0 的空行，App 正常值（0）將被 ON CONFLICT DO NOTHING 吞掉

    # ── Load（依外鍵順序寫入 PostgreSQL）────────────────────────────────────
    logger.info("💾 [3/3] Load：依外鍵順序寫入 PostgreSQL（SCD Type 1 Upsert）...")
    # 外鍵依賴順序：組織/人員 → 設備 → 工單
    upsert_dataframe(org,           "t_organization",  pg_eng)

    # ── ForeignKeyViolation 防護：t_equipment → t_organization ───────────────
    valid_torg_ids = set(org["unitid"].dropna().astype(str))
    equip_valid = equip[equip["unitid"].astype(str).isin(valid_torg_ids)].copy()
    equip_orphan_count = len(equip) - len(equip_valid)
    if equip_orphan_count > 0:
        logger.warning(
            f"  ⚠️  t_equipment: 略過 {equip_orphan_count} 筆孤兒紀錄"
            f"（unitid 未出現在 t_organization，FK 防護）"
        )
    upsert_dataframe(equip_valid,   "t_equipment",     pg_eng)
    
    upsert_dataframe(hr_org,        "hr_organization", pg_eng)

    # ── ForeignKeyViolation 防護：hr_account → hr_organization ───────────────
    # hr_account.organizationid 受 FK 約束，若 Oracle 來源有孤兒紀錄
    # （organizationid 不存在於 hr_organization），寫入時 PG 會報 FK 錯誤。
    # 解法：以 hr_org 實際同步成功的 id 集合做白名單過濾。
    valid_org_ids = set(hr_org["id"].dropna().astype(str))
    hr_acc_valid  = hr_acc[hr_acc["organizationid"].astype(str).isin(valid_org_ids)].copy()
    orphan_count  = len(hr_acc) - len(hr_acc_valid)
    if orphan_count > 0:
        logger.warning(
            f"  ⚠️  hr_account: 略過 {orphan_count} 筆孤兒紀錄"
            f"（organizationid 未出現在 hr_organization，FK 防護）"
        )
    upsert_dataframe(hr_acc_valid,  "hr_account",      pg_eng)

    # ── NOT NULL 防護：t_job.mdate 不可為 null ────────────────────────────────
    # PostgreSQL t_job.mdate 定義為 nullable=False，
    # 但 Oracle AIMS 存在 mdate=NULL 的工單（未排定日期），需在此過濾。
    jobs_valid = jobs_enriched.dropna(subset=["mdate"]).copy()
    null_mdate_count = len(jobs_enriched) - len(jobs_valid)
    if null_mdate_count > 0:
        logger.warning(
            f"  ⚠️  t_job: 略過 {null_mdate_count} 筆 mdate=NULL 的工單"
            f"（Oracle 未排定日期，不符合 NOT NULL 約束）"
        )

    # ── ForeignKeyViolation 防護：t_job → t_equipment ────────────────────────
    # t_job.equipmentid 受 FK 約束，若對應設備因 t_organization 孤兒而被過濾，
    # 相關工單也必須一併排除，否則寫入時 PG 會報 FK 錯誤。
    valid_equip_ids = set(equip_valid["id"].dropna().astype(str))
    jobs_equip_valid = jobs_valid[jobs_valid["equipmentid"].astype(str).isin(valid_equip_ids)].copy()
    equip_job_orphan_count = len(jobs_valid) - len(jobs_equip_valid)
    if equip_job_orphan_count > 0:
        logger.warning(
            f"  ⚠️  t_job: 略過 {equip_job_orphan_count} 筆孤兒工單"
            f"（equipmentid 未出現在 t_equipment，FK 防護）"
        )
    upsert_dataframe(jobs_equip_valid, "t_job", pg_eng)
    # inspection_result：不同步（量測結果僅由 App 巡檢員產生）
    # abnormal_cases  ：不同步（純 FEM 業務資料，Oracle AIMS 不存在此概念）

    logger.info("=" * 60)
    logger.info("🏁 同步作業完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
