#!/usr/bin/env python3
"""Generate theme-aware (dark/light) real-time profile SVGs for exvhoria."""

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

THEMES = {
    "dark": {
        "bg0": "#09090b",
        "bg1": "#111114",
        "bg_mid": "#0d0d11",
        "card": "#111114",
        "pill": "#18181b",
        "border": "#27272a",
        "border_strong": "#3f3f46",
        "text": "#fafafa",
        "hero": "#ffffff",
        "label": "#d4d4d8",
        "sub": "#a1a1aa",
        "muted": "#71717a",
        "faint": "#52525b",
        "glow": "#27272a",
        "aura_core": "#ffffff",
        "aura_op": "0.08",
        "ring_aura_op": "0.16",
        "sheen": "#e4e4e7",
        "ring_stop0": "#ffffff",
        "ring_stop1": "#e4e4e7",
        "ring_stop2": "#a1a1aa",
        "live": "#22c55e",
        "glow_flood": "#ffffff",
        "glow_op": "0.35",
    },
    "light": {
        "bg0": "#ffffff",
        "bg1": "#f4f4f5",
        "bg_mid": "#fafafa",
        "card": "#f4f4f5",
        "pill": "#ffffff",
        "border": "#e4e4e7",
        "border_strong": "#d4d4d8",
        "text": "#09090b",
        "hero": "#09090b",
        "label": "#27272a",
        "sub": "#52525b",
        "muted": "#71717a",
        "faint": "#a1a1aa",
        "glow": "#e4e4e7",
        "aura_core": "#18181b",
        "aura_op": "0.04",
        "ring_aura_op": "0.07",
        "sheen": "#18181b",
        "ring_stop0": "#09090b",
        "ring_stop1": "#27272a",
        "ring_stop2": "#71717a",
        "live": "#16a34a",
        "glow_flood": "#71717a",
        "glow_op": "0.18",
    },
}


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


def build_featured_svg(tname: str, th: dict, repo: dict, commit: dict) -> str:
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
            f'  <rect x="{cur_x}" y="152" width="{w}" height="26" rx="6" fill="{th["pill"]}" stroke="{th["border"]}" stroke-width="1"/>\n'
            f'  <text x="{cx:.1f}" y="169" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="12" fill="{th["label"]}">{html.escape(label)}</text>'
        )
        cur_x += w + 8
    pills_block = "\n".join(pill_svg)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 198" width="760" height="198" role="img" aria-label="Featured Project: {html.escape(OWNER)}/{html.escape(REPO)}">
  <style>
    .fp-live {{ animation: fpPulse 2.4s ease-in-out infinite; }}
    @keyframes fpPulse {{ 0%, 100% {{ opacity: 0.45; }} 50% {{ opacity: 1; }} }}
  </style>
  <defs>
    <linearGradient id="fp_bg_{tname}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{th['bg0']}"/>
      <stop offset="100%" stop-color="{th['bg1']}"/>
    </linearGradient>
    <radialGradient id="fp_glow_{tname}" cx="92%" cy="15%" r="50%">
      <stop offset="0%" stop-color="{th['glow']}" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="{th['bg0']}" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect x="1" y="1" width="758" height="196" rx="14" fill="url(#fp_bg_{tname})" stroke="{th['border']}" stroke-width="1"/>
  <rect x="1" y="1" width="758" height="196" rx="14" fill="url(#fp_glow_{tname})"/>

  <text x="28" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" letter-spacing="2" fill="{th['muted']}">FEATURED PROJECT · LIVE</text>

  <rect x="626" y="17" width="78" height="24" rx="12" fill="{th['pill']}" stroke="{th['border']}" stroke-width="1"/>
  <circle class="fp-live" cx="641" cy="29" r="3" fill="{th['live']}"/>
  <text x="651" y="33" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="{th['label']}">{html.escape(visibility)}</text>
  <text x="720" y="34" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="16" fill="{th['muted']}">&#8599;</text>

  <text x="28" y="68" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="24" fill="{th['muted']}">{html.escape(OWNER)} / <tspan fill="{th['text']}" font-weight="700">{html.escape(REPO)}</tspan></text>

  <text x="28" y="96" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14.5" fill="{th['sub']}">{html.escape(desc1)}</text>
  <text x="28" y="116" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14.5" fill="{th['sub']}">{html.escape(desc2)}</text>

  <text x="28" y="139" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" fill="{th['muted']}">commit {html.escape(sha)} · &quot;{html.escape(msg)}&quot; ({html.escape(commit_date)})</text>

