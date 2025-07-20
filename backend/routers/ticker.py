import os
import logging
from typing import List
from fastapi import Query, APIRouter, Depends, status, HTTPException
import redis.asyncio as aioredis
from backend.dependencies.injection import get_ticker_service
from backend.dependencies.auth import get_current_user
from backend.services.ticker import TickerService
from backend.db.schemas.ticker import TickerOut

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/tickers", response_model=List[TickerOut])
async def get_tickers(
    exchange1: str = Query(..., description="첫 번째 거래소 이름"),
    exchange2: str = Query(..., description="두 번째 거래소 이름"),
    user=Depends(get_current_user),
    ticker_service: TickerService = Depends(get_ticker_service)
):
    exchange1 = exchange1.lower()
    exchange2 = exchange2.lower()
    tickers = ticker_service.get_common_tickers(user.id, exchange1, exchange2)  # [{'name': 'BTC'}, ...]
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    redis_db = int(os.getenv('REDIS_DB', '1'))
    redis = aioredis.from_url(f"redis://{redis_host}:{redis_port}/{redis_db}", decode_responses=True)
    # 모든 티커 이름 추출
    names = [t['name'] if isinstance(t, dict) else t.name for t in tickers]
    # Redis에서 거래소 조합별로 키 생성
    redis_keys = [f"{exchange1}_{exchange2}:{name}" for name in names]
    ex_rates = await redis.mget(*redis_keys) if redis_keys else []
    result = [TickerOut(name=name, ex_rate=ex_rate) for name, ex_rate in zip(names, ex_rates)]
    await redis.close()
    return result

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
