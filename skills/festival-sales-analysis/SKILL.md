---
name: festival-sales-analysis
description: Use when a marketer has sales, POS, or e-commerce export data (CSV or Excel) and needs 促銷成效分析 — promotional lift, 銷售高峰期, 通路貢獻, 促銷類型比較, 客單價, ROI — before planning a festival campaign or when reading last year's festival numbers.
---

# 節慶銷售資料分析

核心原則：**數字要用算的，不要用估的；算出來之後，更重要的是知道它不能證明什麼。** 腳本只做算術，不產生任何市場統計。

## 執行

Excel 檔先另存為 CSV（**編碼不用選，Excel 預設的就讀得動**），再跑：

```bash
python3 scripts/analyze_sales.py <檔案.csv> [--baseline-days N] [--top N]
```

必要欄位只有日期與銷售額。欄名對不上時腳本會印出偵測到的欄名與可接受別名，照著改欄名列，別動資料。報表標題列與空列在欄名上方時會自動略過，不必先回 Excel 刪列。輸出為 markdown，**直接引用，不要自己重算腳本算過的數字**。

節慶日期與檔期回推一律交給 `${CLAUDE_PLUGIN_ROOT}/shared/backplan.py`（若此變數未展開，改用專案根目錄的 `shared/...`）。禁止自行推算節慶日期或回推 D-x。

參數選擇、逐節讀法、三句結論交棒格式、lift 三陷阱：看 `references/reading-the-report.md`。

## 輸入不足時

- 沒有資料：拿 `${CLAUDE_PLUGIN_ROOT}/templates/sales_template.csv` 當格式範本請對方匯出；要不到就轉 festival-campaign-ideas，假設標 `[假設]`。
- 缺 brief（品類、目標、通路）：問，缺這三項無法判讀。
- 缺欄位：照跑，結論註明哪幾節被跳過。
- 缺成本或預算：ROI、毛利留「待填」，不准用假成本回推。

## 常見錯誤

- 拿促銷期比淡季，得出好看的 lift 就報上去。
- 把平台補貼與站內流量的量算成自己機制有效。
- 忽略退貨與取消，用毛額下結論。
- 用總額比較卻沒對齊天數（14 天 vs 7 天），該比平均日銷。
- 只有三五天樣本就下結論；腳本標「樣本不足」要照實寫。
- 把「平均單價」當客單價 AOV；AOV 需要訂單筆數，這份資料算不出來。

## 資料隱私

真實銷售資料放 `data/`，整個目錄已被 gitignore，不要 commit。

## 銜接

有數據時本 skill 是鏈路起點：結論交 festival-campaign-plan 當事實基礎，或交 festival-campaign-ideas 當發想約束。檔期結束後由 festival-campaign-review 用同一支腳本重跑，比對計畫與實績。品類 KPI 口徑見 `${CLAUDE_PLUGIN_ROOT}/shared/category-profiles.md`。
