# API endpoints for managing orders
from fastapi import APIRouter

router = APIRouter()

@router.get("/orders")
def get_orders():
    return {"message": "List of orders"}
