"""Tests for the data robot. They run on GitHub before every update; if any fails, nothing is changed."""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import robot  # noqa: E402
import validate_data  # noqa: E402

FX = lambda n: open(os.path.join(HERE, "fixtures", n), encoding="utf-8").read()
DATA = json.load(open(os.path.join(HERE, "..", "..", "data.json"), encoding="utf-8"))


def fake_fetch(url):
    m = {robot.SOURCES["patch_s1"]: "patch.html", robot.SOURCES["wzstats"]: "wzstats.html", robot.SOURCES["codmunity_wz"]: "codmunity.html", robot.SOURCES["shop"]: "shop.html", robot.SOURCES["apex"]: "apex.html"}
    if url == robot.SOURCES["patch_index"]:
        return "<html></html>"
    return FX(m[url])


class Math(unittest.TestCase):
    def test_segs(self):
        self.assertEqual(robot.segs_from_profile([[35.56, 30], [None, 25]]), [[None, 4]])
        self.assertEqual(robot.segs_from_profile([[13.34, 19], [21.34, 16], [None, 14]], 1.06), [[13.34, 5], [21.34, 6], [None, 7]])

    def test_profile_rejects_nonsense(self):
        self.assertIsNone(robot.profile_from_rows([("Max Damage", "30", "30"), ("Max Damage Range", "40 m", "40 m"), ("Mid Damage 1", "25", "25"), ("Mid Damage Range 1", "20 m", "20 m"), ("Min Damage", "20", "20")])[0])
        self.assertIsNone(robot.profile_from_rows([("Max Damage", "30", "3000"), ("Max Damage Range", "40 m", "40 m"), ("Min Damage", "20", "20")])[0])
        self.assertIsNone(robot.profile_from_rows([("Min Damage", "20", "21")])[0])

    def test_wz_segs(self):
        s = robot.wz_segs([558, 558, 671, 782], 645)
        self.assertIsNone(s[-1][0]); self.assertTrue(all(isinstance(n, int) for _, n in s))

    def test_clean(self):
        self.assertEqual(robot.clean('<b>Hi</b> "there" <script>x</script>'), "Hi there")
        self.assertNotIn("<", robot.clean("a<b"))


class Parsers(unittest.TestCase):
    def test_patch(self):
        secs = robot.parse_patch_page(FX("patch.html"), "https://www.callofduty.com/patchnotes/x")
        self.assertEqual(secs[0]["date"], "2026-12-02")
        names = [w["weapon"] for w in secs[0]["weapons"]]
        self.assertEqual(names, ["Patriot XMR", "Hyeon Burst", "Oden", "CSG-35"])
        self.assertEqual(secs[0]["weapons"][0]["rows"][0], ("Max Damage", "30", "31"))
        self.assertEqual(secs[-1]["date"], "2026-11-19")

    def test_codmunity_only_mw4(self):
        rows = robot.parse_codmunity_wz(FX("codmunity.html"))
        self.assertNotIn("gremlin", [r["norm"] for r in rows])
        self.assertEqual(rows[0]["ttk"], [558, 558, 671, 782])

    def test_wzstats(self):
        ws = robot.parse_wzstats(FX("wzstats.html"))
        self.assertIn("ferro9", [w["norm"] for w in ws])
        self.assertNotIn("kastov545", [w["norm"] for w in ws])  # variants are not new guns
        self.assertEqual(next(w for w in ws if w["norm"] == "ferro9")["cls"], "SMG")

    def test_shop_is_safe(self):
        b = robot.parse_shop(FX("shop.html"))
        self.assertEqual([x["name"] for x in b][:2], ["Deadly Grounds", "Drone Out"])
        self.assertIsNone(b[1]["url"])  # link to another site dropped
        self.assertTrue(all("<" not in x["name"] for x in b))
        self.assertIsNone(b[2]["price"])  # 0 CP is not a real price
        self.assertNotIn("Other Game", [x["name"] for x in b])

    def test_apex(self):
        self.assertEqual(len(robot.parse_apex(FX("apex.html"))), 5)


