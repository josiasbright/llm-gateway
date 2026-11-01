"""Page web des depenses par agent : du HTML simple, sans dependance."""

from html import escape

from app.reporting import UsageReport, dollars

PERIODS = (7, 30, 90)

STYLE = """
:root { color-scheme: light dark; }
body { font-family: system-ui, sans-serif; margin: 0; padding: 1.5rem; line-height: 1.5;
       background: #ffffff; color: #1a1a1a; }
main { max-width: 64rem; margin: 0 auto; }
nav ul { list-style: none; display: flex; gap: 1rem; padding: 0; }
nav a { color: #0b4fb3; }
nav a[aria-current="page"] { font-weight: bold; text-decoration: none; color: inherit; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; }
caption { text-align: left; padding: 0.5rem 0; font-weight: bold; }
th, td { border: 1px solid #767676; padding: 0.5rem 0.75rem; text-align: left; }
thead th { background: #e8e8e8; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
tfoot th, tfoot td { font-weight: bold; background: #f3f3f3; }
.note { border-left: 4px solid #8a6d00; padding: 0.5rem 1rem; background: #fff4cc; }
@media (prefers-color-scheme: dark) {
  body { background: #121212; color: #ececec; }
  nav a { color: #8ab4ff; }
  th, td { border-color: #8a8a8a; }
  thead th { background: #2a2a2a; }
  tfoot th, tfoot td { background: #1f1f1f; }
  .note { background: #3a3000; border-color: #e0b400; }
}
"""


def _nav(current_days: int) -> str:
    items = []
    for days in PERIODS:
        current = ' aria-current="page"' if days == current_days else ""
        items.append(f'<li><a href="/dashboard?days={days}"{current}>{days} jours</a></li>')
    return '<nav aria-label="Periode"><ul>' + "".join(items) + "</ul></nav>"


def _table(report: UsageReport) -> str:
    if not report.rows:
        return "<p>Aucun appel enregistré sur cette période.</p>"
    body = "".join(
        "<tr>"
        f"<td>{escape(row.project)}</td>"
        f'<th scope="row">{escape(row.agent)}</th>'
        f'<td class="num">{row.calls}</td>'
        f'<td class="num">{row.tokens_in}</td>'
        f'<td class="num">{row.tokens_out}</td>'
        f'<td class="num">{dollars(row.cost_micro_usd)}</td>'
        "</tr>"
        for row in report.rows
    )
    return (
        '<div class="scroll"><table>'
        f"<caption>Dépenses des {report.days} derniers jours (UTC)</caption>"
        "<thead><tr>"
        '<th scope="col">Projet</th><th scope="col">Agent</th>'
        '<th scope="col" class="num">Appels</th>'
        '<th scope="col" class="num">Tokens en entrée</th>'
        '<th scope="col" class="num">Tokens en sortie</th>'
        '<th scope="col" class="num">Coût (USD)</th>'
        "</tr></thead>"
        f"<tbody>{body}</tbody>"
        "<tfoot><tr>"
        '<th scope="row" colspan="2">Total</th>'
        f'<td class="num">{report.total_calls}</td>'
        f'<td class="num">{report.total_tokens_in}</td>'
        f'<td class="num">{report.total_tokens_out}</td>'
        f'<td class="num">{dollars(report.total_cost_micro_usd)}</td>'
        "</tr></tfoot>"
        "</table></div>"
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
        f"<style>{STYLE}</style></head><body><main>"
        "<h1>Dépenses par agent</h1>"
        f"{_nav(report.days)}{note}{_table(report)}"
        "</main></body></html>"
    )
