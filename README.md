# 🎉 Festival Campaign Planner - AI-Powered Marketing Assistant

> **一鍵啟動你的節慶行銷戰情室** | 專為台灣 FMCG 品牌行銷人員打造

---

## 🚀 這是什麼？

這是一個 **AI 助理技能包**,讓你無需寫程式就能：

✅ 自動分析銷售數據 (Promotional Lift, Peak Period, 通路貢獻)
✅ 掌握 2026 台灣市場趨勢
✅ 30 秒產出專業的節慶促銷計畫書
✅ 一鍵生成執行時程圖 (Gantt Chart)

**適用對象**: Brand Managers, Marketing Specialists, 電商經營者

---

## 📦 快速開始 (3 分鐘安裝)

### 步驟 1: 下載專案
在你的電腦終端機執行：
```bash
git clone https://github.com/your-username/festival-campaign-planner.git
cd festival-campaign-planner
```

> **沒有安裝 Git？** 點擊 GitHub 頁面右上角的綠色 `Code` 按鈕 → `Download ZIP`

### 步驟 2: 匯入 Claude AI
1. 打開 [Claude.ai](https://claude.ai) 或 Claude Desktop App
2. 創建新的 **Project**
3. 將整個 `festival-campaign-planner` 資料夾拖放至 Project 視窗
4. 完成！✨

### 步驟 3: 準備你的數據（可選）
1. 下載 `templates/sales_template.csv` 作為範本
2. 填入你的真實銷售數據
3. 將檔案拖放至 Claude 對話框或上傳至 `data/` 資料夾

---

## 🎯 核心指令表

| 指令 | 功能 | 範例 |
|------|------|------|
| `/analyze` | 深度分析銷售數據<br>（Lift、高峰期、通路佔比） | 直接輸入 `/analyze` |
| `/trend` | 解析 2026 台灣市場趨勢 | `/trend` |
| `/plan [節慶]` | 產出 1500 字專業計畫書 | `/plan 中秋節`<br>`/plan 雙11` |
| `/gantt` | 產出執行時程視覺化圖表 | `/gantt` |

---

## 💼 實際使用範例

### 範例 1: 中秋節促銷規劃
```
你: /analyze
AI: [讀取你的銷售數據] → 產出完整分析報告 + 圖表

你: /trend
AI: 2026 年中秋節市場機會點：健康化、禮盒客製化、直播帶貨...

你: /plan 中秋節
AI: [產出 1500 字計畫書]
    - 戰情回顧: 去年中秋銷售 +35%，主要來自電商通路...
    - 策略目標: 今年目標 NT$ 50M，鎖定 25-40 歲消費者...
    - 產品組合: 主推低糖月餅禮盒 + 買一送一機制...
    - 通路佈局: 電商 60% / 實體 40%...
    - 預算分配: 總預算 NT$ 8M，廣告 50%、促銷 30%...

你: /gantt
AI: [產出 Mermaid 時程圖]
```

### 範例 2: 無數據時快速上手
```
你: /analyze
AI: ⚠️ 未偵測到數據檔案。

    請依照以下步驟:
    1. 下載範本: templates/sales_template.csv
    2. 填入你的銷售數據 (日期、金額、產品、通路)
    3. 上傳至對話框
    4. 重新執行 /analyze
```

---

## 📂 專案結構說明

```
festival-campaign-planner/
├── README.md                    ← 你正在看的檔案
├── Skill.md                     ← AI 的「大腦」(指令定義)
├── .gitignore                   ← 保護你的隱私數據
├── templates/
│   └── sales_template.csv       ← 銷售數據範本 (可下載使用)
├── docs/
│   └── marketing_trends_2026.md ← 2026 台灣市場趨勢知識庫
└── data/                        ← 你的私有數據放這裡 (已被 git 忽略)
```

---

## 🛡️ 安全性與隱私

### ✅ 你的數據是安全的
- 所有分析在 **本地 Sandbox** 執行
- 不會將數據傳送至第三方伺服器
- `data/` 資料夾已被 `.gitignore` 排除，不會上傳至 GitHub

### ⚠️ 重要提醒
- **不要**將包含真實銷售數據的檔案 commit 到 GitHub
- **不要**在 `.env` 檔案中儲存 API Key 後上傳（本專案不需 API Key）
- 若需分享專案，請先刪除 `data/` 資料夾內容

---

## 🔧 常見問題 (FAQ)

### Q1: 我不會寫程式，可以使用嗎？
**A**: 完全可以！只需要：
1. 會複製貼上指令（如 `/analyze`）
2. 會上傳 Excel/CSV 檔案
3. 會閱讀 AI 產出的報告

### Q2: 支援哪些數據格式？
**A**:
- CSV (`.csv`)
- Excel (`.xlsx`, `.xls`)
- 必要欄位: 日期、銷售額、產品名稱、通路

### Q3: 沒有歷史數據怎麼辦？
**A**:
- 仍可使用 `/trend` 查看市場趨勢
- 下載 `templates/sales_template.csv` 參考欄位格式
- 開始記錄未來的銷售數據

### Q4: 可以分析多個品牌嗎？
**A**: 可以！在 CSV 中新增「品牌」欄位，AI 會自動識別並比較

### Q5: 產出的計畫書可以直接用嗎？
**A**:
- 計畫書提供 **80% 的框架**
- 建議你根據品牌特性微調 20%
- 可直接匯出為 PDF 使用

---

## 🎓 進階使用技巧

### 技巧 1: 自訂分析維度
```
你: 請幫我分析「包裝規格」對銷售的影響
AI: [自動分組分析不同包裝的銷售表現]
```

### 技巧 2: 競品對比
```
你: 請比較我們的月餅禮盒 vs. 競品 A 的價格策略
AI: [結合趨勢知識庫產出對比分析]
```

### 技巧 3: 快速覆盤
```
你: 請用上個月的數據，分析哪些促銷活動效果最好
AI: [計算各活動的 ROI 並排序]
```

---

## 📊 範本檔案說明

### `templates/sales_template.csv`
這是符合 FMCG 產業邏輯的標準範本，包含欄位：

| 欄位 | 說明 | 範例 |
|------|------|------|
| `日期` | 銷售日期 | 2025-09-01 |
| `產品名稱` | SKU 名稱 | 低糖月餅禮盒 A |
| `銷售額` | 當日銷售金額 (NT$) | 125000 |
| `通路` | 銷售通路 | 電商 / 超市 / 便利商店 |
| `促銷活動` | 是否有促銷 | 是 / 否 |

---

## 🤝 貢獻與支援

### 回報問題
發現 Bug 或有功能建議？請至 [GitHub Issues](https://github.com/your-username/festival-campaign-planner/issues) 回報

### 貢獻程式碼
歡迎 Fork 本專案並提交 Pull Request！

### 商業支援
需要客製化功能或企業培訓？請聯繫: [your-email@example.com](mailto:your-email@example.com)

---

## 📜 授權條款

本專案採用 **MIT License**，可自由使用於商業與個人專案。

---

## 🙏 致謝

- 感謝所有提供數據範本的行銷夥伴
- 技術支援: Claude AI by Anthropic
- 數據視覺化: Mermaid.js, Matplotlib

---

<div align="center">

**Made with ❤️ for Taiwan Marketers**

[⭐ Star this repo](https://github.com/your-username/festival-campaign-planner) if you find it helpful!

</div>
