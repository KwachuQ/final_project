from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
import pathlib


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)   

templates = Jinja2Templates(directory=pathlib.Path(__file__).parent.parent / "templates")

@router.get("/")
def get_dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")