class EndToEnd(unittest.TestCase):
    def run_robot(self, last="2026-11-19"):
        d = copy.deepcopy(DATA); d["meta"]["lastPatch"] = last
        r = robot.Robot(d).run(fake_fetch); r.finish()
        return d, r

    def test_full_run_passes_the_data_check(self):
        d, r = self.run_robot()
        self.assertEqual(validate_data.check(d, DATA), [])
        self.assertTrue(r.changes)

    def test_patch_applied_only_when_confirmed(self):
        d, r = self.run_robot()
        w = {x["id"]: x for x in d["weapons"]}
        self.assertEqual(w["patriot-xmr"]["segs"], [[None, 4]])  # 31/26 damage is still 4 shots
        self.assertEqual(d["meta"]["lastPatch"], "2026-12-02")
        p = next(p for p in d["patches"] if p["date"] == "2026-12-02")
        kinds = {c[0]: c[1] for c in p["changes"]}
        self.assertEqual(kinds["patriot-xmr"], "buff"); self.assertEqual(kinds["oden"], "nerf")
        self.assertIn("hyeon-auto", kinds)  # Apex table goes to the Apex gun
        self.assertTrue(p["summary"])
        # CSG-35's sample table does not match today's numbers, so its damage must stay untouched
        self.assertEqual(w["csg-35"]["segs"], {x["id"]: x for x in DATA["weapons"]}["csg-35"]["segs"])
        self.assertTrue(any("CSG-35" in x for x in r.problems))

    def test_old_sections_ignored(self):
        d, r = self.run_robot(last="2026-12-02")
        self.assertFalse(any("patch notes" in c for c in r.changes))

    def test_new_gun_and_apex(self):
        d, r = self.run_robot()
        self.assertIn("ferro-9", [w["id"] for w in d["weapons"]])
        ax = [a["name"] for w in d["weapons"] for a in w.get("apexes", [])]
        self.assertIn("Axion Reaver", ax)
        self.assertNotIn("Mojave .357 Lawless", ax)  # same as the known Mojave Lawless
        self.assertNotIn("Signal 50 Inferno", ax)
        self.assertTrue(any("Cronen Storm" in p for p in r.problems))  # two Cronen guns: not guessed

    def test_shop_and_log(self):
        d, r = self.run_robot()
        self.assertEqual(d["shop"]["bundles"][0]["name"], "Deadly Grounds")
        self.assertTrue(d["robotLog"][-1]["changes"])
        self.assertTrue(d["meta"]["updatedAt"].endswith("Z"))

    def test_source_failure_changes_nothing_else(self):
        def broken(url):
            if "itemshop" in url: raise RuntimeError("down")
            return fake_fetch(url)
        d = copy.deepcopy(DATA); r = robot.Robot(d).run(broken)
        self.assertEqual(r.sources["shop"], "failed")
        self.assertEqual(d["shop"], DATA["shop"])

    def test_blocked_hosts(self):
        with self.assertRaises(ValueError):
            robot.fetch("http://www.callofduty.com/x")
        with self.assertRaises(ValueError):
            robot.fetch("https://evil.example/x")


class DataCheck(unittest.TestCase):
    def test_rejects_unsafe_and_lost_data(self):
        d = copy.deepcopy(DATA); d["weapons"][0]["name"] = "<img src=x onerror=alert(1)>"
        self.assertTrue(validate_data.check(d, DATA))
        d = copy.deepcopy(DATA); d["weapons"].pop()
        self.assertTrue(any("removed" in e for e in validate_data.check(d, DATA)))
        d = copy.deepcopy(DATA); d["shop"]["bundles"][0]["url"] = "https://evil.example"
        self.assertTrue(validate_data.check(d, DATA))
        d = copy.deepcopy(DATA); d["weapons"][0]["segs"] = [[10, 3], [5, 4], [None, 5]]
        self.assertTrue(validate_data.check(d, DATA))

    def test_current_data_passes(self):
        self.assertEqual(validate_data.check(DATA, DATA), [])


if __name__ == "__main__":
    unittest.main()
