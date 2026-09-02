#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""計畫書健檢 — 機械稽核一份行銷計畫書的數字紀律。

這支程式不評價策略好壞，只查形式：數字有沒有出處、假設有沒有登記、
日期有沒有經過 backplan.py、預算加不加得起來、KPI 有沒有量測方式。
只用 Python 標準函式庫，沒有任何第三方相依。

用法：
    python3 shared/audit_plan.py 計畫書.md
    python3 shared/audit_plan.py 計畫書.md --festival 中秋 --year 2026
    python3 shared/audit_plan.py 計畫書.md --quiet

離開碼：C1／C2／C4／C5 有違規 → 1；只有 C3 可疑或 C6 待填 → 0；檔案讀不到 → 2。
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKPLAN = os.path.join(HERE, "backplan.py")
ASSUM = "[假設]"

# ── 業務數字的樣子 ────────────────────────────────────────────────────────
# 只抓「看起來像業務數字」的形態：百分比、千分位金額／數量、元、萬億、倍數、
# 廣告效率指標。刻意不抓裸整數（天數、分數、序號），那是偽陽性的主要來源。
TOKEN_RES = [
    ("百分比", re.compile(r"(?<![\d.])[＋+\-]?\d+(?:,\d{3})*(?:\.\d+)?\s*[%％]")),
    ("千分位", re.compile(r"(?<![\d,.])\d{1,3}(?:,\d{3})+(?:\.\d+)?"
                          r"(?:\s*(?:元|萬|億|張|次|件|人|盒|份|台|組))?")),
    ("外幣金額", re.compile(r"(?:NT\$|NTD|US\$|新台幣)\s*\d+(?:,\d{3})*(?:\.\d+)?"
                            r"(?:\s*(?:元|萬|億))?")),
    ("金額", re.compile(r"(?<![\d,.])\d+(?:\.\d+)?\s*(?:元|萬元|億元)")),
    ("萬億", re.compile(r"(?<![\d,.])\d+(?:\.\d+)?\s*(?:萬|億)(?![\d元])")),
    ("倍數", re.compile(r"(?<![\d,.xX×])\d+(?:\.\d+)?\s*(?:倍|[xX×])(?![\d,.])")),
    ("效率指標", re.compile(r"(?:ROAS|ROI|CPC|CPA|CPM|CPO|CTR|CVR|LTV|AOV)"
                            r"\s*[:：=＝]?\s*\d+(?:,\d{3})*(?:\.\d+)?")),
]

# ── 必須排除的偽陽性 ──────────────────────────────────────────────────────
EXCLUDE_RES = [
    ("日期", re.compile(r"\d{4}\s*[-/年]\s*\d{1,2}\s*[-/月]\s*\d{1,2}\s*日?")),
    ("月日", re.compile(r"(?<![\d])\d{1,2}\s*/\s*\d{1,2}(?![\d])")),
    ("年份", re.compile(r"(?<![\d,.])(?:19|20)\d{2}"
                        r"(?![\d,.%％]|\s*(?:元|萬|億|倍|[xX×]|張|次|件|人|盒|份|台|組))")),
    ("圖片尺寸", re.compile(r"(?<![\d])\d{2,5}\s*[xX×*]\s*\d{2,5}(?![\d])")),
    ("檔期節點", re.compile(r"D\s*[-+]\s*\d+")),
    ("評分區間", re.compile(r"(?<![\d])\d+\s*[-~－～]\s*\d+\s*[分維級]")),
    ("維度數", re.compile(r"[×xX]\s*\d+\s*[維軸項]")),
    ("版本號", re.compile(r"\bv?\d+\.\d+(?:\.\d+)+\b")),
    ("品號", re.compile(r"[A-Za-z]{2,}[-_]\d+")),
]

# 這三個只在「一整行」的開頭才有意義，判斷片段時不能套用。
EXCLUDE_ANCHORED = [
    ("章節編號", re.compile(r"^\s*(?:#{1,6}\s*)?\d+(?:\.\d+)*[.、)）](?=\s|$)")),
    ("清單編號", re.compile(r"^\s*[-*+]?\s*\d+[.、)）]\s")),
    ("表格列號", re.compile(r"^\s*\|\s*\d{1,3}\s*\|")),
]
EXCLUDE_FULL = EXCLUDE_RES + EXCLUDE_ANCHORED

SEP_RE = re.compile(r"^\s*\|[\s:|\-–—]*[-–—][\s:|\-–—]*\|?\s*$")
FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
DATE_RE = re.compile(r"(?<![\d])(\d{4})-(\d{2})-(\d{2})(?![\d])")

