import os
import math
import asyncio
import logging
from typing import List
from dotenv import load_dotenv
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.upbit import UpbitExchange

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# 환경 변수에서 API 키 로드
def get_api_keys():
    upbit_api_key = os.getenv('UPBIT_ACCESS_KEY')
    upbit_secret_key = os.getenv('UPBIT_SECRET_KEY')
    bybit_api_key = os.getenv('BYBIT_ACCESS_KEY')
    bybit_secret_key = os.getenv('BYBIT_SECRET_KEY')
    return upbit_api_key, upbit_secret_key, bybit_api_key, bybit_secret_key

async def test_order_block(ticker: str, seed: float):
    upbit_api_key, upbit_secret_key, bybit_api_key, bybit_secret_key = get_api_keys()
    if not upbit_api_key or not upbit_secret_key or not bybit_api_key or not bybit_secret_key:
        raise ValueError("API keys must be set in environment variables.")
    
    # UpbitExchange와 BybitExchange 인스턴스 생성
    upbit_service = UpbitExchange(upbit_api_key, upbit_secret_key)
    bybit_service = BybitExchange(bybit_api_key, bybit_secret_key)

    # Upbit에서 KRW로 매수 주문 실행
    upbit_order = await upbit_service.order(ticker, 'bid', seed)
    upbit_order_id = upbit_order.get('uuid')
    logger.info(f"Upbit 주문 ID: {upbit_order_id}")
    if not upbit_order_id:
        logger.error(f"Upbit 주문 실행 실패: {upbit_order}")
        return None

    # Upbit 주문내역 조회
    upbit_order_result: List[dict] = await upbit_service.get_orders(ticker, upbit_order_id)
    upbit_order_volume = upbit_order_result[0].get('executed_volume')
    logger.info(f"Upbit 주문 체결량: {upbit_order_volume}")
    if not upbit_order_volume:
        logger.error(f"Upbit 주문 결과에서 volume을 찾을 수 없습니다: {upbit_order_result}")
        return None

    # Bybit 최소 주문 단위(lot size) 조회 
    lot_size = await bybit_service.get_lot_size(ticker)
    logger.info(f"Bybit lot size: {lot_size}")
    if not lot_size:
        logger.error(f"Bybit lot size 정보를 가져올 수 없습니다: {ticker}")
        return None

    # volume을 lot_size 단위로 내림(round down)
    rounded_volume = math.floor(float(upbit_order_volume) / lot_size) * lot_size
    logger.info(f"Rounded volume for Bybit order: {rounded_volume}")
    if rounded_volume <= 0:
        logger.error(f"Bybit 주문 가능한 최소 수량 미만: {upbit_order_volume} -> {rounded_volume}")
        return None

    # Bybit에서 rounded_volume만큼 매도 주문 실행
    bybit_order = await bybit_service.order(ticker, 'ask', rounded_volume)
    bybit_order_id = bybit_order.get('result', {}).get('orderId')
    logger.info(f"Bybit 주문 ID: {bybit_order_id}")
    if not bybit_order_id:
        logger.error(f"Bybit 주문 실행 실패: {bybit_order}")
        return None
    
    # Bybit 주문내역 조회
    # (get_orders 함수가 bybit에도 구현되어 있어야 함)
    bybit_order_result: List[dict] = await bybit_service.get_orders(ticker, bybit_order_id)
    from decimal import Decimal, ROUND_DOWN
    price = Decimal(str(bybit_order_result[0].get('price', 0)))
    qty = Decimal(str(bybit_order_result[0].get('qty', 0)))
    bybit_order_usdt = (price * qty).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

    seed_decimal = Decimal(str(seed))
    order_rate = (seed_decimal / bybit_order_usdt).quantize(Decimal('0.01'), rounding=ROUND_DOWN) if bybit_order_usdt else None
    logger.info(f"주문을 실행했습니다: {ticker} KRW매수금액={seed_decimal} USDT매도금액={bybit_order_usdt} 주문환율={order_rate}")

    return {
        "ticker": ticker,
        "krw_buy": seed_decimal,
        "bybit_sell_usdt": bybit_order_usdt,
        "order_rate": order_rate,
        "upbit_order": upbit_order,
        "bybit_order": bybit_order,
        "bybit_order_result": bybit_order_usdt
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python test_order_block.py <ticker> <krw_seed>")
        sys.exit(1)
    ticker = sys.argv[1]
    seed = float(sys.argv[2])
    result = asyncio.run(test_order_block(ticker, seed))
    print(result)
