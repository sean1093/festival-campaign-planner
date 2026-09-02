# 節慶行銷戰情室 Festival Campaign Planner

給台灣行銷人的一組 AI 技能。節慶檔期的完整迴路——**想點子 → 寫計畫書 → 排落地物料 → 看數據 → 覆盤**——都在裡面。

不用寫程式。裝好之後，用中文講你要做什麼就會啟動對應的技能。

**想先看產出長什麼樣？** 直接讀 [`examples/2026-中秋-完整範例.md`](examples/2026-中秋-完整範例.md)，一路走完五個步驟，可以照著自己重跑一次。

---

## 你會得到什麼

| 你的處境 | 會啟動的技能 | 你拿到的東西 |
|---|---|---|
| 「老闆叫我做中秋，還沒有想法」 | `festival-campaign-ideas` | 6-10 張**方向真的不一樣**的概念卡，加上評分表幫你收斂到 1-3 個，並說明其他為什麼被刷掉 |
| 「要交一份提案給主管」 | `festival-campaign-plan` | 八節計畫書、預算怎麼算出來的、KPI 怎麼量、完整時程表與甘特圖 |
| 「計畫過了，接下來怎麼動」 | `festival-execution-kit` | 內容日曆、給通路的 brief、給 KOC 的邀約與規範、上線前 70 項檢查表 |
| 「去年的數字到底代表什麼」 | `festival-sales-analysis` | 促銷 lift（分通路各算一次）、高峰期、通路貢獻、促銷類型比較、節後衰退 |
| 「檔期結束了要交檢討」 | `festival-campaign-review` | 數字／執行／決策三層覆盤，結論存起來，下次規劃時自動被讀 |

五個可以單獨用，不必從頭跑。

---

## 安裝

### 方式一：不用打指令（推薦給沒有技術背景的人）

1. 在 GitHub 頁面點綠色的 **Code** 按鈕 → **Download ZIP**，解壓縮。
2. 打開 Finder，按 `Cmd + Shift + G`，貼上 `~/.claude/skills` 後按 Enter。
   （沒有這個資料夾就先建一個。Windows 是在檔案總管網址列貼 `%USERPROFILE%\.claude\skills`）
3. 把解壓出來的資料夾整個拖進去，並把名字改成 `festival-campaign-planner`。
4. 重開 Claude Code。輸入 `/plugin`，看到 `festival-campaign-planner` 就成功了。

路徑會長這樣：`~/.claude/skills/festival-campaign-planner/skills/festival-campaign-ideas/SKILL.md`

### 方式二：用指令

```bash
git clone git@github.com:sean1093/festival-campaign-planner.git ~/.claude/skills/festival-campaign-planner
```

### 方式三：Claude.ai 的 Project

建一個 Project，把整個資料夾拖進去。技能不會自動觸發，要自己說「照 `skills/festival-campaign-ideas/SKILL.md` 的流程幫我想中秋活動」。

⚠️ 這條路徑有個未經確認的風險：`backplan.py` 與 `analyze_sales.py` 是否跑得起來，要看你的方案有沒有程式執行環境。**跑不起來的話，日期與數據都會退回模型自己算——那正是這套東西設計來避免的事。** 建議優先用方式一或二。

---

## 第一次怎麼用

打開 Claude Code，在專案任意目錄下直接說話就好：

```
我做的是低糖月餅禮盒，主力電商，想規劃 2026 中秋，先給我幾個不一樣的方向
```

它會先跟你確認六件事（生意目標、節慶日期、品類、受眾、預算級距、硬限制），這一步不要跳過——**brief 不清楚，產出就一定籠統**。

沒有真實資料也能跑。庫裡附了 `templates/sales_template.csv`（2025 中秋檔期的示範資料），可以直接說「用範本資料示範一次」。

---

## 出問題怎麼辦

**Q：我講了但 AI 沒反應，也沒啟動技能**
先確認 `/plugin` 裡有沒有 `festival-campaign-planner`。有的話，把節慶名稱講出來（「中秋」「雙11」「母親節」），觸發率會高很多。還是不行就直接指定：「用 festival-campaign-ideas 這個技能」。

**Q：它說找不到我的檔案**
把檔案放到專案的 `data/` 資料夾（已經幫你建好了），然後講完整檔名。或者直接把檔案拖進 Claude 的對話框。

