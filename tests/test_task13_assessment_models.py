def test_assessment_model_table():
    from app.database import AssessmentModel
    assert AssessmentModel.__tablename__ == "assessments"
    columns = {c.name for c in AssessmentModel.__table__.columns}
    assert {"id", "user_id", "name", "created_at", "system_count", "s3_key"} <= columns

def test_scored_system_model_table():
    from app.database import ScoredSystemModel
    assert ScoredSystemModel.__tablename__ == "scored_systems"
    columns = {c.name for c in ScoredSystemModel.__table__.columns}
    assert {"id", "assessment_id", "system_name", "system_type", "composite_score", "complexity_score", "cloud_fit_score", "risk_score", "wave", "recommended_strategy", "effort_min", "effort_max"} <= columns

def test_assessment_cascade_relationship():
    from app.database import AssessmentModel
    rel = AssessmentModel.__mapper__.relationships["scored_systems"]
    assert "delete" in rel.cascade

def test_user_id_foreign_key():
    from app.database import AssessmentModel
    fks = [fk.target_fullname for fk in AssessmentModel.__table__.c.user_id.foreign_keys]
    assert "users.id" in fks