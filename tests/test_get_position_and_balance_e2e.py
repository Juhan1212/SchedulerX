import asyncio
import os
import pytest
from backend.exchanges.bybit import BybitExchange

@pytest.mark.asyncio
async def test_get_position_and_balance_e2e():
    """
    Bybit 실계정 API 키가 필요합니다.
    환경변수 BYBIT_ACCESS_KEY, BYBIT_SECRET_KEY가 설정되어 있어야 합니다.
    실제 Bybit API에 요청하여 position과 잔고를 조회합니다.
    """
    api_key = os.getenv('BYBIT_ACCESS_KEY')
    secret_key = os.getenv('BYBIT_SECRET_KEY')
    symbol = 'PROVE'  # 테스트할 심볼

    if not api_key or not secret_key:
        pytest.skip('BYBIT_ACCESS_KEY, BYBIT_SECRET_KEY 환경변수가 필요합니다.')

    bybit_service = BybitExchange(api_key, secret_key)

    async def get_position_and_balance():
        return await asyncio.gather(
            bybit_service.get_position_info(symbol),
            bybit_service.get_available_balance()
        )

    res, bybit_balance = await get_position_and_balance()
    assert isinstance(res, dict)
    assert 'list' in res
    assert isinstance(bybit_balance, (str))
    # position 필터링
    position = list(filter(lambda x: float(x.get('size', 0)) > 0, res.get('list', [])))
    assert isinstance(position, list)
    # position이 없을 수도 있으므로 길이 체크는 하지 않음
    print(f"bybit_balance: {bybit_balance}, position: {position}")