# 行內來源標記：這一行自己交代了數字從哪來。
SOURCE_MARKS = ("來源", "資料來源", "依據", "出處", "取自", "根據",
                "實跑", "實際輸出", "腳本", "引用", "逐字", "查表")
SOURCE_FILE_RE = re.compile(r"[\w./-]+\.(?:py|csv|tsv|json|xlsx)")
# 表頭出現這些字，代表整張表逐列都有出處欄。
TABLE_SOURCE_MARKS = ("來源", "資料來源", "依據", "出處", "實跑", "腳本", "取自", "量測")
# 段落級宣告：一句話交代底下一整段的出處。
BLOCK_CUES = ("以下", "下表", "下列", "底下", "本表", "本節", "本區", "這一區",
              "這一節", "這張表", "整段", "全部", "所有", "逐字", "皆", "都")
DERIVE_CUES = ("×", "÷", "＊", "相乘", "相除", "反推", "推導", "推算", "回推", "得出")

PLACEHOLDERS = [
    ("角括號待填", re.compile(r"<[^<>\n]{1,60}>")),
    ("待指派", re.compile(r"\[待指派\]|\[待確認\]|\[待填\]")),
    ("待填", re.compile(r"待填|待補")),
    ("TBD", re.compile(r"\bTBD\b|\bXXX+\b|\bN/?A\b")),
]
HTMLISH_RE = re.compile(r"^</|^<(?:br|img|a|div|span|p|hr|b|i|u|em|strong|http)")

TOTAL_MARKS = ("合計", "總計", "總預算", "總額", "小計", "合計金額", "共計")
HARD_TOTAL_MARKS = ("合計", "總計", "總預算", "總額", "共計")


# ── 基礎工具 ──────────────────────────────────────────────────────────────

def norm_token(tok):
    """把 token 正規化成 (類別, 數值字串)，供全文追溯比對用。

    +394.7% 與 394.7% 同值；30,675,000 元 與 30,675,000 同值；44.0% 與 44% 同值。
    百分比自成一類，其餘（金額／數量／倍數）合成「量」一類。
    """
    pct = "%" in tok or "％" in tok
    raw = tok.replace(",", "").replace("，", "").replace("＋", "")
    raw = re.sub(r"[^\d.\-]", "", raw)
    raw = raw.lstrip("-") if raw.startswith("--") else raw
    if not re.search(r"\d", raw):
        return None
    try:
        val = float(raw)
    except ValueError:
        return None
    num = "%d" % int(val) if val == int(val) else "%s" % round(val, 6)
    return ("pct" if pct else "量", num)


def excluded_spans(line, fragment=False):
    spans = []
    pats = EXCLUDE_RES if fragment else EXCLUDE_FULL
    for _name, rx in pats:
        for m in rx.finditer(line):
            spans.append((m.start(), m.end()))
    return spans


def find_tokens(line, fragment=False):
    """抓出一行裡的業務數字 token，過濾偽陽性後回傳 [(token, start, end)]。

    fragment=True 用於稽核從行中切出來的片段（例如 `[假設]` 後面那一段），
    此時行首錨定的偽陽性規則（章節編號、清單編號、表格列號）不適用。
    """
    if SEP_RE.match(line):
        return []
    bad = excluded_spans(line, fragment)
    cands = []
    for _name, rx in TOKEN_RES:
        for m in rx.finditer(line):
            cands.append((m.start(), m.end(), m.group(0).strip()))
    cands.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    out, taken = [], []
    for s, e, tok in cands:
        if any(s < be and bs < e for bs, be in bad):
            continue
        if any(s < te and ts < e for ts, te in taken):
            continue
        if norm_token(tok) is None:
            continue
        taken.append((s, e))
        out.append((tok, s, e))
    return out


def excerpt(line, width=80):
    s = line.strip().replace("`", "'").replace("\t", " ")
    s = re.sub(r"\s+", " ", s)
    return s[:width] + ("…" if len(s) > width else "")


def split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def clean_cell(cell):
    s = cell.replace("`", "").replace("*", "").strip()
    return s


def fence_map(lines):
    """回傳每一行是否落在代碼區塊內。"""
    inside, flags = False, []
    for line in lines:
        if FENCE_RE.match(line):
            flags.append(True)      # 圍籬本身也算區塊內
            inside = not inside
            continue
        flags.append(inside)
    return flags


