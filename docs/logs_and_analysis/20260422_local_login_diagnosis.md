---
type: investigation
audience: developer
date: 2026-04-22
---

# Local 登入失敗根因診斷

## 第一性原理：認證的本質是什麼？

> 認證 = **「驗證你所知道的事（密碼）與我所記得的（Hash）是否對應同一個明文」**

正確的密碼生命週期只有三個環節：

```
[1. 建立] 明文密碼 → Hash(明文, salt) → 存儲 Hash
[2. 驗證] 輸入明文 → Hash(明文, 存儲的salt) → 比對 Hash
[3. 系統邊界] 明文永遠不跨系統傳遞；Hash 也永遠不需要「解密」
```

從這個基礎出發，**唯一可能造成 Local 登入失敗的根本原因只有一個**：
> 「驗證時計算的 Hash」≠「資料庫中儲存的 Hash」

---

## MECE 根因分析

### 維度 A：密碼被寫入資料庫時（Write Side）

| # | 問題 | 程式位置 | 現況 |
|---|------|---------|------|
| A1 | **Hash 格式不一致** | `sync_oracle_data.py` L455 | `generate_password_hash(str(uid), method='pbkdf2:sha256')` → 預設 iterations=600000 |
| A2 | **觸發條件有漏洞** | `sync_oracle_data.py` L450 | 只對 `password IS NULL OR password = ''` 初始化，**若已有舊值就永遠不更新** |
| A3 | **SCD Upsert 設定排除 password 欄位** | `sync_oracle_data.py` L171-174 | `hr_account` 的 update 清單為 `["name", "organizationid", "email"]`，**沒有 password** → 首次 INSERT 後密碼欄位就被 upsert 略過 |

**問題 A3 是最危險的靜默邊界條件**：
- 第一次 Sync 時帳號不存在 → INSERT 成功，密碼欄位為 NULL
- 密碼初始化成功 → Hash 寫入
- 第二次 Sync 時帳號已存在 → ON CONFLICT DO UPDATE 只更新 name/org/email，password **保持不變**（這是正確設計）
- **但若資料庫被重置或帳號被刪除後重新 Sync**，第一次 INSERT 的欄位僅為 Oracle 來源欄位（id, name, organizationid, email），**password 欄位為 NULL**，然後密碼初始化邏輯才補上 → 這個流程本身正確

> **結論 A**：Write Side 的設計邏輯流程上是正確的，但存在一個**時序性的靜默風險**：若密碼初始化那段 try/except 因任何原因（DB 連線中斷、Werkzeug 未安裝）靜默失敗，密碼就會停留在 NULL，而之後的 Sync 因為 ON CONFLICT DO UPDATE 不含 password，永遠不會補回。

---

### 維度 B：密碼被讀取驗證時（Read Side）

#### B1：WEB 端（Flask / `Mortor_user.py`）

```python
# L65-73: check_password 實作
if not self.password.startswith('pbkdf2:'):
    # 明文比對（相容舊版）
    return self.password == password
return check_password_hash(self.password, password)
```

`check_password_hash` 是 Werkzeug 標準函式，能正確解析：
```
pbkdf2:sha256:600000$<salt>$<hash>
```

**WEB 端驗證邏輯本身是正確的**，問題不在這裡。

---

#### B2：APP 端（Dart / `database_helper.dart`）

```dart
// L86-114: _checkPbkdf2Hash 自實作的 PBKDF2 驗證
final colonParts = storedHash.split(':');
// 期望格式: pbkdf2:sha256:{iterations}${salt}${hash}

final dollarParts = colonParts[2].split('$');
// colonParts[2] = "600000$<salt>$<hash>"
// dollarParts[0] = iterations
// dollarParts[1] = salt
// dollarParts[2] = hash
```

**⚠️ 關鍵 Bug 已確認**：

Werkzeug 產生的 Hash 格式中，salt 是隨機字元組成的字串，**不是 Base64 的 bytes**。
APP 端用 `utf8.encode(saltStr)` 來解碼 salt：

```dart
final saltBytes = utf8.encode(saltStr); // L104 — 這是正確的
```

Werkzeug 的 `_hash_internal` 函式中：
```python
# Werkzeug 原始碼
salt = gen_salt()              # 例如 "a1b2c3d4"
salt_bytes = salt.encode()     # = b"a1b2c3d4" （即 UTF-8）
```

所以 `utf8.encode(saltStr)` 理論上與 Werkzeug 的 `salt.encode()` 等價，**這部分是正確的**。

**真正的問題點在於 iterations 的解析**：

Werkzeug `pbkdf2:sha256:600000$xxx$yyy` 中第三個冒號段為 `600000$xxx$yyy`，
APP 端用 `colonParts[2].split('$')` 分割：
- `dollarParts[0]` = `"600000"` → `int.parse` → 600000 ✅
- `dollarParts[1]` = salt ✅
- `dollarParts[2]` = hash ✅

邏輯本身看起來正確，但需要驗證**實際的 Werkzeug 預設 iterations 是否真的是 600000**。

