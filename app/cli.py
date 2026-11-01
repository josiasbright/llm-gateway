import argparse
import sys

from sqlalchemy import Connection

from app.agents import AgentExistsError, create_agent
from app.db.session import get_engine
from app.reporting import dollars, fetch_usage


def render_report(conn: Connection, days: int) -> str:
    report = fetch_usage(conn, days)
    title = f"Depenses des {days} derniers jours (UTC)"
    if not report.rows:
        return f"{title}\nAucun appel enregistre sur cette periode."
    header = ("Projet", "Agent", "Appels", "Tokens entree", "Tokens sortie", "Cout (USD)")
    lines = [
        (
            r.project,
            r.agent,
            str(r.calls),
            str(r.tokens_in),
            str(r.tokens_out),
            dollars(r.cost_micro_usd),
        )
        for r in report.rows
    ]
    total = (
        "Total",
        "",
        str(report.total_calls),
        str(report.total_tokens_in),
        str(report.total_tokens_out),
        dollars(report.total_cost_micro_usd),
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
