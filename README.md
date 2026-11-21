# ZEROED: MW4 gun lab

A fan-made Call of Duty: Modern Warfare 4 multiplayer tool. Pick your gameplay style, map, mode and aim, and it builds every gun for that match, then ranks them by their chance to win 1v1s against the strongest guns there. Every number can be checked on the How it works page. Not affiliated with Activision or Infinity Ward.

## Put it online with GitHub Pages
1. Create a new repository on GitHub (for example `zeroed`).
2. Upload everything in this folder: `index.html`, `data.json`, `.nojekyll` and this README.
3. Go to **Settings → Pages**, set **Source** to *Deploy from a branch*, pick `main` and `/ (root)`, then **Save**.
4. After a minute your site is live at `https://YOUR-NAME.github.io/zeroed/`.

## How the data updates
- The page loads `data.json` from this folder. If it can't, it uses the copy built into `index.html`, so the site always works.
- To update stats, the shop or patch notes, edit `data.json` and bump `meta.dataDate`. Weapons use `segs` = chest shots-to-kill by distance (players have 100 health): `[[range_end_m, shots], ..., [null, shots]]`, or `dmg` = damage by distance plus `mult` (upper-torso multiplier) and the site works shots to kill out itself.
- A gun can list several Apex attachments in `apexes` (`id`, `name`, `desc`, `blocks`, `unlock`, optional `stats` = id of the converted gun's entry).
- New guns, attachments, Apex attachments and maps can be added with only the numbers that are known: the site fills the rest with class-typical values, labels them as estimates, and adds everything to the rankings, Gunsmith, 3D models and coach.
- Automatic updates: connect GitHub to Claude, and the twice-daily update task can commit a fresh `data.json` here for you.

## Install it like an app
Open the site on your phone, then use **Install app** in the More menu (Android/Chrome) or **Share → Add to Home Screen** (iPhone). It works offline with the last data it downloaded.

## What's inside
Best gun finder for Multiplayer and Warzone (map, mode, playstyle, aim, fight distance, enemy skill, level, Hardcore) with win rates, 1v2 odds, smart builds, Warzone two-gun loadouts and what-if checks · Squad builder · Aim test · Match log · Weapon levels · Events with countdowns · Search (Ctrl+K) · Arabic · Kill race animation · Gunsmith with detailed 3D models · Create a class with share codes · Compare · Shots-to-kill sheet · Maps & modes · Patch notes · Shop · Camo tracker · Unlock planner · Class roulette · AI coach (calculator mode on GitHub) · How it works.

Camo progress and saved classes are stored in your browser on GitHub Pages.

## Creator

ZEROED is made by **@mhmd8p2**. Follow on Instagram: https://instagram.com/mhmd8p2

## The data robot (no Claude needed)

`.github/workflows/update-data.yml` runs on GitHub's servers every 3 hours. Each run it:

1. Runs its own tests (`tools/tests`). If any test fails, it stops.
2. Reads the official MW4 patch notes (callofduty.com), the WZStats MW4 weapon list, CODMunity's Warzone TTK table, itemshop.gg and the Apex list on warzoneloadout.games (`tools/robot.py`).
3. Adds new patch entries with a plain-English summary, updates gun damage, ranges and head multipliers, adds new guns and Apex attachments, updates Warzone kill times and refreshes the store.
4. Checks every value against safe limits (`tools/validate_data.py`).
5. Opens the site with the new data in headless Chrome and makes sure the rankings and coach still work (`?robot=1`, `tools/selftest.py`). This also saves a tier snapshot so the tier list can show moves since the last patch.
6. Only then commits `data.json`. The site picks it up by itself.

If a source changes its layout or a number can't be confirmed, the robot leaves that part alone and opens one issue called **"ZEROED robot needs a look"**. It closes that issue by itself once everything reads fine again.

You can start a run any time from the Actions tab (Update data → Run workflow).

## Security

- No passwords, keys or personal tokens are stored anywhere. Each run uses GitHub's temporary `GITHUB_TOKEN`, which only works on this repo and expires when the run ends.
- The workflow only runs on its schedule or when someone with write access starts it. It never runs code from pull requests or from other people.
- The robot uses the Python standard library only (nothing installed), fetches only `https` pages from a fixed list of hosts, caps download size, and never runs anything it downloads.
- All text is stripped of HTML before it is saved, links must point to known sites, and `validate_data.py` rejects anything that looks like code.
- It can only change `data.json`; the page itself (`index.html`) is never touched by the robot.
- Turn on two-factor authentication for your GitHub account (Settings → Password and authentication). That protects the repo more than anything else.
