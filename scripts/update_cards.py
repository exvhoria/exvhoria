#!/usr/bin/env python3
"""Generate real-time monodark profile SVGs for exvhoria."""

import html
import json
import os
import re
import urllib.request
from datetime import date, datetime, timedelta, timezone

OWNER = "exvhoria"
REPO = "Asanagi-Code"
FALLBACK_DESC_1 = "Self-hosted AI coding agent and proxy gateway supervisor for Termux/Android"
FALLBACK_DESC_2 = "with automatic session re-minting, WARP egress rotation, and watchdog recovery."
WIB = timezone(timedelta(hours=7))


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


def fetch_contributions_year(year: int) -> dict[str, int]:
    url = f"https://github.com/users/{OWNER}/contributions?from={year}-01-01&to={year}-12-31"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    page = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")

    cells = {
        cid: d
        for d, cid in re.findall(
            r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*id="(contribution-day-component-\d+-\d+)"',
            page,
        )
    }
    if not cells:
        cells = dict(
            re.findall(
                r'id="(contribution-day-component-\d+-\d+)"[^>]*data-date="(\d{4}-\d{2}-\d{2})"',
                page,
            )
        )

    out: dict[str, int] = {}
    for cid, txt in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]+)<', page):
        d = cells.get(cid)
        if not d:
            continue
        m = re.match(r"(\d+)\s+contribution", txt.strip())
        out[d] = int(m.group(1)) if m else 0
    return out


def fmt_range(s: str, e: str) -> str:
    ds = date.fromisoformat(s)
    de = date.fromisoformat(e)
    if s == e:
        return ds.strftime("%b %d")
    if ds.year == de.year and ds.month == de.month:
        return f"{ds.strftime('%b %d')} – {de.strftime('%b %d')}"
    return f"{ds.strftime('%b %d')} – {de.strftime('%b %d')}"


def compute_contribution_stats(start_year: int = 2024) -> dict:
    today = datetime.now(WIB).date()
    all_days: dict[str, int] = {}
    for y in range(start_year, today.year + 1):
        try:
            all_days.update(fetch_contributions_year(y))
        except Exception:
            pass

    sorted_days = sorted((d, c) for d, c in all_days.items() if d <= today.isoformat())
    total = sum(c for _, c in sorted_days)

    longest = 0
    longest_start = ""
    longest_end = ""
    cur = 0
    cur_start = ""
    prev_d: date | None = None

    for d_str, cnt in sorted_days:
        d_obj = date.fromisoformat(d_str)
        if cnt > 0:
            if prev_d and (d_obj - prev_d).days == 1 and cur > 0:
                cur += 1
            else:
                cur = 1
                cur_start = d_str
            if cur >= longest:
                longest = cur
                longest_start = cur_start
                longest_end = d_str
        else:
            cur = 0
        prev_d = d_obj

    day_map = dict(sorted_days)
    check_day = today
    if day_map.get(check_day.isoformat(), 0) == 0:
        check_day = today - timedelta(days=1)

    current = 0
    current_end = check_day.isoformat()
    current_start = current_end
    while day_map.get(check_day.isoformat(), 0) > 0:
        current += 1
        current_start = check_day.isoformat()
        check_day -= timedelta(days=1)

    return {
        "total": total,
        "current": current,
        "current_range": fmt_range(current_start, current_end) if current > 0 else "No active streak",
        "longest": longest,
        "longest_range": fmt_range(longest_start, longest_end) if longest > 0 else "—",
    }


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


