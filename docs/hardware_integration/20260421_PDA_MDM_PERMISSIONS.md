---
type: it-deployment-guide
audience: IT / MDM 管理員
date: 2026-04-21
---

# 管控 PDA 設備權限開通說明

> 本文件說明在企業 MDM（Mobile Device Management）管控環境下，
> 部署「設備巡檢 App（chimei-fem-app）」所需開通的所有設備權限項目，
> 以及各項權限的用途與技術依據。

---

## 一、硬體設備與 App 版本資訊

| 項目 | 說明 |
|------|------|
| App 名稱 | 設備巡檢 |
| 套件名稱 | `inspection_mobile_app` |
| 目前版本 | v1.0.3 build 4 |
| 平台 | Android（Flutter） |
| 最低 API Level | Android 6.0（API 23） |

---

## 二、需開通的設備權限總覽

| 優先順序 | 權限類型 | 是否必要 | 用途摘要 |
|---------|---------|---------|---------|
| 🔴 必要 | **USB Host 功能** | ✅ 是 | 連接 PMU201 溫度計、Digiducer 震動計 |
| 🔴 必要 | **RECORD_AUDIO（麥克風）** | ✅ 是 | Digiducer USB 音訊震動資料接收 |
| 🔴 必要 | **INTERNET（網路）** | ✅ 是 | 連接後端 API（工單下載、結果上傳） |
| 🟡 建議 | **USB 持久授權** | 建議 | 避免每次插拔 USB 重複彈出授權視窗 |
| 🟢 選用 | **CAMERA（相機）** | ❌ 保留 | 現版本未啟用，未來拍照功能預留 |
| 🟢 選用 | **NFC** | ❌ 保留 | 現版本未啟用，未來 RFID 驗證預留 |

---

## 三、各權限詳細說明

### 3.1 🔴 USB Host 功能（android.hardware.usb.host）

**AndroidManifest.xml 聲明：**
```xml
<uses-feature
    android:name="android.hardware.usb.host"
    android:required="false" />
```

**用途：**
App 需以「USB Host 模式」直接存取以下兩台量測儀器：

| 儀器 | 型號 | USB 識別 | 通訊方式 |
|------|------|---------|---------|
| 溫度計 | Calex PyroMini USB（PMU201） | USB-Serial 虛擬 COM Port | Modbus RTU FC04，9600 baud, 8N1 |
| 震動計 | Digiducer 333D05-C | USB Audio Class（VID: 0x29DA，PID: 0x0011） | USB Isochronous（libusb 直接存取） |

**技術說明：**
- 溫度計透過 `usb_serial` 套件建立 COM Port，發送 Modbus RTU 封包讀取濾波後溫度（暫存器 `0x000E`）
- 震動計透過 Native Plugin（`com.chimei.fem/digiducer_usb` MethodChannel）使用 `libusb` 繞過 Android Audio HAL，直接讀取 24-bit 原始震動資料
- `android:required="false"`：PDA 若無 USB Host 硬體只是無法使用量測功能，App 仍可執行

**MDM 需設定：**
- ✅ 允許使用 USB Host（OTG）功能
- ✅ **不可封鎖 USB OTG**（許多 MDM 策略預設封鎖此功能）

---

### 3.2 🔴 RECORD_AUDIO（麥克風 / 音訊輸入）

**AndroidManifest.xml 聲明：**
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

**用途：**
Digiducer 333D05-C 在 Android 系統層呈現為「USB Audio 裝置」（UAC），其資料鏈為：

```
Digiducer ADC（24-bit）→ USB Isochronous → Linux USB kernel
→ libusb（JNI）→ DigiducerUsbPlugin.kt → MethodChannel → Flutter
```

即便採用 USB Direct 方案（繞過 HAL），Android 系統在建立 USB Audio 設備連線時，仍會檢查 `RECORD_AUDIO` 權限。**此權限在 Android 6.0 以上為 Runtime Permission，部署時必須預先授予。**

**MDM 需設定：**
- ✅ 預授予（Pre-grant）`RECORD_AUDIO` 權限給本 App，避免使用者手動允許
- ✅ MDM Policy 不可禁止「麥克風 / 音訊輸入」設備類別

---

### 3.3 🔴 網路存取（INTERNET）

**用途：**
App 需連接後端 API（GCP Cloud Run 服務），以下操作均需網路：

| 操作 | API 端點 | 觸發時機 |
|------|---------|---------|
| 登入（JWT 取得） | `POST /api/v1/auth/login` | App 啟動 |
| 工單下載 | `GET /api/v1/tasks/download` | 巡檢員同步任務 |
| 量測結果上傳 | `POST /api/v1/results/upload` | 巡檢完成後批次上傳 |
| Token 自動刷新 | `POST /api/v1/auth/refresh` | Token 到期前自動觸發 |
| 照片上傳（GCS） | `POST /api/v1/results/{id}/photo` | 有異常情況時 |

**連線目標：**
- 後端 API：`https://api.fem.example.com`（正式 HTTPS 443）
- Azure AD 登入：`https://login.microsoftonline.com`（SSO 驗證）

**MDM 需設定：**
- ✅ 允許 App 存取企業網路（Wi-Fi / 行動數據）
- ✅ 防火牆或代理伺服器允許以下出站連線：
  - `api.fem.example.com:443`（後端 API）
  - `login.microsoftonline.com:443`（Azure AD SSO）
  - `storage.googleapis.com:443`（GCS 照片上傳）

