#!/usr/bin/env python3
"""Generate real-time monodark featured project SVG for exvhoria's GitHub profile."""

import html
import json
import os
import urllib.request
from datetime import datetime, timezone

OWNER = "exvhoria"
REPO = "Asanagi-Code"
FALLBACK_DESC_1 = "Self-hosted AI coding agent and proxy gateway supervisor for Termux/Android"
FALLBACK_DESC_2 = "with automatic session re-minting, WARP egress rotation, and watchdog recovery."


def api_get(path: str) -> dict:
    url = f"https://api.github.com/{path.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "exvhoria-profile-sync",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def truncate(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def wrap_description(desc: str | None) -> tuple[str, str]:
    if not desc or not desc.strip():
        return FALLBACK_DESC_1, FALLBACK_DESC_2
    words = desc.strip().split()
    line1, line2 = [], []
    cur = 0
    for w in words:
        if cur + len(w) + (1 if line1 else 0) <= 74 and not line2:
            line1.append(w)
            cur += len(w) + (1 if len(line1) > 1 else 0)
        else:
            line2.append(w)
    l1 = " ".join(line1)
    l2 = truncate(" ".join(line2), 74) if line2 else ""
    return l1, l2


def format_date(iso_ts: str) -> str:
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    return dt.strftime("%b %d, %Y")


def build_featured_svg() -> str:
    repo = api_get(f"repos/{OWNER}/{REPO}")
    branch = repo.get("default_branch", "main")
    commit = api_get(f"repos/{OWNER}/{REPO}/commits/{branch}")

    visibility = "PRIVATE" if repo.get("private") else "PUBLIC"
    language = repo.get("language") or "Code"
    stars = int(repo.get("stargazers_count", 0))
    forks = int(repo.get("forks_count", 0))
    issues = int(repo.get("open_issues_count", 0))

    sha = commit.get("sha", "")[:7]
    raw_msg = (commit.get("commit", {}).get("message") or "").splitlines()[0]
    msg = truncate(raw_msg, 46)
    commit_date = format_date(commit["commit"]["committer"]["date"])
    synced = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    desc1, desc2 = wrap_description(repo.get("description"))

    pill_labels = [
        language,
        f"★ {stars} {'star' if stars == 1 else 'stars'}",
        f"⑂ {forks} {'fork' if forks == 1 else 'forks'}",
        f"• {issues} {'issue' if issues == 1 else 'issues'}",
    ]

    pill_svg = []
    cur_x = 28
    for label in pill_labels:
        w = max(62, len(label) * 7 + 24)
        cx = cur_x + w / 2
        pill_svg.append(
            f'  <rect x="{cur_x}" y="152" width="{w}" height="26" rx="6" fill="#18181b" stroke="#27272a" stroke-width="1"/>\n'
            f'  <text x="{cx:.1f}" y="169" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="12" fill="#d4d4d8">{html.escape(label)}</text>'
        )
        cur_x += w + 8

    pills_block = "\n".join(pill_svg)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 198" width="760" height="198" role="img" aria-label="Featured Project: {html.escape(OWNER)}/{html.escape(REPO)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#09090b"/>
      <stop offset="100%" stop-color="#111114"/>
    </linearGradient>
    <radialGradient id="glow" cx="92%" cy="15%" r="50%">
      <stop offset="0%" stop-color="#27272a" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#09090b" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect x="1" y="1" width="758" height="196" rx="14" fill="url(#bg)" stroke="#27272a" stroke-width="1"/>
  <rect x="1" y="1" width="758" height="196" rx="14" fill="url(#glow)"/>

  <!-- Eyebrow & Status -->
  <text x="28" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" letter-spacing="2" fill="#71717a">FEATURED PROJECT · LIVE</text>

  <rect x="626" y="17" width="78" height="24" rx="12" fill="#18181b" stroke="#27272a" stroke-width="1"/>
  <circle cx="641" cy="29" r="3" fill="#22c55e"/>
  <text x="651" y="33" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#d4d4d8">{html.escape(visibility)}</text>
  <text x="720" y="34" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="16" fill="#71717a">&#8599;</text>

  <!-- Repo Title -->
  <text x="28" y="68" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="24" fill="#71717a">{html.escape(OWNER)} / <tspan fill="#fafafa" font-weight="700">{html.escape(REPO)}</tspan></text>

  <!-- Description -->
  <text x="28" y="96" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14.5" fill="#a1a1aa">{html.escape(desc1)}</text>
  <text x="28" y="116" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14.5" fill="#a1a1aa">{html.escape(desc2)}</text>

  <!-- Latest Commit -->
  <text x="28" y="139" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" fill="#71717a">commit {html.escape(sha)} · &quot;{html.escape(msg)}&quot; ({html.escape(commit_date)})</text>

  <!-- Live Telemetry Pills -->
{pills_block}

  <!-- Synced Timestamp -->
  <text x="732" y="169" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#52525b">synced {html.escape(synced)}</text>
</svg>
'''


def main() -> None:
    svg = build_featured_svg()
    with open("featured.svg", "w", encoding="utf-8") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
