from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from backend.dependencies.injection import get_ticker_service
from backend.dependencies.auth import get_current_user
from backend.services.ticker import TickerService
from backend.db.schemas.ticker import TickerOut

router = APIRouter()

@router.get("/tickers", response_model=List[TickerOut])
def get_tickers(
    user=Depends(get_current_user),
    ticker_service: TickerService = Depends(get_ticker_service)
):
    return ticker_service.get_common_tickers(user.id)

@router.post("/tickers/exclude")
def exclude_ticker(
    name: str,
    user=Depends(get_current_user),
    ticker_service: TickerService = Depends(get_ticker_service)
):
    res = ticker_service.exclude_ticker(user.id, name)
    if not res:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="티커 제외 실패")
    return {"message": f"{name} 제외 완료"}

