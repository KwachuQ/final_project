from datetime import datetime
from enum import Enum

from pydantic import BaseModel, model_validator, ConfigDict


# ── Enums ────────────────────────────────────────────────────────────

class SystemTypeEnum(str, Enum):
    web_app = "web_app"
    database = "database"
    batch_job = "batch_job"
    file_server = "file_server"


class OperatingSystemEnum(str, Enum):
    linux = "linux"
    windows = "windows"


class LanguageEnum(str, Enum):
    python = "python"
    java = "java"
    dotnet = "dotnet"
    cobol = "cobol"
    cpp = "cpp"


class AvailabilityEnum(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class WaveEnum(str, Enum):
    quick_win = "quick_win"
    standard = "standard"
    complex = "complex"


class StrategyEnum(str, Enum):
    retire = "retire"
    repurchase = "repurchase"
    retain = "retain"
    rehost = "rehost"
    replatform = "replatform"
    refactor = "refactor"


# ── Auth Schemas ─────────────────────────────────────────────────────


class UserRegister(BaseModel):
    username: str
    password: str
    password_repeat: str

    @model_validator(mode="after")
    def passwords_match(self) -> "UserRegister":
        if self.password != self.password_repeat:
            raise ValueError("passwords do not match")
        return self


class UserResponse(BaseModel):
    user_id: int
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class ErrorResponse(BaseModel):
    detail: str


# ── Domain Schemas ───────────────────────────────────────────────────


class SystemInventory(BaseModel):
    system_name: str
    system_type: SystemTypeEnum
    operating_system: OperatingSystemEnum
    language: LanguageEnum
    num_users: int
    data_size_gb: float
    availability: AvailabilityEnum
    has_compliance: bool
    is_vendor_software: bool


class ScoredSystem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    system_name: str
    system_type: SystemTypeEnum
    composite_score: float
    complexity_score: float
    cloud_fit_score: float
    risk_score: float
    wave: WaveEnum
    recommended_strategy: StrategyEnum
    effort_min: int
    effort_max: int


class AssessmentSummary(BaseModel):
    id: int
    name: str
    created_at: datetime
    system_count: int


class AssessmentDetail(BaseModel):
    id: int
    name: str
    created_at: datetime
    system_count: int
    s3_key: str
    scored_systems: list[ScoredSystem]


class AssessmentCreateResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    system_count: int
    s3_key: str
    scored_systems: list[ScoredSystem]