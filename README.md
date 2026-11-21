# ZEROED: MW4 gun lab

A fan-made Call of Duty: Modern Warfare 4 multiplayer tool. Pick your gameplay style, map and mode, and it works out the best gun, the best five attachments, and shows kill times you can check. Not affiliated with Activision or Infinity Ward.

## Put it online with GitHub Pages
1. Create a new repository on GitHub (for example `zeroed`).
2. Upload everything in this folder: `index.html`, `data.json`, `.nojekyll` and this README.
3. Go to **Settings → Pages**, set **Source** to *Deploy from a branch*, pick `main` and `/ (root)`, then **Save**.
4. After a minute your site is live at `https://YOUR-NAME.github.io/zeroed/`.

## How the data updates
- The page loads `data.json` from this folder. If it can't, it uses the copy built into `index.html`, so the site always works.
- To update stats, the shop or patch notes, edit `data.json` and bump `meta.dataDate`. Weapons use `segs` = chest shots-to-kill by distance (players have 100 health): `[[range_end_m, shots], ..., [null, shots]]`.
- Automatic updates: connect GitHub to Claude, and the twice-daily update task can commit a fresh `data.json` here for you.

## What's inside
Best gun finder (map, mode, playstyle, accuracy, level) · Kill race animation · Gunsmith with detailed 3D models · Create a class with share codes · Compare · Shots-to-kill sheet · Maps & modes · Patch notes · Shop · Camo tracker · Unlock planner · Class roulette · AI coach (calculator mode on GitHub) · How it works.

Camo progress and saved classes are stored in your browser on GitHub Pages.
