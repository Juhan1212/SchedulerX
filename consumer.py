from decimal import ROUND_DOWN, Decimal
import json
from pathlib import Path
from async_lru import alru_cache
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
from backend.utils.telegram import send_telegram, send_telegram_to_admin
import gzip
import base64

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

# 테더 가격 호출 api async 캐시설정
@alru_cache(maxsize=10, ttl=1)
async def get_usdt_ticker_ob_price():
    return await UpbitExchange.get_ticker_ob_price('USDT')

# facade exMgr 객체에 거래소 등록
exMgr.register_exchange("upbit", UpbitExchange.from_env())
exMgr.register_exchange("bybit", BybitExchange.from_env())
exMgr.register_exchange("bithumb", BithumbExchange.from_env())

def round_volume_to_lot_size(volume, lot_size):
    lot_size_decimal = Decimal(str(lot_size))
    volume_decimal = Decimal(str(volume))
    rounded_volume = (volume_decimal // lot_size_decimal) * lot_size_decimal
    return float(rounded_volume)

# 최적화용 함수              
async def get_both_ex_available_balance(korean_ex_cls, foreign_ex_cls):
    return await asyncio.gather(
        korean_ex_cls.get_available_balance(),
        foreign_ex_cls.get_available_balance()
    )

async def fetch_order_details(foreign_ex_cls, korean_ex_cls, symbol, kr_order_id):
    fr_order_details, kr_order_details = await asyncio.gather(
        foreign_ex_cls.get_position_closed_pnl(symbol),
        korean_ex_cls.get_order(kr_order_id)
    )
    return fr_order_details, kr_order_details

async def process_user(user, item, korean_ex_cls, foreign_ex_cls, korean_ex, foreign_ex, usdt_price):
    """단일 사용자의 포지션 진입/종료를 처리"""
    message = ""
    try:                
        # 유저 데이터
        coin_mode = user['coin_mode']
        trade_mode = user['trade_mode']
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
        telegram_chat_id = user.get('telegram_chat_id', None)
        telegram_username = user.get('telegram_username', None)
        telegram_notifications_enabled = user.get('telegram_notifications_enabled', False)
        entry_position_flag = False 
        exit_position_flag = False

        # 사용자의 entry_seed 기준으로 ex_rates를 seed ascending 정렬 후 범위검색
        ex_rates_sorted = sorted(item.get('ex_rates', []), key=lambda r: r.get('seed', 0))
        ex_rate_info = None
        for rate in ex_rates_sorted:
            # entry_seed 이상인 첫 번째 시드를 선택 (기존: entry_seed < seed, 변경: entry_seed <= seed)
            if entry_seed <= rate.get('seed', 0):
                ex_rate_info = rate
                break

        # 일치하는 시드머니에 대한 환율 정보가 없으면 다음 사용자로 넘어갑니다. ~ 범위 탐색으로 변경했기 때문에 없다면 말이 안됨.
        if not ex_rate_info:
            logger.error(f"No matching ex_rate found for user {user['email']} with entry_seed {entry_seed} in item {item['name']}. Skipping.")
            return
        
        current_entry_ex_rate = ex_rate_info['entry_ex_rate']
        current_exit_ex_rate = ex_rate_info['exit_ex_rate']

        # 방어로직 - 호가창 모두 소진되어도 주문금액이 남는 경우 제대로된 환율 계산 불가
        if current_entry_ex_rate is None or current_exit_ex_rate is None:
            logger.error(f"환율 계산에 실패했습니다. 호가창이 모두 소진되었을 수 있습니다. user: {user['email']}, ticker: {item['name']}, entry_seed: {entry_seed}")
            return

        # 검증 1. 파라미터의 코인과 동일한 코인을 선택했는지 확인 ~ 자동모드이면 검증 안함
        if coin_mode == 'custom':
            # 선택한 코인이 현재 처리중인 코인과 동일한지 확인
            if item['name'] not in selected_coins:
                entry_position_flag = False
                exit_position_flag = False

        positionDB = None
        # 커스텀 모드인 경우, 목표환율 도달했는지 확인
        if trade_mode == 'custom':
            if current_entry_ex_rate <= float(entry_rate):
                entry_position_flag = True
            if current_exit_ex_rate >= float(exit_rate):
                exit_position_flag = True
        # todo : AI를 적용해서 더 개선할 수 있는 방안 고민    
        # 자동 모드인 경우, 진입환율 대비 1% 이상 상승했는지 확인 
        else:
            if current_entry_ex_rate <= float(usdt_price) * 0.99:
                entry_position_flag = True
            else:
                positionDB = exMgr.get_user_positions_for_settlement(user['id'], item['name'], korean_ex.upper(), foreign_ex.upper())
                if positionDB:
                    avg_entry_rate = positionDB.get('avg_entry_rate', 0)
                    if current_exit_ex_rate >= float(avg_entry_rate) * 1.02:
                        exit_position_flag = True
                
        # for mock test
        # entry_position_flag = True

        # 포지션 종료
        if exit_position_flag:
            # 속도를 위해 주석처리
            # # 포지션 종료전 검증 : 우리 서비스 주문내역DB와 실제 거래소 포지션 비교
            # positionReal = await foreign_ex_cls.get_position_info(item['name'])
            # position = list(filter(lambda x: float(x.get('size', 0)) > 0, positionReal.get('list', [])))

            # # 검증 1. 실제 거래소 포지션이 없으면 skip
            # if len(position) == 0:
            #     logger.info(f'''
            #                     유저 : {user['email']}
            #                     한국거래소 : {korean_ex}
            #                     해외거래소 : {foreign_ex}
            #                     티커 : {item['name']}
            #                     현재환율 : {round(current_exit_ex_rate,2)}
            #                     테더가격 : {usdt_price}
            #                     Karbit 주문내역 존재 : o
            #                     실제 거래소 포지션 : x
            #                 ''')
        
        
            #     if telegram_notifications_enabled and telegram_chat_id:
            #         telegram_message = f'''
            #         ⚠️ 포지션 불일치
            #         ┌─────────────────────
            #         │ 👤 유저 : {telegram_username}
            #         │ 🌍 한국거래소 : {korean_ex}
            #         │ 🌍 해외거래소 : {foreign_ex}
            #         │ 🪙 티커 : {item['name']}
            #         │ 📋 Karbit 자동매매 포지션 종료 실패
            #         │ 🔍 사유 : 실제 거래소에 현재 포지션이 존재 x
            #         └─────────────────────
            #         '''
            #         await send_telegram(telegram_chat_id, telegram_message)
            #     return
            
            # 검증 및 정산을 위해 포지션 정보 조회 (이미 조회한 경우 재사용)
            if not positionDB:
                positionDB = exMgr.get_user_positions_for_settlement(user['id'], item['name'], korean_ex.upper(), foreign_ex.upper())
            
            if not positionDB:
                logger.error(f"포지션 정보 조회 실패 - user_id: {user['email']}, ticker: {item['name']}")
                return
            
            # 포지션 종료전 환율 재확인
            recheck_data = [(korean_ex, foreign_ex, item['name'])]
            recheck_result = await exMgr.calc_exrate_batch(recheck_data)
            
            if not recheck_result or len(recheck_result) == 0:
                logger.error(f"환율 재확인 실패 - user: {user['email']}, ticker: {item['name']}")
                return
            
            # 재확인한 환율 데이터에서 entry_seed에 맞는 환율 찾기
            recheck_ex_rates = sorted(recheck_result[0].get('ex_rates', []), key=lambda r: r.get('seed', 0))
            recheck_ex_rate_info = None
            for rate in recheck_ex_rates:
                # entry_seed 이상인 첫 번째 시드를 선택 (기존: entry_seed < seed, 변경: entry_seed <= seed)
                if entry_seed <= rate.get('seed', 0):
                    recheck_ex_rate_info = rate
                    break
            
            if not recheck_ex_rate_info or recheck_ex_rate_info['exit_ex_rate'] is None:
                logger.error(f"환율 재확인 데이터 추출 실패 - user: {user['email']}, ticker: {item['name']}, entry_seed: {entry_seed}")
                return
            
            rechecked_exit_ex_rate = recheck_ex_rate_info['exit_ex_rate']
            
            # 환율 오차범위 검증 (0.5% 이내)
            rate_difference = abs(rechecked_exit_ex_rate - current_exit_ex_rate)
            rate_difference_percent = (rate_difference / current_exit_ex_rate) * 100
            
            if rate_difference_percent > 0.5:
                logger.warning(f'''
                                환율 변동으로 포지션 종료 취소
                                유저 : {user['email']}
                                티커 : {item['name']}
                                초기 환율 : {current_exit_ex_rate}
                                재확인 환율 : {rechecked_exit_ex_rate}
                                변동률 : {rate_difference_percent:.2f}%
                            ''')
                message += f'''
                ⚠️ 포지션 종료 취소
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🪙 티커 : {item['name']}
                │ ❗ 사유 : 환율 변동폭 초과
                │ 📊 포착 환율 : {current_exit_ex_rate}
                │ 📊 재확인 환율 : {rechecked_exit_ex_rate}
                │ 📈 변동률 : {rate_difference_percent:.2f}%
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return
            
            logger.info(f'''
                            환율 재확인 완료
                            유저 : {user['email']}
                            티커 : {item['name']}
                            초기 환율 : {current_exit_ex_rate}
                            재확인 환율 : {rechecked_exit_ex_rate}
                            변동률 : {rate_difference_percent:.2f}%
                        ''')

            # 포지션 종료
            exit_results = await exMgr.exit_position(korean_ex_cls, foreign_ex_cls, item['name'], positionDB['total_kr_volume'])

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
                return
            
            if not kr_order_id:
                logger.error(f"포지션 종료 주문 실패 - kr_order_id: {kr_order_id}")
                return
            
            # 주문 체결 대기
            await asyncio.sleep(0.5)
            # 실제 종료 주문 내역 조회
            fr_order_details, kr_order_details = await fetch_order_details(foreign_ex_cls, korean_ex_cls, item['name'], kr_order_id)
            
            logger.info(f"해외거래소 종료 주문 상세: {json.dumps(fr_order_details, indent=2)}")
            logger.info(f"한국거래소 종료 주문 상세: {json.dumps(kr_order_details, indent=2)}")

            # 실제 종료 환율 계산
            # 해외거래소 종료(청산) 금액 (USDT)
            fr_order_volume = Decimal(str(fr_order_details.get('qty', 0)))
            fr_order_funds = Decimal(str(fr_order_details.get('cumEntryValue', 0)))
            fr_pnl = Decimal(str(fr_order_details.get('closedPnl', 0)))
            fr_total_fee = Decimal(str(fr_order_details.get('openFee', 0.0))) + Decimal(str(fr_order_details.get('closeFee', 0.0)))
            fr_avg_exit_price = Decimal(str(fr_order_details.get('avgExitPrice', 0)))
            fr_entry_fee = Decimal(str(fr_order_details.get('openFee', 0.0)))
            fr_entry_price = Decimal(str(fr_order_details.get('avgExitPrice', 0)))

            # 한국거래소 종료(매도) 금액 (KRW)
            kr_trades = kr_order_details.get('trades', [])
            if not kr_trades:
                logger.error(f"한국거래소 trades 정보가 없습니다 - user: {user['email']}, order_id: {kr_order_id}")
                return

            # trades 배열을 순회하며 총 체결금액과 총 체결수량 계산
            total_kr_funds = Decimal('0')
            total_kr_volume = Decimal('0')

            for trade in kr_trades:
                trade_funds = Decimal(str(trade.get('funds', 0)))
                trade_volume = Decimal(str(trade.get('volume', 0)))
                total_kr_funds += trade_funds
                total_kr_volume += trade_volume

            # 실제 평균 체결가 계산
            if total_kr_volume > 0:
                kr_avg_exit_price = (total_kr_funds / total_kr_volume).quantize(Decimal('0.00000000'))
            else:
                logger.error(f"한국거래소 체결 수량이 0입니다 - user: {user['email']}, order_id: {kr_order_id}")
                return

            kr_order_volume = total_kr_volume
            kr_order_funds = total_kr_funds
            kr_entry_price = kr_avg_exit_price
            kr_entry_fee = Decimal(str(kr_order_details.get('paid_fee', 0.0)))

            # 실제 종료 환율
            if fr_avg_exit_price > 0 and kr_avg_exit_price > 0:
                exit_rate = (kr_avg_exit_price / fr_avg_exit_price).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            else:
                logger.error(f"환율 계산 불가 - kr_avg_exit_price: {kr_avg_exit_price}, fr_avg_exit_price: {fr_avg_exit_price}")
                return
            
            avg_entry_rate = positionDB.get('avg_entry_rate', 0)
            total_kr_funds = Decimal(str(positionDB.get('total_kr_funds', 0)))
            total_fr_funds = Decimal(str(positionDB.get('total_fr_funds', 0)))
            total_kr_fee = Decimal(str(positionDB.get('total_kr_fee', 0.0)))

            # 진입시 자금: KRW + (USDT * 환율)
            total_invested = total_kr_funds + (total_fr_funds * Decimal(str(usdt_price)))

            # 총 수수료
            total_fee = total_kr_fee + kr_entry_fee + (fr_total_fee * Decimal(str(usdt_price)))
            
            # profit, profitRate 계산
            kr_profit = kr_order_funds - total_kr_funds - (total_kr_fee + kr_entry_fee)
            fr_profit = fr_pnl - (fr_total_fee)
            
            # 원화 환산
            profit = kr_profit + (fr_profit * Decimal(str(usdt_price)))
            profit_rate = (profit / total_invested * Decimal('100')) if total_invested > 0 else Decimal('0')

            logger.info(f'''
                            유저 : {user['email']}
                            티커 : {item['name']}
                            진입환율(피라미딩): {avg_entry_rate}
                            종료환율 : {exit_rate}
                            테더 가격 : {usdt_price}
                            profit : {profit}
                            profitRate : {profit_rate}
                        ''')
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
                'fr_original_price': float(fr_order_details.get('orderPrice', 0)),
                'fr_volume': float(fr_order_volume),
                'fr_funds': float(fr_order_funds),
                'fr_fee': float(fr_entry_fee),
                'entry_rate': float(avg_entry_rate),
                'exit_rate': float(exit_rate) if exit_rate is not None else 0.0,
                'profit': float(profit),
                'profit_rate': float(profit_rate),
                'usdt_price': float(usdt_price),
            }
            exMgr.insert_positions(user['id'], **position_data)
            message += f'''
            ═══════════════════════
            📈 포지션 종료 완료
            ═══════════════════════
            👤 유저 : {telegram_username}
            🪙 티커 : {item['name']}
            📊 진입환율(피라미딩): {avg_entry_rate}
            📊 종료환율 : {exit_rate}
            💰 테더 가격 : {usdt_price}
            💰 수수료 : {total_fee}₩
            💵 수익 : {round(profit,2)}₩
            📈 수익률 : {round(profit_rate,2)}%
            ═══════════════════════
            '''
            if telegram_notifications_enabled and telegram_chat_id:
                await send_telegram(telegram_chat_id, message)
            return

        # 포지션 진입
        elif entry_position_flag: 
            message = f'''
            ═══════════════════════
            🎯 포지션 진입 기회 포착
            ═══════════════════════
            🇰🇷 한국거래소 : {korean_ex}
            🌍 해외거래소 : {foreign_ex}
            🪙 티커 : {item['name']}
            📊 포착환율 : {round(current_entry_ex_rate,2)}
            💰 테더가격 : {usdt_price}
            ═══════════════════════
            '''

            # 포지션 진입전 검증
            # 검증 0. 포지션 누적진입 횟수와 시드 분할 횟수 비교
            if seed_division <= entry_count:
                return message

            # 잔액 동시조회 ~ 한쪽만 잔액이 부족해서 한쪽만 들어가는 불상사를 막기위해서
            kr_balance, fr_balance = await get_both_ex_available_balance(korean_ex_cls, foreign_ex_cls)

            # 검증 1. 한국거래소 잔액과 진입시드 비교
            if kr_balance < entry_seed:
                logger.info(f'''
                                유저 : {user['email']}
                                한국거래소 : {korean_ex}
                                포지션 주문 실패 
                                사유 : 잔액부족
                                주문가능잔액 : {kr_balance}''')
                message += f'''
                ❌ 포지션 진입 실패
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🌍 거래소 : {korean_ex}
                │ ❗ 사유 : 잔액부족
                │ 💰 주문가능잔액 : {kr_balance}₩
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return
            
            # 검증 2. 외국거래소 잔액과 진입시드 비교 ~ 설정시드는 원화기준금액이므로 테더로 환산한다.
            if fr_balance < round(entry_seed / usdt_price, 2):
                logger.info(f'''
                                유저 : {user['email']}
                                해외거래소 : {foreign_ex}
                                포지션 주문 실패 
                                사유 : 잔액부족
                                주문가능잔액 : {fr_balance}''')
                message += f'''
                ❌ 포지션 진입 실패
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🌍 해외거래소 : {foreign_ex}
                │ ❗ 사유 : 잔액부족
                │ 💰 주문가능잔액 : {fr_balance}$
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return

            # 검증 3. 누적 포지션 진입 횟수 확인
            if seed_division <= entry_count:
                logger.info(f'''
                                유저 : {user['email']}
                                해외거래소 : {foreign_ex}
                                포지션 주문 실패 
                                사유 : 누적 포지션 진입 횟수 초과
                                포지션 진입 가능 횟수 : {seed_division}
                                현재값 : {entry_count}''')
                message += f'''
                ❌ 포지션 진입 실패
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🌍 해외거래소 : {foreign_ex}
                │ ❗ 사유 : 누적 포지션 진입 횟수 초과
                │ 🔢 진입 가능 횟수 : {seed_division}
                │ 📊 현재 진입 횟수 : {entry_count}
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return
            
            # 검증 4. 이미 진입한 포지션이라면, 물타기 허용여부에 따라 더 낮은 환율에서만 진입 허용
            existing_positions = exMgr.get_user_positions_for_settlement(user['id'], item['name'], korean_ex.upper(), foreign_ex.upper())
            if existing_positions:
                # 물타기 허용이 안되면 진입 불가
                if not allow_average_down:
                    return message

                # 물타기 허용이면서 현재 환율이 기존 포지션의 평균 진입가보다 높으면 진입 불가
                if allow_average_down and current_entry_ex_rate > existing_positions.get('avg_entry_rate', 0):
                    return message
                
            # 포지션 실제 주문하기 전에 환율 재확인
            recheck_data = [(korean_ex, foreign_ex, item['name'])]
            recheck_result = await exMgr.calc_exrate_batch(recheck_data)
            
            if not recheck_result or len(recheck_result) == 0:
                logger.error(f"환율 재확인 실패 - user: {user['email']}, ticker: {item['name']}")
                return
            
            # 재확인한 환율 데이터에서 entry_seed에 맞는 환율 찾기
            recheck_ex_rates = sorted(recheck_result[0].get('ex_rates', []), key=lambda r: r.get('seed', 0))
            recheck_ex_rate_info = None
            for rate in recheck_ex_rates:
                # entry_seed 이상인 첫 번째 시드를 선택 (기존: entry_seed < seed, 변경: entry_seed <= seed)
                if entry_seed <= rate.get('seed', 0):
                    recheck_ex_rate_info = rate
                    break
            
            if not recheck_ex_rate_info or recheck_ex_rate_info['entry_ex_rate'] is None:
                logger.error(f"환율 재확인 데이터 추출 실패 - user: {user['email']}, ticker: {item['name']}, entry_seed: {entry_seed}")
                return
            
            rechecked_entry_ex_rate = recheck_ex_rate_info['entry_ex_rate']
            
            # 환율 오차범위 검증 (0.5% 이내)
            rate_difference = abs(rechecked_entry_ex_rate - current_entry_ex_rate)
            rate_difference_percent = (rate_difference / current_entry_ex_rate) * 100
            
            if rate_difference_percent > 0.5:
                logger.warning(f'''
                                환율 변동으로 주문 취소
                                유저 : {user['email']}
                                티커 : {item['name']}
                                초기 환율 : {current_entry_ex_rate}
                                재확인 환율 : {rechecked_entry_ex_rate}
                                변동률 : {rate_difference_percent:.2f}%
                            ''')
                message += f'''
                ⚠️ 포지션 진입 취소
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🪙 티커 : {item['name']}
                │ ❗ 사유 : 환율 변동폭 초과
                │ 📊 포착 환율 : {current_entry_ex_rate}
                │ 📊 재확인 환율 : {rechecked_entry_ex_rate}
                │ 📈 변동률 : {rate_difference_percent:.2f}%
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return
            
            logger.info(f'''
                            환율 재확인 완료
                            유저 : {user['email']}
                            티커 : {item['name']}
                            초기 환율 : {current_entry_ex_rate}
                            재확인 환율 : {rechecked_entry_ex_rate}
                            변동률 : {rate_difference_percent:.2f}%
                        ''')

            # 한국거래소 먼저 주문 ~ 주문량을 알아야 같은 주문량으로 해외거래소에서 포지션을 잡을 수 있기 때문
            kr_order = await korean_ex_cls.order(item['name'], 'bid', entry_seed)
            kr_order_id = kr_order.get('uuid')
            
            # for mock test
            # kr_order_id = 'test-uuid'

            logger.info(f'''
                            유저 : {user['email']}
                            한국거래소 : {korean_ex}
                            주문 ID : {kr_order_id}''')
            
            if not kr_order_id:
                logger.error(f'''
                                    유저 : {user['email']}
                                    한국거래소 : {korean_ex}
                                    주문 실패''')
                message += f'''
                ❌ 포지션 진입 실패
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🌍 한국거래소 : {korean_ex}
                │ ❗ 사유 : 한국거래소 주문 실패
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return
            
            # 주문 체결 대기
            await asyncio.sleep(0.5)
            
            # 한국거래소 주문 체결량 조회
            kr_order_result = await korean_ex_cls.get_order(kr_order_id)
            
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
            if kr_order_result.get('trades', []) == []:
                await asyncio.sleep(0.5)
                # 2차 조회
                kr_order_result = await korean_ex_cls.get_order(kr_order_id)

            logger.info(f"한국거래소 주문 결과: {json.dumps(kr_order_result, indent=2)}")

            kr_order_volume = Decimal(str(kr_order_result.get('executed_volume')))
            kr_order_funds = Decimal(str(kr_order_result.get('price', 0)))
            executed_volume = Decimal(str(kr_order_result.get('executed_volume', 0)))
            if executed_volume > 0:
                kr_entry_price = (kr_order_funds / executed_volume).quantize(Decimal('0.00000000'))
            else:
                kr_entry_price = Decimal('0.00000000')
            kr_entry_fee = Decimal(str(kr_order_result.get('paid_fee', 0.0)))

            if not kr_order_volume or not kr_order_funds:
                logger.error(f"한국거래소 주문 결과에서 volume을 찾을 수 없습니다: {kr_order_result} (유저 {user['email']})")
                message += f'''
                ❌ 주문 처리 실패
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🇰🇷 한국거래소 주문 결과에서 volume을 찾을 수 없습니다
                │ 📊 결과 : {kr_order_result}
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return
            
            # 해외거래소 주문최소가능단위 조회
            lot_size = await foreign_ex_cls.get_lot_size(item['name'])
            if lot_size is None:
                logger.error(f"해외거래소 주문 최소 가능 단위 조회 실패 (유저 {user['email']})")
                message += f'''
                ❌ 거래소 설정 실패
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🌍 해외거래소 주문 최소 가능 단위 조회 실패
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return

            rounded_volume = round_volume_to_lot_size(kr_order_volume, lot_size)

            logger.info(f"Rounded volume for 해외거래소 order: {rounded_volume} (유저 {user['email']})")

            if rounded_volume <= 0:
                logger.error(f"해외거래소 주문 가능한 최소 수량 미만: {kr_order_volume} -> {rounded_volume} (유저 {user['email']})")
                message += f'''
                ❌ 주문 수량 부족
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 📊 원래 수량 : {kr_order_volume}
                │ 📊 조정된 수량 : {rounded_volume}
                │ ❗ 해외거래소 주문 가능한 최소 수량 미만
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return

            # 해외거래소 레버리지 설정
            fr_leverage = await foreign_ex_cls.set_leverage(item['name'], str(leverage))
            if fr_leverage.get('retMsg') != 'OK' and fr_leverage.get('retMsg') != 'leverage not modified':
                logger.error(f"해외거래소 레버리지 설정 실패: {fr_leverage} (유저 {user['email']})")
                message += f'''
                ❌ 레버리지 설정 실패
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ ⚡ 설정 결과 : {fr_leverage}
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return

            # 해외거래소 주문 실행
            fr_order = await foreign_ex_cls.order(item['name'], 'ask', rounded_volume)
            logger.info(f"해외거래소 주문 결과: {json.dumps(fr_order, indent=2)}")
            
            fr_order_id = fr_order.get('result', {}).get('orderId')
            
            # for mock test
            # fr_order_id = 'test-uuid'
            
            logger.info(f'''
                            유저 : {user['email']}
                            해외거래소 : {foreign_ex}
                            주문 ID : {fr_order_id}''')
            if not fr_order_id:
                logger.error(f"해외거래소 주문 실행 실패: (유저 {user['email']})")
                message += f'''
                ❌ 해외거래소 주문 실행 실패
                ┌─────────────────────
                │ 👤 유저 : {telegram_username}
                │ 🌍 거래소 : {foreign_ex}
                │ ❗ 주문 ID 생성 실패
                └─────────────────────
                '''
                if telegram_notifications_enabled and telegram_chat_id:
                    await send_telegram(telegram_chat_id, message)
                return
            
            await asyncio.sleep(0.5)
            
            # 해외거래소 주문 결과 조회
            fr_order_result = await foreign_ex_cls.get_order(fr_order_id)
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
            
            if fr_order_result.get('orderStatus') != 'Filled':
                await asyncio.sleep(0.5)
                # 2차 조회
                fr_order_result = await foreign_ex_cls.get_order(fr_order_id)
            
            fr_order_volume = Decimal(str(fr_order_result.get('qty', 0)))
            fr_order_funds = Decimal(str(fr_order_result.get('cumExecValue', 0)))
            fr_entry_price = Decimal(str(fr_order_result.get('lastPriceOnCreated', 0)))
            fr_order_price = Decimal(str(fr_order_result.get('price', 0)))
            fr_entry_fee = fr_order_result.get('cumExecFee', 0.0)
            
            # 주문환율 구하기
            order_rate = (kr_order_funds / fr_order_funds).quantize(Decimal('0.01'), rounding=ROUND_DOWN) if fr_order_funds else None

            logger.info(f'''
                            유저 : {user['email']}
                            한국거래소 : {korean_ex}
                            한국 체결량 : {kr_order_volume}
                            한국 체결금액 : {kr_order_funds}₩
                            해외거래소 : {foreign_ex}
                            해외 체결량 : {fr_order_volume}
                            주문 체결금액 : {fr_order_funds}$
                            레버리지 : {leverage}
                            ''')
                            
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
                'fr_original_price': float(fr_order_price),
                'fr_volume': float(fr_order_volume),
                'fr_funds': float(fr_order_funds),
                'fr_fee': float(fr_entry_fee),
                'entry_rate': float(order_rate) if order_rate is not None else 0.0,
                'usdt_price': float(usdt_price)
            }
            exMgr.insert_positions(user['id'], **position_data)
            message += f'''
            ═══════════════════════
            ✅ 포지션 진입 성공
            ═══════════════════════
            👤 유저 : {telegram_username}
            🇰🇷 한국거래소 : {korean_ex}
            📊 한국 체결량 : {kr_order_volume}
            💰 한국 체결금액 : {kr_order_funds}₩
            🌍 해외거래소 : {foreign_ex}
            📊 해외 체결량 : {fr_order_volume}
            💰 주문 체결금액 : {fr_order_funds}$
            ⚡ 레버리지 : {leverage}x
            ═══════════════════════
            📊 포착환율 : {round(current_entry_ex_rate,2)}
            📊 주문환율 : {order_rate}
            💰 테더가격 : {usdt_price}
            ═══════════════════════
            '''
            if telegram_notifications_enabled and telegram_chat_id:
                await send_telegram(telegram_chat_id, message)
            return
    except Exception as e:
        logger.error(f"작업 처리 중 에러가 발생했습니다: {e}", exc_info=True)
    return "error"

