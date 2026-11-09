from app.dashboard import render_dashboard
from app.reporting import UsageReport, UsageRow

ROWS = (
    UsageRow("projet", "agent-a", 3, 10, 20, 75),
    UsageRow("projet", "agent-b", 1, 5, 5, 25),
)


def make_report(
    rows: tuple[UsageRow, ...] = ROWS, days: int = 7, mock: bool = False
) -> UsageReport:
    return UsageReport(days=days, rows=rows, uses_mock_prices=mock)


def test_shares_are_computed_from_the_total() -> None:
    html = render_dashboard(make_report())
    assert 'value="75"' in html
    assert 'value="25"' in html
    assert "<span>75%</span>" in html
    assert "<span>25%</span>" in html


def test_zero_total_does_not_divide_by_zero() -> None:
    rows = (UsageRow("projet", "agent-a", 1, 1, 1, 0),)
    html = render_dashboard(make_report(rows))
    assert "<span>0%</span>" in html


def test_page_loads_nothing_external() -> None:
    html = render_dashboard(make_report())
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html


def test_page_is_in_french() -> None:
    assert '<html lang="fr">' in render_dashboard(make_report())


def test_current_period_is_marked() -> None:
    html = render_dashboard(make_report(days=30))
    assert 'href="/dashboard?days=30" aria-current="page"' in html
    assert html.count(' aria-current="page">') == 1


def test_names_are_escaped() -> None:
    rows = (UsageRow("<i>x</i>", "<b>y</b>", 1, 1, 1, 10),)
    html = render_dashboard(make_report(rows))
    assert "&lt;b&gt;y&lt;/b&gt;" in html
    assert "<b>y</b>" not in html
    assert "<i>x</i>" not in html


def test_empty_report_shows_a_message_and_no_table() -> None:
    html = render_dashboard(make_report(rows=()))
    assert "Aucun appel enregistré" in html
    assert "<table" not in html


def test_decorations_are_hidden_from_assistive_technology() -> None:
    html = render_dashboard(make_report())
    assert 'aria-hidden="true"' in html
