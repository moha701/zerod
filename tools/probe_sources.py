"""Look at the public pages the updater reads and print their structure (GitHub Action probe mode)."""
import json, re, sys, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
def fetch(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "text/html,*/*", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode("utf-8", "replace")
def around(s, needle, before=300, after=1500, n=1, label=""):
    i = -1
    for k in range(n):
        i = s.find(needle, i + 1)
        if i < 0: print(f"  [{label}] '{needle}' not found"); return
        print(f"  [{label}] around '{needle}' #{k+1}:\n" + s[max(0, i - before): i + after].replace("\n", "\\n")[:before + after] + "\n")
def json_scripts(html):
    for m in re.finditer(r'<script([^>]*)>(.*?)</script>', html, re.S):
        attrs, body = m.group(1), m.group(2)
        if len(body) > 2000 and ("json" in attrs or body.strip()[:1] in "{[" or "__" in body[:60]):
            print("   script attrs", attrs.strip()[:120], "len", len(body), "start", body.strip()[:200].replace("\n", " "))

print("#### CALLOFDUTY")
h = fetch("https://www.callofduty.com/patchnotes/2026/11/call-of-duty-modern-warfare-4-season-1-patch-notes")
around(h, "Damage Profiles", 2500, 4000, 1, "cod")
around(h, "November 19, 2026", 800, 1500, 2, "cod-date")
around(h, "November 13, 2026", 300, 800, 1, "cod-date2")
print("  h-tags:", re.findall(r"<h[1-4][^>]*>([^<]{3,90})</h[1-4]>", h)[:60])
print("  classes:", sorted(set(re.findall(r'class="([a-z0-9_\- ]{3,60})"', h)))[:120])

print("#### CODMUNITY TTK")
h = fetch("https://codmunity.gg/ttk/warzone")
json_scripts(h)
around(h, "Patriot XMR", 1500, 2500, 1, "cm")
i = h.find('"Patriot XMR"'); print("  quoted name idx", i)
if i > 0: print("  quoted ctx:", h[max(0, i - 1500): i + 1500].replace("\n", "\\n"))
print("  mw4 tag count:", h.count(">MW4<"), "names with tags sample:", re.findall(r">([A-Z][A-Za-z0-9 .\-]{2,24})<[^>]*>\s*<[^>]*>MW4<", h)[:10])

print("#### WZSTATS MW4 MP")
h = fetch("https://wzstats.gg/mw4/multiplayer/stats")
json_scripts(h)
for nd in ["ng-state", "serverApp-state", "transfer-state", "__NUXT", "__NEXT", "window.__"]:
    print("  marker", nd, h.find(nd))
around(h, "Lower Legs", 3000, 1500, 1, "wz")
i = h.find("cronen-osprey"); print("  slug idx", i, h[max(0, i - 600): i + 1400].replace("\n", "\\n") if i > 0 else "")

print("#### ITEMSHOP")
h = fetch("https://itemshop.gg/call-of-duty")
m = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', h, re.S)
for c in m:
    if '"sections"' in c or '\\"sections\\"' in c:
        t = c.encode().decode("unicode_escape", "ignore")
        i = t.find('"cards"'); print("  cards ctx:", t[i: i + 3500]); break
around(h, "CP", 600, 400, 1, "shop-cp")
