from fastapi import APIRouter

# Create router
router = APIRouter()

# Endpoint to check health
@router.get("/health")
def health_check():
    return {"status": "ok"}