---

### 3.4 🟡 USB 裝置持久授權（建議設定）

**問題說明：**
Android 預設行為是每次偵測到 USB 裝置插入，都會彈出授權視窗詢問使用者。這在工廠環境中每次插拔儀器都會中斷操作。

**App 已設定的 USB 自動識別過濾清單（`device_filter.xml`）：**
```xml
<!-- 允許所有 USB 裝置（App 層再過濾） -->
<usb-device />
<!-- Digiducer 333D05 明確指定 -->
<usb-device vendor-id="10714" product-id="17" />
```

**建議 MDM 設定：**

**方案一（推薦）：透過 MDM 預授予 USB 裝置存取**
- 在 Android Enterprise 政策中設定「USB 裝置白名單」，對以下 VID/PID 免詢問自動授權：

  | 裝置 | Vendor ID | Product ID | 備註 |
  |------|-----------|-----------|------|
  | Digiducer 333D05-C | `0x29DA`（10714） | `0x0011`（17） | 確認日期：2026-04-16 |
  | PMU201（任何 USB-Serial 橋接晶片） | 視實際晶片而定 | 視實際晶片而定 | 常見：CH340 / CP210x / FTDI |

**方案二：設定 `android:required` 為 true**
- 若 MDM 不支援 USB 白名單，需確認 `uses-feature android:required="false"` 設定不被 MDM 覆蓋

---

### 3.5 🟢 未啟用但聲明的功能（保留）

以下功能已在 `pubspec.yaml` 中列為「未來開發備用」，目前**未啟用**，MDM 策略中可暫不開通：

| 功能 | 套件 | 狀態 |
|------|------|------|
| NFC / RFID 掃描 | `nfc_manager` | 已移除（`pubspec.yaml` 註解中） |
| 相機拍照 | `camera` / `image_picker` | 已移除（`pubspec.yaml` 註解中） |
| 藍牙通訊 | `flutter_blue_plus` | 已移除（`pubspec.yaml` 註解中） |

> **注意**：若未來版本啟用以上功能，將另行通知 IT 補充開通對應權限（`CAMERA`、`BLUETOOTH`、`NFC`）。

---

## 四、Token 與資料安全機制（IT 確認用）

App 在 PDA 本地的資料安全設計供 IT 參考：

| 機制 | 說明 |
|------|------|
| **JWT Token 加密儲存** | Access Token / Refresh Token 存入 `flutter_secure_storage`（Android Keystore 加密），不以明文存儲 |
| **自動 Token 刷新** | Token 到期前 App 自動刷新，不需使用者重新登入（`DioClient` 401 攔截器） |
| **離線資料庫** | 本地工單資料存於 SQLite（`inspection_local.db`），僅儲存必要巡檢資料，不含敏感個資 |
| **API 全程 HTTPS** | 所有後端通訊走 TLS 1.2+，含 Token 不經明文傳輸 |

---

## 五、MDM 部署 Checklist

IT 設定時請逐項確認：

```
USB Host（OTG）
  [ ] PDA 硬體具備 USB Host（OTG）能力（通常透過 OTG 轉接線）
  [ ] MDM 政策未封鎖 USB OTG 功能（Android Enterprise → "USB File Transfer" 與 "USB Host" 為不同設定）
  [ ] （建議）VID:0x29DA / PID:0x0011 列入 USB 裝置白名單，免每次彈授權視窗

音訊 / 震動量測
  [ ] RECORD_AUDIO 已由 MDM 預授予給本 App（或確保使用者首次啟動時可自行允許）

網路
  [ ] Wi-Fi 或行動數據已允許本 App 存取
  [ ] 防火牆已開通 api.fem.example.com:443（出站 HTTPS）
  [ ] 防火牆已開通 login.microsoftonline.com:443（Azure AD SSO）
  [ ] 防火牆已開通 storage.googleapis.com:443（GCS 照片上傳）

App 安裝
  [ ] APK 來源：透過 MDM 或企業 App Store 推送，禁止側載不明 APK
  [ ] 版本確認：目前部署版本 v1.0.3 build 4

（選用）未來功能預留
  [ ] 如需相機功能：屆時補開 CAMERA 權限
  [ ] 如需 NFC：屆時補開 NFC 功能
```

---

## 六、常見問題排除

| 問題症狀 | 可能原因 | 解決方法 |
|---------|---------|---------|
| 插入 USB 儀器後無反應 | USB OTG 被 MDM 封鎖 | 確認 MDM 政策允許 USB Host |
| 震動計讀數失敗，顯示「PERMISSION_DENIED」 | RECORD_AUDIO 未授予 | 手動至設定 → 應用程式 → 設備巡檢 → 權限 → 麥克風 → 允許 |
| 每次插入儀器都要點授權視窗 | USB 裝置未在白名單 | 透過 MDM 設定 VID/PID 白名單 |
| App 無法連線後端 | 防火牆封鎖 | 確認出站 HTTPS 443 白名單已設定 |
| 登入失敗（Azure AD） | 代理伺服器攔截 HTTPS | 確認 login.microsoftonline.com 可直連或已信任 |

---

*文件版本：v1.0*
*建立日期：2026-04-21*
*依據：chimei-fem-app AndroidManifest.xml、device_filter.xml、pubspec.yaml（main branch）*
