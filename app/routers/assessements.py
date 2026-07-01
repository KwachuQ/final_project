import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Annotated

from app.database import get_db, AssessmentModel, ScoredSystemModel
from app.deps import get_current_user
from app.database import UserModel
from app.schemas import AssessmentCreateResponse
from app.services import loader, scoring
from app.s3 import upload_file, delete_file
from app.schemas import AssessmentDetail
from app.schemas import AssessmentSummary

# Assessment endpoints
router = APIRouter(prefix="/assessments", tags=["Assessments"])

@router.post(
    "",
    response_model=AssessmentCreateResponse,
    status_code=status.HTTP_201_CREATED
)

def create_assessment(
    inventory: Annotated[UploadFile, File(...)],
    name: Annotated[str, Form(None)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(get_current_user)]
):
    """
    Create a new assessment from a CSV inventory upload.

    Parses the inventory, calculates scores for each system, uploads the original file to S3, 
    and saves the assessment and scored systems to the database.
    """
    data = inventory.read()

    try:
        parsed_systems = loader.parse_inventory(data)
    except loader.CSVValidationError as e:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail=e.errors)
    except ValueError as e:
        raise HTTPException(status_code = status.HTTP_400_BAD_REQUEST, detail=str(e))

    scored_systems = scoring.score_systems(parsed_systems)
    
    s3_key = f"uploads/{current_user.id}/{uuid.uuid4()}.csv"
    upload_file(s3_key, data)

    assessment = AssessmentModel(
        user_id=current_user.id,
        name=name,
        s3_key=s3_key,
        system_count=len(scored_systems)
    )
    
    for inv, sc in zip(parsed_systems, scored_systems):
        scored_system = ScoredSystemModel(
            system_name = sc.system_name,
            system_type = sc.system_type,
            complexity_score = sc.complexity_score,
            cloud_fit_score = sc.cloud_fit_score,
            risk_score = sc.risk_score,
            composite_score = sc.composite_score,
            recommended_strategy = sc.recommended_strategy,
            wave = sc.wave,
            effort_min = sc.effort_min,
            effort_max = sc.effort_max,
            operating_system = inv.operating_system,
            language = inv.language,
            num_users = inv.num_users,
            data_size_gb = inv.data_size_gb,
            availability = inv.availability,
            has_compliance = inv.has_compliance,
            is_vendor_software = inv.is_vendor_software
        )
        assessment.scored_systems.append(scored_system)

    db.add(assessment)
    try:    
        db.commit()
        db.refresh(assessment)

    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
        delete_file(s3_key)
        raise HTTPException(status_code=500, detail="Failed to save assessment")

    return assessment

@router.get(
    "", 
    response_model=list[AssessmentSummary]
    )

def list_assessments(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve a summary list of all assessments belonging to the current user.
    """
    assessments = db.query(AssessmentModel).filter(AssessmentModel.user_id == current_user.id).order_by(AssessmentModel.created_at.desc()).all()
    return [AssessmentSummary(id=a.id, name=a.name, system_count=a.system_count, created_at=a.created_at) for a in assessments]

@router.get(
    "/{assessment_id}", 
    response_model=AssessmentDetail
    )

def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve detailed information for a specific assessment.
    """
    assessment = db.query(AssessmentModel).filter(AssessmentModel.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    elif assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return AssessmentDetail(
        id=assessment.id,
        name=assessment.name,
        created_at=assessment.created_at,
        system_count=assessment.system_count,
        s3_key=assessment.s3_key,
        scored_systems=assessment.scored_systems 
    )


@router.delete(
    "/{assessment_id}", 
    status_code=status.HTTP_204_NO_CONTENT
    )
    
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete a specific assessment, along with its associated S3 file.
    """
    assessment = db.query(AssessmentModel).filter(AssessmentModel.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    elif assessment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    delete_file(assessment.s3_key)
    db.delete(assessment)
    db.commit()
    
    return None