def heading_levels(lines):
    lv = [0] * len(lines)
    for i, line in enumerate(lines):
        m = HEAD_RE.match(line)
        if m:
            lv[i] = len(m.group(1))
    return lv


def section_range(lines, levels, idx):
    """從第 idx 行（0-based，標題行）算出該節的行區間 [start, end]。"""
    own = levels[idx] or 7
    j = idx + 1
    while j < len(lines) and not (levels[j] and levels[j] <= own):
        j += 1
    return idx, j - 1


def find_tables(lines, in_fence):
    tables, i, n = [], 0, len(lines)
    while i < n:
        if (not in_fence[i] and lines[i].lstrip().startswith("|")
                and i + 1 < n and SEP_RE.match(lines[i + 1])):
            header = split_row(lines[i])
            rows, j = [], i + 2
            while j < n and not in_fence[j] and lines[j].lstrip().startswith("|"):
                if not SEP_RE.match(lines[j]):
                    rows.append((j, split_row(lines[j])))
                j += 1
            tables.append({"head": i, "header": header, "rows": rows, "end": j - 1})
            i = max(j, i + 1)
        else:
            i += 1
    return tables


# ── 出處歸屬 ──────────────────────────────────────────────────────────────

def has_source_mark(line):
    if any(m in line for m in SOURCE_MARKS):
        return True
    return bool(SOURCE_FILE_RE.search(line))


def build_provenance(lines, in_fence, levels, tables):
    """判定每一行的出處狀態。回傳 status[]，None 代表沒有任何出處宣告。"""
    status = [None] * len(lines)

    # 1) 段落級宣告：一句話交代底下整段的出處，效力延伸到該節結束。
    for i, line in enumerate(lines):
        if in_fence[i] or not has_source_mark(line):
            continue
        if not any(c in line for c in BLOCK_CUES):
            continue
        own = 0
        for k in range(i, -1, -1):
            if levels[k]:
                own = levels[k]
                break
        j = i + 1
        while j < len(lines) and not (levels[j] and levels[j] <= (own or 7)):
            j += 1
        for k in range(i, j):
            if status[k] is None:
                status[k] = "段落已宣告來源（第 %d 行）" % (i + 1)

    # 2) 表頭有出處欄：整張表逐列都有出處。
    for t in tables:
        if any(any(m in c for m in TABLE_SOURCE_MARKS) for c in t["header"]):
            for ln, _cells in t["rows"]:
                status[ln] = "表頭已標來源（第 %d 行）" % (t["head"] + 1)

    # 3) 行內標記優先於前兩者。
    for i, line in enumerate(lines):
        if in_fence[i]:
            status[i] = "代碼區塊"
        elif ASSUM in line:
            status[i] = "已標假設"
        elif has_source_mark(line):
            status[i] = "行內已標來源"
    return status


# ── C1 裸奔的數字 ─────────────────────────────────────────────────────────

def check_c1(lines, status):
    tokens = [find_tokens(line) for line in lines]
    attributed = set()
    for i, toks in enumerate(tokens):
        if status[i] is None:
            continue
        for tok, _s, _e in toks:
            key = norm_token(tok)
            if key:
                attributed.add(key)

    findings, traced = [], 0
    for i, toks in enumerate(tokens):
        if status[i] is not None:
            continue
        for tok, _s, _e in toks:
            key = norm_token(tok)
            if key in attributed:
                traced += 1
                continue
            findings.append((i + 1, tok, excerpt(lines[i])))

    notes = ["全文共 %d 個業務數字 token 帶有出處宣告（行內標記、表頭出處欄、"
             "段落宣告或代碼區塊）。" % len(attributed)]
    if traced:
        notes.append("另有 %d 處數字所在行沒有出處，但同一數值在文件別處已宣告出處，"
                     "視為可追溯、不列違規。" % traced)
    return {
        "code": "C1", "title": "裸奔的數字", "hard": True,
        "findings": [(ln, "`%s`" % tok, "在該行補 `[假設]`、寫「來源：…／依據：…」，"
                                        "或把它挪進已宣告出處的段落；查得到的事實不該用猜的。"
                                        "（原文：%s）" % ex)
                     for ln, tok, ex in findings],
        "notes": notes,
    }


# ── C2 假設清單漏登記 ─────────────────────────────────────────────────────

def assumption_occurrences(lines, in_fence):
    out = []
    for i, line in enumerate(lines):
        if in_fence[i]:
            continue
        pos = line.find(ASSUM)
        while pos >= 0:
            tail = line[pos + len(ASSUM):]
            m = re.search(r"[`｜|。；;—–]", tail)
            seg = (tail[:m.start()] if m else tail).strip()[:60]
            out.append((i, seg))
            pos = line.find(ASSUM, pos + len(ASSUM))
    return out


