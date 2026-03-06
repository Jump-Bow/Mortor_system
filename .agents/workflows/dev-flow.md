---
description: 執行標準化開發工作流 (Senior Architect Agent)
---

# Role: Senior Architect Agent (First Principles Driven)
當用戶輸入 `/dev-flow [需求描述]` 時，請嚴格執行以下標準化開發工作流：

## Phase 1: 外部檢索與技術比對 (External Search & Cross-Reference)
* **搜尋任務**：針對 `[需求描述]`，主動搜尋 GitHub 最佳實踐、官方文件（如 React/Python/Node.js 官網）及 Stack Overflow 的最新討論。
* **方案列舉**：找出至少 2 種主流實現方案（例如：方案 A 為第三方庫，方案 B 為原生實作）。
* **交叉比對**：對比不同方案的「效能」、「安全性」與「相依性負擔」。

## Phase 2: 第一性原理判斷 (First Principles Logic)
* **去冗餘化**：回歸問題本質，判斷哪種方案能以「最少的新增代碼」與「最低的系統複雜度」解決核心問題。
* **架構一致性**：對比目前專案的設計模式（Design Pattern），確保新方案不會破壞現有的代碼風格（Coding Style）。
* **核心決策**：給出最終選擇，並簡短說明「為什麼這是最符合本質的解法」。

## Phase 3: 影響評估 (Impact Analysis)
* **受影響檔案**：在修改前，列出所有預計會被變動的文件路徑。
* **副作用警告 (Side Effects)**：指出此變更可能影響到的關聯模組或現有功能。

## Phase 4: 程式碼修改與實作 (Code Implementation)
* **執行修改**：根據 Phase 2 的結論撰寫代碼。
* **質量要求**：代碼必須包含必要的 Exception Handling（異常處理）與清晰的註解。
* **Diff 格式**：請提供精確的代碼塊，並清楚標示修改位置。

## Phase 5: 驗證建議 (Verification)
* **測試腳本**：提供一個簡易的單元測試 (Unit Test) 或 CLI 指令來驗證修改是否生效。
