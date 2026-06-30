from app.schemas import ScoredSystem
from app.schemas import WaveEnum
from app.schemas import StrategyEnum
from app.schemas import SystemInventory

# Weight constants for scoring system

COMPLEXITY_W = 0.30
CLOUD_FIT_W = 0.40
RISK_W = 0.30

def _compute_complexity_score(system_inventory: SystemInventory) -> float:
    """Compute a complexity score (1–10) based on language and system type.

    Higher values indicate a more complex system that will be harder to migrate.

    Args:
        system_inventory: The system to evaluate.

    Returns:
        Average of the language complexity score and system-type complexity score.
    """
    
    system_type_complexity = {
    "web_app": 5,
    "database" : 8,
    "batch_job": 7,
    "file_server": 2
    }

    language_complexity = {
    "python": 3,
    "java": 4,
    "dotnet": 5,
    "cobol": 8,
    "cpp": 9    
    }

    lang_score = language_complexity[system_inventory.language.value]
    type_score = system_type_complexity[system_inventory.system_type.value]
    
    return (lang_score + type_score) / 2

def _compute_cloud_fit_score(system_inventory: SystemInventory) -> float:
    """Compute a cloud-fit score (1–10) based on OS and system type.

    Higher values indicate the system is a better candidate for cloud migration.

    Args:
        system_inventory: The system to evaluate.

    Returns:
        Average of the OS fit score and system-type fit score.
    """
    
    system_type_fit = {
    "web_app": 9,
    "database" : 8,
    "batch_job": 7,
    "file_server": 2
    }
    
    operating_system_fit = {
    "linux": 10,
    "windows": 4
    }

    os_score = operating_system_fit[system_inventory.operating_system.value]
    type_score = system_type_fit[system_inventory.system_type.value]
    
    return (os_score + type_score) / 2

def _compute_risk_score(system_inventory: SystemInventory) -> float:
    """Compute a migration risk score based on user count, data size, availability, and compliance.

    Score contributions:
        - num_users:    <100 → +1, <1000 → +2, ≥1000 → +3
        - data_size_gb: <10  → +1, <100  → +2, ≥100  → +3
        - availability: low → +0, medium → +1, high → +2
        - has_compliance: True → +2

    Args:
        system_inventory: The system to evaluate.

    Returns:
        Integer risk score (higher = riskier migration).
    """
    
    risk_score = 0
    if system_inventory.num_users < 100:
        risk_score += 1
    elif system_inventory.num_users < 1000:
        risk_score += 2
    else:                         
        risk_score += 3

    if system_inventory.data_size_gb < 10:
        risk_score += 1
    elif system_inventory.data_size_gb < 100:
        risk_score += 2
    else:                         
        risk_score += 3

    availability_risk = {"high": 2, "medium": 1, "low": 0}
    risk_score += availability_risk[system_inventory.availability.value]

    risk_score += 2 * system_inventory.has_compliance

    return risk_score

def _compute_composite_score(system_inventory: SystemInventory) -> float:
    """Compute the weighted composite score combining complexity, cloud fit, and risk.

    Weights: complexity × 0.30 + cloud_fit × 0.40 + risk × 0.30.

    Args:
        system_inventory: The system to evaluate.

    Returns:
        Weighted composite score as a float.
    """
    return (_compute_complexity_score(system_inventory) * COMPLEXITY_W + 
            _compute_cloud_fit_score(system_inventory) * CLOUD_FIT_W + 
            _compute_risk_score(system_inventory) * RISK_W) 

def _assign_strategy(system_inventory: SystemInventory) -> StrategyEnum:
    """Determine the recommended migration strategy for a system.

    Rules applied in priority order:
        1. retire      — no active users (num_users == 0)
        2. repurchase  — vendor-managed software
        3. retain      — compliance-sensitive system using COBOL or C++
        4. rehost      — low complexity (<5) and good cloud fit (≥7)
        5. replatform  — moderate complexity (<8) and acceptable cloud fit (≥6)
        6. refactor    — high complexity_score and low cloud_fit_score

    Args:
        system_inventory: The system to evaluate.

    Returns:
        A StrategyEnum value for the recommended migration approach.
    """

    complexity = _compute_complexity_score(system_inventory)
    cloud_fit = _compute_cloud_fit_score(system_inventory)

    if system_inventory.num_users == 0:
        return StrategyEnum.retire

    if system_inventory.is_vendor_software:
        return StrategyEnum.repurchase

    if system_inventory.has_compliance and system_inventory.language.value in ("cobol", "cpp"):
        return StrategyEnum.retain

    if complexity < 5 and cloud_fit >= 7:
        return StrategyEnum.rehost

    if complexity < 8 and cloud_fit >= 6:
        return StrategyEnum.replatform

    return StrategyEnum.refactor

def _assign_wave(composite_score: float) -> WaveEnum:
    """Assign a migration wave based on the composite score.

    Thresholds:
        - quick_win: composite_score < 4
        - standard:  4 ≤ composite_score < 7
        - complex:   composite_score ≥ 7

    Args:
        composite_score: Weighted composite score from _compute_composite_score.

    Returns:
        A WaveEnum value indicating when the system should be migrated.
    """
    if composite_score < 4:
        return WaveEnum.quick_win
    elif composite_score < 7:
        return WaveEnum.standard
    else:
        return WaveEnum.complex

def _estimate_effort(strategy: StrategyEnum) -> tuple[int, int]:
    """Estimate the effort range (in person-days) for a given migration strategy.

    Ranges by strategy:
        - retire:     (0, 0)
        - repurchase: (2, 5)
        - retain:     (1, 2)
        - rehost:     (5, 12)
        - replatform: (10, 25)
        - refactor:   (25, 60)

    Args:
        strategy: The recommended migration strategy.

    Returns:
        A (min_days, max_days) tuple.
    """

    if strategy == StrategyEnum.retire:
        return (0, 0)
    
    if strategy == StrategyEnum.repurchase:
        return (2, 5)
    
    if strategy == StrategyEnum.retain:
        return (1, 2)
    
    if strategy == StrategyEnum.rehost:
        return (5, 12)
    
    if strategy == StrategyEnum.replatform:
        return (10, 25)
    
    if strategy == StrategyEnum.refactor:
        return (25, 60)

def score_systems(systems: list[SystemInventory]) -> list[ScoredSystem]:
    """Score and classify a list of systems for cloud migration.

    For each system, computes complexity, cloud-fit, risk, and composite scores,
    then assigns a migration strategy, wave, and effort estimate.
    Systems assigned the 'retire' strategy are always placed in the quick_win wave.

    Args:
        systems: List of SystemInventory objects to evaluate.

    Returns:
        List of ScoredSystem objects with all scoring fields populated.
    """
    scored_list = []
    for system in systems:
        composite_score = _compute_composite_score(system)
        complexity = _compute_complexity_score(system)
        cloud_fit = _compute_cloud_fit_score(system)
        risk = _compute_risk_score(system)
        wave = _assign_wave(composite_score)
        strategy = _assign_strategy(system)
        if strategy == StrategyEnum.retire:
            wave = WaveEnum.quick_win
        effort_min, effort_max = _estimate_effort(strategy)
        scored_list.append(ScoredSystem(
            system_name = system.system_name,
            system_type = system.system_type,
            composite_score = composite_score,
            complexity_score = complexity,
            cloud_fit_score = cloud_fit,
            risk_score = risk,
            wave = wave,
            recommended_strategy = strategy,
            effort_min = effort_min,
            effort_max = effort_max
        ))
    return scored_list