#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""促銷成效分析器 — 吃一份銷售明細 CSV，輸出 markdown 分析報告到 stdout。

用法:
    python3 analyze_sales.py <檔案.csv>
    python3 analyze_sales.py data/2025中秋.csv --baseline-days 14 --top 10

參數:
    --baseline-days N   把 lift 的非促銷基準限定為「第一個促銷日之前最近 N 個非促銷日」。
                        不給就用資料裡所有非促銷日當基準。
    --top N             商品排行與單日排行取前 N 名（預設 5）。

只用 Python 標準函式庫，不需要安裝任何套件，也不畫圖。
必要欄位只有兩個：日期、銷售額；其餘欄位有就多算一節，沒有就跳過該節。
中英文欄名都認得，對應表見 ALIASES；欄名對不上時程式會印出偵測到的欄名與可接受別名。

這支腳本只做算術。報告裡每個數字都是從你給的 CSV 算出來的，
腳本不會生成任何市場統計、業界平均或推估值。
"""

import argparse
import collections
import csv
import datetime as dt
import os
import statistics
import sys

WEEKDAY = "一二三四五六日"

# 欄位別名表。比對前會做正規化：去空白、去底線與連字號、轉小寫。
ALIASES = {
    "date": ["日期", "日", "交易日期", "銷售日期", "訂單日期", "出貨日期", "帳務日期",
             "交易日", "銷售日", "訂單日", "出貨日", "業績日期", "統計日期", "date",
             "orderdate", "transactiondate", "saledate", "salesdate", "day", "ds"],
    "product": ["產品名稱", "品名", "商品名稱", "產品", "商品", "品項", "商品品名",
                "product", "productname", "item", "itemname", "goods", "title"],
    "sku": ["sku", "sku代碼", "sku編號", "skucode", "貨號", "料號", "商品編號",
            "產品編號", "品號", "itemcode", "productcode", "barcode"],
    "amount": ["銷售額", "營收", "金額", "銷售金額", "營業額", "業績", "成交金額",
               "淨銷售額", "amount", "revenue", "sales", "salesamount", "netsales",
               "total", "totalamount", "gmv", "turnover"],
    "qty": ["銷售數量", "數量", "銷量", "件數", "售出數量", "成交數量",
            "qty", "quantity", "units", "unitsold", "count", "pcs"],
    "price": ["單價", "售價", "定價", "商品單價", "price", "unitprice", "listprice"],
    "channel": ["通路", "銷售通路", "平台", "門市", "店別", "販售通路",
                "channel", "store", "shop", "platform", "salechannel", "saleschannel"],
    "promo": ["促銷活動", "是否促銷", "促銷", "有促銷", "活動", "是否有活動", "檔期",
              "promo", "promotion", "ispromo", "onpromotion", "haspromo", "campaign"],
    "promo_type": ["促銷類型", "促銷方式", "活動類型", "活動名稱", "機制", "促銷機制",
                   "promotype", "promotiontype", "mechanic", "offertype", "campaigntype"],
    "region": ["區域", "地區", "縣市", "地域", "大區",
               "region", "area", "district", "zone", "city"],
}
REQUIRED = ["date", "amount"]
FIELD_LABEL = {
    "date": "日期", "product": "產品名稱", "sku": "SKU", "amount": "銷售額",
    "qty": "銷售數量", "price": "單價", "channel": "通路", "promo": "促銷活動",
    "promo_type": "促銷類型", "region": "區域",
}

TRUE_VALUES = {"是", "y", "yes", "true", "t", "1", "有", "有促銷", "促銷", "on", "v", "✓", "檔期"}
FALSE_VALUES = {"否", "n", "no", "false", "f", "0", "無", "沒有", "非促銷", "正常",
                "平日", "off", "-", "—", "none", "na", "n/a", "null", ""}

DATE_FORMATS = [
    ("%Y-%m-%d", None),
    ("%Y/%m/%d", None),
    ("%Y.%m.%d", None),
    ("%Y%m%d", None),
    ("%m/%d/%Y", "偵測到 M/D/Y 日期格式，已假設為「月/日/年」"),
    ("%m-%d-%Y", "偵測到 M-D-Y 日期格式，已假設為「月-日-年」"),
    ("%d/%m/%Y", "偵測到 D/M/Y 日期格式（第一段大於 12），已假設為「日/月/年」"),
    ("%Y-%m", "偵測到只有年月的日期，已當作該月 1 日"),
]


# --------------------------------------------------------------------------
# 欄位對應與值解析
# --------------------------------------------------------------------------

def norm_key(name):
    """把欄名正規化成比對用的鍵：去 BOM、去空白與標點、轉小寫。"""
    if name is None:
        return ""
    s = name.replace("\ufeff", "").strip().lower()
    for ch in " \t_-()（）[]【】.、/\\:：":
        s = s.replace(ch, "")
    return s


def build_column_map(headers):
    """回傳 {欄位: 原始欄名}。同一欄位有多個候選時取最先出現的那個。"""
    lookup = {}
    for field, names in ALIASES.items():
        for alias in names:
            lookup.setdefault(norm_key(alias), field)
    mapping = {}
    for raw in headers:
        field = lookup.get(norm_key(raw))
        if field and field not in mapping:
            mapping[field] = raw
    return mapping


def parse_date(value):
    """寬鬆解析日期，回傳 (date, 提示字串)；失敗回傳 (None, None)。"""
    if value is None:
        return None, None
    s = str(value).replace("\ufeff", "").strip()
    if not s:
        return None, None
    s = s.split(" ")[0].split("T")[0]
    s = s.replace("年", "-").replace("月", "-").replace("日", "").rstrip("-")
    for fmt, hint in DATE_FORMATS:
        if fmt == "%Y%m%d" and not (s.isdigit() and len(s) == 8):
            continue
        try:
            return dt.datetime.strptime(s, fmt).date(), hint
        except ValueError:
            continue
    return None, None


def parse_number(value):
    """寬鬆解析金額／數量：吃掉千分位、貨幣符號、單位字，括號視為負數。"""
    if value is None:
        return None
    s = str(value).replace("\ufeff", "").strip()
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    for token in ["nt$", "ntd", "twd", "rmb", "usd"]:
        s = s.lower().replace(token, "")
    for ch in ",，$＄¥￥元個件台組盒箱(）) (（%　":
        s = s.replace(ch, "")
    s = s.strip()
    if s in ("", "-", "—", "--", "na", "n/a", "null", "none"):
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    return -n if negative and n > 0 else n


def parse_bool(value):
    """解析促銷旗標，回傳 (bool, 是否認得)。認不出來時當作非促銷並回報。"""
    s = str(value if value is not None else "").replace("\ufeff", "").strip().lower()
    if s in TRUE_VALUES:
        return True, True
    if s in FALSE_VALUES:
        return False, True
    return False, False


def open_csv(path):
    """依序嘗試常見編碼開檔（Excel 台灣版常存成 cp950），回傳 (文字, 編碼名)。"""
    last = None
    for enc in ("utf-8-sig", "cp950", "utf-8", "latin-1"):
        try:
            with open(path, encoding=enc) as fh:
                return fh.read(), enc
        except UnicodeDecodeError as exc:
            last = exc
    raise SystemExit("錯誤：無法解碼檔案 %s（試過 utf-8/cp950）。請在 Excel 另存為「CSV UTF-8」。\n%s"
                     % (path, last))


def locate_table(text):
    """同時決定分隔符與標題列所在列號。

    POS、ERP 與電商後台匯出常在欄名上方多一列報表標題與空列，直接把第一列當欄名會失敗。
    做法：對每個候選分隔符掃前 15 列，挑「對應到最多已知欄位」的那一列當標題列。
    回傳 (DictReader, 分隔符, 標題列列號從 0 算)。
    """
    lines = text.splitlines()
    header_idx, delimiter, best = 0, ",", -1
    for cand in (",", "\t", ";", "|"):
        for i, row in enumerate(csv.reader(lines[:15], delimiter=cand)):
            cells = [c.strip() for c in row if c and c.strip()]
            if len(cells) < 2:
                continue
            mapping = build_column_map(cells)
            score = len(mapping) * 2 + len(cells)
            if all(f in mapping for f in REQUIRED):
                score += 100
            if score > best:
                header_idx, delimiter, best = i, cand, score
    return csv.DictReader(lines[header_idx:], delimiter=delimiter), delimiter, header_idx


# --------------------------------------------------------------------------
# 讀檔
# --------------------------------------------------------------------------

def fail_missing_columns(headers, mapping):
    """必要欄位缺失時，印出偵測到的欄名與可接受別名，然後 exit 1。"""
    missing = [f for f in REQUIRED if f not in mapping]
    out = ["錯誤：CSV 缺少必要欄位，無法分析。", ""]
    out.append("缺少的欄位：" + "、".join(FIELD_LABEL[f] for f in missing))
    out.append("")
    out.append("在你的檔案裡偵測到的欄名（共 %d 個）：" % len(headers))
    for i, h in enumerate(headers, 1):
        hit = [FIELD_LABEL[f] for f, raw in mapping.items() if raw == h]
        out.append("  %2d. %s%s" % (i, h, "  → 已對應到「%s」" % hit[0] if hit else ""))
    out.append("")
    out.append("這兩個欄位是必要的。可接受的欄名（大小寫、底線、空白不影響比對）：")
    for f in REQUIRED:
        names = ALIASES[f]
        shown = "、".join(names[:6])
        more = "，另有 %d 個別名" % (len(names) - 6) if len(names) > 6 else ""
        out.append("  %s：%s%s" % (FIELD_LABEL[f], shown, more))
    out.append("")
    out.append("修法：把 CSV 標題列的欄名改成上面任一個，另存為 CSV 再重跑（編碼不用管，"
               "Excel 預設的就讀得動）。")
    out.append("格式範例見 templates/sales_template.csv。")
    sys.stderr.write("\n".join(out) + "\n")
    raise SystemExit(1)


def read_rows(path):
    """讀檔並清洗，回傳 (可用紀錄list, 略過原因Counter, 警示list, 欄位對應, 原始欄名, 編碼, 分隔符)。"""
    if not os.path.exists(path):
        sys.stderr.write("錯誤：找不到檔案 %s\n" % path)
        raise SystemExit(1)
    text, encoding = open_csv(path)
    reader, delimiter, header_idx = locate_table(text)
    headers = [h for h in (reader.fieldnames or []) if h is not None]
    if not headers:
        sys.stderr.write("錯誤：檔案 %s 沒有標題列，或是空檔案。\n" % path)
        raise SystemExit(1)

    mapping = build_column_map(headers)
    if any(f not in mapping for f in REQUIRED):
        fail_missing_columns(headers, mapping)

    records, skipped, hints = [], collections.Counter(), collections.Counter()
    total_rows = 0
    bad_promo, negative, zero_amount = 0, 0, 0

    for raw in reader:
        total_rows += 1
        if not any((v or "").strip() for v in raw.values() if isinstance(v, str)):
            skipped["整列空白"] += 1
            continue
        day, hint = parse_date(raw.get(mapping["date"]))
        if hint:
            hints[hint] += 1
        if day is None:
            value = (raw.get(mapping["date"]) or "").strip()
            skipped["日期為空" if not value else "日期格式無法辨識"] += 1
            continue
        amount = parse_number(raw.get(mapping["amount"]))
        if amount is None:
            value = (raw.get(mapping["amount"]) or "").strip()
            skipped["銷售額為空" if not value else "銷售額非數字"] += 1
            continue
        if amount < 0:
            negative += 1
        elif amount == 0:
            zero_amount += 1

        promo, known = False, True
        if "promo" in mapping:
            promo, known = parse_bool(raw.get(mapping["promo"]))
            if not known:
                bad_promo += 1
        promo_type = (raw.get(mapping.get("promo_type", ""), "") or "").strip()
        if promo_type and not promo and "promo" not in mapping:
            promo = True  # 沒有促銷旗標欄，但填了促銷類型，視為促銷日

        records.append({
            "date": day,
            "amount": amount,
            "qty": parse_number(raw.get(mapping.get("qty", ""))),
            "channel": (raw.get(mapping.get("channel", ""), "") or "").strip() or "（未填）",
            "promo": promo,
            "promo_type": promo_type,
            "product": (raw.get(mapping.get("product", ""), "") or "").strip(),
            "sku": (raw.get(mapping.get("sku", ""), "") or "").strip(),
            "region": (raw.get(mapping.get("region", ""), "") or "").strip(),
        })

    warnings = ["%s（%d 列）" % (h, n) for h, n in hints.items()]
    if header_idx:
        warnings.append("檔案開頭 %d 列不是欄名（報表標題或空列），已自動略過，"
                        "從第 %d 列開始讀欄名" % (header_idx, header_idx + 1))
    if negative:
        warnings.append("⚠️ %d 列銷售額為負（可能是退貨或沖銷），已以淨額計入" % negative)
    if zero_amount:
        warnings.append("%d 列銷售額為 0，已計入天數但不貢獻金額" % zero_amount)
    if bad_promo:
        warnings.append("⚠️ %d 列的促銷欄位值無法辨識，已當作非促銷處理；"
                        "請改成 是/否 或 Y/N 或 1/0" % bad_promo)
    return records, skipped, warnings, mapping, headers, encoding, delimiter, total_rows


# --------------------------------------------------------------------------
# 彙總
# --------------------------------------------------------------------------

def daily_totals(records, key=None):
    """按日彙總銷售額。key 給定時先分組，回傳 {組: {日期: 金額}}；否則回傳 {日期: 金額}。"""
    if key is None:
        out = collections.defaultdict(float)
        for r in records:
            out[r["date"]] += r["amount"]
        return dict(out)
    grouped = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in records:
        grouped[r[key]][r["date"]] += r["amount"]
    return {g: dict(d) for g, d in grouped.items()}


def promo_day_sets(records, key=None):
    """回傳 (促銷日集合, 非促銷日集合, 混合日集合)。同一天有任一促銷紀錄就算促銷日。"""
    flags = collections.defaultdict(set)
    for r in records:
        k = r["date"] if key is None else (r[key], r["date"])
        flags[k].add(r["promo"])
    promo = {k for k, v in flags.items() if True in v}
    plain = {k for k, v in flags.items() if v == {False}}
    mixed = {k for k, v in flags.items() if v == {True, False}}
    return promo, plain, mixed


def pick_baseline(plain_days, promo_days, baseline_days, notes):
    """挑非促銷基準日。給了 --baseline-days 就取第一個促銷日之前最近 N 個非促銷日。"""
    if baseline_days is None or not promo_days:
        return set(plain_days)
    first = min(promo_days)
    before = sorted(d for d in plain_days if d < first)
    if not before:
        notes.append("第一個促銷日（%s）之前沒有非促銷日，--baseline-days 無法套用，已改用全部非促銷日當基準。"
                     % first.isoformat())
        return set(plain_days)
    if len(before) < baseline_days:
        notes.append("第一個促銷日之前只有 %d 個非促銷日，少於指定的 %d 天，已全部採用。"
                     % (len(before), baseline_days))
    return set(before[-baseline_days:])


def fill_calendar(by_date):
    """把每日金額補成連續日曆序列（沒有紀錄的日期補 0），回傳 [(日期, 金額)]。"""
    if not by_date:
        return []
    start, end = min(by_date), max(by_date)
    days = (end - start).days + 1
    return [(start + dt.timedelta(days=i), by_date.get(start + dt.timedelta(days=i), 0.0))
            for i in range(days)]


# --------------------------------------------------------------------------
# 格式化
# --------------------------------------------------------------------------

def money(v):
    return "{:,.0f}".format(v)


def pct(v):
    return "{:.1f}%".format(v)


def signed_pct(v):
    return "{:+.1f}%".format(v)


def day_str(d):
    return "%s（週%s）" % (d.isoformat(), WEEKDAY[d.weekday()])


def mean_or_zero(values):
    return statistics.mean(values) if values else 0.0


def lift_pct(promo_avg, base_avg):
    """回傳 lift 字串。基準不是正數時不硬算百分比（除以 0 或負數的百分比沒有意義）。"""
    if base_avg <= 0:
        return "無法計算（基準平均日銷為 %s，非正數）" % money(base_avg)
    return signed_pct((promo_avg / base_avg - 1) * 100)


def small_sample_note(promo_n, base_n, extra=""):
    tags = []
    if promo_n < 5:
        tags.append("促銷日僅 %d 天" % promo_n)
    if base_n < 5:
        tags.append("非促銷日僅 %d 天" % base_n)
    note = "樣本不足，僅供參考（%s）" % "、".join(tags) if tags else ""
    return "；".join(x for x in (note, extra) if x)


def table(header, rows):
    """組 markdown 表格。rows 為字串序列的序列。"""
    out = ["| " + " | ".join(header) + " |",
           "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return out


# --------------------------------------------------------------------------
# 報告區塊
# --------------------------------------------------------------------------

def render_quality(path, total_rows, records, skipped, warnings, mapping, headers,
                   encoding, delimiter, gaps):
    """資料品質：讀了幾列、略過幾列與原因分布、欄位對應結果、已知警示。"""
    out = ["## 資料品質", ""]
    out.append("- 來源：`%s`（編碼 %s，分隔符 %s）"
               % (path, encoding, {",": "逗號", "\t": "Tab", ";": "分號", "|": "豎線"}.get(delimiter, delimiter)))
    out.append("- 讀入 %d 列，採用 %d 列，略過 %d 列。"
               % (total_rows, len(records), sum(skipped.values())))
    if skipped:
        out.append("- 略過原因分布：" + "；".join("%s %d 列" % (k, v)
                                            for k, v in skipped.most_common()))
    matched = "、".join("%s ← `%s`" % (FIELD_LABEL[f], mapping[f])
                       for f in FIELD_LABEL if f in mapping)
    out.append("- 已對應欄位：" + matched)
    unused = [h for h in headers if h not in mapping.values()]
    if unused:
        out.append("- 未使用的欄位（不影響分析）：" + "、".join("`%s`" % h for h in unused))
    absent = [FIELD_LABEL[f] for f in FIELD_LABEL if f not in mapping]
    if absent:
        out.append("- 檔案裡沒有的欄位，相關小節會直接跳過：" + "、".join(absent))
    if gaps:
        out.append("- ⚠️ 資料期間內有 %d 個日期完全沒有紀錄，滾動窗口與節後衰退分析把它們當作 0；"
                   "若那幾天其實有營業，這兩節的結論會失真。" % gaps)
    for w in warnings:
        out.append("- " + w)
    out.append("")
    return out


def render_overview(records, by_date, promo_days, plain_days, mixed_days):
    """總覽：期間、天數、總額、總量、平均單價、平均日銷。"""
    total = sum(r["amount"] for r in records)
    qtys = [r["qty"] for r in records if r["qty"] is not None]
    start, end = min(by_date), max(by_date)
    span = (end - start).days + 1
    rows = [
        ["資料期間", "%s ～ %s" % (day_str(start), day_str(end))],
        ["日曆天數 / 有紀錄天數", "%d 天 / %d 天" % (span, len(by_date))],
        ["總銷售額", money(total) + " 元"],
        ["平均日銷（有紀錄日）", money(total / len(by_date)) + " 元"],
        ["平均日銷（含無紀錄日，除以日曆天）", money(total / span) + " 元"],
    ]
    if qtys:
        total_qty = sum(qtys)
        rows.append(["總銷售數量", money(total_qty)])
        if total_qty:
            rows.append(["平均單價（銷售額 ÷ 數量）", money(total / total_qty) + " 元"])
    rows.append(["促銷日 / 非促銷日", "%d 天 / %d 天" % (len(promo_days), len(plain_days))])
    out = ["## 總覽", ""] + table(["項目", "值"], rows) + [""]
    if qtys:
        out.append("平均單價是「銷售額 ÷ 銷售數量」的加權均價，**不是客單價 AOV**。"
                   "AOV 需要訂單筆數，這份資料裡沒有；要看 AOV 請另外匯出訂單層級資料。")
        out.append("")
    if mixed_days:
        out.append("⚠️ 有 %d 天同時存在促銷與非促銷紀錄，本報告把這些天整天算作促銷日，"
                   "會讓 lift 偏低（促銷日混進了非促銷業績）。要精確比較請把資料拆到通路或 SKU 層級再跑。"
                   % len(mixed_days))
        out.append("")
    return out


def render_lift(records, by_date, promo_days, baseline, has_channel, baseline_days, notes):
    """Promotional lift：全站與分通路各算一次，樣本不足要標註。"""
    out = ["## Promotional lift", ""]
    if not promo_days:
        out.append("資料裡沒有任何促銷日（促銷欄位全為否，或檔案沒有促銷欄位），無法計算 lift。")
        out.append("")
        return out
    if not baseline:
        out.append("資料裡沒有非促銷日可當基準，無法計算 lift。"
                   "把促銷前後的正常銷售期一起匯出，再重跑。")
        out.append("")
        return out

    if baseline_days is None:
        out.append("基準定義：資料期間內**所有非促銷日**的平均日銷。")
    else:
        out.append("基準定義：第一個促銷日之前最近 **%d 個非促銷日**的平均日銷"
                   "（--baseline-days %d）。" % (baseline_days, baseline_days))
    out.append("")

    rows = []
    promo_vals = [by_date[d] for d in promo_days if d in by_date]
    base_vals = [by_date[d] for d in baseline if d in by_date]
    p_avg, b_avg = mean_or_zero(promo_vals), mean_or_zero(base_vals)
    rows.append(["**全站**", str(len(promo_vals)), money(p_avg), str(len(base_vals)),
                 money(b_avg), lift_pct(p_avg, b_avg),
                 small_sample_note(len(promo_vals), len(base_vals))])

    if has_channel:
        ch_daily = daily_totals(records, "channel")
        ch_promo, ch_plain, _ = promo_day_sets(records, "channel")
        for channel in sorted(ch_daily, key=lambda c: -sum(ch_daily[c].values())):
            days = ch_daily[channel]
            p_days = [d for d in days if (channel, d) in ch_promo]
            b_days = [d for d in days if (channel, d) in ch_plain and d in baseline]
            if not p_days and not b_days:
                continue
            pv = [days[d] for d in p_days]
            bv = [days[d] for d in b_days]
            pa, ba = mean_or_zero(pv), mean_or_zero(bv)
            extra = "" if bv else "此通路在基準期沒有非促銷紀錄"
            rows.append([channel, str(len(pv)), money(pa), str(len(bv)), money(ba),
                         lift_pct(pa, ba) if bv and pv else "無法計算",
                         small_sample_note(len(pv), len(bv), extra)])

    out += table(["範圍", "促銷日數", "促銷平均日銷", "非促銷日數", "非促銷平均日銷",
                  "lift", "備註"], rows)
    out.append("")
    out.append("平均日銷的分母是「該範圍有銷售紀錄的天數」，不是日曆天。")
    if has_channel:
        out.append("")
        out.append("分通路各算一次是為了避免通路組合變化被誤讀成促銷效果"
                   "（例如促銷期多開了一個高單價通路，全站數字就會動）。"
                   "各通路的 lift 差距很大時，全站那一列就不能單獨拿去報告。")
    else:
        out.append("")
        out.append("資料沒有通路欄位，只能算全站一列。"
                   "全站 lift 無法排除通路組合變化的影響——加一欄通路再重跑會可靠得多。")
    for n in notes:
        out.append("")
        out.append("⚠️ " + n)
    out.append("")
    return out


def render_peaks(by_date, promo_days, top_n):
    """銷售高峰：滾動 7 日最大窗口 + 單日前 N 名。"""
    series = fill_calendar(by_date)
    total = sum(v for _, v in series)
    out = ["## 銷售高峰", ""]
    if len(series) >= 7:
        window = max(range(len(series) - 6),
                     key=lambda i: sum(v for _, v in series[i:i + 7]))
        s, e = series[window][0], series[window + 6][0]
        amount = sum(v for _, v in series[window:window + 7])
        n_promo = sum(1 for d, _ in series[window:window + 7] if d in promo_days)
        out.append("### 滾動 7 日最大窗口")
        out.append("")
        out.append("- 期間：%s ～ %s" % (day_str(s), day_str(e)))
        out.append("- 窗口銷售額：%s 元，佔資料期間總額 %s"
                   % (money(amount), pct(amount / total * 100) if total else "—"))
        out.append("- 窗口內促銷日：%d / 7 天" % n_promo)
        out.append("")
    else:
        out.append("資料期間不足 7 天，跳過滾動窗口分析。")
        out.append("")

    ranked = sorted(by_date.items(), key=lambda kv: -kv[1])[:top_n]
    out.append("### 單日前 %d 名" % len(ranked))
    out.append("")
    rows = [[str(i), day_str(d), money(v),
             pct(v / total * 100) if total else "—",
             "促銷" if d in promo_days else "非促銷"]
            for i, (d, v) in enumerate(ranked, 1)]
    out += table(["#", "日期", "銷售額", "佔總額", "檔期狀態"], rows)
    out.append("")
    return out


def render_channels(records):
    """通路貢獻：金額、佔比、促銷日與非促銷日平均日銷。"""
    ch_daily = daily_totals(records, "channel")
    ch_promo, ch_plain, _ = promo_day_sets(records, "channel")
    total = sum(sum(d.values()) for d in ch_daily.values())
    out = ["## 通路貢獻", ""]
    rows = []
    for channel in sorted(ch_daily, key=lambda c: -sum(ch_daily[c].values())):
        days = ch_daily[channel]
        amount = sum(days.values())
        pv = [days[d] for d in days if (channel, d) in ch_promo]
        bv = [days[d] for d in days if (channel, d) in ch_plain]
        rows.append([channel, money(amount), pct(amount / total * 100) if total else "—",
                     str(len(days)),
                     money(mean_or_zero(pv)) if pv else "—",
                     money(mean_or_zero(bv)) if bv else "—"])
    out += table(["通路", "銷售額", "佔比", "有紀錄天數", "促銷日平均日銷", "非促銷日平均日銷"], rows)
    out.append("")
    out.append("此表的非促銷平均日銷用該通路**所有**非促銷日計算，"
               "與上一節的基準期定義可能不同，兩者不要混用。")
    out.append("")
    return out


def render_promo_types(records, by_date, baseline):
    """促銷類型比較：天數、總額、平均日銷、相對非促銷基準的倍數。"""
    out = ["## 促銷類型比較", ""]
    groups = collections.defaultdict(lambda: {"dates": set(), "amount": 0.0})
    for r in records:
        if not r["promo"]:
            continue
        label = r["promo_type"] or "（促銷但未填類型）"
        groups[label]["dates"].add(r["date"])
        groups[label]["amount"] += r["amount"]
    if not groups:
        out.append("資料裡沒有標記為促銷的紀錄，沒有促銷類型可比較。"
                   "若確實有做活動，請補上「促銷活動」欄（是/否）與「促銷類型」欄再重跑。")
        out.append("")
        return out

    base_vals = [by_date[d] for d in baseline if d in by_date]
    base_avg = mean_or_zero(base_vals)
    rows = []
    for label in sorted(groups, key=lambda g: -groups[g]["amount"]):
        g = groups[label]
        days = len(g["dates"])
        avg = g["amount"] / days if days else 0.0
        ratio = "%.2fx" % (avg / base_avg) if base_avg > 0 else "無基準"
        note = "樣本不足，僅供參考（僅 %d 天）" % days if days < 5 else ""
        rows.append([label, str(days), money(g["amount"]), money(avg), ratio, note])
    out += table(["促銷類型", "有活動天數", "該類型銷售額", "平均日銷", "相對非促銷基準", "備註"], rows)
    out.append("")
    out.append("非促銷基準平均日銷：%s 元（%d 天）。" % (money(base_avg), len(base_vals))
               if base_vals else "沒有非促銷日可當基準，倍數欄位無法計算。")
    out.append("")
    out.append("⚠️ 各類型的天數、通路、商品組合都不一樣，這張表只能說「哪一種在當時賣得多」，"
               "不能當成「哪一種機制比較有效」。要比機制效果需要同期同通路的對照設計。")
    out.append("")
    return out


def render_products(records, top_n):
    """商品排行：前 N 名 SKU／品名的銷售額與佔比。"""
    out = ["## 商品排行", ""]
    has_sku = any(r["sku"] for r in records)
    has_name = any(r["product"] for r in records)
    if not has_sku and not has_name:
        out.append("資料裡沒有 SKU 或產品名稱欄位，跳過商品排行。")
        out.append("")
        return out

    groups = collections.defaultdict(float)
    qty_groups = collections.defaultdict(float)
    for r in records:
        key = r["sku"] if has_sku and r["sku"] else (r["product"] or "（未填）")
        name = r["product"] if has_sku and r["sku"] and r["product"] else ""
        groups[(key, name)] += r["amount"]
        if r["qty"] is not None:
            qty_groups[(key, name)] += r["qty"]
    total = sum(groups.values())
    ranked = sorted(groups.items(), key=lambda kv: -kv[1])[:top_n]
    out[0] = "## 商品排行（前 %d 名）" % len(ranked)
    header = ["#", "商品", "銷售額", "佔比"]
    show_qty = bool(qty_groups)
    if show_qty:
        header += ["數量", "均價"]
    rows = []
    for i, ((key, name), amount) in enumerate(ranked, 1):
        row = [str(i), "%s %s" % (key, name) if name else key,
               money(amount), pct(amount / total * 100) if total else "—"]
        if show_qty:
            q = qty_groups.get((key, name), 0.0)
            row += [money(q), money(amount / q) if q else "—"]
        rows.append(row)
    out += table(header, rows)
    out.append("")
    out.append("共 %d 個商品，前 %d 名合計佔 %s。"
               % (len(groups), len(ranked),
                  pct(sum(v for _, v in ranked) / total * 100) if total else "—"))
    out.append("")
    return out


def render_decay(by_date, promo_days):
    """節後衰退：高峰日之後跌破高峰 50% 與 20% 分別是第幾天。"""
    out = ["## 節後衰退", ""]
    series = fill_calendar(by_date)
    if not series:
        return out + [""]
    peak_i = max(range(len(series)), key=lambda i: series[i][1])
    peak_date, peak_value = series[peak_i]
    total = sum(v for _, v in series)
    after = series[peak_i + 1:]
    out.append("- 高峰日：%s，%s 元%s"
               % (day_str(peak_date), money(peak_value),
                  "（促銷日）" if peak_date in promo_days else "（非促銷日）"))
    if not after:
        out.append("- 高峰日就是資料最後一天，無法觀察節後衰退。把節後 2～4 週的資料一起匯出再重跑。")
        out.append("")
        return out

    for threshold in (0.5, 0.2):
        line = "- 跌破高峰 %d%%（%s 元）：" % (threshold * 100, money(peak_value * threshold))
        hit = next(((i, d, v) for i, (d, v) in enumerate(after, 1) if v < peak_value * threshold), None)
        if hit:
            i, d, v = hit
            out.append(line + "高峰後第 %d 天，%s，當日 %s 元" % (i, day_str(d), money(v)))
        else:
            out.append(line + "資料期間內（高峰後 %d 天）未跌破" % len(after))
    tail = sum(v for _, v in after)
    out.append("- 高峰日之後累計：%s 元，佔資料期間總額 %s（共 %d 天）"
               % (money(tail), pct(tail / total * 100) if total else "—", len(after)))
    out.append("")
    out.append("這節只描述「銷售額何時掉到哪」，不解釋原因。掉下來可能是需求結束、"
               "也可能是缺貨、下架、廣告停投或促銷結束，資料本身分不出來。")
    out.append("")
    return out


def render_caveats():
    """固定結尾：這份分析不能證明什麼。"""
    return [
        "## 這份分析不能證明什麼",
        "",
        "以下限制無法用這份資料排除，寫進計畫書或簡報時必須一起帶上：",
        "",
        "1. **相關不等於因果。** 促銷日賣得多，不代表是促銷「造成」的。節慶本身的需求、"
        "當期廣告投放、鋪貨與陳列變化都同時發生，這份資料無法把它們分開。",
        "2. **沒有對照組。** 促銷期間沒有一組「同條件但不促銷」的對照，"
        "所以 lift 是「促銷期 vs 其他時期」的差異，不是促銷的增額效果（incremental lift）。"
        "真要量增額，需要事前設計對照（分區、分店、holdout 名單）。",
        "3. **季節性與同期活動的干擾。** 節慶檔期的需求本來就會上升，"
        "平台大促、對手動作、天氣、發薪日、連假位置都在同一段時間作用。"
        "把季節性上升算成促銷功勞，是這類分析最常見的高估來源。",
        "4. **通路混淆。** 各通路的客群、定價與補貼條件不同。"
        "促銷期若通路組合改變（多了一個高單價通路、或平台給了流量），"
        "全站數字會動，但不是機制的效果。分通路那一列就是為了看出這件事。",
        "5. **樣本量限制。** 標了「樣本不足」的列只有幾天資料，"
        "一天的天氣或一次缺貨就能翻轉結論，不要拿來做決策依據。",
        "6. **資料定義未知。** 這支腳本不知道你的銷售額有沒有扣掉退貨、取消、"
        "平台補貼與運費，也不知道是否含稅。定義不同，結論可以完全相反——"
        "請先向財務或營運確認欄位定義。",
        "",
        "任何需要外部數字（市場規模、業界平均、競品表現）的判斷，"
        "都不在這份分析的能力範圍內，必須另外引用標明出處的報告。",
        "",
    ]


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------

def build_report(path, args):
    """組出完整 markdown 報告字串。"""
    (records, skipped, warnings, mapping, headers,
     encoding, delimiter, total_rows) = read_rows(path)
    if not records:
        sys.stderr.write("錯誤：清洗後沒有任何可用資料列。略過原因：%s\n"
                         % ("；".join("%s %d 列" % (k, v) for k, v in skipped.most_common())
                            or "檔案沒有資料列"))
        raise SystemExit(1)

    by_date = daily_totals(records)
    promo_days, plain_days, mixed_days = promo_day_sets(records)
    notes = []
    baseline = pick_baseline(plain_days, promo_days, args.baseline_days, notes)
    span = (max(by_date) - min(by_date)).days + 1
    gaps = span - len(by_date)
    has_channel = "channel" in mapping

    out = ["# 促銷成效分析報告", ""]
    out.append("產出時間：%s｜分析工具：analyze_sales.py（純算術，不含任何外部估計值）"
               % dt.date.today().isoformat())
    out.append("")
    out += render_quality(path, total_rows, records, skipped, warnings, mapping,
                          headers, encoding, delimiter, gaps)
    out += render_overview(records, by_date, promo_days, plain_days, mixed_days)
    out += render_lift(records, by_date, promo_days, baseline, has_channel,
                       args.baseline_days, notes)
    out += render_peaks(by_date, promo_days, args.top)
    if has_channel:
        out += render_channels(records)
    out += render_promo_types(records, by_date, baseline)
    out += render_products(records, args.top)
    out += render_decay(by_date, promo_days)
    out += render_caveats()
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(
        description="促銷成效分析器：讀銷售明細 CSV，輸出 markdown 分析報告（只用標準函式庫）。",
        epilog="範例：python3 analyze_sales.py templates/sales_template.csv --baseline-days 14 --top 10")
    p.add_argument("csv_path", metavar="檔案.csv",
                   help="銷售明細 CSV；Excel 另存為 CSV 即可，編碼不用選")
    p.add_argument("--baseline-days", type=int, default=None,
                   help="lift 基準期：第一個促銷日之前最近 N 個非促銷日（預設用全部非促銷日）")
    p.add_argument("--top", type=int, default=5, help="商品與單日排行取前 N 名（預設 5）")
    args = p.parse_args()
    if args.top < 1:
        p.error("--top 必須大於 0")
    if args.baseline_days is not None and args.baseline_days < 1:
        p.error("--baseline-days 必須大於 0")
    sys.stdout.write(build_report(args.csv_path, args) + "\n")


if __name__ == "__main__":
    main()
