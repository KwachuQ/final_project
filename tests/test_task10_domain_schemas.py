from app.schemas import (
    AssessmentCreateResponse,
    AssessmentDetail,
    AssessmentSummary,
    ScoredSystem,
    StrategyEnum,
    SystemInventory,
    SystemTypeEnum,
    WaveEnum,
)


def test_system_type_enum_values():
    assert set(SystemTypeEnum) == {
        SystemTypeEnum.web_app,
        SystemTypeEnum.database,
        SystemTypeEnum.batch_job,
        SystemTypeEnum.file_server,
    }


def test_system_inventory_accepts_valid_data():
    si = SystemInventory(
        system_name="erp",
        system_type="web_app",
        operating_system="linux",
        language="python",
        num_users=100,
        data_size_gb=10.0,
        availability="high",
        has_compliance=False,
        is_vendor_software=False,
    )
    assert si.system_name == "erp"
    assert si.system_type == SystemTypeEnum.web_app


def test_scored_system_fields():
    ss = ScoredSystem(
        system_name="erp",
        system_type="web_app",
        composite_score=5.0,
        complexity_score=3.0,
        cloud_fit_score=7.0,
        risk_score=4.0,
        wave="standard",
        recommended_strategy="rehost",
        effort_min=10,
        effort_max=30,
    )
    assert ss.wave == WaveEnum.standard
    assert ss.recommended_strategy == StrategyEnum.rehost


def test_assessment_summary_fields():
    from datetime import datetime

    s = AssessmentSummary(id=1, name="test", created_at=datetime.now(), system_count=5)
    assert s.system_count == 5


def test_assessment_detail_fields():
    from datetime import datetime

    ss = ScoredSystem(
        system_name="erp",
        system_type="web_app",
        composite_score=5.0,
        complexity_score=3.0,
        cloud_fit_score=7.0,
        risk_score=4.0,
        wave="standard",
        recommended_strategy="rehost",
        effort_min=10,
        effort_max=30,
    )
    d = AssessmentDetail(
        id=1,
        name="test",
        created_at=datetime.now(),
        system_count=1,
        s3_key="uploads/1/test.csv",
        scored_systems=[ss],
    )
    assert d.s3_key == "uploads/1/test.csv"
    assert len(d.scored_systems) == 1


def test_assessment_create_response_fields():
    from datetime import datetime

    ss = ScoredSystem(
        system_name="erp",
        system_type="web_app",
        composite_score=5.0,
        complexity_score=3.0,
        cloud_fit_score=7.0,
        risk_score=4.0,
        wave="standard",
        recommended_strategy="rehost",
        effort_min=10,
        effort_max=30,
    )
    r = AssessmentCreateResponse(
        id=1,
        name="test",
        created_at=datetime.now(),
        system_count=1,
        s3_key="uploads/1/test.csv",
        scored_systems=[ss],
    )
    assert r.id == 1
    assert r.name == "test"