@app.task(name='producer.calculate_orderbook_exrate_task', ignore_result=True, soft_time_limit=30)
def work_task(data, retry_count=0):
    """
    Celery 작업을 처리하는 함수입니다.
    Args:
        data (list[tuple]): (upbit, bybit, coin_symbol) 형식의 튜플 리스트
    """
    start_time = time.time()
    logger.debug(f"수신된 데이터 : {data}")

    try:
        # 현재 테더 가격 조회 ~ 테더 가격 1초 캐시 적용되어있음. 
        loop = asyncio.get_event_loop()
        usdt = loop.run_until_complete(get_usdt_ticker_ob_price())
        usdt_price = usdt.get('price', 0)
        if usdt_price == 0:
            raise ValueError("테더 가격이 0입니다. API 호출이 실패했을 수 있습니다.")

        try:
            res = loop.run_until_complete(exMgr.calc_exrate_batch(data))
        except Exception as e:
            logger.error(f"exMgr.calc_exrate_batch 실행 중 에러 발생: {e}", exc_info=True)
            raise  # 예외를 상위 except로 전달

        if res:
            # redis pub/sub 메시지 발행: 데이터 gzip 압축 + base64 인코딩
            raw_json = json.dumps({"results": res})
            compressed = gzip.compress(raw_json.encode('utf-8'))
            encoded = base64.b64encode(compressed).decode('utf-8')
            redis_client.publish('exchange_rate', encoded)
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
                
                # 모든 사용자를 동시에 처리 - 각 코루틴을 생성하여 gather로 실행 (create_task는 실행 중인 이벤트 루프에서만 사용)
                tasks = [process_user(user, item, korean_ex_cls, foreign_ex_cls, korean_ex, foreign_ex, usdt_price)
                         for user in user_ids]
                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        logger.info("작업이 성공적으로 완료되었습니다.")
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
        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_telegram_to_admin(e))
    finally:
        # 작업 실행 시간 로그
        execution_time = time.time() - start_time
        logger.info(f"work_task 실행 시간: {execution_time:.2f}초")

    
if __name__ == "__main__":
    app.worker_main()
    # work_task(['BTC'], 'upbit', 'bybit')
