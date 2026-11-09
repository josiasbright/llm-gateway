from html import escape

from app.reporting import UsageReport, dollars

PERIODS = (7, 30, 90)

STYLE = """
:root {
  color-scheme: light dark;
  --bg: #ffffff; --ink: #0a0a0a; --muted: #4b5563; --line: #d1d5db; --grid: #64748b;
  --font-display: "Orbitron", ui-sans-serif, system-ui, "Segoe UI", sans-serif;
  --font-body: ui-sans-serif, system-ui, "Segoe UI", sans-serif;
  --pad-x: clamp(1.25rem, 4.5vw, 5rem);
  --pad-y: clamp(1rem, 3vh, 3rem);
  --gap-nav: clamp(1rem, 2.2vw, 2.25rem);
  --logo: clamp(1.1rem, 1vw + 0.8rem, 1.75rem);
  --nav: clamp(0.72rem, 0.3vw + 0.6rem, 0.9rem);
  --headline: clamp(2rem, 4vw + 0.75rem, 4.5rem);
  --body: clamp(0.875rem, 0.3vw + 0.75rem, 1rem);
  --micro: clamp(0.72rem, 0.2vw + 0.62rem, 0.8rem);
  --kpi: clamp(1.5rem, 2.4vw + 0.6rem, 2.75rem);
  --corner: clamp(0.65rem, 0.4vw + 0.4rem, 0.95rem);
  --globe: clamp(2.25rem, 2.5vw + 1rem, 3.25rem);
  --checker-w: clamp(2.5rem, 4vw, 5.5rem);
  --checker-h: clamp(1.25rem, 2vw, 2.75rem);
  --cell: clamp(2.25rem, 2.8vw, 4rem);
  --box: clamp(1rem, 1.5vw, 1.75rem);
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #0b0b0b; --ink: #f2f2f2; --muted: #a3a3a3; --line: #3f3f46; --grid: #94a3b8; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font-family: var(--font-body);
       font-size: var(--body); line-height: 1.5; -webkit-font-smoothing: antialiased; }
body::before { content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  opacity: 0.1; background-size: var(--cell) var(--cell);
  background-image: linear-gradient(var(--grid) 1px, transparent 1px),
                    linear-gradient(90deg, var(--grid) 1px, transparent 1px); }
::selection { background: var(--ink); color: var(--bg); }
.page { position: relative; z-index: 1; min-height: 100vh; display: flex;
        flex-direction: column; padding: var(--pad-y) var(--pad-x); gap: var(--pad-y); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden;
           clip: rect(0 0 0 0); white-space: nowrap; }
a { color: inherit; }
a:focus-visible { outline: 2px solid currentColor; outline-offset: 3px; }
header.top { display: flex; justify-content: space-between; align-items: center;
             flex-wrap: wrap; gap: 1rem; }
.logo { font-family: var(--font-display); font-weight: 900; letter-spacing: 0.15em;
        font-size: var(--logo); text-decoration: none; text-transform: uppercase; }
.logo sup { font-size: 0.55em; margin-left: 0.15em; }
nav ul { display: flex; align-items: center; flex-wrap: wrap; gap: var(--gap-nav);
         list-style: none; margin: 0; padding: 0; }
nav a { font-size: var(--nav); font-weight: 500; letter-spacing: 0.2em;
        text-transform: uppercase; text-decoration: none; }
nav a:hover { opacity: 0.5; }
nav a[aria-current="page"] { font-weight: 800; border-bottom: 2px solid currentColor; }
nav .sep { color: var(--muted); }
.hero { display: flex; flex-direction: column; gap: var(--pad-y);
        justify-content: space-between; align-items: flex-start; }
@media (min-width: 64rem) { .hero { flex-direction: row; align-items: flex-end; } }
.framed { position: relative; padding: var(--box); }
.corner { position: absolute; width: var(--corner); height: var(--corner); }
.corner.tl { top: 0; left: 0; } .corner.tr { top: 0; right: 0; }
.corner.bl { bottom: 0; left: 0; } .corner.br { bottom: 0; right: 0; }
h1 { margin: 0; font-family: var(--font-display); font-weight: 800; text-transform: uppercase;
     letter-spacing: 0.08em; line-height: 1.05; font-size: var(--headline); }
.checker { width: var(--checker-w); height: var(--checker-h); margin-left: 0.3em;
           vertical-align: baseline; transform: translateY(2px); }
.lead { margin: 0.75rem 0 0; color: var(--muted); }
.feature { display: flex; align-items: center; gap: var(--box); min-width: 13rem; }
.globe { width: var(--globe); height: var(--globe); flex: none; }
.tagline { margin: 0; font-weight: 600; text-transform: uppercase; letter-spacing: 0.18em;
           font-size: var(--micro); }
.note { margin: 0; padding: 0.5rem 1rem; border-left: 4px solid #8a6d00; background: #fff4cc;
        color: #1a1a1a; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
        gap: var(--pad-y); margin: 0; }
.kpi { position: relative; padding: var(--box); background: var(--bg); }
.kpi dt { font-size: var(--micro); letter-spacing: 0.18em; text-transform: uppercase;
          color: var(--muted); }
.kpi dd { margin: 0.25rem 0 0; font-family: var(--font-display); font-weight: 700;
          font-size: var(--kpi); font-variant-numeric: tabular-nums; }
.table-wrap { overflow-x: auto; background: var(--bg); }
table { border-collapse: collapse; width: 100%; }
caption { text-align: left; padding: 0.5rem 0; font-size: var(--micro); letter-spacing: 0.18em;
          text-transform: uppercase; color: var(--muted); }
th, td { padding: 0.65rem 0.75rem; text-align: left; border-bottom: 1px solid var(--line); }
thead th { font-size: var(--micro); letter-spacing: 0.12em; text-transform: uppercase;
           color: var(--muted); border-bottom: 1px solid var(--ink); }
tbody th { font-weight: 600; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
tfoot th, tfoot td { font-weight: 700; border-top: 1px solid var(--ink); border-bottom: 0; }
.share { white-space: nowrap; }
.share span { display: inline-block; min-width: 3.5ch; text-align: right; margin-left: 0.5rem;
              font-variant-numeric: tabular-nums; }
progress { appearance: none; -webkit-appearance: none; width: 6rem; height: 0.5rem;
           border: 1px solid var(--ink); background: transparent; vertical-align: middle; }
progress::-webkit-progress-bar { background: transparent; }
progress::-webkit-progress-value { background: var(--ink); }
progress::-moz-progress-bar { background: var(--ink); }
.empty { color: var(--muted); }
footer { font-size: var(--micro); letter-spacing: 0.18em; text-transform: uppercase;
         color: var(--muted); text-align: center; padding-top: var(--pad-y); }
@media (prefers-color-scheme: dark) { .note { background: #3a3000; color: #f2f2f2; } }
@media (prefers-reduced-motion: no-preference) { nav a { transition: opacity 0.15s; } }
"""

