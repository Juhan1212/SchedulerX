import json
import time
import pytest
from backend.core.ex_manager import ExchangeManager
from backend.exchanges.base import KoreanExchange
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.upbit import UpbitExchange
from consumer import work_task

def test_work_task_entry_e2e():
    """
    work_task E2E 테스트로, 실제 포지션에 진입을 시도합니다.
    - 티커: XRP
    - 한국 거래소: upbit
    - 해외 거래소: bybit

    실제 E2E 테스트이며, 시장 상황이 조건에 맞을 경우 실제 주문이 발생할 수 있습니다.
    `entry_position_flag`는 실시간 시장 데이터에 따라 결정됩니다.
    """
    data = ['ARKM']
    korean_ex = 'upbit'
    foreign_ex = 'bybit'

    # work_task 함수를 호출합니다.
    # 포지션 진입 로직이 실행되려면, DB에 자동매매가 활성화된 사용자가 있어야 하고,
    # 시장 진입 조건(자동 모드의 경우 ex_rate <= usdt_price * 0.99)이 충족되어야 합니다.
    work_task(data=data, korean_ex=korean_ex, foreign_ex=foreign_ex)

def test_exMgr_get_user_positions_for_settlement():
    exMgr = ExchangeManager()
    exMgr.register_exchange("upbit", UpbitExchange.from_env())
    exMgr.register_exchange("bybit", BybitExchange.from_env())

    user_id = '6'
    item_name = 'AXS'
    positions = exMgr.get_user_positions_for_settlement(user_id, item_name)
    assert isinstance(positions, list)
    
@pytest.mark.asyncio
async def test_upbit_get_order():
    exMgr = ExchangeManager()
    exMgr.register_exchange("upbit", UpbitExchange.from_env())
    exMgr.register_exchange("bybit", BybitExchange.from_env())

    upbit = exMgr.exchanges.get("upbit")
    if not isinstance(upbit, KoreanExchange):
        raise TypeError("Expected upbit to be a KoreanExchange")
    start_time = time.time()
    ret = await upbit.get_order('862db017-75e4-42b7-ac0f-67ade08a60f4')
    print(f'elapsed_time : {time.time() - start_time}')
    
    print(json.dumps(ret, indent=2))