# API endpoints for managing positions
from fastapi import APIRouter

router = APIRouter()

@router.get("/positions")
def get_positions():
    return {"message": "List of positions"}