def find_assumption_section(lines, levels):
    for i, line in enumerate(lines):
        m = HEAD_RE.match(line)
        if m and ("假設清單" in m.group(2)
                  or ("待驗證" in m.group(2) and "假設" in m.group(2))):
            return section_range(lines, levels, i)
    for i, line in enumerate(lines):
        s = line.strip().strip("*").strip()
        if s and "假設清單" in s and len(s) <= 24:
            j = i + 1
            while j < len(lines) and not levels[j]:
                j += 1
            return i, j - 1
    return None


def check_c2(lines, in_fence, levels):
    occ = assumption_occurrences(lines, in_fence)
    sec = find_assumption_section(lines, levels)
    findings, notes = [], []

    if not occ:
        notes.append("全文沒有任何 `[假設]` 標記。")
        if sec is None:
            notes.append("也沒有「待驗證假設清單」章節。若這份計畫書真的一個假設都沒有，"
                         "請確認每個數字都有實據；否則是漏標。")
        return {"code": "C2", "title": "假設清單漏登記", "hard": True,
                "findings": [], "notes": notes}

    if sec is None:
        return {
            "code": "C2", "title": "假設清單漏登記", "hard": True,
            "findings": [(occ[0][0] + 1,
                          "找不到「待驗證假設清單」章節",
                          "全文有 %d 處 `[假設]` 標記卻沒有集中登記的清單。"
                          "請新增一節「待驗證假設清單」，逐條寫依據、驗證方式、驗證時點。"
                          % len(occ))],
            "notes": [],
        }

    s0, s1 = sec
    reg_text = "\n".join(lines[s0:s1 + 1])
    # 只有表格列算登記。若把整個區段都算進來，散落在該節的敘述句會登記自己，
    # 於是「其他假設：…」永遠通得過檢查。
    registered = set()
    for ln in range(s0, s1 + 1):
        if not lines[ln].lstrip().startswith("|") or SEP_RE.match(lines[ln]):
            continue
        for tok, _s, _e in find_tokens(lines[ln]):
            key = norm_token(tok)
            if key:
                registered.add(key)
    reg_rows = sum(1 for line in lines[s0:s1 + 1]
                   if line.lstrip().startswith("|") and not SEP_RE.match(line))
    reg_rows = max(reg_rows - 1, 0)

    # 由已登記假設推導出來的結果，仍然是假設，但它的出處就是那些輸入值。
    derived = set()
    for ln, _seg in occ:
        if s0 <= ln <= s1 or not any(c in lines[ln] for c in DERIVE_CUES):
            continue
        for tok, _s, _e in find_tokens(lines[ln]):
            key = norm_token(tok)
            if key:
                derived.add(key)

    plain = re.compile(r"[^\u4e00-\u9fffA-Za-z0-9]")
    seen, meta, derived_hits = set(), 0, 0
    for ln, seg in occ:
        # 清單章節內只承認表格列。散落在該節裡的敘述句（「其他假設：…」）不算登記，
        # 否則只要把漏掉的假設寫在清單後面就能繞過這項檢查。
        if s0 <= ln <= s1 and (lines[ln].lstrip().startswith("|")
                               or lines[ln].lstrip().startswith("#")):
            continue
        if not seg:
            meta += 1
            continue
        keys = [norm_token(t) for t, _s, _e in find_tokens(seg, fragment=True)]
        keys = [k for k in keys if k]
        if keys:
            if any(k in registered for k in keys):
                continue
            if any(k in derived for k in keys):
                derived_hits += 1
                continue
        else:
            flat = plain.sub("", seg)
            if flat and (len(flat) < 4 and flat in plain.sub("", reg_text)
                         or any(flat[k:k + 4] in plain.sub("", reg_text)
                                for k in range(max(len(flat) - 3, 1)))):
                continue
        if (ln, seg) in seen:
            continue
        seen.add((ln, seg))
        findings.append((ln + 1, "`[假設] %s`" % seg,
                         "文中標了假設，但「待驗證假設清單」（第 %d 行起）沒有這一條。"
                         "請補進清單並寫依據、驗證方式、驗證時點；"
                         "或把這裡的標記改成引用清單既有編號。" % (s0 + 1)))

    notes.append("清單章節在第 %d 行，共 %d 列登記。" % (s0 + 1, reg_rows))
    notes.append("全文 `[假設]` 標記 %d 處。" % len(occ))
    if derived_hits:
        notes.append("其中 %d 處是由已登記假設相乘／相除推導出的結果（例如總預算＝"
                     "工作階段 × CPC），輸入值已在清單內，不另列違規。" % derived_hits)
    if meta:
        notes.append("另有 %d 處 `[假設]` 是在說明標記本身的用法，非實際假設。" % meta)
    return {"code": "C2", "title": "假設清單漏登記", "hard": True,
            "findings": findings, "notes": notes}


