"""Scoring engine for the AI Skill Monetization Predictor.

Matching: a user can type any skill name in free text. We match it against
the skill_catalog table three ways, cheapest first:
  1. exact (case-insensitive) name match
  2. substring containment either direction
  3. TF-IDF character-ngram cosine similarity, so close spellings/phrasings
     ("Node.js dev", "front end design") still land on a sensible catalog row

Anything below the similarity threshold is scored as an "emerging" skill
with a conservative default, rather than dropped, so it still shows up in
results.

Everything below is a transparent, explainable heuristic — no black box.
That's a deliberate choice for a tool whose whole point is to be trusted
with someone's career decisions; see README 'Ideas to extend this' for how
you'd graduate this to a trained model.
"""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import SkillCatalog

SIMILARITY_THRESHOLD = 0.25
DEFAULT_DEMAND = 4
DEFAULT_LOW = 12
DEFAULT_HIGH = 30
DEFAULT_CATEGORY = "Emerging"
DEFAULT_PLATFORMS = ["Upwork", "Fiverr"]


def catalog_dataframe():
    rows = SkillCatalog.query.all()
    return pd.DataFrame([{
        "name": r.name,
        "category": r.category,
        "demand": r.demand,
        "low": r.hourly_low,
        "high": r.hourly_high,
        "platforms": r.platform_list(),
        "trend": r.trend,
        "product": r.product_idea,
        "pairs": r.pair_list(),
    } for r in rows])


def _match_skill(name, df):
    n = name.strip().lower()
    if not n or df.empty:
        return None

    exact = df[df["name"].str.lower() == n]
    if not exact.empty:
        return exact.iloc[0]

    contains = df[df["name"].str.lower().apply(lambda x: x in n or n in x)]
    if not contains.empty:
        return contains.iloc[0]

    corpus = (df["name"] + " " + df["category"]).tolist()
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    tfidf = vectorizer.fit_transform(corpus + [name])
    sims = cosine_similarity(tfidf[-1], tfidf[:-1]).flatten()
    best_idx = int(np.argmax(sims))
    if sims[best_idx] >= SIMILARITY_THRESHOLD:
        return df.iloc[best_idx]
    return None


def score_entries(entries, experience_multiplier, df):
    scored = []
    for e in entries:
        match = _match_skill(e["name"], df)
        demand = int(match["demand"]) if match is not None else DEFAULT_DEMAND
        low = int(match["low"]) if match is not None else DEFAULT_LOW
        high = int(match["high"]) if match is not None else DEFAULT_HIGH
        category = match["category"] if match is not None else DEFAULT_CATEGORY
        platforms = list(match["platforms"]) if match is not None else DEFAULT_PLATFORMS
        product = match["product"] if match is not None else None
        pairs = list(match["pairs"]) if match is not None else []

        prof_frac = e["proficiency"] / 5
        fit = min(100, round(demand * 10 * prof_frac * experience_multiplier))

        scored.append({
            "name": e["name"],
            "proficiency": e["proficiency"],
            "matched": match is not None,
            "category": category,
            "demand": demand,
            "low": low,
            "high": high,
            "fit": fit,
            "weighted_low": low * prof_frac * experience_multiplier,
            "weighted_high": high * prof_frac * experience_multiplier,
            "platforms": platforms,
            "product": product,
            "pairs": pairs,
        })
    return sorted(scored, key=lambda x: -x["fit"])


def compute_coverage(scored):
    totals = {}
    for s in scored:
        totals[s["category"]] = totals.get(s["category"], 0) + s["fit"]
    if not totals:
        return []
    mx = max(totals.values()) or 1
    rows = [{"category": k, "pct": round(v / mx * 100)} for k, v in totals.items()]
    return sorted(rows, key=lambda x: -x["pct"])


def _product_estimate(t, which):
    rate = t["low"] if which == "low" else t["high"]
    units = 3 + t["demand"] + t["proficiency"] * 2
    return rate * units * 0.4


