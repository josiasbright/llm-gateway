# LLM Gateway Auto Pilot

Proxy compatible API OpenAI qui mesure, valorise et plafonne les dépenses d'IA par agent et par projet.

État : étape E0 (dépôt, outillage, intégration continue). Aucune fonctionnalité métier pour l'instant.

## Prérequis (Windows)

- Python 3.12 ou plus récent
- Git
- Docker Desktop démarré
- uv (gestionnaire de dépendances) : `pip install uv`

## Démarrage

```powershell
copy .env.example .env        # puis adapter les valeurs si besoin
uv sync                        # crée .venv et installe les dépendances verrouillées
docker compose up -d           # démarre PostgreSQL
docker compose ps              # l'état doit devenir "healthy"
```

## Vérifications (les mêmes que la CI)

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run pip-audit
```

## Règles

- Jamais de secret dans le dépôt. `.env` est ignoré par Git.
- Une étape = une branche = une demande de fusion. La CI doit être verte.
- Les dépendances sont verrouillées dans `uv.lock`. Les mises à jour se font volontairement avec `uv lock --upgrade`.

## Arrêter et nettoyer

```powershell
docker compose down            # arrête PostgreSQL, conserve les données
docker compose down -v         # arrête ET supprime les données (destructif)
```
