from decimal import ROUND_DOWN, Decimal
import json
from pathlib import Path
from cachetools import TTLCache, cached
import asyncio
import os
import logging
import logging.config
import time
from celery import Celery
import redis
from dotenv import load_dotenv
import yaml
from backend.core.ex_manager import exMgr
from backend.exchanges.base import ForeignExchange, KoreanExchange
from backend.exchanges.bithumb import BithumbExchange
from backend.exchanges.bybit import BybitExchange
from backend.exchanges.upbit import UpbitExchange
from backend.utils.telegram import send_telegram

load_dotenv()

# YAML 파일 경로
LOGGING_CONFIG_PATH = Path(__file__).resolve().parent / "celery_logging_config.yaml"

# YAML 파일에서 로깅 설정 로드
def setup_logging():
    """
    YAML 파일에서 로깅 설정을 로드합니다.

    Args:
        None

    Returns:
        None

    Raises:
        FileNotFoundError: YAML 파일이 존재하지 않을 경우.
        yaml.YAMLError: YAML 파일 파싱 중 오류가 발생한 경우.
    """
    try:
        with open(LOGGING_CONFIG_PATH, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
            logging.config.dictConfig(config)
    except FileNotFoundError as fnf_error:
        print(f"Logging config file not found: {fnf_error}")
        logging.basicConfig(level=logging.INFO)
    except yaml.YAMLError as yaml_error:
        print(f"Error parsing YAML logging config: {yaml_error}")
        logging.basicConfig(level=logging.INFO)

# 로깅 설정 초기화
setup_logging()

# 로거 생성
logger = logging.getLogger(__name__)

# Redis 클라이언트 생성 (글로벌 네임스페이스)
redis_host = os.getenv('REDIS_HOST')
if redis_host is None:
    raise ValueError("Environment variable 'REDIS_HOST' is not set.")

redis_client = redis.StrictRedis(
    host=redis_host,
    port=6379,
    db=1,
    socket_connect_timeout=5,  # 연결 타임아웃 설정
    decode_responses=True  # byte 대신 str로 응답 받기
)

# Redis 재연결 함수
def reconnect_redis():
    global redis_client
    while True:
        try:
            if redis_host is None:
                raise ValueError("Environment variable 'REDIS_HOST' is not set.")
            
            redis_client = redis.StrictRedis(
                host=redis_host,
                port=6379,
                db=1,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                decode_responses=True  # byte 대신 str로 응답 받기
            )
            # 연결 테스트
            redis_client.ping()
            logger.info("Reconnected to Redis")
            break
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Retrying Redis connection: {e}")
            time.sleep(5)

# Celery 인스턴스 생성
app = Celery('consumer')
app.config_from_object('celeryconfig')

EXCHANGE_CLASS_MAP = {
    "upbit": UpbitExchange,
    "bithumb": BithumbExchange,
    "bybit": BybitExchange,
    # 필요시 추가
}

# 테더 가격 호출 api 캐시설정            
usdt_cache = TTLCache(maxsize=10, ttl=1)

@cached(usdt_cache)
async def get_usdt_ticker_ob_price():
    return await UpbitExchange.get_ticker_ob_price('USDT')

# facade exMgr 객체에 거래소 등록
exMgr.register_exchange("upbit", UpbitExchange.from_env())
exMgr.register_exchange("bybit", BybitExchange.from_env())
exMgr.register_exchange("bithumb", BithumbExchange.from_env())

def round_volume_to_lot_size(volume, lot_size):
    lot_size_decimal = Decimal(str(lot_size))
    volume_decimal = Decimal(str(volume))
    rounded_volume = volume_decimal.quantize(lot_size_decimal)
    return float(rounded_volume)

# 최적화용 함수              
async def get_both_ex_available_balance(korean_ex_cls, foreign_ex_cls):
    return await asyncio.gather(
        korean_ex_cls.get_available_balance(),
        foreign_ex_cls.get_available_balance()
    )

@app.task(name='producer.calculate_orderbook_exrate_task', ignore_result=True, soft_time_limit=5)
def work_task(data, retry_count=0):
    """
    Celery 작업을 처리하는 함수입니다.
    Args:
        data (list[tuple]): (upbit, bybit, coin_symbol) 형식의 튜플 리스트
    """
    logger.debug(f"수신된 데이터 : {data}")

    message = ""

    try:
        # 현재 테더 가격 조회 ~ 테더 가격 1초 캐시 적용되어있음. 
        loop = asyncio.get_event_loop()
        usdt = loop.run_until_complete(get_usdt_ticker_ob_price())
        usdt_price = usdt.get('price', 0)
        if usdt_price == 0:
            raise ValueError("테더 가격이 0입니다. API 호출이 실패했을 수 있습니다.")

        res = loop.run_until_complete(exMgr.calc_exrate_batch(data))
        if res:
            # redis pub/sub 메시지 발행하여 app에서 환율 업데이트
            redis_client.publish('exchange_rate', json.dumps({
                "results": res
            }))
            # 티커별로 돌면서
            for item in res:
                korean_ex = item.get('korean_ex')
                foreign_ex = item.get('foreign_ex')
                # 거래소 객체 생성
                korean_ex_instance = exMgr.exchanges.get(korean_ex)
                if not isinstance(korean_ex_instance, KoreanExchange):
                    logger.error(f"{korean_ex} is not a KoreanExchange instance.")
                    return
                korean_ex_cls: KoreanExchange = korean_ex_instance

                foreign_ex_instance = exMgr.exchanges.get(foreign_ex)
                if not isinstance(foreign_ex_instance, ForeignExchange):
                    logger.error(f"{foreign_ex} is not a ForeignExchange instance.")
                    return
                foreign_ex_cls: ForeignExchange = foreign_ex_instance

                # 자동매매 돌리면서 두 거래소 모두 연결된 고객 조회
                user_ids = exMgr.get_users_with_both_exchanges_running_autotrading(korean_ex, foreign_ex)
                
                # 자동매매 연동된 고객들 돌면서
                for user in user_ids:
                    # 유저 데이터
                    coin_mode = user['coin_mode']
                    selected_coins = user['selected_coins']
                    seed = user['seed_amount']
                    seed_division = user['seed_division']
                    entry_seed = int(seed / seed_division)
                    entry_count = user['entry_count']
                    leverage = user['leverage']
                    entry_rate = user['entry_rate']
                    exit_rate = user['exit_rate']
                    total_entry_count = user['total_entry_count']
                    total_order_amount = user['total_order_amount']
                    allow_average_down = user.get('allow_average_down', False)
                    allow_average_up = user.get('allow_average_up', False)

                    # 사용자의 entry_seed 기준으로 ex_rates를 seed ascending 정렬 후 범위검색
                    ex_rates_sorted = sorted(item.get('ex_rates', []), key=lambda r: r.get('seed', 0))
                    ex_rate_info = None
                    for rate in ex_rates_sorted:
                        if entry_seed < rate.get('seed', 0):
                            ex_rate_info = rate
                            break
                    
                    # 일치하는 시드머니에 대한 환율 정보가 없으면 다음 사용자로 넘어갑니다. ~ 범위 탐색으로 변경했기 때문에 없다면 말이 안됨.
                    if not ex_rate_info:
                        logger.error(f"No matching ex_rate found for user {user['id']} with entry_seed {entry_seed} in item {item['name']}. Skipping.")
                        continue
                        
                    current_ex_rate = ex_rate_info['ex_rate']

                    # 검증 1. 파라미터의 코인과 동일한 코인을 선택했는지 확인 ~ 자동모드이면 검증 안함
                    if coin_mode == 'custom':
                        # 선택한 코인이 현재 처리중인 코인과 동일한지 확인
                        if item['name'] not in selected_coins:
                            continue
                        
                    entry_position_flag = False
                    exit_position_flag = False
                    
                    # 커스텀 모드인 경우, 목표환율 도달했는지 확인
                    if coin_mode == 'custom':
                        if current_ex_rate <= float(entry_rate):
                            entry_position_flag = True
                        if current_ex_rate >= float(exit_rate):
                            exit_position_flag = True
                    # 자동 모드인 경우, 진입환율 대비 1% 이상 상승했는지 확인 
                    # todo : AI를 적용해서 더 개선할 수 있는 방안 고민    
                    else:
                        if current_ex_rate <= float(entry_rate) * 0.99:
                            entry_position_flag = True
                        if current_ex_rate >= float(entry_rate) * 1.01:
                            exit_position_flag = True
                            
                    # for mock test
                    # entry_position_flag = True
                    
                    # 포지션 종료
                    if exit_position_flag:
                        # 포지션 종료전 검증 : 우리 서비스 주문내역DB와 실제 거래소 포지션 비교
                        positionReal = loop.run_until_complete(foreign_ex_cls.get_position_info(item['name']))
                        position = list(filter(lambda x: float(x.get('size', 0)) > 0, positionReal.get('list', [])))

                        # 검증 1. 실제 거래소 포지션이 없으면 skip
                        if len(position) == 0:
                            logger.info(f'''
                                            유저 : {user['id']}
                                            거래소 : {foreign_ex}
                                            티커 : {item['name']}
                                            Karbit 주문내역 존재 : o
                                            실제 거래소 포지션 : x
                                        ''')
                            message += f'''
⚠️ 포지션 불일치
┌─────────────────────
│ 👤 유저 : {user['id']}
│ 🌍 거래소 : {foreign_ex}
│ 🪙 티커 : {item['name']}
│ 📋 Karbit 주문내역 : ✓
│ 🔍 실제 거래소 포지션 : ✗
└─────────────────────
                                        '''
                            continue
                        
                        # 검증 및 정산을 위해 포지션 정보 조회
                        positionDB = exMgr.get_user_positions_for_settlement(user['id'], item['name'])
                        
                        if not positionDB:
                            logger.error(f"포지션 정보 조회 실패 - user_id: {user['id']}, ticker: {item['name']}")
                            continue

                        # 포지션 종료
                        exit_results = loop.run_until_complete(exMgr.exit_position(korean_ex_cls, foreign_ex_cls, item['name'], positionDB['total_kr_volume']))
                        
                        # foreign_ex_cls.close_position 결과
                        kr_exit_result = exit_results[0] 
                        # korean_ex_cls.order 결과
                        fr_exit_result = exit_results[1] 

                        logger.info(f"한국 거래소 주문 결과: {json.dumps(kr_exit_result, indent=2)}")
                        logger.info(f"해외 거래소 주문 결과: {json.dumps(fr_exit_result, indent=2)}")

                        # 종료 주문 ID 추출
                        kr_order_id = kr_exit_result.get('uuid')
                        fr_order_id = fr_exit_result.get('result', {}).get('orderId')

                        if not fr_order_id:
                            logger.error(f"포지션 종료 주문 실패 - fr_order_id: {fr_order_id}")
                            continue
                        
                        if not kr_order_id:
                            logger.error(f"포지션 종료 주문 실패 - kr_order_id: {kr_order_id}")
                            continue

                        # 최적화
                        async def fetch_order_details(fr_order_id, kr_order_id):
                            fr_order_details, kr_order_details = await asyncio.gather(
                                foreign_ex_cls.get_order(fr_order_id),
                                korean_ex_cls.get_order(kr_order_id)
                            )
                            return fr_order_details, kr_order_details
                        # 주문 체결 대기
                        time.sleep(0.1)
                        # 실제 종료 주문 내역 조회
                        fr_order_details, kr_order_details = loop.run_until_complete(fetch_order_details(fr_order_id, kr_order_id))

                        # 실제 종료 환율 계산
                        # 해외거래소 종료(청산) 금액 (USDT)
                        fr_order_volume = Decimal(str(fr_order_details.get('qty', 0)))
                        fr_order_funds = Decimal(str(fr_order_details.get('cumExecValue', 0)))
                        fr_entry_price = Decimal(str(fr_order_details.get('lastPriceOnCreated', 0)))
                        fr_entry_fee = Decimal(str(fr_order_details.get('cumExecFee', 0.0)))

                        # 한국거래소 종료(매도) 금액 (KRW)
                        kr_order_volume = Decimal(str(kr_order_details.get('executed_volume')))
                        kr_order_funds = Decimal(str(kr_order_details.get('trades', [])[0].get('funds', 0)))
                        kr_entry_price = Decimal(str(kr_order_details.get('trades', [])[0].get('price', 0)))
                        kr_entry_fee = Decimal(str(kr_order_details.get('paid_fee', 0.0)))

                        # 실제 종료 환율
                        exit_rate = (kr_order_funds / fr_order_funds).quantize(Decimal('0.01'), rounding=ROUND_DOWN) if fr_order_funds else None
                        
                        avg_entry_rate = positionDB.get('avg_entry_rate', 0)
                        total_kr_funds = Decimal(str(positionDB.get('total_kr_funds', 0)))
                        total_fr_funds = Decimal(str(positionDB.get('total_fr_funds', 0)))
                        total_kr_fee = Decimal(str(positionDB.get('total_kr_fee', 0.0)))
                        total_fr_fee = Decimal(str(positionDB.get('total_fr_fee', 0.0)))
                        # 진입시 자금: KRW + (USDT * 환율)
                        total_invested = total_kr_funds + (total_fr_funds * Decimal(str(usdt_price)))

                        # 종료시 자금: KRW + (USDT * 환율)
                        total_closed = kr_order_funds + (fr_order_funds * Decimal(str(usdt_price)))
                        
                        # 총 수수료
                        total_fee = total_kr_fee + (total_fr_fee * Decimal(str(usdt_price)))
                        total_fee += kr_entry_fee + (fr_entry_fee * Decimal(str(usdt_price)))

                        # profit, profitRate 계산
                        profit = total_closed - total_invested - total_fee
                        profit_rate = (profit / total_invested * Decimal('100')) if total_invested > 0 else Decimal('0')

                        logger.info(f'''
                                        유저 : {user['id']}
                                        티커 : {item['name']}
                                        진입환율(피라미딩): {avg_entry_rate}
                                        종료환율 : {exit_rate}
                                        테더 가격 : {usdt_price}
                                        profit : {profit}
                                        profitRate : {profit_rate}
                                    ''')
                        message += f'''
═══════════════════════
📈 포지션 종료 완료
═══════════════════════
👤 유저 : {user['id']}
🪙 티커 : {item['name']}
📊 진입환율(피라미딩): {avg_entry_rate}
📊 종료환율 : {exit_rate}
💰 테더 가격 : {usdt_price}
💵 수익 : {round(profit,2)}
📈 수익률 : {round(profit_rate,2)}%
═══════════════════════
                        '''
                        exMgr.update_strategies(user['id'], entry_count=entry_count-1)
                        # 누적주문횟수, 누적주문금액 갱신
                        exMgr.update_users(user['id'], total_entry_count=total_entry_count+1, total_order_amount=total_order_amount+int(total_kr_funds))
                        
                        # 포지션 정보 저장
                        position_data = {
                            'strategy_id': user['active_strategy_id'],
                            'coin_symbol': item['name'],
                            'leverage': leverage,
                            'status': 'CLOSED',
                            'kr_exchange': korean_ex.upper(),
                            'kr_order_id': kr_order_id,
                            'kr_price': float(kr_entry_price),
                            'kr_volume': float(kr_order_volume),
                            'kr_funds': float(kr_order_funds),
                            'kr_fee': float(kr_entry_fee),
                            'fr_exchange': foreign_ex.upper(),
                            'fr_order_id': fr_order_id,
                            'fr_price': float(fr_entry_price),
                            'fr_volume': float(fr_order_volume),
                            'fr_funds': float(fr_order_funds),
                            'fr_fee': float(fr_entry_fee),
                            'entry_rate': float(avg_entry_rate),
                            'exit_rate': float(exit_rate) if exit_rate is not None else 0.0,
                            'profit': float(profit),
                            'profit_rate': float(profit_rate),
                            'usdt_price': float(usdt_price)
                        }
                        exMgr.insert_positions(user['id'], **position_data)

                    # 포지션 진입
                    elif entry_position_flag: 
                        message = f'''
═══════════════════════
🎯 포지션 진입 기회 포착
═══════════════════════
🇰🇷 한국거래소 : {korean_ex}
🌍 해외거래소 : {foreign_ex}
🪙 티커 : {item['name']}
📊 포착환율 : {round(current_ex_rate,2)}
💰 테더가격 : {usdt_price}
═══════════════════════
'''
                        
                        # 잔액 동시조회 ~ 한쪽만 잔액이 부족해서 한쪽만 들어가는 불상사를 막기위해서             
                        kr_balance, fr_balance = loop.run_until_complete(get_both_ex_available_balance(korean_ex_cls, foreign_ex_cls))
                        
                        # 검증 1. 한국거래소 잔액과 진입시드 비교 
                        if kr_balance < entry_seed:
                            logger.info(f'''
                                            유저 : {user['id']}
                                            해외거래소 : {foreign_ex}
                                            포지션 주문 실패 
                                            사유 : 잔액부족
                                            주문가능잔액 : {kr_balance}''')
                            message += f'''
❌ 포지션 진입 실패
┌─────────────────────
│ 👤 유저 : {user['id']}
│ 🌍 거래소 : {foreign_ex}
│ ❗ 사유 : 잔액부족
│ 💰 주문가능잔액 : {kr_balance}₩
└─────────────────────
'''
                            continue
                        
                        # 검증 2. 외국거래소 잔액과 진입시드 비교 ~ 설정시드는 원화기준금액이므로 테더로 환산한다.
                        if fr_balance < round(entry_seed / usdt_price, 2):
                            logger.info(f'''
                                            유저 : {user['id']}
                                            해외거래소 : {foreign_ex}
                                            포지션 주문 실패 
                                            사유 : 잔액부족
                                            주문가능잔액 : {fr_balance}''')
                            message += f'''
❌ 포지션 진입 실패
┌─────────────────────
│ 👤 유저 : {user['id']}
│ 🌍 해외거래소 : {foreign_ex}
│ ❗ 사유 : 잔액부족
│ 💰 주문가능잔액 : {fr_balance}$
└─────────────────────
'''
                            continue

                        # 검증 3. 누적 포지션 진입 횟수 확인
                        if seed_division <= entry_count:
                            logger.info(f'''
                                            유저 : {user['id']}
                                            해외거래소 : {foreign_ex}
                                            포지션 주문 실패 
                                            사유 : 누적 포지션 진입 횟수 초과
                                            포지션 진입 가능 횟수 : {seed_division}
                                            현재값 : {entry_count}''')
                            message += f'''
❌ 포지션 진입 실패
┌─────────────────────
│ 👤 유저 : {user['id']}
│ 🌍 해외거래소 : {foreign_ex}
│ ❗ 사유 : 누적 포지션 진입 횟수 초과
│ 🔢 진입 가능 횟수 : {seed_division}
│ 📊 현재 진입 횟수 : {entry_count}
└─────────────────────
'''
                            continue
                        
                        # 검증 4. 이미 진입한 포지션이라면, 물타기 허용여부에 따라 더 낮은 환율에서만 진입 허용
                        existing_positions = exMgr.get_user_positions_for_settlement(user['id'], item['name'])
                        if existing_positions:
                            # 물타기 허용이 안되면 진입 불가
                            if not allow_average_down:
                                continue

                            # 물타기 허용이면서 현재 환율이 기존 포지션의 평균 진입가보다 높으면 진입 불가
                            if allow_average_down and current_ex_rate > existing_positions.get('avg_entry_rate', 0):
                                continue

                        # 한국거래소 먼저 주문 ~ 주문량을 알아야 같은 주문량으로 해외거래소에서 포지션을 잡을 수 있기 때문
                        kr_order = loop.run_until_complete(korean_ex_cls.order(item['name'], 'bid', entry_seed))
                        kr_order_id = kr_order.get('uuid')
                        
                        # for mock test
                        # kr_order_id = 'test-uuid'

                        logger.info(f'''
                                        유저 : {user['id']}
                                        한국거래소 : {korean_ex}
                                        주문 ID : {kr_order_id}''')
                        
                        if not kr_order_id:
                            logger.error(f'''
                                                유저 : {user['id']}
                                                한국거래소 : {korean_ex}
                                                주문 실패''')
                            message += f'''
                                            유저 : {user['id']}
                                            한국거래소 : {korean_ex}
                                            주문 실패
'''
                            continue
                        
                        # 주문 체결 대기
                        time.sleep(0.1)
                        
                        # 한국거래소 주문 체결량 조회
                        kr_order_result = loop.run_until_complete(korean_ex_cls.get_order(kr_order_id))
                        
                        # for mock test
                        # kr_order_result = {
                        #     'uuid': 'e367f352-f537-4770-8de0-eb2d8a1cd0f4', 
                        #     'side': 'bid', 
                        #     'ord_type': 'price', 
                        #     'price': '10000', 
                        #     'state': 'wait', 
                        #     'market': 'KRW-AXS', 
                        #     'created_at': '2025-09-01T01:07:00+09:00', 
                        #     'reserved_fee': '5', 
                        #     'remaining_fee': '5', 
                        #     'paid_fee': '0', 
                        #     'locked': '10005', 
                        #     'prevented_locked': '0', 
                        #     'executed_volume': '2.878', 
                        #     'trades_count': 0, 
                        #     'identifier': 'f1ee6ce4-bf91-4340-bd4b-50186e0f8071',
                        #     'trades': [
                        #         {
                        #             "market": "KRW-AXS",
                        #             "uuid": "795dff29-bba6-49b2-baab-63473ab7931c",
                        #             "price": "3475",
                        #             "volume": "2.878",
                        #             "funds": "10000",
                        #             "trend": "down",
                        #             "created_at": "2025-08-09T16:44:00.597751+09:00",
                        #             "side": "bid"
                        #         }
                        #     ]
                        # }

                        logger.info(f"한국거래소 주문 결과: {json.dumps(kr_order_result, indent=2)}")

                        kr_order_volume = Decimal(str(kr_order_result.get('executed_volume')))
                        kr_order_funds = Decimal(str(kr_order_result.get('trades', [])[0].get('funds', 0)))
                        kr_entry_price = Decimal(str(kr_order_result.get('trades', [])[0].get('price', 0)))
                        kr_entry_fee = Decimal(str(kr_order_result.get('reserved_fee', 0.0)))

                        if not kr_order_volume or not kr_order_funds:
                            logger.error(f"한국거래소 주문 결과에서 volume을 찾을 수 없습니다: {kr_order_result} (유저 {user['id']})")
                            message += f'''
❌ 주문 처리 실패
┌─────────────────────
│ 👤 유저 : {user['id']}
│ 🇰🇷 한국거래소 주문 결과에서 volume을 찾을 수 없습니다
│ 📊 결과 : {kr_order_result}
└─────────────────────
'''
                            continue
                        
                        # 해외거래소 주문최소가능단위 조회
                        lot_size = loop.run_until_complete(foreign_ex_cls.get_lot_size(item['name']))
                        if lot_size is None:
                            logger.error(f"해외거래소 주문 최소 가능 단위 조회 실패 (유저 {user['id']})")
                            message += f'''
❌ 거래소 설정 실패
┌─────────────────────
│ 👤 유저 : {user['id']}
│ 🌍 해외거래소 주문 최소 가능 단위 조회 실패
└─────────────────────
'''
                            continue

                        rounded_volume = round_volume_to_lot_size(kr_order_volume, lot_size)

                        logger.info(f"Rounded volume for 해외거래소 order: {rounded_volume} (유저 {user['id']})")

                        if rounded_volume <= 0:
                            logger.error(f"해외거래소 주문 가능한 최소 수량 미만: {kr_order_volume} -> {rounded_volume} (유저 {user['id']})")
                            message += f'''
❌ 주문 수량 부족
┌─────────────────────
│ 👤 유저 : {user['id']}
│ 📊 원래 수량 : {kr_order_volume}
│ 📊 조정된 수량 : {rounded_volume}
│ ❗ 해외거래소 주문 가능한 최소 수량 미만
└─────────────────────
'''
                            continue
                        
                        # 해외거래소 레버리지 설정
                        fr_leverage = loop.run_until_complete(foreign_ex_cls.set_leverage(item['name'], str(leverage)))
                        if fr_leverage.get('retMsg') != 'OK' and fr_leverage.get('retMsg') != 'leverage not modified':
                            logger.error(f"해외거래소 레버리지 설정 실패: {fr_leverage} (유저 {user['id']})")
                            message += f'''
❌ 레버리지 설정 실패
┌─────────────────────
│ 👤 유저 : {user['id']}
│ ⚡ 설정 결과 : {fr_leverage}
└─────────────────────
'''
                            continue

                        # 해외거래소 주문 실행
                        fr_order = loop.run_until_complete(foreign_ex_cls.order(item['name'], 'ask', rounded_volume))
                        logger.info(f"해외거래소 주문 결과: {json.dumps(fr_order, indent=2)}")
                        
                        fr_order_id = fr_order.get('result', {}).get('orderId')
                        
                        # for mock test
                        # fr_order_id = 'test-uuid'
                        
                        logger.info(f'''
                                        유저 : {user['id']}
                                        해외거래소 : {foreign_ex}
                                        주문 ID : {fr_order_id}''')
                        if not fr_order_id:
                            logger.error(f"해외거래소 주문 실행 실패: (유저 {user['id']})")
                            message += f'''
❌ 해외거래소 주문 실행 실패
┌─────────────────────
│ 👤 유저 : {user['id']}
│ 🌍 거래소 : {foreign_ex}
│ ❗ 주문 ID 생성 실패
└─────────────────────
'''
                            continue
                        
                        # 해외거래소 주문 결과 조회
                        fr_order_result = loop.run_until_complete(foreign_ex_cls.get_order(fr_order_id))
                        # for mock test
                        # fr_order_result = {
                        #     'symbol': 'AXSUSDT', 
                        #     'orderType': 'Market', 
                        #     'orderLinkId': 'AXS_20250901 01:26:31', 
                        #     'slLimitPrice': '0', 
                        #     'orderId': '73b917c7-53b7-4917-8b92-47836f0092fb', 
                        #     'cancelType': 'UNKNOWN', 
                        #     'avgPrice': '2.505', 
                        #     'stopOrderType': '', 
                        #     'lastPriceOnCreated': '2.505', 
                        #     'orderStatus': 'Filled', 
                        #     'createType': 'CreateByUser', 
                        #     'takeProfit': '', 
                        #     'cumExecValue': '7.2645', 
                        #     'tpslMode': '', 
                        #     'smpType': 'None', 
                        #     'triggerDirection': 0, 
                        #     'blockTradeId': '', 
                        #     'isLeverage': '', 
                        #     'rejectReason': 'EC_NoError', 
                        #     'price': '2.255', 
                        #     'orderIv': '', 
                        #     'createdTime': '1756657591937', 
                        #     'tpTriggerBy': '', 
                        #     'positionIdx': 0, 
                        #     'timeInForce': 'IOC', 
                        #     'leavesValue': '0', 
                        #     'updatedTime': '1756657591941', 
                        #     'side': 'Sell', 
                        #     'smpGroup': 0, 
                        #     'triggerPrice': '', 
                        #     'tpLimitPrice': '0', 
                        #     'cumExecFee': '0.00399548', 
                        #     'leavesQty': '0', 
                        #     'slTriggerBy': '', 
                        #     'closeOnTrigger': False, 
                        #     'placeType': '', 
                        #     'cumExecQty': '2.9', 
                        #     'reduceOnly': False, 
                        #     'qty': '2.9', 
                        #     'stopLoss': '', 
                        #     'marketUnit': '', 
                        #     'smpOrderId': '', 
                        #     'triggerBy': ''
                        # }
                        
                        fr_order_volume = Decimal(str(fr_order_result.get('qty', 0)))
                        fr_order_funds = Decimal(str(fr_order_result.get('cumExecValue', 0)))
                        fr_entry_price = Decimal(str(fr_order_result.get('lastPriceOnCreated', 0)))
                        fr_entry_fee = fr_order_result.get('cumExecFee', 0.0)
                        
                        # 주문환율 구하기
                        order_rate = (kr_order_funds / fr_order_funds).quantize(Decimal('0.01'), rounding=ROUND_DOWN) if fr_order_funds else None

                        logger.info(f'''
                                        유저 : {user['id']}
                                        한국거래소 : {korean_ex}
                                        한국 체결량 : {kr_order_volume}
                                        한국 체결금액 : {kr_order_funds}₩
                                        해외거래소 : {foreign_ex}
                                        해외 체결량 : {fr_order_volume}
                                        주문 체결금액 : {fr_order_funds}$
                                        레버리지 : {leverage}
                                        ''')
                        message += f'''
═══════════════════════
✅ 포지션 진입 성공
═══════════════════════
👤 유저 : {user['id']}
🇰🇷 한국거래소 : {korean_ex}
📊 한국 체결량 : {kr_order_volume}
💰 한국 체결금액 : {kr_order_funds}₩
🌍 해외거래소 : {foreign_ex}
📊 해외 체결량 : {fr_order_volume}
💰 주문 체결금액 : {fr_order_funds}$
⚡ 레버리지 : {leverage}x
═══════════════════════
📊 주문환율 : {order_rate}
💰 테더가격 : {usdt_price}
═══════════════════════
                        '''
                                        
                        exMgr.update_strategies(user['id'], entry_count=entry_count+1)
                        # 누적주문횟수, 누적주문금액 갱신
                        exMgr.update_users(user['id'], total_entry_count=total_entry_count+1, total_order_amount=total_order_amount+int(kr_order_funds))
                        # 포지션 데이터 저장
                        position_data = {
                            'strategy_id': user['active_strategy_id'],
                            'coin_symbol': item['name'],
                            'leverage': leverage,
                            'status': 'PYRAMIDING' if entry_count > 1 else 'OPEN',
                            'kr_exchange': korean_ex.upper(),
                            'kr_order_id': kr_order_id,
                            'kr_price': float(kr_entry_price),
                            'kr_volume': float(kr_order_volume),
                            'kr_funds': float(kr_order_funds),
                            'kr_fee': float(kr_entry_fee),
                            'fr_exchange': foreign_ex.upper(),
                            'fr_order_id': fr_order_id,
                            'fr_price': float(fr_entry_price),
                            'fr_volume': float(fr_order_volume),
                            'fr_funds': float(fr_order_funds),
                            'fr_fee': float(fr_entry_fee),
                            'entry_rate': float(order_rate) if order_rate is not None else 0.0,
                            'usdt_price': float(usdt_price)
                        }
                        exMgr.insert_positions(user['id'], **position_data)

    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis connection error: {e}")
        if retry_count < 3:  # 무한루프 방지
            reconnect_redis()
            logger.info("작업 전체를 재시도합니다.")
            work_task(data, retry_count + 1)
        else:
            logger.error("최대 재시도 횟수 초과. 작업을 중단합니다.")
            return
    except Exception as e:
        logger.error(f"작업 처리 중 알 수 없는 에러가 발생했습니다: {e}", exc_info=True)
        message += f'''
❌ 시스템 오류
┌─────────────────────
│ ⚠️  작업 처리 중 알 수 없는 에러가 발생했습니다
│ 🔧 시스템 점검이 필요합니다
└─────────────────────
'''
        # 일반 에러는 재시도하지 않고 바로 중단
        return
    finally:
        # 작업 완료 후 Telegram 메시지 전송
        if message:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(send_telegram(message))
            logger.info(f"Telegram 메시지를 전송했습니다: {message}")

    logger.info("작업이 성공적으로 완료되었습니다.")
    
if __name__ == "__main__":
    app.worker_main()
    # work_task(['BTC'], 'upbit', 'bybit')
