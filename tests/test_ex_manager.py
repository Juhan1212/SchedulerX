import json
import pytest
import types
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend.core.ex_manager import ExchangeManager
from backend.core.ex_manager import exMgr

@pytest.fixture
def ex_manager():
    return ExchangeManager()

@pytest.fixture
def tickers():
    return [
        ('bithumb', 'bybit', 'BTC'),
        ('bithumb', 'bybit', 'ETH'),
        ('bithumb', 'bybit', 'XRP'),
        ('bithumb', 'bybit', 'SOL'),
        ('bithumb', 'bybit', 'ADA'),
        ('bithumb', 'bybit', 'DOGE'),
        ('bithumb', 'bybit', 'AVAX'),
        ('bithumb', 'bybit', 'LINK'),
        ('bithumb', 'bybit', 'DOT'),
        ('bithumb', 'bybit', 'MATIC'),
        ('bithumb', 'bybit', 'UNI'),
        ('bithumb', 'bybit', 'ATOM'),
        ('bithumb', 'bybit', 'NEAR'),
        ('bithumb', 'bybit', 'APT'),
        ('bithumb', 'bybit', 'ARB'),
        ('bithumb', 'bybit', 'OP'),
        ('bithumb', 'bybit', 'IMX'),
        ('bithumb', 'bybit', 'MANTA'),
        ('bithumb', 'bybit', 'STX'),
        ('bithumb', 'bybit', 'SUI'),
    ]

def test_register_exchange(ex_manager):
    dummy_exchange = object()
    ex_manager.register_exchange("test", dummy_exchange)
    assert ex_manager.exchanges["test"] is dummy_exchange

def test_get_common_tickers_from_db(ex_manager):
    result = ex_manager.get_common_tickers_from_db()
    print(result)

@pytest.mark.asyncio
async def test_calc_exrate_batch(ex_manager, tickers):
    result = await ex_manager.calc_exrate_batch(tickers)
    # with open('test_calc_exrate_batch_output.json', 'w') as f:
    #     json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))

