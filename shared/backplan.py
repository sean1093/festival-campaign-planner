#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""節慶檔期回推排程器 — 給節慶名稱，算出每個里程碑的實際日期。

為什麼要有這支程式：語言模型算農曆與日期會錯。日期一律由這裡算，不要用推估的。

資料來源：shared/festivals-tw.csv。國曆日期由天文曆算產生，並與中央氣象署
115 年日曆資料表及行政院人事行政總處行事曆交叉比對通過。
標示「概略」的檔期（尾牙季、開學季、百貨週年慶）為錨點日，非官方日期。

用法：
    python3 backplan.py 中秋                    # 自動抓下一次中秋
    python3 backplan.py 中秋 --year 2027
    python3 backplan.py 中秋 --gantt            # 輸出 mermaid 甘特圖
    python3 backplan.py 中秋 --feasibility      # 疊上你的交期與通路截止日，算哪些方案還來得及
    python3 backplan.py --date 2026-11-11 --profile short --name 品牌週年慶
    python3 backplan.py --list --year 2026
    python3 backplan.py --list --category 美妝個護

--feasibility 讀 data/operations.csv（你自己的營運常數，複製 data/operations.example.csv
來填）。這是這支程式唯一知道「你家」而不只是「一般人」的地方：沒有它，D-60 只是通用
日曆算術；有了它，才答得出「現在啟動，禮盒版還來不來得及」。