def build_streak_svg() -> str:
    stats = compute_contribution_stats()
    synced = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 192" width="760" height="192" role="img" aria-label="GitHub Contribution Streak">
  <defs>
    <linearGradient id="st_bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#09090b"/>
      <stop offset="100%" stop-color="#111114"/>
    </linearGradient>
    <pattern id="st_dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#27272a" opacity="0.35"/>
    </pattern>
  </defs>

  <rect x="1" y="1" width="758" height="190" rx="14" fill="url(#st_bg)" stroke="#27272a" stroke-width="1"/>
  <rect x="1" y="1" width="758" height="190" rx="14" fill="url(#st_dots)"/>

  <text x="24" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" letter-spacing="2" fill="#71717a">CONTRIBUTION TELEMETRY</text>
  <text x="736" y="34" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#52525b">synced {html.escape(synced)}</text>

  <!-- Left: Total Contributions -->
  <rect x="24" y="50" width="226" height="118" rx="10" fill="#111114" stroke="#27272a" stroke-width="1"/>
  <text x="137" y="77" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10.5" letter-spacing="1.4" fill="#71717a">TOTAL CONTRIBUTIONS</text>
  <text x="137" y="121" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="38" font-weight="700" fill="#fafafa">{stats['total']}</text>
  <text x="137" y="149" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#a1a1aa">Mar 6, 2024 – Present</text>

  <!-- Center: Current Streak -->
  <rect x="267" y="50" width="226" height="118" rx="10" fill="#111114" stroke="#27272a" stroke-width="1"/>
  <circle cx="380" cy="95" r="24" fill="none" stroke="#27272a" stroke-width="2.5"/>
  <circle cx="380" cy="95" r="24" fill="none" stroke="#fafafa" stroke-width="2.5" stroke-dasharray="122 29" stroke-dashoffset="-14" stroke-linecap="round"/>
  <circle cx="380" cy="71" r="4" fill="#111114"/>
  <path d="M380 63 C382.5 66.5 384 68.8 384 71 A4 4 0 0 1 376 71 C376 68.8 377.5 66.5 380 63 Z" fill="#fafafa"/>
  <text x="380" y="103" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="23" font-weight="700" fill="#fafafa">{stats['current']}</text>
  <text x="380" y="136" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10.5" letter-spacing="1.4" fill="#d4d4d8">CURRENT STREAK</text>
  <text x="380" y="153" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#a1a1aa">{html.escape(stats['current_range'])}</text>

  <!-- Right: Longest Streak -->
  <rect x="510" y="50" width="226" height="118" rx="10" fill="#111114" stroke="#27272a" stroke-width="1"/>
  <text x="623" y="77" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10.5" letter-spacing="1.4" fill="#71717a">LONGEST STREAK</text>
  <text x="623" y="121" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="38" font-weight="700" fill="#fafafa">{stats['longest']}</text>
  <text x="623" y="149" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#a1a1aa">{html.escape(stats['longest_range'])}</text>
</svg>
'''


def build_footer_svg() -> str:
    profile_commit = api_get(f"repos/{OWNER}/{OWNER}/commits/main")
    p_sha = profile_commit.get("sha", "")[:7]
    now_utc = datetime.now(timezone.utc)
    synced_pretty = now_utc.strftime("%b %d, %Y · %H:%M UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 106" width="760" height="106" role="img" aria-label="Profile Sync &amp; Last Update">
  <defs>
    <linearGradient id="ft_bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#09090b"/>
      <stop offset="100%" stop-color="#111114"/>
    </linearGradient>
    <pattern id="ft_dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#27272a" opacity="0.35"/>
    </pattern>
  </defs>

  <rect x="1" y="1" width="758" height="104" rx="14" fill="url(#ft_bg)" stroke="#27272a" stroke-width="1"/>
  <rect x="1" y="1" width="758" height="104" rx="14" fill="url(#ft_dots)"/>

  <!-- Left Card: Last Update -->
  <rect x="20" y="18" width="352" height="70" rx="10" fill="#111114" stroke="#27272a" stroke-width="1"/>
  <text x="38" y="40" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" letter-spacing="1.8" fill="#71717a">LAST UPDATE</text>
  <text x="38" y="68" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="17" font-weight="600" fill="#fafafa">{html.escape(synced_pretty)}</text>

  <!-- Right Card: Live Sync Status -->
  <rect x="388" y="18" width="352" height="70" rx="10" fill="#111114" stroke="#27272a" stroke-width="1"/>
  <text x="406" y="40" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" letter-spacing="1.8" fill="#71717a">EXVHORIA // ZYRUMHD</text>
  <circle cx="411" cy="63" r="4" fill="#22c55e"/>
  <text x="424" y="68" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="16.5" font-weight="600" fill="#fafafa">commit {html.escape(p_sha)} · auto-synced</text>
</svg>
'''


def main() -> None:
    with open("featured.svg", "w", encoding="utf-8") as f:
        f.write(build_featured_svg())
    with open("streak.svg", "w", encoding="utf-8") as f:
        f.write(build_streak_svg())
    with open("footer.svg", "w", encoding="utf-8") as f:
        f.write(build_footer_svg())


if __name__ == "__main__":
    main()
