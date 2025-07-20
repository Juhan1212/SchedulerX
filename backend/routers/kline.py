from decimal import Decimal
from typing import List
import logging
from fastapi import APIRouter, Depends, Query
from backend.dependencies.exchange_hub import get_exchange_hub
from backend.exchanges.upbit import UpbitExchange
from backend.exchanges.gateio import GateioExchange
from backend.services.exchange_hub import ExchangeHub

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/kline")
async def get_kline(
    exchanges: List[str] = Query(..., description="거래소명 배열, 예: ['upbit', 'bybit', 'gateio']"),
    symbol: str = Query(..., description="티커명, 예: 'BTC'"),
    interval: str = Query("1", description="캔들 간격, 예: '1m', '5', '15', 'D', 'W', 'M'"),
    to: int = Query(0, description="종료 시간 (UTC 타임스탬프 초단위)"),
    hub: ExchangeHub = Depends(get_exchange_hub),
):
    exchanges = exchanges[0].lower().split(',')
    try:
        # 등록된 거래소 객체 중 요청된 거래소만 추출
        results = await hub.call_method_on_all(
            method_name="get_ticker_candles",
            exchanges=exchanges,
            ticker=symbol,
            interval=interval,
            to=to
        )
        
        # gateio 거래소의 경우, volume이 아니라 contract_size를 사용하기 때문에 티커 정보를 가져옵니다.
        if results.get('gateio'):
            ticker_info = await GateioExchange.get_ticker(symbol)
            # 결과를 병합
            results['gateio'] = list(map(lambda x: {**x, 'volume': Decimal(str(x['volume'])) * Decimal(ticker_info['quanto_multiplier'])}, results['gateio']))
            
        merged = hub.merge_kline_data(*results.values())
        # 타임스탬프 기준으로 정렬 ~ 정렬안하면 TradingView에서 캔들 차트가 에러발생함
        merged_sorted = sorted(merged, key=lambda x: x['timestamp'])
        
        # 업비트 USDT 캔들 데이터 가져오기
        usdt_candle = await UpbitExchange.get_ticker_candles(
            ticker='USDT',
            interval=interval,
            to=to
        )

        return to_candle_data(merged_sorted, ex1=results.get(exchanges[0]), ex2=results.get(exchanges[1]), usdt_candle=usdt_candle)
    except Exception as e:
        logger.error(f"Error fetching kline data: {e}")
        raise

def to_candle_data(merged, ex1=None, ex2=None, usdt_candle=None):
    candleData = [
        {
            "time": item["timestamp"],
            "open": float(item["open"]),
            "high": float(item["high"]),
            "low": float(item["low"]),
            "close": float(item["close"]),
        }
        for item in merged
    ]
    volumeData = [
        {
            "time": item["timestamp"],
            "value": float(item["volume"])
        }
        for item in merged
    ]
    result = {
        "candleData": candleData,
        "volumeData": volumeData
    }
    if ex1:
        ex1_sorted = sorted(ex1, key=lambda x: x["timestamp"])
        result["ex1VolumeData"] = [
            {"time": item["timestamp"], "value": float(item["volume"])} for item in ex1_sorted
        ]
    if ex2:
        ex2_sorted = sorted(ex2, key=lambda x: x["timestamp"])
        result["ex2VolumeData"] = [
            {"time": item["timestamp"], "value": float(item["volume"])} for item in ex2_sorted
        ]
    if usdt_candle:
        usdt_sorted = sorted(usdt_candle, key=lambda x: x["timestamp"])
        result["usdtCandleData"] = [
            {
                "time": item["timestamp"],
                "value": float(item["close"]),
            }
            for item in usdt_sorted
        ]
    return result

