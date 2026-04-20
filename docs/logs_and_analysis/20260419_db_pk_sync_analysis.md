---
type: log_and_analysis
audience: developers, maintainers
date: 2026-04-19
---
# 資料庫複合主鍵 (PK) 同步狀態與重複寫入分析

## 1. 調查背景
近端檢查發現，當量測資料更新到 APP 端時會發生「重複新增單據/資料」的現象。為了防堵問題擴大，本次全面清查了網頁端 (Web/Server Backend) 與 APP 端 (Flutter/SQLite) 的關聯資料庫模型設計。

## 2. APP 端發生重複新增的原因 (首要防線)
探究其根本原因：問題出在早期 APP 資料寫入行為與 SQLite 的隱含特性發生衝突。
*   **發生機理**：SQLite 內部認定包含 `NULL` 值的複合主鍵是互相不可比對的（即 `NULL != NULL`）。當早先 APP `saveResult` 未給定 `equipmentid`，資料庫將該欄位存為 NULL；此時搭配 `ConflictAlgorithm.replace` 覆蓋邏輯完全失效。結果造成每次儲存都視為一個「全新且獨立」的異常紀錄，進而長出無限多筆重覆資料。
*   **目前修補情形 (App)**：審視專案 `check_item_list_page.dart` 可見，此問題已由前端工程師修復。其存檔函數內已正式補入了 `equipmentid: widget.equipment.id` 讓主鍵的 3 欄都不為空，並標註了防呆註解（`FIX: PRIMARY KEY ...`）。

## 3. Web 端與 APP 端 PK 同步狀態盤點 (次要防線)
將兩端資料儲存核心邏輯依第一性原理切開來看：
*   **`InspectionResult` (量測紀錄)**：
    *   **網頁與 API 寫入**：完全以 `(actid, equipmentid, item_id)` 複合索引作 PostgreSQL UPSERT (`Mortor_results.py` 中明確定義 `index_elements`)。
    *   **狀態**：兩端完美對齊。
*   **`AbnormalCases` (異常檢核表)**：
    *   **APP 端**：與量測紀錄連動，明確採用 `PRIMARY KEY (actid, equipmentid, item_id)`。
    *   **網頁端 (原)**：ORM Schema 中僅有 `actid` 與 `item_id` 標註了 `primary_key=True`，而 `equipmentid` 宣告遺漏了這項指引。
    *   **潛藏危險**：若伺服器端後續觸發擴張的關聯儲存或是異常修復 `AbnormalCases` 資料寫入邏輯，可能因 `equipmentid` 缺乏 PK 宣告，導致資料庫對齊不完全，ORM 不能建立預期的鎖（Locks），從而拋出 `IntegrityError`。

## 4. 修正與結論
*   我們已經直接修改網頁端核心模組的 `app/models/Mortor_abnormal.py`，補上 `equipmentid` 相關的 `primary_key=True` 屬性。
*   此修改讓 Server Schema 與 Flutter SQLite Schema 正式達到 MECE 上的嚴格對齊，防堵未來任一端同步引發重疊與索引相衝。

---

## 5. 後續補修（2026-04-20）

在逐一審查所有觸碰 `InspectionResult` 的程式碼路徑後，發現 `upload_photo()` API 原本僅以 `(actid, item_id)` 兩欄查詢，未帶入 `equipmentid`，與三欄複合主鍵原則不符。

已於 `app/api/Mortor_results.py` 補齊：

| 路徑 | 修正前 | 修正後 |
|------|--------|--------|
| `upload_results` UPSERT | `(actid, equipmentid, item_id)` ✅ | 不變 |
| `upload_photo` filter_by | `(actid, item_id)` ❌ | `(actid, equipmentid, item_id)` ✅ |

詳見 `20260420_upload_api_photo_pk_fix.md`。

至此，所有觸碰 `InspectionResult` 的寫入與查詢路徑均已完整對齊三欄複合主鍵：

```
InspectionResult PK: (actid, equipmentid, item_id)
    ├── upload_results  UPSERT index_elements ✅
    ├── upload_photo    filter_by             ✅ (2026-04-20 修補)
    └── AbnormalCases   FK / PK               ✅ (2026-04-19 修補)
```