# ── C3 日期來源 ───────────────────────────────────────────────────────────

def run_backplan(festival, year):
    if not os.path.exists(BACKPLAN):
        return None, "找不到 %s，無法驗證日期。" % BACKPLAN
    cmd = [sys.executable, BACKPLAN, festival, "--year", str(year)]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=60)
    except Exception as exc:                                  # pragma: no cover
        return None, "呼叫 backplan.py 失敗：%s" % exc
    out = p.stdout.decode("utf-8", "replace")
    err = p.stderr.decode("utf-8", "replace").strip()
    if p.returncode != 0:
        return None, "backplan.py 離開碼 %d：%s" % (p.returncode, err[:200])
    if not DATE_RE.search(out):
        return None, "backplan.py 沒有輸出任何日期（節慶名稱是否打錯？）：%s" % err[:120]
    return out, None


def check_c3(lines, festival, year):
    res = {"code": "C3", "title": "日期來源", "hard": False,
           "findings": [], "notes": []}
    if not festival or not year:
        res["skip"] = True
        res["notes"].append("已跳過：沒有給 `--festival` 與 `--year`，"
                            "無法呼叫 backplan.py 取得合法日期集合。"
                            "要開啟這項檢查請加上兩個參數。")
        return res

    out, err = run_backplan(festival, year)
    if err:
        res["skip"] = True
        res["notes"].append("已跳過：%s" % err)
        return res

    valid = sorted({m.group(0) for m in DATE_RE.finditer(out)})
    lo, hi = valid[0], valid[-1]
    res["notes"].append("合法日期集合取自 `python3 shared/backplan.py %s --year %d` 實跑輸出，"
                        "共 %d 個里程碑日期，檔期區間 %s ～ %s。"
                        % (festival, year, len(valid), lo, hi))

    hist, odd = {}, {}
    for i, line in enumerate(lines):
        for m in DATE_RE.finditer(line):
            d = m.group(0)
            if d in valid or lo <= d <= hi:
                continue
            bucket = hist if d[:4] < lo[:4] else odd
            bucket.setdefault(d, []).append(i + 1)

    for d in sorted(odd):
        lns = odd[d]
        res["findings"].append((
            "、".join(str(n) for n in lns), "`%s`" % d,
            "不在 backplan.py 的里程碑集合、也不在檔期區間 %s ～ %s 內。"
            "若是手算的請改用腳本輸出；若是通路給的截止日或第三方硬性日期，"
            "請在該行寫清楚它是誰給的。（原文：%s）"
            % (lo, hi, excerpt(lines[lns[0] - 1]))))
    for d in sorted(hist):
        lns = hist[d]
        res["findings"].append((
            "、".join(str(n) for n in lns), "`%s`" % d,
            "早於檔期年份。若是去年同期的歷史資料則屬正常，"
            "但它不是 backplan.py 給的日期，請確認它來自實際銷售資料而非手打。"))
    if hist:
        res["notes"].append("其中 %d 個是早於檔期年份的日期（共出現 %d 次），"
                            "通常是去年同期的比較基期；這類日期 backplan.py 管不到，"
                            "要靠銷售資料本身佐證。"
                            % (len(hist), sum(len(v) for v in hist.values())))
    if not odd and not hist:
        res["notes"].append("文中每一個 YYYY-MM-DD 都落在 backplan.py 的里程碑集合"
                            "或檔期區間內，沒有手算日期的跡象。")
    return res


# ── C4 預算加總 ───────────────────────────────────────────────────────────

def parse_amount(cell):
    s = clean_cell(cell)
    if not s:
        return None
    s = re.sub(r"\[[^\]]*\]|<[^>]*>", " ", s)
    s = s.replace(",", "").replace("，", "")
    m = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(萬|億)?\s*元?", s)
    if not m:
        return None
    val = float(m.group(1))
    if m.group(2) == "萬":
        val *= 10000
    elif m.group(2) == "億":
        val *= 100000000
    return val


