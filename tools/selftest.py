#!/usr/bin/env python3
"""Reads the site's self-test result (Chrome loaded index.html?robot=1 with the new data.json)
and saves a tier snapshot so the site can show tier moves since the last patch.
Usage: selftest.py DOM.html data.json   -> exits 1 if the site could not run with the new data."""
import datetime as dt
import html
import json
import re
import sys

dom = open(sys.argv[1], encoding="utf-8", errors="replace").read()
m = re.search(r'<pre id="robotOut"[^>]*>(.*?)</pre>', dom, re.S)
if not m:
    print("SELF-TEST FAILED: the site did not produce a result (it may have crashed with the new data)")
    sys.exit(1)
out = json.loads(html.unescape(m.group(1)))
if not out.get("ok"):
    print("SELF-TEST FAILED:", json.dumps(out)[:800])
    sys.exit(1)
print("self-test passed:", json.dumps(out.get("checks")))
path = sys.argv[2]
data = json.load(open(path, encoding="utf-8"))
t = out.get("tiers") or {}
snap = {"date": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=4)).date().isoformat(), "dataDate": data["meta"].get("dataDate")}
for k in ("mp", "ranked", "wzL", "wzC"):
    ids = [i for i in t.get(k, []) if isinstance(i, str) and re.fullmatch(r"[a-z0-9\-]{1,60}", i)]
    if ids:
        snap[k] = ids[:80]
hist = data.get("tierHistory") or []
last = hist[-1] if hist else None
if not last or any(last.get(k) != snap.get(k) for k in ("mp", "ranked", "wzL", "wzC")):
    hist = [h for h in hist if h.get("date") != snap["date"]] + [snap]
    data["tierHistory"] = hist[-40:]
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("tier snapshot saved for", snap["date"])
