from abc import ABC
from typing import List

class Exchange(ABC):
    name = None  # 또는 기본값을 문자열로 지정할 수 있습니다.
    server_url = None  # 또는 기본값을 문자열로 지정할 수 있습니다.

    @classmethod
    async def get_tickers(cls) -> List[str]:
        """
        거래소 API로 티커 목록을 가져옵니다.

        Returns:
            list[dict]: 티커 목록 (각 티커의 정보가 포함된 딕셔너리 리스트)
        """
        return []
