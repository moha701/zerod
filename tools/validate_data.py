#!/usr/bin/env python3
"""Checks data.json before the robot is allowed to save it.

Usage: validate_data.py NEW.json [OLD.json]
Exits 1 (and prints why) if anything looks wrong, so a bad update never reaches the site.
"""
import json
import re
import sys

CLASSES = {"AR", "SMG", "LMG", "Marksman", "Sniper", "Shotgun", "Pistol"}
URL_HOSTS = ("https://www.callofduty.com/", "https://itemshop.gg/", "https://codmunity.gg/", "https://wzstats.gg/", "https://warzoneloadout.games/", "https://www.dexerto.com/")
BAD_TEXT = re.compile(r"<\s*/?\s*(script|iframe|object|embed|img|svg|style|link|meta)|javascript:|data:text|on[a-z]+\s*=", re.I)
ID = re.compile(r"^[a-z0-9][a-z0-9\-]{0,60}$")


def walk_strings(o, path="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def check(new, old=None):
    errs = []
    def err(m):
        errs.append(m)
    for k in ("meta", "weapons", "attachments", "patches", "shop", "maps", "modes", "playstyles", "profiles"):
        if k not in new:
            err(f"missing top-level '{k}'")
    if errs:
        return errs
    raw = json.dumps(new)
    if len(raw) > 3_000_000:
        err("data.json is over 3 MB")
    for p, s in walk_strings(new):
        if BAD_TEXT.search(s):
            err(f"unsafe text at {p}: {s[:60]!r}")
        if len(s) > 2000:
            err(f"text too long at {p}")
    ids = set()
    for w in new["weapons"]:
        wid = w.get("id", "")
        if not ID.match(wid):
            err(f"bad weapon id {wid!r}")
        if wid in ids:
            err(f"duplicate weapon id {wid}")
        ids.add(wid)
        if not isinstance(w.get("name"), str) or not (1 <= len(w["name"]) <= 60):
            err(f"{wid}: bad name")
        if w.get("cls") not in CLASSES:
            err(f"{wid}: bad class {w.get('cls')!r}")
        segs = w.get("segs")
        if segs is not None:
            if not isinstance(segs, list) or not segs:
                err(f"{wid}: empty segs")
            else:
                prev = 0
                for i, sg in enumerate(segs):
                    if not (isinstance(sg, list) and len(sg) == 2 and isinstance(sg[1], int) and 1 <= sg[1] <= 25):
                        err(f"{wid}: bad seg {sg}"); break
                    end = sg[0]
                    if i < len(segs) - 1:
                        if not isinstance(end, (int, float)) or not (prev < end < 300):
                            err(f"{wid}: seg ends not increasing {segs}"); break
                        prev = end
                    elif end is not None:
                        err(f"{wid}: last seg must be open-ended")
        for k, lo, hi in (("rpm", 20, 2600), ("mag", 1, 500), ("vel", 100, 3000), ("ads", 50, 1500), ("stf", 30, 1500), ("head", 1, 5), ("mult", .5, 3)):
            if w.get(k) is not None and not (isinstance(w[k], (int, float)) and lo <= w[k] <= hi):
                err(f"{wid}: {k}={w[k]!r} outside {lo}-{hi}")
        wz = w.get("wz")
        if wz:
            t = wz.get("ttk")
            if t is not None and not (isinstance(t, list) and len(t) == 4 and all(isinstance(x, (int, float)) and 50 <= x <= 9000 for x in t)):
                err(f"{wid}: bad Warzone ttk {t}")
        if w.get("parent") and w["parent"] not in {x.get("id") for x in new["weapons"]}:
            err(f"{wid}: parent {w['parent']} missing")
    for b in new["shop"].get("bundles", []):
        if b.get("url") and not str(b["url"]).startswith(URL_HOSTS):
            err(f"shop link not allowed: {b['url']}")
        if b.get("price") is not None and not (isinstance(b["price"], (int, float)) and 0 < b["price"] <= 20000):
            err(f"shop price odd: {b}")
    if len(new["shop"].get("bundles", [])) > 150:
        err("too many shop bundles")
    for p in new["patches"]:
        if not re.match(r"^20\d\d-\d\d-\d\d$", str(p.get("date", ""))):
            err(f"bad patch date {p.get('date')}")
        if p.get("url") and not str(p["url"]).startswith(URL_HOSTS):
            err(f"patch link not allowed: {p['url']}")
        for c in p.get("changes", []):
            if not (isinstance(c, list) and len(c) == 3 and c[1] in ("buff", "nerf", "adjust", "new")):
                err(f"bad patch change {c}")
            elif c[0] != "*" and c[0] not in ids:
                err(f"patch change for unknown gun {c[0]}")
    if old:
        oldids = {w["id"] for w in old["weapons"]}
        gone = oldids - ids
        if gone:
            err(f"guns removed: {sorted(gone)}")
        if len(new["weapons"]) - len(old["weapons"]) > 6:
            err("more than 6 new guns in one update")
        ow = {w["id"]: w for w in old["weapons"]}
        seg_changes = [w["id"] for w in new["weapons"] if w["id"] in ow and w.get("segs") != ow[w["id"]].get("segs")]
        new_patch = new["meta"].get("lastPatch") != old["meta"].get("lastPatch")
        if len(seg_changes) > (40 if new_patch else 3):
            err(f"too many damage changes at once without a new patch: {seg_changes}")
        if len(new["patches"]) < len(old["patches"]):
            err("patch history shrank")
    return errs


def main():
    new = json.load(open(sys.argv[1], encoding="utf-8"))
    old = json.load(open(sys.argv[2], encoding="utf-8")) if len(sys.argv) > 2 else None
    errs = check(new, old)
    if errs:
        print("DATA CHECK FAILED:")
        for e in errs[:40]:
            print("  -", e)
        sys.exit(1)
    print("data check passed:", len(new["weapons"]), "guns,", len(new["patches"]), "patches,", len(new["shop"].get("bundles", [])), "bundles")


if __name__ == "__main__":
    main()
