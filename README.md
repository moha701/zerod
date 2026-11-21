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
