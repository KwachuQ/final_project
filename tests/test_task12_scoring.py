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

def test_rehost_strategy():
    result = score_systems([_make_system(system_type="web_app", operating_system="linux", language="python")])
    assert result[0].recommended_strategy.value == "rehost"

def test_replatform_strategy():
    result = score_systems([_make_system(system_type="database", operating_system="linux", language="java")])
    assert result[0].recommended_strategy.value == "replatform"

def test_refactor_strategy():
    result = score_systems([_make_system(system_type="database", operating_system="windows", language="cpp")])
    assert result[0].recommended_strategy.value == "refactor"
    
def test_scores_are_bounded_0_to_10():
    result = score_systems([_make_system()])
    for s in result:
        assert 0 <= s.complexity_score <= 10
        assert 0 <= s.cloud_fit_score <= 10
        assert 0 <= s.risk_score <= 10
        assert 0 <= s.composite_score <= 10

def test_wave_boundaries_quick_win():
    # complexity=(python=3+file_server=2)/2=2.5, cloud_fit=(linux=10+file_server=2)/2=6.0
    # risk: users<100→+1, data<10→+1, low→+0 = 2
    # composite = 2.5×0.3 + 6.0×0.4 + 2×0.3 = 0.75+2.4+0.6 = 3.75 → quick_win
    result = score_systems([_make_system(
        system_type="file_server",
        operating_system="linux",
        language="python",
        num_users=50,
        data_size_gb=5,
        availability="low",
    )])
    assert result[0].wave.value == "quick_win"

def test_wave_boundaries_standard():
    # complexity=(python=3+web_app=5)/2=4.0, cloud_fit=(windows=4+web_app=9)/2=6.5
    # risk: 100≤users<1000→+2, 10≤data<100→+2, low→+0 = 4
    # composite = 4.0×0.3 + 6.5×0.4 + 4×0.3 = 1.2+2.6+1.2 = 5.0 → standard
    result = score_systems([_make_system(
        system_type="web_app",
        operating_system="windows",
        language="python",
        num_users=262,
        data_size_gb=50,
        availability="low",
    )])
    assert result[0].wave.value == "standard"

def test_wave_boundaries_complex():
    # complexity=(cpp=9+database=8)/2=8.5, cloud_fit=(windows=4+database=8)/2=6.0
    # risk: users≥1000→+3, data≥100→+3, high→+2 = 8
    # composite = 8.5×0.3 + 6.0×0.4 + 8×0.3 = 2.55+2.4+2.4 = 7.35 → complex
    result = score_systems([_make_system(
        system_type="database",
        operating_system="windows",
        language="cpp",
        num_users=1881,
        data_size_gb=500,
        availability="high",
    )])
    assert result[0].wave.value == "complex"

def test_composite_formula():
    result = score_systems([_make_system()])
    
    expected_composite = (
        0.3 * result[0].complexity_score +
        0.4 * result[0].cloud_fit_score +
        0.3 * result[0].risk_score
    )
    assert result[0].composite_score == expected_composite