{pills_block}

  <text x="732" y="169" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="{th['faint']}">synced {html.escape(synced)}</text>
</svg>
'''


def build_streak_svg(tname: str, th: dict, stats: dict) -> str:
    synced = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 202" width="760" height="202" role="img" aria-label="GitHub Contribution Streak">
  <style>
    .st-aura {{ animation: stBreathe 3.4s ease-in-out infinite; }}
    .st-flame {{ animation: stFlame 2.4s ease-in-out infinite; }}
    @keyframes stBreathe {{ 0%, 100% {{ opacity: 0.55; }} 50% {{ opacity: 1; }} }}
    @keyframes stFlame {{ 0%, 100% {{ opacity: 0.72; }} 50% {{ opacity: 1; }} }}
  </style>
  <defs>
    <linearGradient id="st_bg_{tname}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{th['bg0']}"/>
      <stop offset="50%" stop-color="{th['bg_mid']}"/>
      <stop offset="100%" stop-color="{th['bg1']}"/>
    </linearGradient>
    <radialGradient id="centerAura_{tname}" cx="50%" cy="44%" r="44%">
      <stop offset="0%" stop-color="{th['aura_core']}" stop-opacity="{th['aura_op']}"/>
      <stop offset="45%" stop-color="{th['sub']}" stop-opacity="0.03"/>
      <stop offset="100%" stop-color="{th['bg0']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ringAura_{tname}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{th['aura_core']}" stop-opacity="{th['ring_aura_op']}"/>
      <stop offset="65%" stop-color="{th['sub']}" stop-opacity="0.05"/>
      <stop offset="100%" stop-color="{th['bg0']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="topSheen_{tname}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{th['border']}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{th['sheen']}" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="{th['border']}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="divGrad_{tname}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{th['border']}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{th['border_strong']}" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="{th['border']}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="ringGrad_{tname}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{th['ring_stop0']}"/>
      <stop offset="50%" stop-color="{th['ring_stop1']}"/>
      <stop offset="100%" stop-color="{th['ring_stop2']}"/>
    </linearGradient>
    <pattern id="st_dots_{tname}" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="{th['border']}" opacity="0.28"/>
    </pattern>
    <filter id="softGlow_{tname}" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="3.0" result="blur"/>
      <feFlood flood-color="{th['glow_flood']}" flood-opacity="{th['glow_op']}" result="col"/>
      <feComposite in="col" in2="blur" operator="in" result="glow"/>
      <feMerge>
        <feMergeNode in="glow"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <rect x="1" y="1" width="758" height="200" rx="14" fill="url(#st_bg_{tname})" stroke="{th['border']}" stroke-width="1"/>
  <rect x="1" y="1" width="758" height="200" rx="14" fill="url(#st_dots_{tname})"/>
  <rect x="1" y="1" width="758" height="200" rx="14" fill="url(#centerAura_{tname})"/>
  <line x1="140" y1="1.5" x2="620" y2="1.5" stroke="url(#topSheen_{tname})" stroke-width="1.2"/>

  <line x1="253" y1="30" x2="253" y2="172" stroke="url(#divGrad_{tname})" stroke-width="1"/>
  <line x1="507" y1="30" x2="507" y2="172" stroke="url(#divGrad_{tname})" stroke-width="1"/>

  <text x="127" y="92" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="42" font-weight="700" fill="{th['hero']}" filter="url(#softGlow_{tname})">{stats['total']}</text>
  <text x="127" y="128" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14" font-weight="500" fill="{th['label']}">Total Contributions</text>
  <text x="127" y="151" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" fill="{th['muted']}">Mar 6, 2024 – Present</text>

  <circle class="st-aura" cx="380" cy="80" r="46" fill="url(#ringAura_{tname})"/>
  <circle cx="380" cy="80" r="34" fill="none" stroke="{th['border']}" stroke-width="3.5"/>
  <circle cx="380" cy="80" r="34" fill="none" stroke="url(#ringGrad_{tname})" stroke-width="3.5" stroke-dasharray="178 36" stroke-dashoffset="-18" stroke-linecap="round" filter="url(#softGlow_{tname})">
    <animateTransform attributeName="transform" type="rotate" from="0 380 80" to="360 380 80" dur="16s" repeatCount="indefinite"/>
  </circle>
  <circle cx="380" cy="46" r="9" fill="{th['bg_mid']}"/>
  <path class="st-flame" d="M380 35.5 C383.8 40.5 385.8 43.8 385.8 47 A5.8 5.8 0 0 1 374.2 47 C374.2 43.8 376.2 40.5 380 35.5 Z" fill="{th['hero']}" filter="url(#softGlow_{tname})"/>
  <text x="380" y="92" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="34" font-weight="700" fill="{th['hero']}" filter="url(#softGlow_{tname})">{stats['current']}</text>
  <text x="380" y="138" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14.5" font-weight="600" fill="{th['text']}">Current Streak</text>
  <text x="380" y="159" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" fill="{th['sub']}">{html.escape(stats['current_range'])}</text>

  <text x="633" y="92" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="42" font-weight="700" fill="{th['hero']}" filter="url(#softGlow_{tname})">{stats['longest']}</text>
  <text x="633" y="128" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14" font-weight="500" fill="{th['label']}">Longest Streak</text>
  <text x="633" y="151" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" fill="{th['muted']}">{html.escape(stats['longest_range'])}</text>

  <text x="738" y="187" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10" fill="{th['faint']}">synced {html.escape(synced)}</text>
</svg>
'''