只用標準函式庫，不需安裝任何套件。
"""

import argparse
import csv
import datetime as dt
import os
import sys

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "festivals-tw.csv")
WEEKDAY = "一二三四五六日"
OPS_HEADER = ["方案", "項目", "類型", "天數", "通路", "說明"]

# 前置節奏：(節前天數, 階段, 工作項目)
# 這是排程預設值，不是市場數據。有自家歷史檔期資料就覆寫它。
PROFILES = {
    "long": [  # 送禮／團聚型長檔期，如中秋、春節、母親節、端午
        (60, "定策略", "生意目標與預算定案、主推品項與定價確認、去年同期數據回顧"),
        (45, "定機制", "促銷機制定版、包裝與禮盒打樣、預購頁架構、法規標示確認"),
        (30, "備彈藥", "預購／早鳥開跑、通路提案與上架溝通完成、KOC 寄樣、廣告素材完稿"),
        (21, "點火", "社群預熱內容上線、廣告開始投放、企業團購名單開發"),
        (14, "黃金期", "全通路加壓、直播／限時活動、庫存日盤點"),
        (5, "最後衝刺", "急單與交期溝通、超商取貨截止提醒、追加投放"),
        (0, "節慶當日", "現場執行與即時應變"),
        (-3, "長尾", "節後出清、剩貨轉檔、感謝溝通"),
        (-14, "覆盤", "成效彙整與學習紀錄"),
    ],
    "mid": [  # 體驗／儀式／中型送禮檔期，如七夕、萬聖節、聖誕、父親節、中元
        (45, "定策略", "目標與預算定案、切入點與主視覺方向確認"),
        (30, "定合作", "異業／KOC／場地敲定、機制與贈品定版"),
        (21, "備彈藥", "素材製作完成、活動頁與報名機制上線、通路溝通"),
        (10, "點火", "預熱內容與廣告開跑、預約／預購開放"),
        (3, "臨門一腳", "提醒推播、庫存與現場人力盤點、客服話術就位"),
        (0, "活動當日", "現場執行、即時內容產出"),
        (-3, "收割", "UGC 蒐集與二次內容、名單導流"),
        (-10, "覆盤", "成效彙整與學習紀錄"),
    ],
    "short": [  # 囤貨／價格導向短檔期，如雙11、雙12、黑五、元宵
        (30, "定策略", "折扣結構與毛利底線定案、平台資源位報名"),
        (21, "備彈藥", "頁面與素材完成、優惠券與行銷工具設定"),
        (14, "蓄水", "預熱投放、加購物車／預售／領券、名單擴充"),
        (7, "加壓", "站外投放拉高、KOC 開箱鋪量、私域推播"),
        (1, "開賣前檢查", "庫存、金流、物流、追蹤碼、客服全項確認"),
        (0, "主檔開賣", "即時監控轉換與庫存、動態調整投放"),
        (-1, "返場", "加碼或延長、未結帳挽回"),
        (-7, "覆盤", "成效彙整與學習紀錄"),
    ],
}


def load_festivals():
    with open(CSV_PATH, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fmt(d):
    return "%s (週%s)" % (d.isoformat(), WEEKDAY[d.weekday()])


def find(rows, name, year):
    hits = [r for r in rows if name in r["節慶"] or r["節慶"] in name]
    if not hits:
        names = sorted({r["節慶"] for r in rows})
        sys.exit("找不到「%s」。可用節慶：%s" % (name, "、".join(names)))
    if year:
        hits = [r for r in hits if r["年份"] == str(year)]
        if not hits:
            sys.exit("「%s」沒有 %s 年的資料，目前收錄 2026-2028。" % (name, year))
        return hits[0]
    today = dt.date.today()
    future = sorted((r for r in hits if dt.date.fromisoformat(r["日期"]) >= today),
                    key=lambda r: r["日期"])
    return future[0] if future else sorted(hits, key=lambda r: r["日期"])[-1]


def milestones(dday, profile):
    return [(dday - dt.timedelta(days=off), off, phase, task)
            for off, phase, task in PROFILES[profile]]


def render(title, dday, profile, note, precision):
    today = dt.date.today()
    out = ["## %s 檔期回推排程" % title, ""]
    out.append("- **節慶當日**：%s" % fmt(dday))
    out.append("- **距今**：%s 天" % (dday - today).days)
    out.append("- **前置節奏**：%s（起跑日 D-%d）" % (profile, PROFILES[profile][0][0]))
    if precision == "概略":
        out.append("- ⚠️ **此日期為概略錨點**，非官方公告日，請向通路或內部確認實際檔期。")
    if note:
        out.append("- **備註**：%s" % note)
    out.append("")

    kickoff = dday - dt.timedelta(days=PROFILES[profile][0][0])
    if kickoff < today:
        late = (today - kickoff).days
        out.append("> ⚠️ **已落後 %d 天**：完整前置期需在 %s 啟動。剩下的時間要壓縮，"
                   "優先砍「備彈藥」以外的環節，並確認物料交期與通路上架截止日是否還來得及。"
                   % (late, fmt(kickoff)))
        out.append("")

    out.append("| 日期 | 星期 | 節點 | 階段 | 工作項目 | 狀態 |")
    out.append("|---|---|---|---|---|---|")
    for date, off, phase, task in milestones(dday, profile):
        label = "D-%d" % off if off > 0 else ("D-day" if off == 0 else "D+%d" % -off)
        delta = (date - today).days
        status = "已過" if delta < 0 else ("今天" if delta == 0 else "剩 %d 天" % delta)
        out.append("| %s | 週%s | %s | %s | %s | %s |"
                   % (date.isoformat(), WEEKDAY[date.weekday()], label, phase, task, status))
    out.append("")
    out.append("_里程碑落在週六日時，內部作業（打樣、通路溝通、驗收）請提前至前一個工作日。_")
    return "\n".join(out)


def render_gantt(title, dday, profile):
    ms = milestones(dday, profile)
    out = ["```mermaid", "gantt", "    title %s 檔期執行時程" % title,
           "    dateFormat YYYY-MM-DD", "    axisFormat %m/%d"]
    for i, (date, off, phase, task) in enumerate(ms):
        nxt = ms[i + 1][0] if i + 1 < len(ms) else date + dt.timedelta(days=3)
        span = max((nxt - date).days, 1)
        out.append("    section %s" % phase)
        tag = "milestone, " if off == 0 else ""
        out.append("    %s :%s%s, %s, %dd" % (task[:24], tag, "m%d" % i, date.isoformat(), span))
    out.append("```")
    return "\n".join(out)


def render_list(rows, year, category):
    today = dt.date.today()
    sel = [r for r in rows
           if (not year or r["年份"] == str(year))
           and (not category or category in r["適配品類"])]
    sel = [r for r in sel if dt.date.fromisoformat(r["日期"]) >= today] or sel
    sel.sort(key=lambda r: r["日期"])
    out = ["| 節慶 | 日期 | 星期 | 距今 | 檔期性質 | 前置 | 起跑日 |", "|---|---|---|---|---|---|---|"]
    for r in sel[:40]:
        d = dt.date.fromisoformat(r["日期"])
        kickoff = d - dt.timedelta(days=PROFILES[r["前置節奏"]][0][0])
        flag = "" if kickoff >= today else " ⚠️已過"
        out.append("| %s%s | %s | %s | %d 天 | %s | %s | %s%s |"
                   % (r["節慶"], "（概略）" if r["日期精確度"] == "概略" else "",
                      r["日期"], r["星期"], (d - today).days,
                      r["檔期性質"].replace("|", "、"),
                      r["前置節奏"], kickoff.isoformat(), flag))
    return "\n".join(out)


# --------------------------------------------------------------------------
# 可行性評估：把使用者自己的交期與通路截止日疊到檔期上
# --------------------------------------------------------------------------

def find_operations(explicit=None):
    """找 operations.csv。順序：--operations 指定 → 專案目錄 → 這支程式旁邊的 data/。

    兩種擺法都支援：外掛裝在 ~/.claude/skills/ 底下時營運常數跟著外掛走（一個人服務一個
    品牌，這樣最自然）；在專案目錄裡工作時則以專案的 data/ 為準。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [explicit] if explicit else []
    candidates += [
        os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()), "data", "operations.csv"),
        os.path.join(here, os.pardir, "data", "operations.csv"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return os.path.abspath(path)
    return None


def load_operations(path):
    """回傳 (交期 {方案: [(項目, 天數或None, 說明)]}, 截止 [(方案, 項目, 通路, 天數, 說明)])。

    天數填 [待確認] 之類的非整數時保留為 None：不猜、不當成 0，而是在報告裡列出來要求補齊。
    """
    chains, deadlines = {}, []
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if not row or (row.get("方案") or "").lstrip().startswith("#"):
                continue
            kind = (row.get("類型") or "").strip()
            plan = (row.get("方案") or "").strip()
            item = (row.get("項目") or "").strip()
            note = (row.get("說明") or "").strip()
            raw = (row.get("天數") or "").strip()
            days = int(raw) if raw.lstrip("-").isdigit() else None
            if not item:
                continue
            if kind == "交期":
                chains.setdefault(plan or "（未分方案）", []).append((item, days, note))
            elif kind == "截止":
                deadlines.append((plan, item, (row.get("通路") or "").strip(), days, note))
    return chains, deadlines


def render_feasibility(title, dday, ops_path):
    """輸出方案可行性與通路截止日判定。"""
    today = dt.date.today()
    chains, deadlines = load_operations(ops_path)
    out = ["## %s 可行性評估" % title, "",
           "- **節慶當日**：%s" % fmt(dday),
           "- **今天**：%s，剩 %d 天" % (fmt(today), (dday - today).days),
           "- **營運常數**：`%s`" % ops_path, ""]

    if not chains and not deadlines:
        out.append("⚠️ 營運常數檔裡沒有任何可用的「交期」或「截止」列，無法評估。")
        return "\n".join(out)

    if chains:
        out += ["### 方案可行性", "",
                "| 方案 | 作業鏈 | 需要天數 | 最快完成 | 對 D-day | 判定 |",
                "|---|---|---|---|---|---|"]
        for plan, steps in chains.items():
            unfilled = [i for i, d, _ in steps if d is None]
            total = sum(d for _, d, _ in steps if d is not None)
            chain = " → ".join("%s(%s)" % (i, d if d is not None else "?") for i, d, _ in steps)
            if unfilled:
                out.append("| %s | %s | %s | — | — | ⚠️ 無法評估：%d 項天數未填 |"
                           % (plan, chain, "已填 %d" % total if total else "—",
                              len(unfilled)))
                continue
            finish = today + dt.timedelta(days=total)
            gap = (dday - finish).days
            verdict = ("來不及，晚 %d 天" % -gap if gap < 0
                       else "⚠️ 只剩 %d 天緩衝" % gap if gap <= 7
                       else "來得及，緩衝 %d 天" % gap)
            out.append("| %s | %s | %d | %s | %s | %s |"
                       % (plan, chain, total, finish.isoformat(),
                          "晚 %d 天" % -gap if gap < 0 else "早 %d 天" % gap, verdict))
        out.append("")
        out.append("_作業鏈視為序列相加。有能並行的步驟，請把它們合併成一列再填天數。_")
        out.append("")

    if deadlines:
        out += ["### 通路截止日", "",
                "| 通路 | 項目 | 適用方案 | 截止日 | 狀態 |", "|---|---|---|---|---|"]
        for plan, item, channel, days, note in deadlines:
            if days is None:
                out.append("| %s | %s | %s | ⚠️ 天數未填 | 無法判定（%s）|"
                           % (channel or "—", item, plan or "全部", note or "去問窗口"))
                continue
            when = dday - dt.timedelta(days=days)
            left = (when - today).days
            state = ("⚠️ 已於 %d 天前截止" % -left if left < 0
                     else "⚠️ 今天最後一天" if left == 0
                     else "剩 %d 天" % left)
            out.append("| %s | %s | %s | %s 週%s，D-%d | %s |"
                       % (channel or "—", item, plan or "全部", when.isoformat(),
                          WEEKDAY[when.weekday()], days, state))
        out.append("")

    alive, dead, blocked = [], [], []
    for plan, steps in chains.items():
        if any(d is None for _, d, _ in steps):
            blocked.append(plan)
        elif today + dt.timedelta(days=sum(d for _, d, _ in steps)) <= dday:
            alive.append(plan)
        else:
            dead.append(plan)
    missed = ["%s%s" % (c + "：" if c else "", i)
              for _, i, c, d, _ in deadlines if d is not None and dday - dt.timedelta(days=d) < today]

    out += ["### 結論", ""]
    if alive:
        out.append("- **還做得到**：%s" % "、".join(alive))
    elif dead:
        out.append("- **沒有任何方案趕得上**。剩下的選擇只有砍規格、換檔期，或今年放棄這一檔。")
    else:
        out.append("- **還無法判定**。所有方案的天數都還沒填，這不代表來得及，"
                   "只代表你現在手上沒有足以判斷的資訊。")
    if dead:
        out.append("- **已經來不及**：%s。要嘛砍規格，要嘛把檔期往後挪。" % "、".join(dead))
    if missed:
        out.append("- **已經錯過的通路窗口**：%s。這幾條線今年不用再想，把資源移到還開著的通路。"
                   % "、".join(missed))
    if blocked:
        out.append("- **算不出來**：%s。天數還沒填，去問到再跑一次——這種事不該用猜的。"
                   % "、".join(blocked))
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(description="節慶檔期回推排程器")
    p.add_argument("festival", nargs="?", help="節慶名稱，如 中秋、雙11、母親節")
    p.add_argument("--year", type=int, help="指定年份（預設抓下一次）")
    p.add_argument("--date", help="自訂檔期日期 YYYY-MM-DD（不查表）")
    p.add_argument("--name", default="自訂檔期", help="搭配 --date 使用的檔期名稱")
    p.add_argument("--profile", choices=sorted(PROFILES), help="前置節奏 long/mid/short")
    p.add_argument("--gantt", action="store_true", help="輸出 mermaid 甘特圖")
    p.add_argument("--list", action="store_true", help="列出節慶總表")
    p.add_argument("--category", help="用適配品類篩選，如 食品飲料、美妝個護")
    p.add_argument("--feasibility", action="store_true",
                   help="疊上 data/operations.csv 的交期與通路截止日，算哪些方案還來得及")
    p.add_argument("--operations", help="指定營運常數檔路徑（預設自動尋找 data/operations.csv）")
    a = p.parse_args()

    rows = load_festivals()

    if a.list:
        print(render_list(rows, a.year, a.category))
        return

    if a.date:
        dday = dt.date.fromisoformat(a.date)
        title, profile, note, precision = a.name, a.profile or "mid", "", "確定"
    elif a.festival:
        r = find(rows, a.festival, a.year)
        dday = dt.date.fromisoformat(r["日期"])
        title = "%s %s" % (r["年份"], r["節慶"])
        profile = a.profile or r["前置節奏"]
        note, precision = r["備註"], r["日期精確度"]
    else:
        p.print_help()
        return

    print(render(title, dday, profile, note, precision))
    if a.gantt:
        print()
        print(render_gantt(title, dday, profile))
    if a.feasibility:
        ops = find_operations(a.operations)
        print()
        if ops:
            print(render_feasibility(title, dday, ops))
        else:
            print("## 可行性評估：無法執行\n\n"
                  "找不到 `data/operations.csv`。這支評估要知道你自己的交期與通路截止日，"
                  "否則只能給通用日曆，講不出「禮盒版還來不來得及」。\n\n"
                  "做法：把 `data/operations.example.csv` 複製成 `data/operations.csv`，"
                  "用 Excel 打開，把「天數」欄的 `[待確認]` 換成真實天數（問印刷廠業務、"
                  "通路窗口、平台後台公告），再跑一次。填一次可以用很多年。")


if __name__ == "__main__":
    main()
