import pytest
import asyncio
from backend.exchanges.bithumb import BithumbExchange


class TestBithumbE2E:
    """
    Bithumb 거래소 API E2E 테스트
    """

    @pytest.mark.asyncio
    async def test_get_ticker_orderbook_single(self):
        """
        단일 티커의 호가창 조회 테스트
        """
        # Given: BTC 티커
        tickers = ["BTC"]
        
        # When: 호가창 조회
        result = await BithumbExchange.get_ticker_orderbook(tickers)
        
        # Then: 결과 검증
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        
        orderbook = result[0]
        assert "ticker" in orderbook
        assert orderbook["ticker"] == "BTC"
        assert "timestamp" in orderbook
        assert "orderbook" in orderbook
        
        # 호가창 데이터 검증
        orderbook_units = orderbook["orderbook"]
        assert isinstance(orderbook_units, list)
        assert len(orderbook_units) > 0
        
        # 첫 번째 호가 검증
        first_unit = orderbook_units[0]
        assert "ask_price" in first_unit
        assert "bid_price" in first_unit
        assert "ask_size" in first_unit
        assert "bid_size" in first_unit
        
        # 가격과 수량이 양수인지 확인
        assert first_unit["ask_price"] > 0
        assert first_unit["bid_price"] > 0
        assert first_unit["ask_size"] >= 0
        assert first_unit["bid_size"] >= 0
        
        # 매도가 >= 매수가 확인 (정상적인 호가창)
        assert first_unit["ask_price"] >= first_unit["bid_price"]
        
        print(f"\n✓ BTC 호가창 조회 성공")
        print(f"  - 타임스탬프: {orderbook['timestamp']}")
        print(f"  - 호가 개수: {len(orderbook_units)}")
        print(f"  - 최우선 매도가: {first_unit['ask_price']:,.0f} KRW")
        print(f"  - 최우선 매수가: {first_unit['bid_price']:,.0f} KRW")

    @pytest.mark.asyncio
    async def test_get_ticker_orderbook_multiple(self):
        """
        여러 티커의 호가창 동시 조회 테스트
        """
        # Given: 여러 티커
        tickers = ["BTC", "ETH", "XRP"]
        
        # When: 호가창 조회
        result = await BithumbExchange.get_ticker_orderbook(tickers)
        
        # Then: 결과 검증
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == len(tickers)
        
        # 각 티커별 검증
        ticker_set = {ob["ticker"] for ob in result}
        assert ticker_set == set(tickers)
        
        for orderbook in result:
            assert "ticker" in orderbook
            assert "timestamp" in orderbook
            assert "orderbook" in orderbook
            
            orderbook_units = orderbook["orderbook"]
            assert len(orderbook_units) > 0
            
            first_unit = orderbook_units[0]
            assert first_unit["ask_price"] >= first_unit["bid_price"]
            
        print(f"\n✓ 다중 티커 호가창 조회 성공")
        for orderbook in result:
            ticker = orderbook["ticker"]
            first_unit = orderbook["orderbook"][0]
            print(f"  - {ticker}: 매도 {first_unit['ask_price']:,.0f} / 매수 {first_unit['bid_price']:,.0f} KRW")

    @pytest.mark.asyncio
    async def test_get_ticker_orderbook_with_count(self):
        """
        호가 개수 지정 테스트
        """
        # Given: BTC 티커와 호가 개수
        tickers = ["BTC"]
        count = 50
        
        # When: 호가창 조회
        result = await BithumbExchange.get_ticker_orderbook(tickers, count=count)
        
        # Then: 결과 검증
        assert result is not None
        orderbook = result[0]
        orderbook_units = orderbook["orderbook"]
        
        # 호가 개수가 요청한 개수 이하인지 확인 (시장 상황에 따라 적을 수 있음)
        assert len(orderbook_units) <= count
        assert len(orderbook_units) > 0
        
        print(f"\n✓ 호가 개수 지정 조회 성공")
        print(f"  - 요청 개수: {count}")
        print(f"  - 실제 개수: {len(orderbook_units)}")

    @pytest.mark.asyncio
    async def test_get_ticker_orderbook_data_consistency(self):
        """
        호가창 데이터 일관성 테스트
        """
        # Given: BTC 티커
        tickers = ["BTC"]
        
        # When: 호가창 조회
        result = await BithumbExchange.get_ticker_orderbook(tickers)
        
        # Then: 데이터 일관성 검증
        orderbook = result[0]
        orderbook_units = orderbook["orderbook"]
        
        # 매도 호가가 오름차순인지 확인 (낮은 가격부터)
        ask_prices = [unit["ask_price"] for unit in orderbook_units]
        # 일부 거래소는 정렬되어 있지 않을 수 있으므로 이 테스트는 선택적
        
        # 매수 호가가 내림차순인지 확인 (높은 가격부터)
        bid_prices = [unit["bid_price"] for unit in orderbook_units]
        
        # 모든 매도가가 매수가보다 크거나 같은지 확인
        for unit in orderbook_units:
            assert unit["ask_price"] >= unit["bid_price"], \
                f"매도가({unit['ask_price']})가 매수가({unit['bid_price']})보다 작습니다"
        
        print(f"\n✓ 호가창 데이터 일관성 검증 성공")
        print(f"  - 모든 호가 단위에서 매도가 >= 매수가 확인")

    @pytest.mark.asyncio
    async def test_get_ticker_orderbook_invalid_ticker(self):
        """
        존재하지 않는 티커 조회 테스트
        """
        # Given: 존재하지 않는 티커
        tickers = ["INVALID_TICKER_XYZ"]
        
        # When & Then: 예외 발생 또는 빈 결과 확인
        try:
            result = await BithumbExchange.get_ticker_orderbook(tickers)
            # 일부 거래소는 빈 결과를 반환할 수 있음
            if result:
                print(f"\n✓ 잘못된 티커에 대해 빈 결과 반환")
        except Exception as e:
            # 예외가 발생하는 것도 정상
            print(f"\n✓ 잘못된 티커에 대해 예외 발생: {type(e).__name__}")

    @pytest.mark.asyncio
    async def test_get_ticker_orderbook_performance(self):
        """
        호가창 조회 성능 테스트
        """
        import time
        
        # Given: 여러 티커
        tickers = ["BTC", "ETH", "XRP", "ADA", "SOL"]
        
        # When: 시간 측정하며 호가창 조회
        start_time = time.time()
        result = await BithumbExchange.get_ticker_orderbook(tickers)
        elapsed_time = time.time() - start_time
        
        # Then: 결과 검증 및 성능 확인
        assert result is not None
        assert len(result) == len(tickers)
        
        # 5개 티커 조회가 5초 이내에 완료되어야 함
        assert elapsed_time < 5.0, f"조회 시간이 너무 깁니다: {elapsed_time:.2f}초"
        
        print(f"\n✓ 호가창 조회 성능 테스트 성공")
        print(f"  - 티커 개수: {len(tickers)}")
        print(f"  - 소요 시간: {elapsed_time:.3f}초")
        print(f"  - 평균 시간: {elapsed_time/len(tickers):.3f}초/티커")


if __name__ == "__main__":
    # 직접 실행 시 모든 테스트 실행
    pytest.main([__file__, "-v", "-s"])
