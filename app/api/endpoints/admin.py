# API endpoints for admin functionalities
from fastapi import APIRouter

router = APIRouter()

@router.get("/admin")
def admin_dashboard():
    return {"message": "Admin dashboard"}
