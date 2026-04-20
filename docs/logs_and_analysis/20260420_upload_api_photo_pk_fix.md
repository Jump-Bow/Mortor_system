---
type: change_log
audience: developer
date: 2026-04-20
---

# 20260420 照片上傳 API 複合主鍵查詢缺口修補

## 摘要

補齊 `POST /api/results/photos/upload` API 的低優先級缺口：查詢 `InspectionResult`
時原本只帶 `(actid, item_id)` 兩欄，與資料庫實際的三欄複合主鍵 `(actid, equipmentid, item_id)` 不符。

---

## 問題描述

**檔案**：`app/api/Mortor_results.py` — `upload_photo()` 函式

**舊版（不完整）**：

```python
# 只用兩欄查詢，未帶入 equipmentid
result = InspectionResult.query.filter_by(
    actid=actid,
    item_id=itemid
).first()
```

**潛在風險**：

| 情境 | 說明 |
|------|------|
| 在同一工單（`actid`）中，兩台設備共用相同的 `item_id`（例如「溫度量測」） | 查詢可能命中「另一台設備」的量測紀錄，照片路徑被錯誤寫入 |
| Form Data 驗證未要求 `equipmentid` | 呼叫端若未傳入，後端無法正確識別紀錄 |

此風險在現行業務中屬低概率（巡檢業務設計傾向一台設備對應一張工單），但與已建立的防護原則不一致，仍需補齊。

---

## 修正內容

**檔案**：`app/api/Mortor_results.py`

### 1. Docstring 補充 `equipmentid` 欄位說明

```python
# 修正後 Docstring
Form Data:
    - actid:       任務 ID
    - itemid:      檢查項目 ID
    - equipmentid: 設備 ID（與 InspectionResult 三欄複合主鍵對齊）
    - file:        圖片檔案
```

### 2. Form Data 驗證加入 `equipmentid`

```python
# 修正前
if 'actid' not in request.form or 'itemid' not in request.form:
    ...message '缺少 actid 或 itemid'

# 修正後
if 'actid' not in request.form or 'itemid' not in request.form or 'equipmentid' not in request.form:
    ...message '缺少 actid、itemid 或 equipmentid'
```

### 3. 查詢條件補齊三欄複合主鍵

```python
# 修正前（兩欄）
result = InspectionResult.query.filter_by(
    actid=actid,
    item_id=itemid
).first()

# 修正後（三欄，與 PK 嚴格對齊）
result = InspectionResult.query.filter_by(
    actid=actid,
    equipmentid=equipmentid,
    item_id=itemid
).first()
```

### 4. Log 訊息補充 `equipmentid`

```python
# 修正後
f'User {current_user.id} uploaded photo for task {actid} equipment {equipmentid} item {itemid}'
```

---

## 關聯性背景

本次修補是 `20260419_db_pk_sync_analysis.md` 中確立的「三欄複合主鍵全面對齊」原則的延伸：

- `inspection_result` PK：`(actid, equipmentid, item_id)` ← 已對齊
- `AbnormalCases` PK：`(actid, equipmentid, item_id)` ← 已對齊（20260419 修正）
- `upload_results` UPSERT：`index_elements=['actid', 'equipmentid', 'item_id']` ← 已對齊
- `upload_photo` 查詢：`filter_by(actid, equipmentid, item_id)` ← **本次修正**

至此，所有觸碰 `InspectionResult` 的寫入與查詢路徑均已對齊三欄複合主鍵，架構防護完整。

---

## App 端現狀確認（2026-04-20 已查閱原始碼）

**結論：App 端照片上傳功能尚未實作，後端此次修補不影響任何現有功能。**

查閱 `lib/data/datasources/remote/result_remote_data_source.dart`（第 68–78 行）確認：

```dart
@override
Future<PhotoUploadResponse> uploadPhoto({
  required int resultId,
  required Uint8List photoData,
  required String photoType,
  String? fileName,
}) async {
  // This part is not fully detailed in APP_FLOW for endpoint,
  // keeping it as placeholder or removing if not needed.
  // Assuming a generic upload photo endpoint exists or we skip it for now.
  throw UnimplementedError("Photo upload not defined in current APP_FLOW scope");
}
```

**現況分析：**

| 項目 | 狀態 |
|------|------|
| App 照片上傳 API 呼叫 | ❌ **尚未實作**（直接 `UnimplementedError`） |
| App 結果上傳（`uploadResults`）| ✅ 已實作，使用 JSON Body 傳入 `photo_data`（Base64） |
| 照片在上傳結果時的傳遞方式 | 在 `results[]` 陣列中，每筆量測結果可附帶 `photo_data`（Base64 字串） |

**實際的照片上傳路徑：**

App 不呼叫 `POST /api/results/photos/upload`，而是在 `POST /api/results/upload` 的 payload 中
直接將照片以 **Base64 字串**（`photo_data` 欄位）包在量測結果內一起上傳，後端在 `upload_results()` 中
透過 `save_base64_image()` 處理（`Mortor_results.py` 第 109–115 行）。

**本次後端 `upload_photo` API 的補修仍有意義**，原因：

1. `photos/upload` 端點是為 **網頁後台** 提供的功能（例如：由設備維護人員在網頁端補充照片）
2. 補修三欄複合主鍵查詢確保網頁端呼叫此 API 時的資料完整性
3. 若未來 App 實作獨立照片上傳功能（如大圖分離上傳），可直接使用已修正的正確端點

**未來 App 實作照片上傳時需補充的內容（備忘）：**

```dart
// result_remote_data_source.dart 中待實作：
// Form Data 必須包含：actid、itemid、equipmentid（三欄複合主鍵）
// POST /api/results/photos/upload
```