**Q：它算出來的日期跟我知道的不一樣**
先讓它跑一次 `python3 shared/backplan.py <節慶> --year <年>`，那個輸出是對的。如果連這個都跟你認知不同，可能是你記成去年的日期了——農曆節慶每年國曆日期都會動。真的有錯請開 issue，附上你的來源。

**Q：產出很籠統，都是廢話**
九成是 brief 沒鎖。回頭補齊六格，特別是「硬限制」（通路、法規、產能、交期、既有庫存）——限制愈具體，產出愈能用。

**Q：Excel 檔要怎麼處理**
另存為 CSV 就好，**編碼不用選**，Excel 預設的存法讀得動。報表標題列在欄名上方也沒關係，會自動略過。

**Q：計畫書裡一堆 `[假設]`，這樣能交嗎？**
能，而且那是優點。把它當成「我知道哪些是事實、哪些還要驗證」的證據，比一份看起來很篤定但數字來源不明的提案可信。報告時講法：「這五個數字來自去年實績，另外六個是假設，我列了驗證方式與時間點。」

**Q：我的銷售數據會外流嗎**
不會。分析在你自己的電腦跑，`analyze_sales.py` 只用 Python 標準函式庫，不連任何外部服務。`data/` 整個目錄已被 `.gitignore` 排除，不會進版控。

---

## 專案結構

```
skills/                             五個技能，各自有 SKILL.md
  festival-campaign-ideas/            + references/（發散軸、機制庫）
  festival-campaign-plan/             + references/（預算與 KPI）、templates/（計畫書骨架）
  festival-execution-kit/             + templates/（日曆、通路 brief、KOC brief、檢查表）
  festival-sales-analysis/            + scripts/analyze_sales.py、references/（判讀指南）
  festival-campaign-review/           + templates/（覆盤骨架）
shared/
  festivals-tw.csv                  2026-2028 台灣節慶日期與檔期性質
  backplan.py                       節慶 → 里程碑日期、甘特圖
  category-profiles.md              六個品類的作戰檔案
templates/sales_template.csv        銷售數據欄位範本
examples/                           完整示範產出
data/                               你的私有資料（不進版控）
```

---

## 兩條硬規則

**一、沒有來源的數字不准出現。**
任何百分比、金額、成長率、ROI 倍數，要嘛來自你的資料，要嘛標明出處，否則一律寫成 `[假設] <數字> — 依據：<推論> — 需驗證：<怎麼驗>`，並在文件最後彙整成清單。**寧可標假設，也不編一個看起來很像真的數字。**

專案前一版滿是「67% 消費者願付溢價」「中秋市場 NT$150 億」「KOC ROI 5.2x」這類無出處數據——精確到會被主管採信，拿去提案就是風險。全部砍掉了。

**二、日期不准用推的。**
語言模型算農曆會錯，而且錯得很自信。前一版把 2026 春節寫成 1/29（那是 2025 年的）、端午 6/14、中秋 9/27，三個全錯。

現在日期一律查表。`festivals-tw.csv` 的國曆日期由天文曆算產生，並與中央氣象署 115 年日曆資料表、行政院人事行政總處行事曆交叉比對通過（2026 春節 2/17、端午 6/19、中秋 9/25）。標「概略」的三個檔期（尾牙季、開學季、百貨週年慶）是錨點日，不是官方公告日。

自己試一次：

```bash
python3 shared/backplan.py 中秋 --year 2026            # 里程碑表，含「已落後幾天」警告
python3 shared/backplan.py 中秋 --year 2026 --gantt     # 加 mermaid 甘特圖
python3 shared/backplan.py --list --category 美妝個護    # 該品類接下來有哪些檔期
python3 shared/backplan.py --date 2027-03-08 --name 婦女節快閃 --profile mid
```

只用標準函式庫，不必安裝任何套件。

---

## 改成自己的樣子

| 想改什麼 | 改哪裡 |
|---|---|
| 加自家檔期（品牌週年慶、會員日） | `shared/festivals-tw.csv` 加一列，或用 `backplan.py --date` |
| 前置節奏不合（物料交期比較長） | `shared/backplan.py` 最上面的 `PROFILES` |
| 品類不在六個 profile 裡 | `shared/category-profiles.md` 加一段，沿用同樣欄位 |
| 補市場數據 | 自建檔案，**每筆附出處**，在 brief 階段餵進去 |
| 節慶日期延伸到 2029 以後 | 用農曆曆算套件重算，與中央氣象署日曆資料表核對後補進 CSV |

---

MIT License
