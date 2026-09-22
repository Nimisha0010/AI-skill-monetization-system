# AI Skill Monetization Predictor 

A Flask + SQLite (swappable for MySQL/Postgres) rebuild of the Skill Ledger
dashboard: enter your skills, get ranked monetization paths, a category
coverage breakdown, skill-gap suggestions, and a 30-day roadmap.

## What's under the hood

- **Flask** app factory (`app/__init__.py`) + blueprint routes (`app/routes.py`)
- **Flask-SQLAlchemy** models (`app/models.py`) — a `skill_catalog` market-data
  table, and `profile` / `profile_skill` tables that persist every prediction
  run so results are shareable via a permanent `/dashboard/<id>` link
- **Prediction engine** (`app/engine.py`) using **pandas** for scoring math and
  **scikit-learn**'s `TfidfVectorizer` + cosine similarity to fuzzy-match
  whatever a user types (e.g. "front end dev") against the catalog, so typos
  or phrasing differences still resolve sensibly
- Server-rendered **Jinja2** templates, no JS framework — one small vanilla
  JS file (`app/static/js/app.js`) just builds the "add a skill" row list
  before a normal form POST
- A small **JSON API** (`/api/skills`, `/api/predict`) so a separate frontend
  (React, mobile app, etc.) could drive the same engine

## Project layout

```
ai-skill-monetization-flask/
├── run.py                  # entry point (flask run / python run.py)
├── config.py                # DB URL, secret key (env-driven)
├── requirements.txt
└── app/
    ├── __init__.py          # app factory, seeds the catalog on first run
    ├── models.py             # SkillCatalog, Profile, ProfileSkill
    ├── data.py                # seed market data for SkillCatalog
    ├── engine.py               # matching + scoring + recommendation logic
    ├── routes.py                # / , /predict , /dashboard/<id> , /api/*
    ├── templates/
    │   ├── base.html
    │   ├── index.html          # input form
    │   └── dashboard.html       # results page
    └── static/
        ├── css/style.css
        └── js/app.js
```

## Setup

```bash
cd ai-skill-monetization-flask
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Visit `http://127.0.0.1:5000`. A `skill_predictor.db` SQLite file is created
automatically in `instance/` on first run, with the skill catalog pre-seeded.

To point at MySQL or Postgres instead, set `DATABASE_URL` before running,
e.g.:

```bash
export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/skill_predictor"
```
(add `PyMySQL` or `psycopg2-binary` to `requirements.txt` for the driver you pick)

## Using the JSON API

```bash
curl -X POST http://127.0.0.1:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "skills": [{"name": "Python", "proficiency": 4}, {"name": "Copywriting", "proficiency": 3}],
    "experience": 1.25,
    "interests": ["Programming & Tech"]
  }'
```

## Ideas to extend this

**Make the data real instead of seeded**
- Swap `app/data.py`'s static list for a scheduled job that pulls live rate
  and demand data from freelance-platform APIs (Upwork, Fiverr's public
  category pages, job-board APIs) and refreshes `skill_catalog` nightly.
- Track *historical* demand per skill (a `skill_history` table) so the
  dashboard can show trend lines, not just a static "rising/stable" tag.

**Grow the "AI" beyond heuristics**
- Replace the TF-IDF matcher with sentence embeddings (e.g. a small
  `sentence-transformers` model) for better free-text skill matching —
  "I can code websites" → Web Development.
- Train a real regression/ranking model on actual outcome data (what users
  who entered similar skills actually earned) once you have enough of it,
  and fall back to the current heuristic engine when data is thin.
- Add a skill-gap recommender using collaborative filtering (`scikit-learn`'s
  `NearestNeighbors` over a user × skill matrix) once you have enough saved
  profiles to learn co-occurrence patterns beyond the hand-curated `pairs`.

**Product features**
- User accounts (Flask-Login) so people can save multiple skill sets over
  time and track how their ledger score changes as they upskill.
- Export a dashboard as a PDF/shareable image (`weasyprint` or a headless
  browser) for a resume or portfolio attachment.
- Email/notify users when a skill they have jumps in demand.
- A public leaderboard or benchmark: "how does my ledger score compare to
  others in Design & Creative?" — needs anonymized aggregate stats.
- Admin view for editing `skill_catalog` rows without touching code.

**Monetization ideas for the product itself**
- Free tier: one prediction, no save. Paid tier: saved history, PDF export,
  deeper skill-gap analysis, and priority access to newly seeded skills.
- Affiliate links on the recommended platforms (Upwork, Preply, Gumroad,
  etc.) in the "Monetization paths" section.
- A "done for you" upsell: a real freelance-profile or digital-product
  review service once someone's dashboard shows a clear top path.

**Ops**
- Add `Flask-Migrate` (Alembic) once the schema needs to change without
  wiping data.
- Add basic rate limiting on `/api/predict` if you expose it publicly.
- Containerize with a `Dockerfile` + `docker-compose.yml` (app + MySQL) for
  easy deployment to Render, Railway, Fly.io, or a VPS.
