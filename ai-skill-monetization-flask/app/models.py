import json
from datetime import datetime
from . import db


class SkillCatalog(db.Model):
    """The market-data table the prediction engine scores user skills against.

    Seeded once at startup from app/data.py. In a production version this is
    where you'd sync in real freelance-platform rates instead of static seed
    data (see README 'Ideas to extend this').
    """
    __tablename__ = "skill_catalog"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    demand = db.Column(db.Integer, nullable=False)          # 1-10 market demand score
    hourly_low = db.Column(db.Integer, nullable=False)      # typical freelance $/hr, low end
    hourly_high = db.Column(db.Integer, nullable=False)     # typical freelance $/hr, high end
    platforms = db.Column(db.String(255))                   # comma-separated
    trend = db.Column(db.String(20))                        # rising | stable | declining
    product_idea = db.Column(db.String(255))                # digital-product suggestion
    pairs = db.Column(db.String(255))                        # comma-separated related skill names

    def platform_list(self):
        return [p.strip() for p in (self.platforms or "").split(",") if p.strip()]

    def pair_list(self):
        return [p.strip() for p in (self.pairs or "").split(",") if p.strip()]


class Profile(db.Model):
    """One prediction run: the experience level + interests + skills a visitor submitted,
    plus a cached copy of the computed results so /dashboard/<id> is shareable and instant."""
    __tablename__ = "profile"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    experience_multiplier = db.Column(db.Float, default=1.0)
    interests_json = db.Column(db.Text, default="[]")
    results_json = db.Column(db.Text)

    skills = db.relationship(
        "ProfileSkill", backref="profile", cascade="all, delete-orphan", lazy=True
    )

    @property
    def interests(self):
        return json.loads(self.interests_json or "[]")

    @interests.setter
    def interests(self, value):
        self.interests_json = json.dumps(value)

    @property
    def results(self):
        return json.loads(self.results_json) if self.results_json else None

    @results.setter
    def results(self, value):
        self.results_json = json.dumps(value)


class ProfileSkill(db.Model):
    __tablename__ = "profile_skill"

    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    proficiency = db.Column(db.Integer, default=3)  # 1-5
