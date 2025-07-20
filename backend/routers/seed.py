from fastapi import APIRouter, Depends, HTTPException
from backend.dependencies.auth import get_current_user
from backend.dependencies.injection import get_seed_service
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()

class SeedOut(BaseModel):
    user_id: int
    amt: int

class SeedUpdate(BaseModel):
    amt: int

@router.get("/seed", response_model=SeedOut)
def get_seed(user_db=Depends(get_current_user), seed_service=Depends(get_seed_service)):
    seed = seed_service.get_seed(user_db.id)
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    return {"user_id": seed.user_id, "amt": seed.amt}

@router.post("/seed", response_model=SeedOut)
def update_seed(data: SeedUpdate, user_db=Depends(get_current_user), seed_service=Depends(get_seed_service)):
    seed = seed_service.update_seed(user_db.id, data.amt)
    return {"user_id": seed.user_id, "amt": seed.amt}
