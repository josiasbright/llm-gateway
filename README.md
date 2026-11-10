# LLM Gateway

Proxy compatible avec les API d'IA habituelles, qui mesure et attribue le coût de chaque appel, agent par agent.

## Fonctionnalités

- Route `POST /v1/chat/completions` au format des API d'IA habituelles.
- Une clé d'API distincte par agent, stockée sous forme d'empreinte uniquement.
- Calcul du coût de chaque appel en micro-dollars entiers, à partir d'une grille de prix datée.
- Journal des appels en ajout seul, protégé par des droits de base de données.
- Page web des dépenses par projet et par agent, protégée par mot de passe.
- Route `GET /api/usage` : les mêmes chiffres en JSON.
- Commandes pour créer un agent et afficher les dépenses.

## Limites actuelles

- Un seul fournisseur : un faux modèle (`mock-small`, `mock-large`) avec des prix fictifs.
- Pas de streaming.
- Pas de budgets bloquants ni d'alertes.
- Pas de limitation du nombre d'essais de connexion à la page web.
- Conçu pour une seule instance.

## Fonctionnement

```text
Application  ->  LLM Gateway  ->  Fournisseur d'IA
                      |
                      v
                 PostgreSQL
        (agents, clés, prix, journal des appels)
```

## Prérequis

- Python 3.12 ou plus récent
- uv : `pip install uv`
- Docker Desktop
- Git

## Installation

```powershell
git clone https://github.com/josiasbright/llm-gateway.git
cd llm-gateway
copy .env.example .env
python -m uv sync
docker compose up -d db
python -m uv run python -m alembic upgrade head
```

## Configuration

Les réglages se trouvent dans `.env`. Ce fichier n'est jamais versionné.

| Variable | Rôle |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Identifiants de la base lancée par Docker Compose |
| `POSTGRES_PORT` | Port de la base sur la machine hôte |
| `DATABASE_URL` | Adresse de connexion à la base utilisée par l'application |
| `ADMIN_PASSWORD` | Mot de passe de la page web, utilisateur `admin` |
| `PORT` | Port d'écoute du serveur dans l'image Docker (8000 par défaut) |
| `APP_PORT` | Port de l'application sur la machine hôte avec Docker Compose (8000 par défaut) |

La page web reste fermée tant que `ADMIN_PASSWORD` est vide ou garde la valeur d'exemple.

## Utilisation

Créer un agent et sa clé. La clé n'est affichée qu'une seule fois.

```powershell
python -m uv run python -m app.cli create-agent --project demo --agent support-bot
```

Démarrer le serveur.

```powershell
python -m uv run python -m uvicorn app.main:app --port 8000
```

Appeler le serveur.

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer gw_..." \
  -H "Content-Type: application/json" \
  -d '{"model":"mock-small","messages":[{"role":"user","content":"Bonjour"}]}'
```

Afficher les dépenses.

```powershell
python -m uv run python -m app.cli report --days 7
```

## Interfaces

| Adresse | Accès | Contenu |
| --- | --- | --- |
| `/dashboard` | `admin` et `ADMIN_PASSWORD` | Dépenses par agent sur 7, 30 ou 90 jours |
| `/api/usage?days=7` | `admin` et `ADMIN_PASSWORD` | Mêmes données en JSON |
| `/v1/chat/completions` | Clé d'agent `Bearer` | Appel d'un modèle |
| `/healthz` | Public | État du serveur |
| `/docs` | Public | Documentation interactive de l'API |

## Docker

```powershell
docker compose up -d --build
```

Cette commande construit l'image, puis démarre la base et l'application. `ADMIN_PASSWORD` doit avoir une vraie valeur dans `.env`, sinon Compose s'arrête avec un message. L'application répond sur `http://127.0.0.1:8000` (ou sur le port `APP_PORT`).

L'image applique les migrations au démarrage, puis lance le serveur sans droits d'administrateur.

Pour lancer le serveur à la main (section Utilisation), arrêter d'abord le conteneur de l'application : `docker compose stop app`.

## Développement

```powershell
python -m uv run ruff format --check .
python -m uv run ruff check .
python -m uv run mypy
python -m uv run pytest
python -m uv run pip-audit
```

Les tests créent et suppriment leurs propres bases temporaires. L'utilisateur PostgreSQL doit pouvoir créer des bases.

## Structure

```text
app/          serveur, sécurité, coûts, fournisseurs, tableau de bord, commandes
migrations/   migrations Alembic
tests/        tests automatiques
docs/         documents de conception
```

## Sécurité

- Les clés d'agents sont stockées sous forme d'empreinte SHA-256.
- Le journal des appels est en ajout seul : le rôle applicatif ne peut ni le modifier ni le supprimer.
- La page web échappe les noms, envoie des en-têtes de protection et refuse de s'ouvrir sans mot de passe réel.
- `.env` est exclu du dépôt et de l'image Docker.

## Licence

Aucune licence : le code est public pour être consulté, aucune autorisation de réutilisation n'est accordée.