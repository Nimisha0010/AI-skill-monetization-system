from flask import Blueprint, render_template, request, redirect, url_for, jsonify

from . import db
from .models import Profile, ProfileSkill, SkillCatalog
from .engine import run_prediction

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    catalog = SkillCatalog.query.order_by(SkillCatalog.category, SkillCatalog.name).all()
    categories = sorted({c.category for c in catalog})
    return render_template("index.html", catalog=catalog, categories=categories)


@bp.route("/predict", methods=["POST"])
def predict():
    names = request.form.getlist("skill_name[]")
    profs = request.form.getlist("skill_proficiency[]")
    interests = request.form.getlist("interests[]")
    experience = float(request.form.get("experience", 1.0))

    entries = []
    for name, prof in zip(names, profs):
        name = (name or "").strip()
        if name:
            try:
                proficiency = int(prof)
            except (TypeError, ValueError):
                proficiency = 3
            entries.append({"name": name, "proficiency": max(1, min(5, proficiency))})

    if not entries:
        return redirect(url_for("main.index"))

    profile = Profile(experience_multiplier=experience)
    profile.interests = interests
    db.session.add(profile)
    db.session.flush()  # get profile.id before commit

    for e in entries:
        db.session.add(ProfileSkill(profile_id=profile.id, name=e["name"], proficiency=e["proficiency"]))

    results = run_prediction(entries, experience, interests)
    profile.results = results

    db.session.commit()

    return redirect(url_for("main.dashboard", profile_id=profile.id))


@bp.route("/dashboard/<int:profile_id>")
def dashboard(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    return render_template("dashboard.html", profile=profile, results=profile.results)


@bp.route("/api/skills")
def api_skills():
    """JSON list of the catalog, e.g. for the autocomplete field or a separate frontend."""
    catalog = SkillCatalog.query.order_by(SkillCatalog.category, SkillCatalog.name).all()
    return jsonify([{"name": c.name, "category": c.category} for c in catalog])


@bp.route("/api/predict", methods=["POST"])
def api_predict():
    """Stateless JSON version of /predict — nothing is saved to the database.

    Expected body:
    {
      "skills": [{"name": "Python", "proficiency": 4}, ...],
      "experience": 1.25,
      "interests": ["Programming & Tech"]
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    raw_entries = data.get("skills", [])
    experience = float(data.get("experience", 1.0))
    interests = data.get("interests", [])

    entries = []
    for e in raw_entries:
        name = str(e.get("name", "")).strip()
        if not name:
            continue
        proficiency = int(e.get("proficiency", 3))
        entries.append({"name": name, "proficiency": max(1, min(5, proficiency))})

    if not entries:
        return jsonify({"error": "no skills provided"}), 400

    results = run_prediction(entries, experience, interests)
    return jsonify(results)
