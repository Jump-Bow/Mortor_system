# 架構改善紀錄 v1.3 (2026-04-09)
## 組織架構遷移、DSP Isolate、Delta Sync、InspectionStatus Enum

---

## 一、組織架構雙軌問題修正

### 問題背景
系統同時存在 `hr_organization`（人資組織）與 `t_organization`（設施組織）兩套體系。
前端巡檢頁面錯誤呼叫 `/api/v1/organizations/tree`，導致後端以 `t_organization.unitid` 過濾時
無法匹配，組織下拉選單功能完全失效。

### 修改內容

#### 後端 (`chimei-fem-admin`)
| 檔案 | 修改內容 |
|---|---|
| `app/api/Mortor_inspection.py` | 刪除廢棄的 `get_descendant_org_ids` 函式 |
| `app/api/Mortor_tasks.py` | `/download` API 回應新增完整 `organizations` 欄位 |
| `app/templates/inspection/Mortor_progress.html` | 組織選擇器 API 改為 `/facilities/tree`，欄位 `id/name` → `unitid/unitname` |
| `app/templates/inspection/Mortor_abnormal_tracking.html` | 同上 |
| `app/templates/inspection/Mortor_aims_progress.html` | 同上 |
| `app/static/js/org_tree_picker.js` | 通用組織選取元件同步修正 |

#### 前端 APP (`chimei-fem-app`)
| 檔案 | 修改內容 |
|---|---|
| `lib/data/datasources/remote/task_remote_data_source.dart` | `TaskDownloadResponse` 新增 `organizations` 欄位 |
| `lib/data/repositories/task_repository_impl.dart` | 寫入 `t_organization` 至 SQLite |
| `lib/data/datasources/local/database_helper.dart` | 移除 `hr_organization` 孤兒表建立邏輯 |
| `lib/core/constants/app_constants.dart` | 資料庫版本升至 v10，移除 `hrOrganizationTable` 常數 |

---

## 二、Flutter Isolate 抽離 DSP 運算

### 問題背景
`vibration_service.dart` 的 `_processSignal` 方法在主執行緒（UI Thread）直接處理數萬筆
浮點數的濾波、積分、FFT 等運算，導致：
1. 量測期間 UI 卡頓甚至無回應
2. PDA 單核頻寬弱，極易觸發 ANR (Application Not Responding)
3. 訊號採樣 Buffer 可能溢位

### 修改內容 (`vibration_service.dart`)

**新增頂層結構：**
```dart
// 1. 輸入封裝類別（可跨 Isolate 傳遞）
class _DspInput {
  final List<int> rawCounts;
  final int fs;
}

// 2. 頂層 RMS 計算（Isolate 不可存取 class member）
double _rmsTopLevel(List<double> data) { ... }

// 3. 頂層 DSP 處理鏈（Step 1~5 完整邏輯）
VibrationResult _processSignalTopLevel(_DspInput input) { ... }
```

**呼叫方式改為：**
```dart
// 舊（主執行緒阻塞）
return _processSignal(pcmSamples, actualFs);

// 新（Isolate 背景執行）
return await compute(
  _processSignalTopLevel,
  _DspInput(rawCounts: pcmSamples, fs: actualFs),
);
```

> **注意事項**：`compute()` 在 Debug 模式同步執行（看不出效果），
> 需使用 `flutter build apk --release` 打包的 Release APK 才能驗證真正的雙核分離效果。

**移除廢棄項目：**
- `_processSignal` 類別方法（170行）→ 已抽離至頂層 `_processSignalTopLevel`
- `_rms` 類別方法 → 已抽離至頂層 `_rmsTopLevel`
- `_hpCutoffHz`、`_lpCutoffHz`、`_warmupFraction` 類別常數（已改為頂層函式使用硬編碼值）

---

## 三、離線安全同步機制 (Delta Sync)

### 問題背景
`downloadTasks` 使用破壞性全量刪除：
```dart
await txn.delete(DatabaseConstants.tJobTable); // ← 危險！
```
若巡檢員在地下室完成量測（`inspection_result.is_synced=0`）後回地面點擊「重新下載工單」，
會導致未上傳的量測結果失去父工單，成為孤兒資料（Orphan Data）。

### 修改內容 (`task_repository_impl.dart`)

```dart
// 舊（破壞性全量刪除）
await txn.delete(DatabaseConstants.tJobTable);

// 新（安全刪除：保護有待上傳結果的工單）
await txn.rawDelete(
  'DELETE FROM t_job '
  'WHERE actid NOT IN ('
  '  SELECT DISTINCT actid FROM inspection_result'
  '  WHERE is_synced = 0'          // 有待上傳結果的工單不刪除
  ')',
);
```

**現有 `is_synced` 生命週期確認（早已實作，本次利用此機制）：**
```
saveResult()     → 寫入時 is_synced = 0 (待上傳)
uploadResults()  → 上傳成功後 UPDATE SET is_synced = 1
syncPendingResults() → 批量同步後同樣標記 is_synced = 1
```

---

## 四、InspectionStatus Enum 封裝

### 問題背景
`is_out_of_spec` 欄位的語意值 0/1/2/3 硬編碼散落於 Python 3 個 API 檔案與 Dart 程式中，
形成高維護風險的魔術數字（Magic Numbers）。

### 修改內容

**Python 端（新增 `app/utils/inspection_status.py`）：**
```python
from enum import IntEnum

class InspectionStatus(IntEnum):
    CREATED  = 0  # 已建立，尚未填寫
    NORMAL   = 1  # 正常
    ABNORMAL = 2  # 異常（超出規格範圍）
    SHUTDOWN = 3  # 停機（需立即處置）
```

使用 `IntEnum` 可直接與整數比較，與 SQLAlchemy ORM 完全相容：
```python
# 舊
InspectionResult.is_out_of_spec >= 2
# 新
InspectionResult.is_out_of_spec >= InspectionStatus.ABNORMAL
```

**影響的 Python 檔案：**
- `Mortor_inspection.py`：8 處替換
- `Mortor_results.py`：2 處替換
- `Mortor_tasks.py`：2 處替換

**Dart 端（新增 `lib/core/constants/inspection_status.dart`）：**
```dart
enum InspectionStatus {
  created(0), normal(1), abnormal(2), shutdown(3);
  const InspectionStatus(this.value);
  final int value;
  static InspectionStatus fromValue(int value) { ... }
}
```

**影響的 Dart 檔案：**
- `result_repository_impl.dart`：1 處替換（`>= 2` → `>= InspectionStatus.abnormal.value`）

---

## 五、Flask Monolithic 架構問題說明與改善路徑

> 詳見 `FLASK_DECOUPLING_GUIDE.md`