def build_footer_svg(tname: str, th: dict, p_sha: str) -> str:
    synced_pretty = datetime.now(timezone.utc).strftime("%b %d, %Y · %H:%M UTC")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 106" width="760" height="106" role="img" aria-label="Profile Sync &amp; Last Update">
  <style>
    .ft-dot {{ animation: ftPulse 2.4s ease-in-out infinite; }}
    @keyframes ftPulse {{ 0%, 100% {{ opacity: 0.45; }} 50% {{ opacity: 1; }} }}
  </style>
  <defs>
    <linearGradient id="ft_bg_{tname}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{th['bg0']}"/>
      <stop offset="100%" stop-color="{th['bg1']}"/>
    </linearGradient>
    <pattern id="ft_dots_{tname}" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="{th['border']}" opacity="0.35"/>
    </pattern>
  </defs>

  <rect x="1" y="1" width="758" height="104" rx="14" fill="url(#ft_bg_{tname})" stroke="{th['border']}" stroke-width="1"/>
  <rect x="1" y="1" width="758" height="104" rx="14" fill="url(#ft_dots_{tname})"/>

  <rect x="20" y="18" width="352" height="70" rx="10" fill="{th['card']}" stroke="{th['border']}" stroke-width="1"/>
  <text x="38" y="40" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" letter-spacing="1.8" fill="{th['muted']}">LAST UPDATE</text>
  <text x="38" y="68" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="17" font-weight="600" fill="{th['text']}">{html.escape(synced_pretty)}</text>

  <rect x="388" y="18" width="352" height="70" rx="10" fill="{th['card']}" stroke="{th['border']}" stroke-width="1"/>
  <text x="406" y="40" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" letter-spacing="1.8" fill="{th['muted']}">EXVHORIA // ZYRUMHD</text>
  <circle class="ft-dot" cx="411" cy="63" r="4" fill="{th['live']}"/>
  <text x="424" y="68" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="16.5" font-weight="600" fill="{th['text']}">commit {html.escape(p_sha)} · auto-synced</text>
</svg>
'''


def main() -> None:
    os.makedirs("assets", exist_ok=True)
    repo = api_get(f"repos/{OWNER}/{REPO}")
    branch = repo.get("default_branch", "main")
    commit = api_get(f"repos/{OWNER}/{REPO}/commits/{branch}")
    profile_commit = api_get(f"repos/{OWNER}/{OWNER}/commits/main")
    p_sha = profile_commit.get("sha", "")[:7]
    stats = compute_contribution_stats()

    for tname, th in THEMES.items():
        with open(f"assets/featured-{tname}.svg", "w", encoding="utf-8") as f:
            f.write(build_featured_svg(tname, th, repo, commit))
        with open(f"assets/streak-{tname}.svg", "w", encoding="utf-8") as f:
            f.write(build_streak_svg(tname, th, stats))
        with open(f"assets/footer-{tname}.svg", "w", encoding="utf-8") as f:
            f.write(build_footer_svg(tname, th, p_sha))


if __name__ == "__main__":
    main()
