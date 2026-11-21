"""Look at the public pages the updater reads and print their structure (run by the GitHub Action in probe mode)."""
import json, re, sys, urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
URLS = sys.argv[1:] or [
    "https://www.callofduty.com/patchnotes/2026/11/call-of-duty-modern-warfare-4-season-1-patch-notes",
    "https://www.callofduty.com/patchnotes",
    "https://codmunity.gg/ttk/warzone",
    "https://codmunity.gg/ttk/multiplayer",
    "https://codmunity.gg/ttk",
    "https://codmunity.gg/weapon-stats/warzone",
    "https://codmunity.gg/weapon-stats/multiplayer",
    "https://wzstats.gg/mw4/multiplayer/stats",
    "https://wzstats.gg/mw4/warzone/stats",
    "https://itemshop.gg/call-of-duty",
    "https://warzoneloadout.games/mw4/attachments/apex",
]
GUNS = ["Patriot XMR", "Kastov 762", "Hyeon Burst", "CSG-35", "PPSh-41", "Cronen Osprey", "M4"]

def fetch(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "text/html,application/json;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")

def tree(o, depth=0, maxd=4, path=""):
    out = []
    if depth > maxd: return out
    if isinstance(o, dict):
        for k, v in list(o.items())[:25]:
            t = type(v).__name__ + (f"[{len(v)}]" if isinstance(v, (list, dict, str)) else "")
            out.append("  " * depth + f"{k}: {t}" + (f" = {v[:60]!r}" if isinstance(v, str) else f" = {v}" if isinstance(v, (int, float, bool)) else ""))
            out += tree(v, depth + 1, maxd, path + "." + k)
    elif isinstance(o, list) and o:
        out.append("  " * depth + f"[0] of {len(o)}: {type(o[0]).__name__}")
        out += tree(o[0], depth + 1, maxd, path + "[0]")
    return out

def find_paths(o, needle, path="$", hits=None):
    hits = [] if hits is None else hits
    if len(hits) > 6: return hits
    if isinstance(o, dict):
        for k, v in o.items(): find_paths(v, needle, f"{path}.{k}", hits)
    elif isinstance(o, list):
        for i, v in enumerate(o[:400]): find_paths(v, needle, f"{path}[{i}]", hits)
    elif isinstance(o, str) and needle.lower() in o.lower():
        hits.append(path)
    return hits

for u in URLS:
    print("=" * 100); print("URL", u)
    try:
        st, final, html = fetch(u)
    except Exception as e:
        print("  FAIL", repr(e)[:300]); continue
    print("  status", st, "final", final, "bytes", len(html))
    t = re.search(r"<title[^>]*>(.*?)</title>", html, re.S); print("  title", (t.group(1).strip()[:120] if t else None))
    nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if nd:
        try:
            j = json.loads(nd.group(1)); print("  __NEXT_DATA__ found, bytes", len(nd.group(1)))
            print("\n".join("   " + l for l in tree(j, maxd=5)[:140]))
            for g in GUNS[:3]: print("  path for", g, find_paths(j, g)[:4])
        except Exception as e: print("  NEXT_DATA parse fail", e)
    nuxt = re.search(r"window\.__NUXT__|__NUXT_DATA__", html); print("  nuxt:", bool(nuxt))
    pushes = re.findall(r"self\.__next_f\.push", html); print("  next app-router chunks:", len(pushes))
    apis = sorted(set(re.findall(r"https?://[a-zA-Z0-9.\-]*(?:api|cdn|data)[a-zA-Z0-9.\-]*/[^\"'\\\s<>)]{0,120}", html)))[:25]
    print("  api-ish urls:", apis)
    jsons = sorted(set(re.findall(r"[\"'](/[^\"'\s]{0,80}\.json)[\"']", html)))[:15]; print("  json paths:", jsons)
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text); text = re.sub(r"\n\s*\n+", "\n", text)
    for g in GUNS:
        i = text.find(g)
        if i >= 0: print(f"  text near {g!r}:", repr(text[max(0, i - 150): i + 450])); break
    if "callofduty.com" in u:
        dates = re.findall(r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d\d", text)
        print("  dates on page:", dates[:20])
        links = sorted(set(re.findall(r'href="(/patchnotes/20\d\d/\d\d/[^"]+)"', html)))[:30]; print("  patch links:", links)
    # app-router payload sample
    if pushes:
        m = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
        big = sorted(m, key=len, reverse=True)[:2]
        for b in big: print("  chunk sample:", b[:1500].encode().decode("unicode_escape", "ignore")[:1500])
