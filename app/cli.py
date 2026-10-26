import argparse
import sys
from decimal import Decimal

from sqlalchemy import Connection, text

from app.agents import AgentExistsError, create_agent
from app.db.session import get_engine
from app.pricing import MICRO


def dollars(micro_usd: int) -> str:
    """Affiche des micro-dollars en dollars, avec six decimales."""
    return f"{Decimal(micro_usd) / Decimal(MICRO):.6f}"


def render_report(conn: Connection, days: int) -> str:
    rows = conn.execute(
        text(
            """
            SELECT p.name AS project, a.name AS agent, count(*) AS calls,
                   coalesce(sum(e.tokens_in), 0) AS tokens_in,
                   coalesce(sum(e.tokens_out), 0) AS tokens_out,
                   coalesce(sum(e.cost_micro_usd), 0) AS cost
            FROM usage_events e
            JOIN agents a ON a.id = e.agent_id
            JOIN projects p ON p.id = e.project_id
            WHERE e.occurred_at >= now() - (:days * interval '1 day')
            GROUP BY p.name, a.name
            ORDER BY sum(e.cost_micro_usd) DESC, a.name
            """
        ),
        {"days": days},
    ).all()
    title = f"Depenses des {days} derniers jours (UTC)"
    if not rows:
        return f"{title}\nAucun appel enregistre sur cette periode."
    header = ("Projet", "Agent", "Appels", "Tokens entree", "Tokens sortie", "Cout (USD)")
    lines = [
        (r.project, r.agent, str(r.calls), str(r.tokens_in), str(r.tokens_out), dollars(r.cost))
        for r in rows
    ]
    total = (
        "Total",
        "",
        str(sum(r.calls for r in rows)),
        str(sum(r.tokens_in for r in rows)),
        str(sum(r.tokens_out for r in rows)),
        dollars(sum(r.cost for r in rows)),
    )
    table = [header, *lines, total]
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]

    def fmt(row: tuple[str, ...]) -> str:
        cells = [row[i].ljust(widths[i]) if i < 2 else row[i].rjust(widths[i]) for i in range(6)]
        return "  ".join(cells).rstrip()

    return "\n".join([title, fmt(header), *(fmt(r) for r in lines), fmt(total)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-agent", help="Creer un agent et sa cle d'API")
    create.add_argument("--project", required=True)
    create.add_argument("--agent", required=True)
    report = commands.add_parser("report", help="Afficher les depenses par agent")
    report.add_argument("--days", type=int, default=7)
    args = parser.parse_args(argv)

    engine = get_engine()
    if args.command == "create-agent":
        try:
            with engine.begin() as conn:
                key = create_agent(conn, args.project, args.agent)
        except (AgentExistsError, ValueError) as error:
            print(f"Erreur : {error}", file=sys.stderr)
            return 1
        print(f"Agent cree : {args.agent} (projet {args.project})")
        print(f"Cle d'API, affichee une seule fois : {key}")
        return 0
    with engine.connect() as conn:
        print(render_report(conn, args.days))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