---

### 維度 C：密碼本身的問題（Identity Side）

這是最根本的問題：

| 使用者輸入 | 系統期望 | 是否正確？ |
|-----------|---------|----------|
| 員工編號（如 `A12345`） | `generate_password_hash("A12345")` 的結果 | ✅ 設計如此 |

**設計前提**：使用者的「Local 登入密碼」= 員工編號。  
這個設計本身沒問題，**但使用者不知道這個規則時，就會輸入自己以為的密碼**。

---

### 維度 D：WEB Local 登入的 Session / Jinja 層問題

WEB 端除了 API 登入外，還有 Jinja Template 的 Web 登入（`flask_login_user`）。  
需確認：

```python
# Mortor_auth.py L183-185
user = HrAccount.query.filter_by(id=username).first()
if not user or not user.check_password(password):
```

`HrAccount.query.filter_by(id=username)` — 這裡 `id` 欄位是員工編號（PK 為字串）。
**如果使用者輸入的是中文名字、EMAIL 而非員工編號，就找不到 user**，會回傳 401。

---

## 診斷總結（MECE 矩陣）

```
┌─────────────────┬──────────────────────────────────────┬────────────────────────┐
│ 分類            │ 問題                                  │ 嚴重性                 │
├─────────────────┼──────────────────────────────────────┼────────────────────────┤
│ A. Write Side   │ 密碼初始化 try/except 靜默失敗         │ 🔴 中高（有發生可能性）  │
│                 │ SCD Upsert 不含 password，無法補救     │ 🟡 設計上可接受         │
├─────────────────┼──────────────────────────────────────┼────────────────────────┤
│ B. Read Side    │ WEB check_password 邏輯正確            │ ✅ 無問題               │
│                 │ APP PBKDF2 Dart 實作待驗證             │ 🟠 需要實測             │
├─────────────────┼──────────────────────────────────────┼────────────────────────┤
│ C. Identity     │ 使用者不知道初始密碼 = 員工編號         │ 🔴 高（UX 設計問題）    │
├─────────────────┼──────────────────────────────────────┼────────────────────────┤
│ D. WEB Login    │ filter_by(id=username) — 需輸入員工編號│ 🟠 使用者體驗問題       │
└─────────────────┴──────────────────────────────────────┴────────────────────────┘
```

---

## 推薦的驗證步驟（由淺入深）

### Step 1：確認 PostgreSQL 中的密碼欄位值

```sql
SELECT id, name, 
       CASE 
         WHEN password IS NULL THEN 'NULL'
         WHEN password = '' THEN 'EMPTY'
         WHEN password LIKE 'pbkdf2:%' THEN 'OK_HASH'
         ELSE 'UNKNOWN_FORMAT'
       END AS pwd_status
FROM hr_account
LIMIT 20;
```

### Step 2：手動驗證 Hash 是否可以被正確驗證（Python）

```python
from werkzeug.security import check_password_hash, generate_password_hash

uid = "A12345"  # 替換為真實員工編號
# 從資料庫取出的 hash
stored_hash = "pbkdf2:sha256:600000$xxxxx$yyyyyyy"

print(check_password_hash(stored_hash, uid))  # 應該印出 True
```

### Step 3：確認 APP 端 PBKDF2 實作與 Werkzeug 輸出一致

在 Python 中手動重算 PBKDF2：
```python
import hashlib, binascii

password = b"A12345"
salt = b"xxxxx"          # 從 hash 字串取出的 salt，UTF-8 encode
iterations = 600000
dk = hashlib.pbkdf2_hmac('sha256', password, salt, iterations, dklen=32)
print(binascii.hexlify(dk).decode())  # 比對 Dart 算出的值
```

---

## 修復建議

### Fix 1（最優先）：在 `sync_oracle_data.py` 中強化密碼初始化的錯誤記錄

目前 `except Exception as e` 只 log 錯誤但繼續執行，導致靜默失敗。建議在 Sync 結束後重新檢查密碼狀態：

```python
# 驗收步驟：確認所有帳號都有 Hash
with pg_eng.connect() as conn:
    null_count = conn.execute(sa.text(
        "SELECT COUNT(*) FROM hr_account WHERE password IS NULL OR password = ''"
    )).scalar()
    if null_count > 0:
        logger.error(f"❌ 仍有 {null_count} 筆帳號無密碼，請手動檢查！")
        sys.exit(1)  # 讓 Cloud Run Job 以失敗狀態結束，觸發警報
```

### Fix 2（WEB）：Local 登入頁面明確提示初始密碼規則

在 WEB 登入頁面加上提示：「初始密碼為您的員工編號」

### Fix 3（APP）：加入 Hash 驗證的 debug log

在 `_checkPbkdf2Hash` 中加入不含敏感資料的 debug log，確認 iterations/salt/hash 是否正確解析：

```dart
AppLogger.d('[Auth] iterations=$iterations, saltLen=${saltStr.length}, storedHex=${storedHex.substring(0, 8)}...');
```
