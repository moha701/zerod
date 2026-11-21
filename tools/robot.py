#!/usr/bin/env python3
"""ZEROED data robot.

Reads public Modern Warfare 4 pages and updates data.json:
  * official patch notes (callofduty.com): new patch entries, gun damage, ranges, head multipliers
  * WZStats MW4 weapon list: new guns, their class and unlock level
  * CODMunity Warzone TTK table: Warzone kill times for every MW4 gun
  * itemshop.gg: today's store bundles
  * warzoneloadout.games: Apex attachments that are missing

Safety rules (see SECURITY in README):
  * Python standard library only, nothing to install.
  * Downloads are treated as text. Nothing downloaded is ever run.
  * Only https pages on the hosts in ALLOWED_HOSTS are fetched, with a size cap.
  * Every value is checked against sane limits before it is written; anything odd is skipped and reported.
  * Only data.json (and the robot's report files) are written.
"""
from __future__ import annotations

import datetime as dt
import html as htmllib
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ALLOWED_HOSTS = {"www.callofduty.com", "codmunity.gg", "wzstats.gg", "itemshop.gg", "warzoneloadout.games"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36 zeroed-robot"
MAX_BYTES = 6_000_000
CLASSES = {"AR", "SMG", "LMG", "Marksman", "Sniper", "Shotgun", "Pistol"}
CLASS_MAP = {"ASSAULT_RIFLE": "AR", "SMG": "SMG", "SUBMACHINE_GUN": "SMG", "LMG": "LMG", "MARKSMAN_RIFLE": "Marksman", "MARKSMAN": "Marksman", "SNIPER_RIFLE": "Sniper", "SNIPER": "Sniper", "SHOTGUN": "Shotgun", "PISTOL": "Pistol", "HANDGUN": "Pistol",
             "assault rifle": "AR", "smg": "SMG", "lmg": "LMG", "marksman rifle": "Marksman", "sniper rifle": "Sniper", "shotgun": "Shotgun", "pistol": "Pistol"}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
SOURCES = {
    "patch_index": "https://www.callofduty.com/patchnotes",
    "patch_s1": "https://www.callofduty.com/patchnotes/2026/11/call-of-duty-modern-warfare-4-season-1-patch-notes",
    "wzstats": "https://wzstats.gg/mw4/multiplayer/stats",
    "codmunity_wz": "https://codmunity.gg/ttk/warzone",
    "shop": "https://itemshop.gg/call-of-duty",
    "apex": "https://warzoneloadout.games/mw4/attachments/apex",
}

# ------------------------------------------------------------------ helpers
def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def today_local() -> str:  # the site's day is Oman time
    return (now_utc() + dt.timedelta(hours=4)).date().isoformat()

def fetch(url: str, retries: int = 2) -> str:
    u = urllib.parse.urlparse(url)
    if u.scheme != "https" or u.hostname not in ALLOWED_HOSTS:
        raise ValueError("blocked url " + url)
    last = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
            with urllib.request.urlopen(req, timeout=30) as r:
                final = urllib.parse.urlparse(r.geturl())
                if final.hostname not in ALLOWED_HOSTS:
                    raise ValueError("redirected off allowed hosts")
                b = r.read(MAX_BYTES + 1)
                if len(b) > MAX_BYTES:
                    raise ValueError("page too big")
                return b.decode("utf-8", "replace")
        except Exception as e:  # network hiccup: wait and retry
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"fetch failed {url}: {last!r}")

def strip_tags(s: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return htmllib.unescape(s).replace("ㅤ", " ").replace("\xa0", " ")

def clean(s, maxlen: int = 120) -> str:
    """Plain, safe text: no tags, no angle brackets or quotes that could break the page, no control chars."""
    s = strip_tags(str(s or ""))
    s = re.sub(r"[\x00-\x1f\x7f<>\"`\\]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen].strip()

def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())

def slug(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(s or "").lower())).strip("-")[:48]

def num(s):
    m = re.search(r"-?\d+(?:\.\d+)?", str(s or "").replace(",", ""))
    return float(m.group(0)) if m else None

