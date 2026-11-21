#!/usr/bin/env python3
"""Opens, updates or closes one GitHub issue ("ZEROED robot needs a look") from the robot's report.
Uses the run's own temporary GITHUB_TOKEN; nothing is stored. Usage: report.py [STEP_FAILED_TEXT]"""
import json
import os
import sys
import urllib.request

repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
if not repo or not token:
    print("no repo/token, skipping report"); sys.exit(0)
API = "https://api.github.com/repos/" + repo
def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json", "User-Agent": "zeroed-robot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        t = r.read(); return json.loads(t) if t else {}
try:
    rep = json.load(open(".robot/report.json"))
except Exception:
    rep = {"changes": [], "problems": [], "sources": {}}
failed = [k for k, v in rep.get("sources", {}).items() if v != "ok"]
extra = " ".join(sys.argv[1:]).strip()
title = "ZEROED robot needs a look"
issues = [i for i in call("GET", "/issues?state=open&labels=robot&per_page=10") if i.get("title") == title]
run = f"https://github.com/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
if failed or extra:
    body = "The data robot hit a problem, so it **did not change anything it couldn't confirm**. The site keeps working with the last good data.\n\n"
    if extra: body += f"**Stopped at:** {extra}\n\n"
    if failed: body += "**Sources that failed:** " + ", ".join(failed) + "\n\n"
    if rep.get("problems"): body += "**Details:**\n" + "\n".join("- " + p for p in rep["problems"][:25]) + "\n\n"
    body += f"Run log: {run}\n\nAsk Claude to fix it, or wait: the robot tries again every 3 hours and closes this note itself once everything works."
    if issues: call("PATCH", f"/issues/{issues[0]['number']}", {"body": body})
    else: call("POST", "/issues", {"title": title, "body": body, "labels": ["robot"]})
    print("issue opened/updated")
elif issues:
    call("POST", f"/issues/{issues[0]['number']}/comments", {"body": "All sources read fine again. Closing."})
    call("PATCH", f"/issues/{issues[0]['number']}", {"state": "closed"})
    print("issue closed")
