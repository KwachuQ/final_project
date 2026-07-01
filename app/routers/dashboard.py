import pathlib
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates



# Create router with prefix
router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)   

# Create template for dashboard
templates = Jinja2Templates(directory=pathlib.Path(__file__).parent.parent / "templates")

# Endpoint to get dashboard
@router.get("/")
def get_dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")