CORNER_PATHS = {
    "tl": "M0 11.5V0.5H11.5",
    "tr": "M0.5 0.5H11.5V11.5",
    "bl": "M0 0.5V11.5H11.5",
    "br": "M0.5 11.5H11.5V0.5",
}


def _corner(position: str) -> str:
    return (
        f'<svg class="corner {position}" viewBox="0 0 12 12" fill="none" '
        'stroke="currentColor" stroke-width="1.5" aria-hidden="true" focusable="false">'
        f'<path d="{CORNER_PATHS[position]}"/></svg>'
    )


def _corners(*positions: str) -> str:
    return "".join(_corner(position) for position in positions)


def _checker() -> str:
    squares = []
    for row in range(4):
        shift = 2.25 if row % 2 == 1 else 0
        for col in range(6):
            x = round(col * 5 + shift, 2)
            y = round(row * 4.6, 2)
            squares.append(f'<rect x="{x}" y="{y}" width="3.8" height="3.8"/>')
    return (
        '<svg class="checker" viewBox="0 0 36 18" fill="currentColor" '
        'aria-hidden="true" focusable="false">' + "".join(squares) + "</svg>"
    )


GLOBE = (
    '<svg class="globe" viewBox="0 0 64 64" fill="none" stroke="currentColor" '
    'stroke-width="1.2" aria-hidden="true" focusable="false">'
    '<circle cx="32" cy="32" r="28"/><path d="M4 32H60"/><path d="M32 4V60"/>'
    '<ellipse cx="32" cy="32" rx="28" ry="10"/><ellipse cx="32" cy="32" rx="28" ry="20"/>'
    '<ellipse cx="32" cy="32" rx="10" ry="28"/><ellipse cx="32" cy="32" rx="20" ry="28"/>'
    "</svg>"
)


def _int(value: int) -> str:
    """Entier avec une espace fine insecable entre les milliers."""
    return f"{value:,}".replace(",", "\u202f")


