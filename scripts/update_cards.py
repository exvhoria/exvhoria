#!/usr/bin/env python3
"""Generate monodark 3D geometric banner and real-time GitHub telemetry dashboard SVGs."""

import html
import json
import math
import os
import re
import urllib.request
from datetime import date, datetime, timedelta, timezone

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


def fetch_contributions_year(year: int) -> dict[str, int]:
    url = f"https://github.com/users/{OWNER}/contributions?from={year}-01-01&to={year}-12-31"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    page = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")

    cells = dict(
        re.findall(
            r'id="(contribution-day-component-\d+-\d+)"[^>]*data-date="(\d{4}-\d{2}-\d{2})"',
            page,
        )
    )
    if not cells:
        cells = {
            cid: d
            for d, cid in re.findall(
                r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*id="(contribution-day-component-\d+-\d+)"',
                page,
            )
        }

    tips = re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]+)<', page)
    out: dict[str, int] = {}
    for cid, txt in tips:
        d = cells.get(cid)
        if not d:
            continue
        m = re.match(r"(\d+)\s+contribution", txt.strip())
        out[d] = int(m.group(1)) if m else 0
    return out


def compute_contribution_stats(start_year: int = 2024) -> dict:
    today = datetime.now(timezone.utc).date()
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

    last_30 = []
    for i in range(29, -1, -1):
        d_str = (today - timedelta(days=i)).isoformat()
        last_30.append((d_str, day_map.get(d_str, 0)))

    return {
        "total": total,
        "current": current,
        "current_range": fmt_range(current_start, current_end) if current > 0 else "No active streak",
        "longest": longest,
        "longest_range": fmt_range(longest_start, longest_end) if longest > 0 else "—",
        "last_30": last_30,
    }


def fmt_range(s: str, e: str) -> str:
    ds = date.fromisoformat(s)
    de = date.fromisoformat(e)
    if s == e:
        return ds.strftime("%b %d")
    if ds.month == de.month and ds.year == de.year:
        return f"{ds.strftime('%b %d')}–{de.strftime('%d')}"
    return f"{ds.strftime('%b %d')}–{de.strftime('%b %d')}"


def rotate_point(pt: tuple[float, float, float], ax: float, ay: float, az: float) -> tuple[float, float, float]:
    x, y, z = pt
    cy, sy = math.cos(ax), math.sin(ax)
    y, z = y * cy - z * sy, y * sy + z * cy
    cx, sx = math.cos(ay), math.sin(ay)
    x, z = x * cx + z * sx, -x * sx + z * cx
    cz, sz = math.cos(az), math.sin(az)
    x, y = x * cz - y * sz, x * sz + y * cz
    return x, y, z