def parse_date(text: str):
    m = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d\d)", text, re.I)
    if not m:
        return None
    return dt.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))).isoformat()

def short_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return d.strftime("%b ") + str(d.day)

def nice_name(upper: str) -> str:
    """'KRAIT P68' -> 'Krait P68', keeps tokens with digits or short acronyms uppercase."""
    out = []
    for t in upper.split():
        if any(c.isdigit() for c in t) or (len(t) <= 3 and t.isalpha() and t.upper() == t and t not in {"THE", "AND"}):
            out.append(t)
        else:
            out.append(t[:1].upper() + t[1:].lower())
    return " ".join(out)

# ------------------------------------------------------------------ parsers
LABELS = {
    "max damage": "d0", "maximum damage": "d0", "max damage range": "r0", "maximum damage range": "r0",
    "min damage": "dmin", "minimum damage": "dmin", "muzzle velocity": "vel", "fire rate": "rpm", "rate of fire": "rpm",
    "head": "head", "upper torso": "upper", "head multiplier": "head", "upper torso multiplier": "upper",
}
for k in (1, 2, 3, 4):
    for w in ("mid", "medium"):
        LABELS[f"{w} damage {k}"] = f"d{k}"
        LABELS[f"{w} damage range {k}"] = f"r{k}"

def parse_patch_page(h: str, url: str) -> list[dict]:
    """Sections of a callofduty.com patch notes page, newest first, each with its weapon change tables."""
    dateline = parse_date(" ".join(re.findall(r'class="dateline">([^<]+)<', h)[:1])) or None
    i0 = h.find("body-content-parsys")
    body = h[i0:] if i0 > 0 else h
    marks = []
    for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", body, re.S):
        d = parse_date(strip_tags(m.group(1)))
        if d:
            marks.append((m.start(), d))
    cuts = [(0, dateline)] + marks
    sections = []
    for i, (pos, d) in enumerate(cuts):
        end = cuts[i + 1][0] if i + 1 < len(cuts) else len(body)
        chunk = body[pos:end]
        if not d or not chunk.strip():
            continue
        weapons = []
        keys = [m.start() for m in re.finditer(r'table__cell--key">\s*Weapon:\s*<', chunk)]
        for j, kpos in enumerate(keys):
            blk = chunk[kpos: keys[j + 1] if j + 1 < len(keys) else len(chunk)]
            name = next((clean(x, 60) for x in re.findall(r"<h3[^>]*>(.*?)</h3>", blk, re.S) if clean(x, 60)), "")
            if not name:
                continue
            # each <h4> title ("M4 Weapon Adjustments", "Hyeon Auto Apex Attachment Adjustments") owns the tables after it
            heads = [(m.start(), clean(m.group(1), 90)) for m in re.finditer(r"<h4[^>]*>(.*?)</h4>", blk, re.S)]
            if not heads:
                heads = [(0, "")]
            for hi, (hpos, title) in enumerate(heads):
                sub = blk[hpos: heads[hi + 1][0] if hi + 1 < len(heads) else len(blk)]
                tables = re.findall(r"<table.*?</table>", sub, re.S)
                rows = []
                for tb in tables[:1]:  # the first table under a title is that gun's own numbers
                    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S):
                        cells = [clean(c, 40) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
                        cells = [c for c in cells if c and c not in ("→", "->")]
                        if len(cells) >= 3 and cells[0].lower() not in ("damage profiles", "hit location modifiers", "pre-patch"):
                            rows.append((cells[0], cells[1], cells[2]))
                bullets = [b for b in (clean(x, 160) for x in re.findall(r"<li[^>]*>(.*?)</li>", sub, re.S)) if b and not b.lower().startswith("all weapons in this category")]
                for b in bullets:  # "Upper Torso Damage Multiplier increased from 1.1 to 1.13"
                    m = re.search(r"(upper torso|head)[a-z ]*multiplier[a-z ]*from ([\d.]+) to ([\d.]+)", b, re.I)
                    if m:
                        rows.append(("Upper Torso" if m.group(1).lower().startswith("upper") else "Head", m.group(2), m.group(3)))
                if rows or (bullets and re.search(r"weapon|apex|adjust", title, re.I)):
                    weapons.append({"weapon": name, "title": title, "rows": rows, "bullets": bullets[:6]})
        sections.append({"date": d, "url": url, "weapons": weapons, "chars": len(chunk)})
    return sections

def find_patch_pages(index_html: str) -> list[str]:
    links = set(re.findall(r'href="(/patchnotes/20\d\d/\d\d/[a-z0-9\-]*modern-warfare-4[a-z0-9\-]*)"', index_html))
    return sorted(("https://www.callofduty.com" + l for l in links), reverse=True)[:4]

def parse_wzstats(h: str) -> list[dict]:
    m = re.search(r'<script id="ng-state" type="application/json">(.*?)</script>', h, re.S)
    if not m:
        raise ValueError("wzstats: no ng-state")
    j = json.loads(m.group(1))
    st = j.get("store:weapons-and-tier-lists-mw4") or {}
    out = []
    for w in st.get("weapons") or []:
        if not isinstance(w, dict) or w.get("game") != "mw4" or w.get("isVariant") or w.get("conversionKitId") or w.get("baseWeaponId"):
            continue
        t = w.get("type") or {}
        cls = CLASS_MAP.get(t.get("id") if isinstance(t, dict) else str(t))
        name = clean(w.get("name"), 40)
        if not cls or not name:
            continue
        out.append({"name": nice_name(name), "norm": norm(name), "cls": cls, "unlock": int(w.get("unlockedAtPlayerLevel") or 0), "isNew": bool(w.get("isNew"))})
    if len(out) < 10:
        raise ValueError("wzstats: too few weapons, layout probably changed")
    return out

def parse_codmunity_wz(h: str) -> list[dict]:
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        a = re.search(r'href="/weapon/([a-z0-9]+)/([a-z0-9.\-]+)"[^>]*>([^<]+)', tr)
        if not a or a.group(1) != "mw4":
            continue
        vals = {int(k): float(v) for k, v in re.findall(r'data-cell="avgTtk(\d)" data-value="([\d.]+)"', tr)}
        if len(vals) != 4:
            continue
        cat = re.search(r'ttk-category-pill">([^<]+)<', tr)
        out.append({"name": clean(a.group(3), 40), "norm": norm(a.group(3)), "cls": CLASS_MAP.get(clean(cat.group(1), 30).lower()) if cat else None, "ttk": [vals[1], vals[2], vals[3], vals[4]]})
    if len(out) < 8:
        raise ValueError("codmunity: too few rows, layout probably changed")
    return out

def _flight_payload(h: str) -> str:
    parts = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', h, re.S)
    return "".join(json.loads('"' + p + '"') for p in parts)

def _balanced(s: str, start: int) -> str:
    depth, i, instr, esc = 0, start, False, False
    while i < len(s):
        c = s[i]
        if instr:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': instr = False
        elif c == '"': instr = True
        elif c in "[{": depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return s[start: i + 1]
        i += 1
    raise ValueError("unbalanced")

def parse_shop(h: str) -> list[dict]:
    p = _flight_payload(h)
    m = re.search(r'"sections":\[', p)
    if not m:
        raise ValueError("shop: no sections")
    secs = json.loads(_balanced(p, m.end() - 1))
    cards = []
    for sec in secs:
        if isinstance(sec, dict) and "modern warfare 4" in str(sec.get("title", "")).lower():
            cards += [c for c in sec.get("cards") or [] if isinstance(c, dict)]
    if not cards:  # fall back to every card tagged MW4
        for sec in secs:
            cards += [c for c in (sec.get("cards") or []) if isinstance(c, dict) and "MW4" in (c.get("tags") or [])]
    out, seen = [], set()
    for c in cards:
        name = clean(c.get("name"), 60)
        if not name or norm(name) in seen:
            continue
        seen.add(norm(name))
        pr = c.get("price") if isinstance(c.get("price"), dict) else {}
        price = int(pr["amount"]) if pr.get("currency") == "codpoints" and isinstance(pr.get("amount"), (int, float)) and 100 <= pr["amount"] <= 10000 else None
        items = len(c.get("contents") or []) or int(num(c.get("subtitle")) or 0)
        url = c.get("url") if isinstance(c.get("url"), str) and c["url"].startswith("https://www.callofduty.com/") else None
        tag = clean(c.get("badge") if c.get("badge") not in (None, "$undefined") else c.get("rarityName"), 24)
        out.append({"name": name, "price": price, "items": max(0, min(items, 60)), "tag": tag, "url": url})
    if not (1 <= len(out) <= 120):
        raise ValueError(f"shop: unexpected bundle count {len(out)}")
    return out

def parse_apex(h: str) -> list[dict]:
    """'<name>' / 'Unlock level' / '<n>' triples from the Apex list page."""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    lines = [clean(x, 60) for x in re.split(r"<[^>]+>", body)]
    lines = [x for x in lines if x]
    out = []
    for i, x in enumerate(lines):
        if x.lower() == "unlock level" and 0 < i < len(lines) - 1 and lines[i + 1].isdigit():
            name = lines[i - 1]
            if re.fullmatch(r"[A-Za-z0-9 .\-]{3,40}", name) and not name.lower().startswith(("apex", "discover")):
                out.append({"name": name, "level": int(lines[i + 1])})
    return out

# ------------------------------------------------------------------ math
def segs_from_profile(prof, mult=1.0, hp=100):
    segs = []
    for end, d in prof:
        n = max(1, math.ceil(hp / (d * (mult or 1)) - 1e-9))
        if segs and segs[-1][1] == n:
            segs[-1][0] = end
        else:
            segs.append([end, n])
    segs[-1][0] = None
    return segs

def profile_from_rows(rows, col=2):
    """Damage profile from a table (col 2 = post-patch, 1 = pre-patch), or None if incomplete or implausible."""
    v = {}
    for row in rows:
        key = LABELS.get(row[0].lower().strip(": "))
        if key:
            v[key] = num(row[col])
    if v.get("d0") is None or v.get("dmin") is None:
        return None, v
    prof = [[v.get("r0"), v["d0"]]]
    for k in (1, 2, 3, 4):
        if v.get(f"d{k}") is not None and v.get(f"r{k}") is not None:
            prof.append([v[f"r{k}"], v[f"d{k}"]])
    prof.append([None, v["dmin"]])
    ends = [e for e, _ in prof[:-1]]
    if any(e is None or not (0 < e < 300) for e in ends) or any(b <= a for a, b in zip(ends, ends[1:])):
        return None, v
    if any(not (5 <= d <= 400) for _, d in prof):
        return None, v
    return prof, v

def wz_segs(ttk, rpm, delay=0):
    """Warzone shots to kill per band from CODMunity's average TTKs (0-10, 10-40, 40-80, 80-120 m)."""
    bands = [(0, 10), (10, 40), (40, 80), (80, 120)]
    iv = 60000.0 / rpm
    segs = []
    def push(end, n):
        if segs and segs[-1][1] == n:
            segs[-1][0] = end
        else:
            segs.append([end, n])
    for (a, b), t in zip(bands, ttk):
        k = 1 + (t - delay) / iv
        whole = round(k)
        if abs(k - whole) <= .06:
            push(b, max(1, int(whole)))
        else:
            fl, frac = math.floor(k), k - math.floor(k)
            mid = round(a + (b - a) * (1 - frac), 1)
            push(mid, max(1, fl)); push(b, max(1, fl + 1))
    segs[-1][0] = None
    return segs

def direction(label: str, pre, post):
    a, b = num(pre), num(post)
    if a is None or b is None or a == b:
        return 0
    up_bad = re.search(r"recoil|ads time|sprint to fire|aim down sight time|reload time|flinch|sway|bloom", label, re.I)
    return (-1 if b > a else 1) if up_bad else (1 if b > a else -1)

def change_text(rows):
    parts = []
    for label, pre, post in rows:
        if pre.strip().lower() == post.strip().lower() or num(pre) == num(post):
            continue
        lab = label.lower().replace("maximum", "max").replace("minimum", "min").replace("medium", "mid").replace(" damage range", " range").replace("muzzle velocity", "bullet speed")
        parts.append(f"{lab} {pre} to {post}")
    return ", ".join(parts)[:180]

def bullet_type(text: str) -> str:
    t = text.lower()
    good = re.search(r"increased (max |min |mid )?(damage|range|fire rate|velocity|magazine)|reduced recoil|decreased recoil|improved|faster|reduced (ads|aim|sprint|reload)", t)
    bad = re.search(r"decreased (max |min |mid )?(damage|range|fire rate|velocity)|reduced (max |min |mid )?(damage|range|fire rate)|increased recoil|slower|increased (ads|aim down|sprint|reload)", t)
    return "buff" if good and not bad else "nerf" if bad and not good else "adjust"

# ------------------------------------------------------------------ apply
class Robot:
    def __init__(self, data: dict):
        self.d = data
        self.changes: list[str] = []
        self.problems: list[str] = []
        self.sources: dict[str, str] = {}
        self.by_norm = {}
        self._index()

    def _index(self):
        self.by_norm = {norm(w["name"]): w for w in self.d["weapons"]}
        for w in self.d["weapons"]:
            if w.get("fullName"):
                self.by_norm[norm(w["fullName"])] = w

    def weapon(self, name: str):
        n = norm(name)
        if n in self.by_norm:
            return self.by_norm[n]
        cands = [w for k, w in self.by_norm.items() if k.startswith(n) or n.startswith(k)]
        return cands[0] if len(cands) == 1 else None

    def apex_weapon(self, gun, title: str):
        name = re.sub(r"\s*apex attachment adjustments?.*$", "", title, flags=re.I).strip()
        n = norm(name.replace(gun["name"], "")) or norm(name)
        for w in self.d["weapons"]:
            if w.get("parent") == gun["id"] and (n in norm(w.get("name", "")) or n in norm(w.get("fullName", ""))):
                return w, name
        return None, name

    # ---- patch notes
    def apply_patches(self, sections):
        last = self.d["meta"].get("lastPatch") or "2000-01-01"
        newest = last
        for sec in sorted(sections, key=lambda s: s["date"]):
            if sec["date"] <= last or not sec["weapons"]:
                continue
            entry_changes = []
            for wb in sec["weapons"]:
                gun = self.weapon(wb["weapon"])
                if not gun:
                    self.problems.append(f"Patch {sec['date']}: unknown weapon '{wb['weapon']}' (it will be added when the weapon list has it)")
                    continue
                target, label = gun, gun["name"]
                if re.search(r"apex", wb["title"], re.I):
                    tw, apx = self.apex_weapon(gun, wb["title"])
                    if tw:
                        target, label = tw, tw["name"]
                    else:
                        txt = change_text(wb["rows"]) or (wb["bullets"][0] if wb["bullets"] else "")
                        if txt:
                            entry_changes.append([gun["id"], "adjust", clean(f"{apx} Apex: {txt}", 180)])
                        continue
                txt = change_text(wb["rows"])
                dirs = [direction(l, a, b) for l, a, b in wb["rows"]]
                if txt:
                    t = "buff" if dirs and all(x >= 0 for x in dirs) and any(x > 0 for x in dirs) else "nerf" if dirs and all(x <= 0 for x in dirs) and any(x < 0 for x in dirs) else "adjust"
                    entry_changes.append([target["id"], t, clean(txt[:1].upper() + txt[1:], 180)])
                    self._apply_numbers(target, wb["rows"], sec["date"])
                elif wb["bullets"]:
                    b = wb["bullets"][0]
                    entry_changes.append([target["id"], bullet_type(b), clean(b, 180)])
            if not entry_changes:
                continue
            ups = [W for W, t, _ in entry_changes if t == "buff"]
            downs = [W for W, t, _ in entry_changes if t == "nerf"]
            name = lambda i: next((w["name"] for w in self.d["weapons"] if w["id"] == i), i)
            summary = ", ".join(filter(None, [
                (f"{len(ups)} buff{'s' if len(ups) != 1 else ''} ({', '.join(name(i) for i in ups[:4])}{'…' if len(ups) > 4 else ''})" if ups else ""),
                (f"{len(downs)} nerf{'s' if len(downs) != 1 else ''} ({', '.join(name(i) for i in downs[:4])}{'…' if len(downs) > 4 else ''})" if downs else ""),
                (f"{len(entry_changes) - len(ups) - len(downs)} other changes" if len(entry_changes) - len(ups) - len(downs) else ""),
            ]))
            existing = next((p for p in self.d["patches"] if p.get("date") == sec["date"]), None)
            if existing:
                have = {c[0] for c in existing["changes"]}
                extra = [c for c in entry_changes if c[0] not in have]
                existing["changes"] += extra
                existing.setdefault("summary", summary)
            else:
                self.d["patches"].append({"date": sec["date"], "title": "Weapon tuning", "url": sec["url"], "summary": summary, "changes": entry_changes})
            self.changes.append(f"New patch notes for {short_date(sec['date'])}: {summary}")
            newest = max(newest, sec["date"])
        if newest > last:
            self.d["meta"]["lastPatch"] = newest

    def calibrate(self, w, rows):
        """Torso multiplier that makes the PRE-patch table reproduce today's shots to kill, or None.
        Patch tables often leave out unchanged multipliers, so this is how the robot proves it reads the gun right
        before changing anything."""
        pre, vpre = profile_from_rows(rows, 1)
        if not pre or not w.get("segs"):
            return None
        cur = [[None if e is None else round(e, 1), n] for e, n in w["segs"]]
        same = lambda sg: [[None if e is None else round(e, 1), n] for e, n in sg] == cur
        base = vpre.get("upper") or w.get("mult") or 1.0
        for m in sorted({round(1 + i * .01, 2) for i in range(0, 61)} | {base}, key=lambda x: abs(x - base)):
            if same(segs_from_profile(pre, m)):
                return m
        return None

    def _apply_numbers(self, w, rows, date):
        prof, v = profile_from_rows(rows)
        changed = []
        if w.get("cls") == "Shotgun":
            prof = None  # shotgun tables are per pellet; text only
        if prof:
            m = self.calibrate(w, rows)
            if m is None:
                self.problems.append(f"{w['name']}: couldn't confirm the {short_date(date)} damage numbers against today's data, left as they were")
                prof = None
            else:
                _, vpre = profile_from_rows(rows, 1)
                w["mult"] = v["upper"] if v.get("upper") and vpre.get("upper") and abs(vpre["upper"] - m) < .015 else m
        if v.get("head") and 1 <= v["head"] <= 4 and v["head"] != w.get("head"):
            w["head"] = v["head"]; changed.append("head")
        if v.get("vel") and 200 <= v["vel"] <= 2500:
            w["vel"] = round(v["vel"]); changed.append("velocity")
        if v.get("rpm") and 30 <= v["rpm"] <= 2500:
            w["rpm"] = v["rpm"]; changed.append("fire rate")
        if prof:
            segs = segs_from_profile(prof, w.get("mult", 1))
            if segs != w.get("segs"):
                w["segs"] = segs
                if w.get("conf") != "high":
                    w["conf"] = "med"
                changed.append("damage")
            w["dmg"] = prof
        if changed:
            w["note"] = clean(f"{short_date(date)}: {change_text(rows)}", 200)
            w["patched"] = date

    # ---- new guns and unlock levels
    def apply_weapon_list(self, wl, cm):
        cm_names = {c["norm"]: c for c in cm}
        known = set(self.by_norm)
        added = 0
        for g in wl:
            if g["norm"] in known or any(k.startswith(g["norm"]) or g["norm"].startswith(k) for k in known if len(k) >= 4):
                w = self.weapon(g["name"])
                if w and w.get("unlock") in (None, "", "Unknown") and 1 <= g["unlock"] <= 99:
                    w["unlock"] = f"Level {g['unlock']}"; self.changes.append(f"{w['name']}: unlock level {g['unlock']}")
                continue
            if added >= 4:
                self.problems.append(f"More new guns than expected ({g['name']} skipped this run)")
                continue
            if not re.fullmatch(r"[A-Za-z0-9 .\-+'/]{2,40}", g["name"]) or g["cls"] not in CLASSES:
                self.problems.append(f"Skipped odd weapon name {g['name']!r}")
                continue
            name = cm_names.get(g["norm"], {}).get("name") or g["name"]
            gid = slug(name)
            if any(w["id"] == gid for w in self.d["weapons"]):
                continue
            self.d["weapons"].append({"id": gid, "name": name, "cls": g["cls"], "unlock": f"Level {g['unlock']}" if 1 <= g["unlock"] <= 99 else "Unknown",
                                      "season": self.d["meta"].get("season", ""), "added": today_local(), "conf": "low", "hEst": True, "apexes": [],
                                      "note": "New gun: class-typical numbers until damage data is published."})
            self.changes.append(f"New gun added: {name} ({g['cls']})")
            added += 1
            self._index(); known = set(self.by_norm)

    # ---- Warzone kill times
    def apply_wz(self, cm):
        n = 0
        for c in cm:
            w = self.weapon(c["name"])
            if not w or w.get("parent"):
                continue
            ttk = c["ttk"]
            if not all(80 <= t <= 8000 for t in ttk) or any(b < a - 5 for a, b in zip(ttk, ttk[1:])):
                self.problems.append(f"Warzone TTK for {w['name']} looks wrong {ttk}, skipped")
                continue
            wz = w.get("wz") or {}
            if wz.get("ttk") == ttk:
                continue
            rpm = w.get("rpm") or 0
            if not rpm:
                continue
            wz.update({"ttk": ttk, "segs": wz_segs(ttk, rpm, w.get("delay") or 0), "conf": wz.get("conf", "med"), "src": f"CODMunity Warzone TTK, {short_date(today_local())}"})
            wz.setdefault("vel", 880); wz.setdefault("velEst", True); wz.setdefault("hitscan", 45)
            w["wz"] = wz
            n += 1
        if n:
            self.d["meta"]["wzSource"] = f"CODMunity Warzone TTK (300 HP target), updated {today_local()}"
            self.changes.append(f"Warzone kill times updated for {n} gun{'s' if n != 1 else ''}")

    # ---- store
    def apply_shop(self, bundles):
        shop = self.d.get("shop") or {}
        old = [b.get("name") for b in shop.get("bundles", [])]
        new = [b["name"] for b in bundles]
        if old == new and shop.get("date") == today_local():
            return
        hist = [h for h in shop.get("history", []) if h.get("date") != today_local()][-59:]
        hist.append({"date": today_local(), "names": new})
        self.d["shop"] = {"date": today_local(), "source": "itemshop.gg", "url": "https://itemshop.gg/call-of-duty", "bundles": bundles, "history": hist}
        self.d["meta"]["shopDate"] = today_local()
        if set(old) != set(new):
            self.changes.append(f"Store refreshed: {len(new)} bundles ({len(set(new) - set(old))} new)")

    # ---- Apex attachments (only when the gun is unmistakable)
    def apply_apex(self, apexes):
        gun_words = {norm(t) for w in self.d["weapons"] for t in re.split(r"[\s\-]+", w["name"]) if norm(t)}
        core = lambda name: frozenset(t for t in (norm(x) for x in re.split(r"[\s\-]+", name)) if t and t not in gun_words and not t.isdigit())
        names = [a.get("name", "") for w in self.d["weapons"] for a in (w.get("apexes") or [])] + [w.get("apex", "") for w in self.d["weapons"] if w.get("apex")] + [w["name"].replace(" (Apex)", "") for w in self.d["weapons"] if w.get("parent")] + [w.get("fullName", "").split(" + ")[-1] for w in self.d["weapons"] if w.get("fullName")]
        have = {norm(x) for x in names if x}
        cores = {core(x) for x in names if x and core(x)}
        added = 0
        for ax in apexes:
            n = norm(ax["name"])
            if n in have or (core(ax["name"]) and core(ax["name"]) in cores):
                continue
            first = norm(ax["name"].split()[0])
            guns = [w for w in self.d["weapons"] if not w.get("parent") and norm(w["name"]).startswith(first) and len(first) >= 2]
            full = [w for w in guns if n.startswith(norm(w["name"]))]
            gun = full[0] if len(full) == 1 else guns[0] if len(guns) == 1 else None
            if not gun:
                self.problems.append(f"New Apex spotted but its gun is unclear: {ax['name']}")
                continue
            if added >= 3:
                self.problems.append(f"Several new Apex attachments at once; {ax['name']} left for next run")
                continue
            gun.setdefault("apexes", []).append({"id": slug(ax["name"]), "name": clean(ax["name"], 40), "desc": "", "blocks": [], "unlock": f"Weapon level {ax['level']}" if 1 <= ax["level"] <= 120 else "", "added": today_local()})
            have.add(n); cores.add(core(ax["name"])); added += 1
            self.changes.append(f"New Apex for the {gun['name']}: {ax['name']}")

    # ---- run everything
    def run(self, fetcher=fetch):
        steps = []
        def step(key, fn):
            try:
                fn(); self.sources[key] = "ok"
            except Exception as e:
                self.sources[key] = "failed"
                self.problems.append(f"{key}: {str(e)[:200]}")
        pages = {}
        def get_patches():
            urls = [SOURCES["patch_s1"]]
            try:
                urls = sorted(set(urls + find_patch_pages(fetcher(SOURCES["patch_index"]))), reverse=True)[:4]
            except Exception as e:
                self.problems.append(f"patch index: {str(e)[:120]}")
            secs = []
            for u in urls:
                try:
                    secs += parse_patch_page(fetcher(u), u)
                except Exception as e:
                    self.problems.append(f"patch page {u.rsplit('/', 1)[-1]}: {str(e)[:120]}")
            if not secs:
                raise ValueError("no dated sections found")
            pages["patch"] = secs
        step("patch_notes", get_patches)
        wl, cm = [], []
        def get_wl():
            nonlocal wl
            wl = parse_wzstats(fetcher(SOURCES["wzstats"]))
        def get_cm():
            nonlocal cm
            cm = parse_codmunity_wz(fetcher(SOURCES["codmunity_wz"]))
        step("weapon_list", get_wl)
        step("warzone_ttk", get_cm)
        if wl:
            step("new_guns", lambda: self.apply_weapon_list(wl, cm))
        if "patch" in pages:
            step("apply_patches", lambda: self.apply_patches(pages["patch"]))
        if cm:
            step("apply_warzone", lambda: self.apply_wz(cm))
        step("shop", lambda: self.apply_shop(parse_shop(fetcher(SOURCES["shop"]))))
        step("apex", lambda: self.apply_apex(parse_apex(fetcher(SOURCES["apex"]))))
        return self

    def finish(self):
        if self.changes:
            m = self.d["meta"]
            m["dataDate"] = today_local()
            m["updatedAt"] = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
            log = self.d.get("robotLog") or []
            log.append({"at": m["updatedAt"], "changes": self.changes[:20]})
            self.d["robotLog"] = log[-30:]
        return self.d


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    before = open(path, encoding="utf-8").read()
    data = json.loads(before)
    r = Robot(data).run()
    out = r.finish()
    if r.changes:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    os.makedirs(".robot", exist_ok=True)
    with open(".robot/report.json", "w") as f:
        json.dump({"changes": r.changes, "problems": r.problems, "sources": r.sources}, f, indent=1)
    print("CHANGES:", *r.changes, sep="\n  ")
    print("PROBLEMS:", *r.problems, sep="\n  ")
    print("SOURCES:", r.sources)


if __name__ == "__main__":
    main()