def _share(cost: int, total: int) -> int:
    """Part du cout total, en pourcentage entier arrondi au plus proche."""
    if total <= 0:
        return 0
    return (200 * cost + total) // (2 * total)


def _nav(current_days: int) -> str:
    items = []
    for days in PERIODS:
        current = ' aria-current="page"' if days == current_days else ""
        items.append(f'<li><a href="/dashboard?days={days}"{current}>{days} jours</a></li>')
    items.append('<li class="sep" aria-hidden="true">|</li>')
    items.append('<li><a href="/docs">API</a></li>')
    return '<nav aria-label="Période"><ul>' + "".join(items) + "</ul></nav>"


def _kpi(label: str, value: str) -> str:
    return (
        f'<div class="kpi">{_corners("tl", "tr", "bl", "br")}<dt>{label}</dt><dd>{value}</dd></div>'
    )


def _kpis(report: UsageReport) -> str:
    tokens = report.total_tokens_in + report.total_tokens_out
    return (
        '<section aria-labelledby="totals"><h2 id="totals" class="sr-only">Totaux</h2>'
        '<dl class="kpis">'
        + _kpi("Appels", _int(report.total_calls))
        + _kpi("Tokens (entrée + sortie)", _int(tokens))
        + _kpi("Coût total (USD)", dollars(report.total_cost_micro_usd))
        + "</dl></section>"
    )


def _table(report: UsageReport) -> str:
    if not report.rows:
        return '<p class="empty">Aucun appel enregistré sur cette période.</p>'
    total = report.total_cost_micro_usd
    body = "".join(
        "<tr>"
        f"<td>{escape(row.project)}</td>"
        f'<th scope="row">{escape(row.agent)}</th>'
        f'<td class="num">{_int(row.calls)}</td>'
        f'<td class="num">{_int(row.tokens_in)}</td>'
        f'<td class="num">{_int(row.tokens_out)}</td>'
        f'<td class="num">{dollars(row.cost_micro_usd)}</td>'
        '<td class="share">'
        f'<progress value="{_share(row.cost_micro_usd, total)}" max="100" '
        'aria-label="Part du coût total"></progress>'
        f"<span>{_share(row.cost_micro_usd, total)}%</span></td>"
        "</tr>"
        for row in report.rows
    )
    return (
        '<section aria-label="Détail par agent"><div class="table-wrap"><table>'
        f"<caption>Dépenses des {report.days} derniers jours (UTC)</caption>"
        "<thead><tr>"
        '<th scope="col">Projet</th><th scope="col">Agent</th>'
        '<th scope="col" class="num">Appels</th>'
        '<th scope="col" class="num">Tokens en entrée</th>'
        '<th scope="col" class="num">Tokens en sortie</th>'
        '<th scope="col" class="num">Coût (USD)</th>'
        '<th scope="col">Part du coût</th>'
        "</tr></thead>"
        f"<tbody>{body}</tbody>"
        "<tfoot><tr>"
        '<th scope="row" colspan="2">Total</th>'
        f'<td class="num">{_int(report.total_calls)}</td>'
        f'<td class="num">{_int(report.total_tokens_in)}</td>'
        f'<td class="num">{_int(report.total_tokens_out)}</td>'
        f'<td class="num">{dollars(total)}</td>'
        "<td></td>"
        "</tr></tfoot>"
        "</table></div></section>"
    )


def render_dashboard(report: UsageReport) -> str:
    note = ""
    if report.uses_mock_prices:
        note = (
            '<p class="note">Une partie de ces coûts est calculée avec les prix fictifs du '
            "faux fournisseur : ce ne sont pas des dépenses réelles.</p>"
        )
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Dépenses par agent – LLM Gateway</title>"
        f'<style>{STYLE}</style></head><body><div class="page">'
        '<header class="top"><a class="logo" href="/dashboard">LLM Gateway<sup>˚</sup></a>'
        f"{_nav(report.days)}</header>"
        "<main>"
        '<section class="hero">'
        f'<div class="framed">{_corners("tl", "bl")}'
        f"<h1>Dépenses<br>par agent{_checker()}</h1>"
        f'<p class="lead">Période : {report.days} derniers jours, en UTC.</p></div>'
        f'<div class="framed feature">{_corners("tl", "tr", "bl", "br")}{GLOBE}'
        '<p class="tagline">Chaque appel mesuré.<br>Chaque coût attribué.</p></div>'
        "</section>"
        f"{note}{_kpis(report)}{_table(report)}"
        "</main>"
        "<footer>LLM Gateway — dépenses en USD, période en UTC</footer>"
        "</div></body></html>"
    )
