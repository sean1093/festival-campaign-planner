---
name: festival-execution-kit
description: Use when a festival campaign plan is approved and the marketer needs the executable artifacts — 內容日曆, 貼文排程, 通路 brief, KOC/KOL 邀約, 物料清單, 上線前檢查表, 分工表 — or asks 接下來誰做什麼, 什麼時候發, 上線前要檢查什麼.
---

核心原則：計畫書不會自己執行。這個環節把里程碑展開成「誰、在哪一天、交出什麼」，沒有負責人與日期的項目等於不存在。

先讀 `data/brand-profile.md` 取通路窗口與審核天數；沒有就複製 `data/brand-profile.example.md` 填一次。

## 1. 取日期

跑 `python3 ${CLAUDE_PLUGIN_ROOT}/shared/backplan.py <節慶> --year <年> --feasibility`（若此變數未展開，改用專案根目錄的 `shared/backplan.py`）。`--feasibility` 讀 `data/operations.csv`，把交期與通路截止日疊上里程碑，指出哪些方案來不及；缺檔退回一般模式並複製 `data/operations.example.csv`。**禁止自行推算節慶日期或回推檔期日。**里程碑遇週六日，內部作業（打樣、通路溝通、驗收）提前到前一個工作日。

## 2. 四類物件（按需取用）

- 貼文排程 → `templates/content-calendar.csv`。易空泛：「主題與角度」，要寫成能直接下筆的一句話。
- 通路上架與供貨 → `templates/channel-brief.md`。易空泛：「素材規格與截稿日」，缺尺寸或日期就整批重做。
- 寄樣邀約 → `templates/koc-brief.md`。易空泛：「素材授權與二次利用範圍」。
- D-7 起逐項驗收 → `templates/launch-checklist.md`，D-1 前全部打勾。

## 3. 分工

每列都要有具名負責人與截止日。不知道是誰就填 `[待指派]` 並列進風險；「行銷部」不算負責人。

## 4. 節奏

階段沿用 backplan：定策略／定機制／備彈藥／點火／黃金期／最後衝刺／節慶當日／長尾／覆盤。密度從點火起遞增，別平均分配貼文。

## 5. 交棒

上游 festival-campaign-plan（未定案先回去做）；結束後交 festival-campaign-review。

## 輸入不足時

- 缺計畫書：問主推品項、機制、預算、通路；缺任一項就回 festival-campaign-plan。
- 缺人名：填 `[待指派]`。
- 缺數字：標 `[假設]`，註明須由使用者歷史資料或標明出處的報告替換，不准編造。

## 常見錯誤

- 只排 D-day 前後三天，蓄水期空白。
- 每則都在賣產品，沒有情境鋪陳，受眾當天才第一次看到。
- 通路 brief 漏寫素材規格與截稿日，交件被退、重做趕不上上架。
- KOC 合作沒講揭露標註（#合作 #廣告）與可否二次利用，事後想下廣告卻沒授權。
- 上線前才發現 UTM 沒埋、優惠碼沒建、客服不知道活動內容。
- 檢查表一次勾完，沒人真的逐項開頁面確認。