@pytest.mark.asyncio
async def test_compare_single_vs_batch_exrate():
    """
    단일 티커(MANTA)를 단독으로 계산할 때와 
    20개 티커와 함께 배치로 계산할 때의 환율 차이를 비교하는 테스트
    
    목적: 포지션 진입 시 초기 계산(배치)과 재확인(단일) 시 환율 차이 원인 파악
    """
    import time
    
    # 테스트 대상 티커
    target_ticker = 'MANTA'
    
    # 20개 티커 배치 (MANTA 포함)
    batch_tickers = [
        ('bithumb', 'bybit', 'BTC'),
        ('bithumb', 'bybit', 'ETH'),
        ('bithumb', 'bybit', 'XRP'),
        ('bithumb', 'bybit', 'SOL'),
        ('bithumb', 'bybit', 'ADA'),
        ('bithumb', 'bybit', 'DOGE'),
        ('bithumb', 'bybit', 'AVAX'),
        ('bithumb', 'bybit', 'LINK'),
        ('bithumb', 'bybit', 'DOT'),
        ('bithumb', 'bybit', 'UNI'),
        ('bithumb', 'bybit', 'ATOM'),
        ('bithumb', 'bybit', 'NEAR'),
        ('bithumb', 'bybit', 'APT'),
        ('bithumb', 'bybit', 'ARB'),
        ('bithumb', 'bybit', 'OP'),
        ('bithumb', 'bybit', target_ticker),
        ('bithumb', 'bybit', 'STX'),
        ('bithumb', 'bybit', 'SUI'),
    ]
    
    # 단일 티커
    single_ticker = [('bithumb', 'bybit', target_ticker)]
    
    print("\n" + "="*80)
    print("🧪 환율 비교 테스트: 단일 vs 배치 계산")
    print("="*80)
    
    # 1단계: 배치로 계산 (실제 초기 계산 시뮬레이션)
    print(f"\n📊 1단계: 20개 티커 배치 계산 중...")
    start_time = time.time()
    batch_result = await exMgr.calc_exrate_batch(batch_tickers)
    batch_duration = time.time() - start_time
    
    # MANTA 환율 추출
    manta_batch = next((item for item in batch_result if item['name'] == target_ticker), None)
    
    # ⏰ 실제 운영환경 시뮬레이션: Redis pub/sub, DB 조회, 잔액 조회 등으로 인한 지연 재현
    print(f"\n⏰ 실제 운영환경 시뮬레이션: 3초 대기 중...")
    print(f"   (Redis 발행, DB 조회, 양쪽 거래소 잔액 API 호출, 검증 로직 등 수행 중...)")
    await asyncio.sleep(3)
    
    # 2단계: 단일 티커로 재계산 (실제 재확인 시뮬레이션)
    print(f"\n📊 2단계: {target_ticker} 단일 티커 재확인 계산 중...")
    start_time = time.time()
    single_result = await exMgr.calc_exrate_batch(single_ticker)
    single_duration = time.time() - start_time
    
    manta_single = single_result[0] if single_result else None
    
    # 결과 분석
    print("\n" + "="*80)
    print("📈 환율 비교 결과")
    print("="*80)
    
    if not manta_batch or not manta_single:
        print("❌ 환율 계산 실패")
        return
    
    # 샘플 시드 금액들 (1M, 5M, 10M, 20M, 50M)
    sample_seeds = [1_000_000, 5_000_000, 10_000_000, 20_000_000, 50_000_000]
    
    print(f"\n🎯 대상 티커: {target_ticker}")
    print(f"⏱️  배치 계산 소요 시간: {batch_duration:.3f}초")
    print(f"⏱️  단일 재확인 소요 시간: {single_duration:.3f}초")
    print(f"⏱️  총 경과 시간 (배치 → 재확인): {batch_duration + 3 + single_duration:.3f}초")
    print(f"\n{'='*80}")
    print(f"{'시드 금액':>12} | {'배치 진입환율':>12} | {'재확인 진입환율':>12} | {'차이':>8} | {'변동률':>8}")
    print(f"{'='*80}")
    
    max_diff_percent = 0
    max_diff_seed = 0
    
    for seed in sample_seeds:
        # 배치 결과에서 해당 시드 찾기
        batch_rate_info = next((r for r in manta_batch['ex_rates'] if r['seed'] == seed), None)
        single_rate_info = next((r for r in manta_single['ex_rates'] if r['seed'] == seed), None)
        
        if batch_rate_info and single_rate_info:
            batch_entry = batch_rate_info['entry_ex_rate']
            single_entry = single_rate_info['entry_ex_rate']
            
            if batch_entry and single_entry:
                diff = abs(single_entry - batch_entry)
                diff_percent = (diff / batch_entry) * 100
                
                # 최대 변동률 추적
                if diff_percent > max_diff_percent:
                    max_diff_percent = diff_percent
                    max_diff_seed = seed
                
                print(f"{seed:>12,}원 | {batch_entry:>12.2f} | {single_entry:>12.2f} | {diff:>8.2f} | {diff_percent:>7.2f}%")
    
    print(f"{'='*80}")
    print(f"\n📌 최대 변동률: {max_diff_percent:.2f}% (시드: {max_diff_seed:,}원)")
    
    # 0.5% 기준 초과 여부 판단
    if max_diff_percent > 0.5:
        print(f"\n⚠️  경고: 최대 변동률이 0.5% 기준을 초과했습니다!")
        print(f"   - 현재 변동률: {max_diff_percent:.2f}%")
        print(f"   - 기준치: 0.5%")
        print(f"   - 초과분: {max_diff_percent - 0.5:.2f}%")
    else:
        print(f"\n✅ 통과: 모든 시드 금액에서 변동률이 0.5% 이내입니다.")
    
    print("\n" + "="*80)
    print("💡 분석 결과:")
    print("="*80)
    print("1. ⏰ 배치 계산 후 3초 대기 (실제 운영환경의 Redis/DB/API 호출 시뮬레이션)")
    print("2. 📊 3초 시간차로 인한 오더북 변동이 환율에 영향을 미칩니다.")
    print("3. 🔍 실제 운영환경에서도 이와 유사한 패턴으로 환율 차이가 발생합니다.")
    print("4. ⚠️  0.5% 이상 차이가 발생하면 실제 거래에서 주문이 취소됩니다.")
    print("="*80 + "\n")
    
    # 전체 데이터 출력 (옵션)
    # print("\n📋 배치 계산 전체 결과:")
    # print(json.dumps(manta_batch, indent=2))
    # print("\n📋 단일 계산 전체 결과:")
    # print(json.dumps(manta_single, indent=2))