def check_c4(tables):
    res = {"code": "C4", "title": "預算加總", "hard": True,
           "findings": [], "notes": []}
    targets = []
    for t in tables:
        idx = None
        for k, cell in enumerate(t["header"]):
            c = clean_cell(cell)
            if "金額" in c or "預算" in c or "費用" in c:
                idx = k
                break
        if idx is not None and t["rows"]:
            targets.append((t, idx))

    if not targets:
        res["skip"] = True
        res["notes"].append("已跳過：找不到欄位名含「金額」「預算」或「費用」的 markdown 表格。"
                            "若預算是寫成條列的反推法，這項檢查無法驗算，"
                            "請人工確認每一步的乘除。")
        return res

    for t, idx in targets:
        label = clean_cell(t["header"][idx])
        head_ln = t["head"] + 1
        detail, totals, unverifiable = [], [], []
        for ln, cells in t["rows"]:
            if idx >= len(cells):
                continue
            first = clean_cell(cells[0])
            amount = parse_amount(cells[idx])
            is_total = any(m in first for m in TOTAL_MARKS) or \
                any(m in clean_cell(" ".join(cells[:idx])) for m in TOTAL_MARKS)
            if amount is None:
                if not clean_cell(re.sub(r"\[[^\]]*\]|<[^>]*>", "", cells[idx])):
                    unverifiable.append((ln + 1, first or "（無科目名）"))
                continue
            if is_total:
                if any(m in first for m in HARD_TOTAL_MARKS) or \
                        any(m in clean_cell(" ".join(cells[:idx]))
                            for m in HARD_TOTAL_MARKS):
                    totals.append((ln + 1, first, amount))
            else:
                detail.append((ln + 1, first, amount))

        if unverifiable:
            res["inconclusive"] = True
            res["notes"].append(
                "第 %d 行的「%s」表：**無法驗算**——%s 列的金額只有 `[假設]` 或 `<填入>` "
                "佔位符，加不起來（第 %s 行）。這不是格式問題，是這份預算還沒填完。"
                % (head_ln, label, len(unverifiable),
                   "、".join(str(n) for n, _t in unverifiable)))
            continue
        if not detail:
            res["inconclusive"] = True
            res["notes"].append("第 %d 行的「%s」表：沒有可加總的明細列，**無法驗算**。"
                                % (head_ln, label))
            continue
        if not totals:
            res["inconclusive"] = True
            res["notes"].append(
                "第 %d 行的「%s」表：明細 %d 列合計 %s 元，但表內沒有標「合計／總計／"
                "總預算」的列，**無法對帳**。建議補一列合計，讓數字可以被驗。"
                % (head_ln, label, len(detail), fmt_money(sum(d[2] for d in detail))))
            continue

        total_sum = sum(d[2] for d in detail)
        for ln, name, declared in totals:
            diff = declared - total_sum
            if abs(diff) > 1:
                res["findings"].append((
                    ln, "「%s」%s 元" % (name or "合計", fmt_money(declared)),
                    "明細 %d 列相加是 %s 元，差 %s 元。修正明細或修正合計，"
                    "不要讓兩個數字並存（表頭在第 %d 行）。"
                    % (len(detail), fmt_money(total_sum), fmt_money(abs(diff)), head_ln)))
            else:
                res["notes"].append("第 %d 行的「%s」表：明細 %d 列相加 %s 元，"
                                    "與合計相符。"
                                    % (head_ln, label, len(detail), fmt_money(total_sum)))
    return res


def fmt_money(val):
    if abs(val - round(val)) < 1e-9:
        return "{:,}".format(int(round(val)))
    return "{:,.2f}".format(val)


# ── C5 KPI 缺資料來源 ─────────────────────────────────────────────────────

EMPTY_CELL_RE = re.compile(r"^(?:[-–—_.·、,，\s]|待填|待補|TBD|XXX+|N/?A|\?)*$", re.I)


def is_blank_cell(cell):
    s = clean_cell(cell)
    s = re.sub(r"\[[^\]]*\]|<[^>]*>", "", s).strip()
    return bool(EMPTY_CELL_RE.match(s))


