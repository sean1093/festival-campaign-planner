---
name: festival-campaign-plan
description: Use when a marketer needs a festival or holiday campaign plan that can be approved — 節慶行銷計畫書, 促銷提案, 檔期規劃, 預算分配, 執行時程, KPI 設定 — or has already picked a concept and must turn it into a costed, scheduled, measurable plan.
---

# 節慶檔期計畫書

計畫書的價值不在字數，在於每個數字都追得到來源、每個時間點都排得進行事曆、每個 KPI 都量得到。

## 步驟

1. **前置檢查**：要有 brief（品類、節慶與年份、生意目標、預算量級、主力通路、人力與素材）與選定概念。缺概念先跑 festival-campaign-ideas；有歷史銷售資料先跑 festival-sales-analysis。

2. **先跑排程再寫內容**：
   `python3 ${CLAUDE_PLUGIN_ROOT}/shared/backplan.py <節慶> --year <年> --gantt`
   （此變數未展開時，改用專案根目錄的 `shared/backplan.py`；非表列檔期加 `--date --name --profile`。）
   **禁止自行推算節慶日期或里程碑日期。** 腳本警告落後 N 天時，明寫要壓縮或砍掉哪些環節、交期與上架截止日是否來得及，不准假裝時間夠。

3. **填 `templates/campaign-plan.md`**：八節骨架見範本，執行時程貼上排程表與甘特圖。機制與 KPI 對齊 `${CLAUDE_PLUGIN_ROOT}/shared/category-profiles.md` 的品類段落。

4. **算預算與 KPI 前先讀 `references/budget-and-kpi.md`**：用反推法，不套現成比例；每個 KPI 都附量測方式。

5. **標假設**：沒有來源的數字一律寫成 `[假設] <數字> — 依據：<推論> — 需驗證：<怎麼驗>`，並彙整成「待驗證假設清單」。寧可標假設，不准編像真的數字。

6. **交棒**：核准後交 festival-execution-kit 產物料；檔期結束交 festival-campaign-review 覆盤。

## 常見錯誤

- 預算憑空套「廣告 50%、促銷 30%」，沒從生意目標反推。
- KPI 寫了但沒有量測方式；做不到歸因的指標不要列。
- 時程沒對物料交期與通路上架截止日，核准時已來不及打樣。
- 沒算毛利底線，營收漲、毛利掉。
- 風險章節是場面話，沒有觸發訊號、負責人、Plan B。
- 把去年的假設當今年的事實。

## 輸入不足時

- 缺 brief：六項問齊再動筆，不要邊猜邊寫。
- 缺數據：客單、轉換率、獲客成本不准憑空填；改列待驗證假設，或用小預算測試期先跑出參數。
- 缺預算：不編總額，改提兩三個量級的做法差異讓決策者選。
