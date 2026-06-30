from collections.abc import Generator
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Boolean, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.settings import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserModel(Base):
    """ORM model for registered users."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    assessments = relationship("AssessmentModel")

class AssessmentModel(Base):
    """ORM model for assessments."""
    
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, default="Untitled")
    created_at = Column(DateTime, default=datetime.utcnow)
    system_count = Column(Integer)
    s3_key = Column(String)

    scored_systems = relationship("ScoredSystemModel", cascade="all, delete-orphan")

class ScoredSystemModel(Base):

    __tablename__ = "scored_systems"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    
    system_name = Column(String, nullable=False)
    system_type = Column(String, nullable=False)
    operating_system = Column(String, nullable=False)
    language = Column(String)
    num_users = Column(Integer)
    data_size_gb = Column(Float)
    availability = Column(String)
    has_compliance = Column(Boolean)
    is_vendor_software = Column(Boolean)

    complexity_score = Column(Float)
    cloud_fit_score = Column(Float)
    risk_score = Column(Float)
    composite_score = Column(Float)

    recommended_strategy = Column(String)
    wave = Column(String)
    effort_min = Column(Integer)
    effort_max = Column(Integer)
    

def get_db() -> Generator:
    """FastAPI dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()