def check_c5(tables):
    res = {"code": "C5", "title": "KPI 缺資料來源", "hard": True,
           "findings": [], "notes": []}
    kpi_tables = []
    for t in tables:
        for cell in t["header"]:
            c = clean_cell(cell)
            if "KPI" in c.upper() or "指標" in c:
                kpi_tables.append(t)
                break

    if not kpi_tables:
        res["skip"] = True
        res["notes"].append("已跳過：找不到欄位名含「KPI」或「指標」的 markdown 表格。")
        return res

    for t in kpi_tables:
        head_ln = t["head"] + 1
        idx = None
        for k, cell in enumerate(t["header"]):
            c = clean_cell(cell)
            if "資料來源" in c or "量測" in c or "來源" in c or "怎麼量" in c:
                idx = k
                break
        if idx is None:
            res["findings"].append((
                head_ln, "表頭缺「資料來源」欄",
                "第 %d 行的 KPI 表沒有「資料來源」或「量測方式」欄（現有欄位：%s）。"
                "沒寫從哪裡看數字，檔後就無從結案。請補一欄，逐列填寫。"
                % (head_ln, "、".join(clean_cell(c) for c in t["header"]))))
            continue
        col = clean_cell(t["header"][idx])
        blanks = []
        for ln, cells in t["rows"]:
            name = clean_cell(cells[0]) if cells else ""
            if idx >= len(cells) or is_blank_cell(cells[idx]):
                blanks.append((ln + 1, name))
        for ln, name in blanks:
            res["findings"].append((
                ln, "「%s」的%s為空" % (name or "（無指標名）", col),
                "指標沒有資料來源就無法量測，等於這條 KPI 不存在。"
                "填後台名稱、報表路徑或量測方式（表頭在第 %d 行）。" % head_ln))
        if not blanks:
            res["notes"].append("第 %d 行的 KPI 表有「%s」欄，%d 列全部填妥。"
                                % (head_ln, col, len(t["rows"])))
    return res


# ── C6 未填佔位符 ─────────────────────────────────────────────────────────

def in_value_slot(line, start, end):
    """裸詞（待填／TBD）只有出現在「值」的位置才算洞。

    寫在反引號裡、寫在表格欄位裡、或跟在冒號後面，才是真的沒填完；
    正文討論「待填」這個詞（例如標題「留待填、刻意不猜的」）不算。
    """
    if line[:start].count("`") % 2 == 1:
        return True
    if line.lstrip().startswith("|"):
        cut = line.rfind("|", 0, start)
        nxt = line.find("|", end)
        if cut >= 0 and nxt > 0:
            cell = clean_cell(line[cut + 1:nxt])
            cell = re.sub(r"[（(].*?[）)]", "", cell).strip("。、，,．. ")
            return len(cell) <= 6
    tail = line[:start].rstrip()
    return tail.endswith("：") or tail.endswith(":")


def check_c6(lines, in_fence):
    res = {"code": "C6", "title": "未填佔位符", "hard": False,
           "findings": [], "notes": []}
    counts = {}
    for i, line in enumerate(lines):
        if in_fence[i] or HEAD_RE.match(line):
            continue
        spans = []
        for name, rx in PLACEHOLDERS:
            for m in rx.finditer(line):
                tok = m.group(0)
                if name == "角括號待填" and HTMLISH_RE.match(tok[1:]):
                    continue
                if name in ("待填", "TBD") and not in_value_slot(line, m.start(), m.end()):
                    continue
                if any(m.start() < e and s < m.end() for s, e in spans):
                    continue
                spans.append((m.start(), m.end()))
                counts[tok] = counts.get(tok, 0) + 1
                res["findings"].append((i + 1, "`%s`" % tok, excerpt(line)))
    if res["findings"]:
        top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        res["notes"].append("共 %d 個洞，%d 種寫法。最多的是：%s。"
                            % (len(res["findings"]), len(counts),
                               "、".join("`%s`×%d" % (k, v) for k, v in top)))
        res["notes"].append("這些不是錯誤，是還沒問到人的地方。"
                            "刻意留白（例如查得到的事實不用猜）就留著，"
                            "但送核准前要能說出每一個洞由誰負責補。")
    else:
        res["notes"].append("沒有未填佔位符。")
    return res


# ── 報告 ──────────────────────────────────────────────────────────────────

