from app.schemas import SystemInventory
from app.services.scoring import score_systems

def _make_system(**overrides):
    defaults = dict(
        system_name="test", system_type="web_app", operating_system="linux",
        language="python", num_users=100, data_size_gb=10.0,
        availability="high", has_compliance=False, is_vendor_software=False,
    )
    defaults.update(overrides)
    return SystemInventory(**defaults)

def test_retire_strategy():
    result = score_systems([_make_system(num_users=0)])
    assert result[0].recommended_strategy.value == "retire"
    assert result[0].wave.value == "quick_win"
    assert result[0].effort_min == 0
    assert result[0].effort_max == 0

def test_repurchase_strategy():
    result = score_systems([_make_system(is_vendor_software=True)])
    assert result[0].recommended_strategy.value == "repurchase"

def test_retain_strategy():
    result = score_systems([_make_system(language="cobol", has_compliance=True)])
    assert result[0].recommended_strategy.value == "retain"

def test_scores_are_bounded_0_to_10():
    result = score_systems([_make_system()])
    for s in result:
        assert 0 <= s.complexity_score <= 10
        assert 0 <= s.cloud_fit_score <= 10
        assert 0 <= s.risk_score <= 10
        assert 0 <= s.composite_score <= 10