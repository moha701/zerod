"""Save raw copies of the source pages so parsers can be written against real HTML (probe mode only)."""
import os, urllib.request
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
SRC = {
    "cod_s1.html": "https://www.callofduty.com/patchnotes/2026/11/call-of-duty-modern-warfare-4-season-1-patch-notes",
    "cod_index.html": "https://www.callofduty.com/patchnotes",
    "cm_wz.html": "https://codmunity.gg/ttk/warzone",
    "wzs_mp.html": "https://wzstats.gg/mw4/multiplayer/stats",
    "shop.html": "https://itemshop.gg/call-of-duty",
    "apex.html": "https://warzoneloadout.games/mw4/attachments/apex",
    "cm_mp.html": "https://codmunity.gg/ttk/mw4",
    "cm_stats.html": "https://codmunity.gg/weapon-stats/mw4",
    "cm_gun.html": "https://codmunity.gg/weapon/mw4/hyeon-burst",
}
os.makedirs("probe", exist_ok=True)
for f, u in SRC.items():
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
        with urllib.request.urlopen(req, timeout=30) as r: b = r.read()
        open("probe/" + f, "wb").write(b); print("saved", f, len(b))
    except Exception as e: print("fail", f, e)