def render_3d_icosahedron(cx: float, cy: float, radius: float) -> str:
    """Render a mathematically projected, depth-sorted 3D shaded icosahedron."""
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    raw_verts = [
        (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
        (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
        (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1),
    ]
    verts = []
    for vx, vy, vz in raw_verts:
        norm = math.sqrt(vx * vx + vy * vy + vz * vz)
        rx, ry, rz = rotate_point((vx / norm, vy / norm, vz / norm), 0.48, -0.62, 0.22)
        verts.append((rx, ry, rz))

    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
    ]

    dist = 3.4
    proj = []
    for vx, vy, vz in verts:
        scale = dist / (dist - vz)
        px = cx + vx * radius * scale
        py = cy + vy * radius * scale
        proj.append((px, py, vz))

    lx, ly, lz = -0.55, -0.55, 0.63
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ln, ly / ln, lz / ln

    face_data = []
    for i0, i1, i2 in faces:
        v0, v1, v2 = verts[i0], verts[i1], verts[i2]
        avg_z = (v0[2] + v1[2] + v2[2]) / 3.0
        ux, uy, uz = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
        wx, wy, wz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
        nx, ny, nz = uy * wz - uz * wy, uz * wx - ux * wz, ux * wy - uy * wx
        nn = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / nn, ny / nn, nz / nn
        if nz < 0:
            face_data.append((avg_z, False, 0.0, (i0, i1, i2)))
        else:
            dot = max(0.0, nx * lx + ny * ly + nz * lz)
            face_data.append((avg_z, True, dot, (i0, i1, i2)))

    face_data.sort(key=lambda item: item[0])

    parts = [
        f'  <ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{radius * 1.32:.1f}" ry="{radius * 0.42:.1f}" '
        f'transform="rotate(-18 {cx:.1f} {cy:.1f})" fill="none" stroke="#27272a" stroke-width="1" stroke-dasharray="3 4"/>'
    ]

    for _, front, dot, (i0, i1, i2) in face_data:
        p0, p1, p2 = proj[i0], proj[i1], proj[i2]
        pts_str = f"{p0[0]:.1f},{p0[1]:.1f} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        if not front:
            parts.append(
                f'  <polygon points="{pts_str}" fill="none" stroke="#27272a" stroke-width="0.7" opacity="0.45"/>'
            )
        else:
            shade = int(18 + dot * 52)
            fill_hex = f"#{shade:02x}{shade:02x}{min(255, shade + 4):02x}"
            edge_shade = int(72 + dot * 110)
            edge_hex = f"#{edge_shade:02x}{edge_shade:02x}{min(255, edge_shade + 8):02x}"
            parts.append(
                f'  <polygon points="{pts_str}" fill="{fill_hex}" fill-opacity="0.88" '
                f'stroke="{edge_hex}" stroke-width="1" stroke-linejoin="round"/>'
            )

    for px, py, vz in proj:
        if vz > 0.15:
            r = 2.4 if vz > 0.55 else 1.7
            op = "0.95" if vz > 0.55 else "0.6"
            parts.append(f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="#fafafa" opacity="{op}"/>')

    return "\n".join(parts)


def render_3d_cube_icon(cx: float, cy: float, size: float) -> str:
    """Render a crisp 3D isometric wireframe cube accent."""
    raw = [
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
    ]
    pts = []
    for p in raw:
        rx, ry, rz = rotate_point(p, 0.52, -0.68, 0.0)
        pts.append((cx + rx * size, cy + ry * size, rz))

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    ]
    lines = []
    for a, b in edges:
        pa, pb = pts[a], pts[b]
        front = (pa[2] + pb[2]) > 0
        stroke = "#71717a" if front else "#27272a"
        sw = "1.2" if front else "0.9"
        lines.append(
            f'  <line x1="{pa[0]:.1f}" y1="{pa[1]:.1f}" x2="{pb[0]:.1f}" y2="{pb[1]:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>'
        )
    for px, py, pz in pts:
        if pz > 0.2:
            lines.append(f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="1.8" fill="#e4e4e7"/>')
    return "\n".join(lines)


def build_banner_svg() -> str:
    poly_3d = render_3d_icosahedron(622, 105, 62)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 214" width="760" height="214" role="img" aria-label="GhosttedXV — Software &amp; Systems Engineering">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#09090b"/>
      <stop offset="100%" stop-color="#111114"/>
    </linearGradient>
    <radialGradient id="glow" cx="82%" cy="48%" r="48%">
      <stop offset="0%" stop-color="#3f3f46" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#09090b" stop-opacity="0"/>
    </radialGradient>
    <pattern id="dots" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1" fill="#27272a" opacity="0.5"/>
    </pattern>
  </defs>

  <rect x="1" y="1" width="758" height="212" rx="14" fill="url(#bg)" stroke="#27272a" stroke-width="1"/>
  <rect x="1" y="1" width="758" height="212" rx="14" fill="url(#dots)"/>
  <rect x="1" y="1" width="758" height="212" rx="14" fill="url(#glow)"/>

  <!-- 3D Perspective Horizon Accent -->
  <g stroke="#1f1f24" stroke-width="0.9" opacity="0.7">
    <line x1="470" y1="186" x2="740" y2="186"/>
    <line x1="505" y1="172" x2="740" y2="172"/>
    <line x1="540" y1="160" x2="740" y2="160"/>
    <line x1="622" y1="160" x2="520" y2="208"/>
    <line x1="622" y1="160" x2="622" y2="208"/>
    <line x1="622" y1="160" x2="724" y2="208"/>
  </g>

  <!-- Shaded 3D Icosahedron -->
{poly_3d}

  <!-- Eyebrow -->
  <circle cx="46" cy="50" r="3.5" fill="#e4e4e7"/>
  <text x="60" y="54" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="12" letter-spacing="2.2" fill="#71717a">EXVHORIA // PROFILE</text>

  <!-- Name -->
  <text x="42" y="108" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="44" font-weight="700" letter-spacing="-1.2" fill="#fafafa">GhosttedXV</text>

  <!-- Subtitle -->
  <text x="42" y="141" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="17" font-weight="400" fill="#a1a1aa">Software &amp; Systems Engineering  ·  MoonVatality</text>

  <!-- Footer meta -->
  <text x="42" y="176" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="12.5" fill="#52525b">Indonesia  ·  APIs · Reverse Proxies · Self-Hosted Tooling</text>
</svg>
'''


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
        if cur + len(w) + (1 if line1 else 0) <= 68 and not line2:
            line1.append(w)
            cur += len(w) + (1 if len(line1) > 1 else 0)
        else:
            line2.append(w)
    l1 = " ".join(line1)
    l2 = truncate(" ".join(line2), 68) if line2 else ""
    return l1, l2


def format_date(iso_ts: str) -> str:
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    return dt.strftime("%b %d, %Y")


def build_smooth_path(pts: list[tuple[float, float]], y_min: float, y_max: float) -> str:
    if not pts:
        return ""
    if len(pts) == 1:
        return f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"
    clamp = lambda y: max(y_min, min(y_max, y))
    d = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else pts[i + 1]
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = clamp(p1[1] + (p2[1] - p0[1]) / 6.0)
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = clamp(p2[1] - (p3[1] - p1[1]) / 6.0)
        d.append(f"C {c1x:.1f} {c1y:.1f}, {c2x:.1f} {c2y:.1f}, {p2[0]:.1f} {p2[1]:.1f}")
    return " ".join(d)


def build_dashboard_svg() -> str:
    repo = api_get(f"repos/{OWNER}/{REPO}")
    branch = repo.get("default_branch", "main")
    commit = api_get(f"repos/{OWNER}/{REPO}/commits/{branch}")
    stats = compute_contribution_stats()

    visibility = "PRIVATE" if repo.get("private") else "PUBLIC"
    language = repo.get("language") or "Code"
    stars = int(repo.get("stargazers_count", 0))
    forks = int(repo.get("forks_count", 0))
    issues = int(repo.get("open_issues_count", 0))

    sha = commit.get("sha", "")[:7]
    raw_msg = (commit.get("commit", {}).get("message") or "").splitlines()[0]
    msg = truncate(raw_msg, 44)
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
            f'  <rect x="{cur_x}" y="150" width="{w}" height="26" rx="6" fill="#18181b" stroke="#27272a" stroke-width="1"/>\n'
            f'  <text x="{cx:.1f}" y="167" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="12" fill="#d4d4d8">{html.escape(label)}</text>'
        )
        cur_x += w + 8
    pills_block = "\n".join(pill_svg)

    series = stats["last_30"]
    max_val = max((c for _, c in series), default=0)
    scale_max = max(max_val, 4)

    gx0, gx1 = 296.0, 712.0
    gy_top, gy_bot = 272.0, 362.0
    step_x = (gx1 - gx0) / max(1, len(series) - 1)

    pts = []
    for idx, (_, val) in enumerate(series):
        px = gx0 + idx * step_x
        py = gy_bot - (val / scale_max) * (gy_bot - gy_top)
        pts.append((px, py))

    line_d = build_smooth_path(pts, gy_top, gy_bot)
    area_d = f"{line_d} L {pts[-1][0]:.1f} {gy_bot:.1f} L {pts[0][0]:.1f} {gy_bot:.1f} Z"

    nodes_svg = []
    for (px, py), (_, val) in zip(pts, series):
        if val > 0:
            is_peak = val == max_val and max_val > 0
            r = "3.4" if is_peak else "2.4"
            fill = "#fafafa" if is_peak else "#d4d4d8"
            nodes_svg.append(f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{fill}" stroke="#09090b" stroke-width="1"/>')
    nodes_block = "\n".join(nodes_svg)

    d_start = date.fromisoformat(series[0][0]).strftime("%b %d")
    d_mid = date.fromisoformat(series[len(series) // 2][0]).strftime("%b %d")
    d_end = date.fromisoformat(series[-1][0]).strftime("%b %d")

    cube_3d = render_3d_cube_icon(682, 92, 18)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 442" width="760" height="442" role="img" aria-label="Featured Project and Real-Time GitHub Telemetry">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#09090b"/>
      <stop offset="100%" stop-color="#111114"/>
    </linearGradient>
    <radialGradient id="glow" cx="90%" cy="12%" r="48%">
      <stop offset="0%" stop-color="#27272a" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#09090b" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e4e4e7" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#09090b" stop-opacity="0.0"/>
    </linearGradient>
    <clipPath id="chartClip">
      <rect x="{gx0 - 4:.0f}" y="{gy_top - 6:.0f}" width="{gx1 - gx0 + 8:.0f}" height="{gy_bot - gy_top + 10:.0f}"/>
    </clipPath>
  </defs>

  <rect x="1" y="1" width="758" height="440" rx="14" fill="url(#bg)" stroke="#27272a" stroke-width="1"/>
  <rect x="1" y="1" width="758" height="440" rx="14" fill="url(#glow)"/>

  <!-- 3D Wireframe Cube Accent -->
{cube_3d}

  <!-- Top Section: Featured Project -->
  <text x="28" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" letter-spacing="2" fill="#71717a">FEATURED PROJECT · LIVE</text>

  <rect x="626" y="17" width="78" height="24" rx="12" fill="#18181b" stroke="#27272a" stroke-width="1"/>
  <circle cx="641" cy="29" r="3" fill="#22c55e"/>
  <text x="651" y="33" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#d4d4d8">{html.escape(visibility)}</text>
  <text x="720" y="34" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="16" fill="#71717a">&#8599;</text>

  <text x="28" y="66" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="24" fill="#71717a">{html.escape(OWNER)} / <tspan fill="#fafafa" font-weight="700">{html.escape(REPO)}</tspan></text>

  <text x="28" y="94" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14" fill="#a1a1aa">{html.escape(desc1)}</text>
  <text x="28" y="113" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="14" fill="#a1a1aa">{html.escape(desc2)}</text>

  <text x="28" y="136" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11.5" fill="#71717a">commit {html.escape(sha)} · &quot;{html.escape(msg)}&quot; ({html.escape(commit_date)})</text>

{pills_block}

  <!-- Section Divider -->
  <line x1="28" y1="196" x2="732" y2="196" stroke="#27272a" stroke-width="1"/>

  <!-- Bottom Left Sub-Card: Real-Time Streak & Contributions -->
  <rect x="28" y="216" width="232" height="178" rx="10" fill="#111114" stroke="#27272a" stroke-width="1"/>
  <text x="46" y="240" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" letter-spacing="1.6" fill="#71717a">LIVE CONTRIBUTIONS</text>

  <text x="46" y="284" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="36" font-weight="700" fill="#fafafa">{stats['total']}</text>
  <text x="46" y="303" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="12.5" fill="#a1a1aa">All-time public commits &amp; PRs</text>

  <line x1="46" y1="319" x2="242" y2="319" stroke="#27272a" stroke-width="1"/>
  <line x1="144" y1="330" x2="144" y2="380" stroke="#27272a" stroke-width="1"/>

  <text x="46" y="339" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10" letter-spacing="1" fill="#71717a">CURRENT</text>
  <text x="46" y="362" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="20" font-weight="700" fill="#fafafa">{stats['current']}d</text>
  <text x="46" y="379" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10" fill="#71717a">{html.escape(stats['current_range'])}</text>

  <text x="158" y="339" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10" letter-spacing="1" fill="#71717a">LONGEST</text>
  <text x="158" y="362" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif" font-size="20" font-weight="700" fill="#fafafa">{stats['longest']}d</text>
  <text x="158" y="379" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10" fill="#71717a">{html.escape(stats['longest_range'])}</text>

  <!-- Bottom Right Sub-Card: Real-Time 30-Day Activity Graph -->
  <rect x="276" y="216" width="456" height="178" rx="10" fill="#111114" stroke="#27272a" stroke-width="1"/>
  <text x="296" y="240" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" letter-spacing="1.6" fill="#71717a">30-DAY ACTIVITY GRAPH</text>
  <text x="712" y="240" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#a1a1aa">peak {max_val}/day</text>

  <!-- Chart Grid Lines -->
  <line x1="{gx0:.0f}" y1="{gy_top:.0f}" x2="{gx1:.0f}" y2="{gy_top:.0f}" stroke="#27272a" stroke-width="0.8" stroke-dasharray="3 4"/>
  <line x1="{gx0:.0f}" y1="{(gy_top + gy_bot) / 2:.0f}" x2="{gx1:.0f}" y2="{(gy_top + gy_bot) / 2:.0f}" stroke="#27272a" stroke-width="0.8" stroke-dasharray="3 4"/>
  <line x1="{gx0:.0f}" y1="{gy_bot:.0f}" x2="{gx1:.0f}" y2="{gy_bot:.0f}" stroke="#27272a" stroke-width="1"/>

  <!-- Clipped Area + Line -->
  <g clip-path="url(#chartClip)">
    <path d="{area_d}" fill="url(#areaGrad)"/>
    <path d="{line_d}" fill="none" stroke="#e4e4e7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
{nodes_block}

  <!-- Axis Dates -->
  <text x="{gx0:.0f}" y="381" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10.5" fill="#52525b">{html.escape(d_start)}</text>
  <text x="{(gx0 + gx1) / 2:.0f}" y="381" text-anchor="middle" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10.5" fill="#52525b">{html.escape(d_mid)}</text>
  <text x="{gx1:.0f}" y="381" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="10.5" fill="#52525b">{html.escape(d_end)}</text>

  <!-- Footer Status -->
  <text x="28" y="421" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#52525b">exvhoria // auto-synced telemetry via GitHub Actions</text>
  <text x="732" y="421" text-anchor="end" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="11" fill="#52525b">synced {html.escape(synced)}</text>
</svg>
'''


def main() -> None:
    with open("banner.svg", "w", encoding="utf-8") as f:
        f.write(build_banner_svg())
    with open("dashboard.svg", "w", encoding="utf-8") as f:
        f.write(build_dashboard_svg())


if __name__ == "__main__":
    main()
