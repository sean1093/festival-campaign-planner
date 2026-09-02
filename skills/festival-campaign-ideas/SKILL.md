---
name: festival-campaign-ideas
description: Use when a marketer needs campaign concepts or creative ideas for a holiday or festival promotion (中秋, 春節, 雙11, 母親節, 端午, 情人節, 聖誕, 週年慶, Valentine's, Christmas), asks 節慶要做什麼活動 or 有什麼點子, wants several genuinely different options instead of one, or needs to screen and shortlist concepts before committing budget.
---

# 節慶點子發散與收斂

核心原則：發散必須沿明確軸線，否則只會產出同一個折扣點子的十種說法；沒收斂的清單對行銷人沒有價值。

## 流程

1. **鎖 brief 六格**：生意目標（衝量／拉新／清庫存／守品牌）、節慶與日期、品類、目標受眾、預算級距、硬限制（通路、法規、產能、交期、庫存）。日期查 `${CLAUDE_PLUGIN_ROOT}/shared/festivals-tw.csv`（若此變數未展開，改用專案根目錄的 `shared/...`），天數跑 `python3 shared/backplan.py <節慶> --year <年>`，**禁止自行推算節慶日或回推檔期日**；品類對照 `${CLAUDE_PLUGIN_ROOT}/shared/category-profiles.md`，送禮型分清「掏錢的人」與「收禮的人」。
2. **選軸發散**：讀 `references/idea-axes.md`，至少跨 4 條軸，每軸 1-2 個，共 6-10 個；同軸變形不算兩個點子。
3. **概念卡**：概念名稱（一句話講完）／為什麼會買單（一句 insight，非形容詞）／核心機制（引用 `references/mechanic-library.md`）／主打通路／要準備什麼（物料、合作對象、系統）／最大風險。
4. **收斂評分**：品牌契合、生意潛力、現有資源可執行性、與去年及競品的差異化、風險，各 1-5 分附一句理由；排序後推薦 1-3 個，並說明落選案為何被刷掉。
5. **交棒**：推薦案交 festival-campaign-plan。有去年數據先跑 festival-sales-analysis；覆盤由 festival-campaign-review 回饋。

## 輸入不足時

- 缺 brief：先問最關鍵的 2-3 項；說「你決定」就用品類常見做法補上並標 `[假設]`，結尾列假設清單。
- 缺數據：不准估，一律寫「由使用者歷史資料或標明出處的外部報告填入」。
- 缺預算：改用級距（小／中／大）並標 `[假設]`。

## 常見錯誤

- 十個點子都是折扣變形（換折數不是換點子）。
- 把機制當創意：「滿額贈」是機制，不是概念。
- 概念美，但物料交期或上架截止日來不及；發散時就對照 backplan 的 D-x。
- 照抄去年只改年份，沒查競品是否也在抄。
- 只想 D-day，忘了預熱與節後長尾。
- 送禮型節慶對著使用者溝通，不是對著出錢的人。