def compute_paths(scored, interests):
    if not scored:
        return []

    top = scored[:4]
    avg_fit = round(sum(s["fit"] for s in scored) / len(scored))
    boost = lambda cat: 12 if cat in interests else 0  # noqa: E731
    paths = []

    t = top[0]
    paths.append({
        "title": f"Freelance {t['name']}",
        "desc": (f"Take on paid client work in {t['name'].lower()} through established "
                 "marketplaces — the fastest path from skill to first dollar."),
        "fit": min(100, t["fit"] + boost(t["category"])),
        "low": round(t["weighted_low"] * 40),
        "high": round(t["weighted_high"] * 60),
        "platforms": " · ".join(t["platforms"]),
    })

    product_candidates = [s for s in top if s["product"]]
    t2 = product_candidates[0] if product_candidates else top[0]
    product_line = t2["product"].lower() if t2["product"] else "a template or guide"
    paths.append({
        "title": "Sell a digital product",
        "desc": (f"Package your {t2['name'].lower()} know-how as a one-time product: "
                 f"{product_line}. Sells while you sleep, no hourly ceiling."),
        "fit": min(100, round(t2["fit"] * 0.8) + boost(t2["category"])),
        "low": round(_product_estimate(t2, "low")),
        "high": round(_product_estimate(t2, "high")),
        "platforms": "Gumroad · Etsy · your own site",
    })

    t3 = top[0]
    paths.append({
        "title": "Teach or coach others",
        "desc": ("Turn your strongest skill into lessons, cohorts, or 1:1 coaching — "
                 "leverages your proficiency more than your hours."),
        "fit": min(100, round(t3["fit"] * 0.75) + boost("Teaching & Coaching")),
        "low": round(t3["weighted_low"] * 20),
        "high": round(t3["weighted_high"] * 35),
        "platforms": "Preply · Outschool · your own cohort",
    })

    if len(scored) >= 3 and avg_fit >= 40:
        top3_names = ", ".join(s["name"] for s in scored[:3])
        paths.append({
            "title": "Start a small agency",
            "desc": (f"Your skill mix ({top3_names}) covers enough of a service to package "
                     "as an offer for small businesses, not just hourly gigs."),
            "fit": min(100, avg_fit + 5 + boost("Marketing & Business")),
            "low": round(sum(s["weighted_low"] for s in scored) * 25),
            "high": round(sum(s["weighted_high"] for s in scored) * 35),
            "platforms": "Direct outreach · LinkedIn · referrals",
        })

    return sorted(paths, key=lambda p: -p["fit"])


def compute_gaps(scored, df):
    have = {s["name"].lower() for s in scored}
    cat_counts = {}
    for s in scored:
        cat_counts[s["category"]] = cat_counts.get(s["category"], 0) + 1
    top_cats = [c for c, _ in sorted(cat_counts.items(), key=lambda x: -x[1])[:2]]

    candidates = {}

    for s in scored:
        for p in s["pairs"]:
            if p.lower() in have:
                continue
            row = df[df["name"] == p]
            if not row.empty:
                r = row.iloc[0]
                candidates.setdefault(r["name"], {
                    "row": r,
                    "why": f"Pairs naturally with your {s['name']} — clients often want both together.",
                })

    if top_cats and not df.empty:
        cat_df = (
            df[df["category"].isin(top_cats) & ~df["name"].str.lower().isin(have)]
            .sort_values("demand", ascending=False)
            .head(3)
        )
        for _, r in cat_df.iterrows():
            candidates.setdefault(r["name"], {
                "row": r,
                "why": f"High demand in {r['category'].lower()}, the category you're strongest in.",
            })

    ranked = sorted(candidates.values(), key=lambda c: -c["row"]["demand"])[:4]
    return [{"name": c["row"]["name"], "demand": int(c["row"]["demand"]), "why": c["why"]} for c in ranked]


def compute_roadmap(paths, gaps, scored):
    steps = []
    if paths:
        first_platform = paths[0]["platforms"].split(" · ")[0]
        top_skill = scored[0]["name"] if scored else "your top skill"
        steps.append({
            "title": f"Set up on {first_platform}",
            "body": (f"Build a focused profile around {top_skill} — one clear offer beats a "
                     "generalist bio. Add 2–3 samples, even mocked-up ones, before you pitch."),
        })
    if gaps:
        steps.append({
            "title": f"Spend a week on {gaps[0]['name']}",
            "body": f"{gaps[0]['why']} A working-level grasp is enough to widen what you can pitch for.",
        })
    steps.append({
        "title": "Ship one proof piece",
        "body": ("Publish a small, finished example of your best-fit path — a sample project, "
                 "a mini digital product, or a single client outcome — so people can see the "
                 "work before they buy it."),
    })
    return steps


def run_prediction(entries, experience_multiplier, interests):
    df = catalog_dataframe()
    scored = score_entries(entries, experience_multiplier, df)
    paths = compute_paths(scored, interests)
    coverage = compute_coverage(scored)
    gaps = compute_gaps(scored, df)
    roadmap = compute_roadmap(paths, gaps, scored)

    total_low = round(sum(s["weighted_low"] for s in scored) * 20)
    total_high = round(sum(s["weighted_high"] for s in scored) * 30)
    ledger_score = round(sum(s["fit"] for s in scored) / len(scored)) if scored else 0

    return {
        "scored": scored,
        "paths": paths,
        "coverage": coverage,
        "gaps": gaps,
        "roadmap": roadmap,
        "total_low": total_low,
        "total_high": total_high,
        "ledger_score": ledger_score,
    }