LIMITS = """## 這支程式檢不出什麼

它只看得到形式，看不出內容。以下每一項它一律沉默：

- **策略好不好。** 一份標記完美、加總正確、每個數字都有出處的計畫書，可以是一個爛策略。
- **數字合不合理。** C1 只驗「這個數字有沒有宣告出處」，不驗那個出處是不是真的，也不驗數值本身合不合理。在任何數字後面貼一句「來源：內部估算」都能過關。
- **假設合不合理。** C2 只驗假設有沒有登記進清單，不判斷那條假設站不站得住腳，也不判斷驗證方式做不做得到。
- **漏了什麼。** 它只能檢查文件裡寫了的東西。整節缺漏、關鍵風險沒寫、該問的人沒問，它看不見。
- **引用對不對。** C1 的追溯是全文比對：同一個數值只要在文件任一處宣告了出處，別處引用就算合格；把數字接到錯誤的來源上，它分不出來。
- **C4 只驗一張表的加減。** 反推法那種條列式的乘除鏈，它不驗算。
- **表格裡指標名與數值分屬兩欄時，C1 抓不到。** 例如 `| ROAS | 4.5 |`，數值 `4.5` 沒有單位也沒有千分位，
  刻意不列入 token 樣式以免把評分、天數、序號全部誤報。這類 KPI 表改由 C5 把關「有沒有資料來源欄」。

過了這支程式，只代表這份計畫書**形式上誠實**。內容誠不誠實、策略對不對，還是要人看。"""


def render(path, checks, quiet):
    hard_fail = sum(len(c["findings"]) for c in checks if c["hard"])
    soft = sum(len(c["findings"]) for c in checks if not c["hard"])
    skipped = [c for c in checks if c.get("skip")]
    unsure = [c for c in checks if c.get("inconclusive") and not c.get("skip")]
    passed = [c for c in checks if not c.get("skip")
              and not c.get("inconclusive") and not c["findings"]]

    out = ["# 計畫書健檢報告", ""]
    out.append("**檔案**：`%s`" % path)
    out.append("")
    out.append("**%d 項檢查，%d 項通過，%d 筆需修正，%d 筆僅提醒，%d 項無法驗算，"
               "%d 項跳過。**"
               % (len(checks), len(passed), hard_fail, soft, len(unsure), len(skipped)))
    out.append("")
    if hard_fail:
        out.append("判定：**不通過**（離開碼 1）。C1／C2／C4／C5 任一有違規就不該送核准。")
    elif unsure:
        out.append("判定：**通過但有項目驗不了**（離開碼 0）。查得出來的形式問題都沒有，"
                   "但下面標「無法驗算」的項目是因為資料還沒填完，不是因為沒問題。")
    else:
        out.append("判定：**通過**（離開碼 0）。形式檢查全過；C3 可疑與 C6 待填不影響判定。")
    out.append("")

    for c in checks:
        if quiet and not c["findings"] and not c.get("inconclusive"):
            continue
        mark = "⚠️ " if (c["findings"] and c["hard"]) else ""
        head = "## %s%s %s" % (mark, c["code"], c["title"])
        if c.get("skip"):
            head += "（已跳過）"
        elif c.get("inconclusive") and not c["findings"]:
            head += "（無法驗算）"
        elif c["findings"]:
            head += "（%d 筆%s）" % (len(c["findings"]),
                                    "需修正" if c["hard"] else "提醒")
        else:
            head += "（通過）"
        out.append(head)
        out.append("")
        for note in c["notes"]:
            out.append("- %s" % note)
        if c["notes"]:
            out.append("")
        for ln, tok, hint in c["findings"]:
            out.append("- **第 %s 行** %s" % (ln, tok))
            out.append("  - %s" % hint)
        if c["findings"]:
            out.append("")

    if not quiet:
        out.append(LIMITS)
    return "\n".join(out).rstrip() + "\n"


def main():
    p = argparse.ArgumentParser(
        description="計畫書健檢：機械稽核一份行銷計畫書的數字紀律")
    p.add_argument("plan", help="計畫書 markdown 檔路徑")
    p.add_argument("--festival", help="節慶名稱，開啟 C3 日期來源檢查")
    p.add_argument("--year", type=int, help="檔期年份，開啟 C3 日期來源檢查")
    p.add_argument("--quiet", action="store_true", help="只印有違規的檢查項")
    a = p.parse_args()

    if not os.path.isfile(a.plan):
        sys.stderr.write("讀不到檔案：%s\n" % a.plan)
        return 2
    with open(a.plan, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    in_fence = fence_map(lines)
    levels = heading_levels(lines)
    tables = find_tables(lines, in_fence)
    status = build_provenance(lines, in_fence, levels, tables)

    checks = [
        check_c1(lines, status),
        check_c2(lines, in_fence, levels),
        check_c3(lines, a.festival, a.year),
        check_c4(tables),
        check_c5(tables),
        check_c6(lines, in_fence),
    ]
    sys.stdout.write(render(a.plan, checks, a.quiet))
    return 1 if any(c["findings"] for c in checks if c["hard"]) else 0


if __name__ == "__main__":
    sys.exit(main())
