---
name: festival-campaign-review
description: Use when a festival or holiday campaign has finished and the marketer needs 覆盤, 檢討會, 成效報告, 達成率分析 — or wants to turn what actually happened into reusable learnings for next year's festival planning.
---

# 節慶檔期覆盤

核心原則：覆盤的產出不是一份報告，是下一次做決策時會被翻出來看的東西。沒有具體到可以照著改的結論，就等於沒覆盤。

開場先讀 `data/brand-profile.md`（沒有就複製 `data/brand-profile.example.md` 填一次），對照主管在意的指標與硬限制。

## 三層覆盤，缺一層都不算完整

- **數字層**：實際 vs 目標達成率。有原始銷售資料先用 festival-sales-analysis 跑，別靠印象。營收之外要看毛利與退貨。
- **執行層**：backplan 的每個里程碑實際落在哪一天、哪裡卡住、為什麼卡（物料交期、通路回覆慢、素材重做、人力不足）。
- **決策層**：計畫書裡每一條 `[假設]` 是被驗證還是被推翻，錯的下次怎麼改。這層最容易跳過，也最值錢。

日期一律跑 `python3 ${CLAUDE_PLUGIN_ROOT}/shared/backplan.py <節慶> --year <年份>` 取得（若此變數未展開，改用專案根目錄的 `shared/...`），禁止自行推算。品類 KPI 見 `${CLAUDE_PLUGIN_ROOT}/shared/category-profiles.md`。

## 產出三份東西

1. **覆盤報告**：填 `templates/review.md`，給上級與團隊看。
2. **學習紀錄**：`data/learnings/<年份>-<節慶>.md`，只留下次規劃要先讀的三到五條結論。`data/` 已 gitignore，不外流。
3. **回寫品牌檔案**：把被刷掉的點子與原因補進 `data/brand-profile.md` 的「被否決過什麼」，並把本檔紀錄加到「過往檔期索引」。

## 回饋迴路

下次跑 festival-campaign-ideas 或 festival-campaign-plan 前，先讀 `data/learnings/` 同節慶的紀錄，把被推翻的假設當起點。少了這步，覆盤只是歸檔。

## 資料不足時

能拿到什麼算什麼：列出缺哪一層、缺了讓哪些結論不成立。數字缺就寫「由使用者歷史資料或標明出處的報告填入」，推論標 `[假設]`，不要用感覺補洞。

## 常見錯誤

- 只報好消息，失敗寫成「持續觀察」。
- 把外部順風（平台大促、競品缺貨、天氣）當成自己的能力，把運氣寫成方法論。
- 結論停在「下次要更早準備」；要寫成哪個節點、誰做、什麼算數。
- 覆盤完沒人追蹤改善項，下一檔期原地重來。
- 只看營收不看毛利與退貨，把折扣換來的營收當戰績。

## 銜接

前一棒 festival-execution-kit 與 festival-sales-analysis；結論回饋給 festival-campaign-ideas 與 festival-campaign-plan。
