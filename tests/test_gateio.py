import json
import pytest
from backend.exchanges.gateio import GateioExchange

@pytest.mark.asyncio
async def test_get_ticker():
    # GateioExchange 인스턴스를 생성하고, HTTP 클라이언트를 모킹합니다.
    data = await GateioExchange.get_ticker("ETH")
    print(json.dumps(data, indent=2, ensure_ascii=False))

