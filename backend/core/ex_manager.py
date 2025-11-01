import logging
import asyncio
import os
from backend.exchanges import *
import psycopg2
from contextlib import contextmanager
from backend.exchanges.base import Exchange, ForeignExchange, KoreanExchange
from backend.utils.safe_numeric import safe_numeric
from dotenv import load_dotenv
from decimal import Decimal, ROUND_HALF_UP


load_dotenv()

logger = logging.getLogger(__name__)

class ExchangeManager:
    def __init__(self):
        self.exchanges: dict[str, KoreanExchange | ForeignExchange] = {}

    def register_exchange(self, name, exchange):
        self.exchanges[name] = exchange

    async def get_common_tickers(self):
        all_tickers = [set(await exchange.get_tickers()) for exchange in self.exchanges.values()]
        return set.intersection(*all_tickers)

    @contextmanager
    def _get_db_cursor(self):
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        # SQLAlchemy URL을 psycopg2 형식으로 변환
        if database_url.startswith("postgresql://"):
            conn = psycopg2.connect(database_url)
        else:
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        finally:
            conn.close()

    async def upsert_tickers(self):
        """
        데이터베이스에 티커 정보를 갱신합니다.
        """
        async def process_exchange(exchange_name, exchange_obj):
            with self._get_db_cursor() as cursor:
                ticker_infos = await exchange_obj.get_full_ticker_info()
                if not ticker_infos:
                    logger.warning(f"No ticker info found for {exchange_name}")
                    return

                cursor.execute("SELECT id FROM exchanges WHERE eng_name = %s", (exchange_name,))
                exchange_id_row = cursor.fetchone()
                if not exchange_id_row:
                    logger.error(f"Exchange id not found for {exchange_name}")
                    return
                exchange_id = exchange_id_row[0]

                for info in ticker_infos:
                    cursor.execute(
                        """
                        INSERT INTO coins_exchanges (exchange_id, coin_symbol, display_name, net_type, deposit_yn, withdraw_yn) 
                        VALUES (%s, %s, %s, %s, %s, %s) 
                        ON CONFLICT (exchange_id, coin_symbol) DO 
                        UPDATE SET 
                        display_name = EXCLUDED.display_name, 
                        net_type = EXCLUDED.net_type, 
                        deposit_yn = EXCLUDED.deposit_yn, 
                        withdraw_yn = EXCLUDED.withdraw_yn
                        """,
                        (
                            exchange_id,
                            info.get('ticker'),
                            info.get('display_name'),
                            info.get('net_type', info.get('chain', None)),
                            bool(info.get('deposit_yn', 0)),
                            bool(info.get('withdraw_yn', 0))
                        )
                    )

                # ticker_infos에 없는 티커는 삭제
                current_tickers = {info.get('ticker') for info in ticker_infos}
                cursor.execute("SELECT coin_symbol FROM coins_exchanges WHERE exchange_id = %s", (exchange_id,))
                existing_tickers = {row[0] for row in cursor.fetchall()}
                tickers_to_delete = existing_tickers - current_tickers
                if tickers_to_delete:
                    cursor.execute(
                        "DELETE FROM coins_exchanges WHERE exchange_id = %s AND coin_symbol = ANY(%s)",
                        (exchange_id, list(tickers_to_delete))
                    )
                    logger.info(f"Deleted {len(tickers_to_delete)} obsolete tickers for {exchange_name}: {list(tickers_to_delete)}")

        tasks = [process_exchange(name, obj) for name, obj in self.exchanges.items()]
        await asyncio.gather(*tasks)

    def get_users_with_both_exchanges_running_autotrading(self, korean_ex, foreign_ex):
        """
        두 거래소 모두 연결되어 있고, 활성화된 전략(is_active=true)을 가진 유저와 전략 정보를 반환합니다.
        반환값: [{user_id, email, strategy_id, strategy_name, ...}]
        """
        with self._get_db_cursor() as cursor:
            query = """
                SELECT u.id, 
                    u.active_strategy_id,
                    u.email, 
                    u.total_entry_count,
                    u.total_order_amount,
                    u.telegram_chat_id, 
                    u.telegram_username,
                    u.telegram_notifications_enabled,
                    s.name AS strategy_name, 
                    s.is_active, 
                    s.seed_amount,
                    s.coin_mode, 
                    s.trade_mode,
                    s.selected_coins, 
                    s.entry_rate, 
                    s.exit_rate, 
                    s.seed_division,
                    s.allow_average_down, 
                    s.allow_average_up, 
                    s.ai_mode,
                    s.leverage,
                    s.entry_count
                FROM users u
                JOIN user_exchanges ue1 ON u.id = ue1.user_id
                JOIN exchanges ex1 ON ue1.exchange_id = ex1.id
                JOIN user_exchanges ue2 ON u.id = ue2.user_id
                JOIN exchanges ex2 ON ue2.exchange_id = ex2.id
                JOIN strategies s ON u.active_strategy_id = s.id
                WHERE ex1.eng_name = %s 
                AND ex2.eng_name = %s
                AND s.is_active = TRUE
            """
            cursor.execute(query, (korean_ex, foreign_ex))
            rows = cursor.fetchall()
            if cursor.description is not None:
                colnames = [desc[0] for desc in cursor.description]
                return [dict(zip(colnames, row)) for row in rows]
            return []
        
    def get_user_positions_for_settlement(self, user_id, coin_symbol):
        """
        마지막 OPEN 포지션부터 마지막 포지션까지 모두 조회하여
        profit, profitRate, 평균진입환율(피라미딩)을 계산합니다.
        실제 positions 테이블 구조 반영 (size 대신 kr_volume, fr_volume, kr_funds, fr_funds 등 사용)
        """
        try:
            with self._get_db_cursor() as cursor:
                # 마지막 CLOSED 포지션의 entry_time 찾기
                cursor.execute(
                    """
                    SELECT entry_time 
                    FROM positions
                    WHERE user_id = %s 
                    AND coin_symbol = %s 
                    AND status = 'CLOSED'
                    ORDER BY entry_time DESC 
                    LIMIT 1
                    """, (user_id, coin_symbol)
                )
                closed_row = cursor.fetchone()
                if closed_row:
                    closed_entry_time = closed_row[0]
                    # 해당 entry_time 이후의 OPEN 포지션 조회
                    cursor.execute(
                        """
                        SELECT entry_rate, 
                            kr_volume, 
                            kr_funds, 
                            fr_funds, 
                            kr_fee, 
                            fr_fee
                        FROM positions
                        WHERE user_id = %s 
                        AND coin_symbol = %s 
                        AND entry_time > %s 
                        AND status = 'OPEN'
                        ORDER BY entry_time ASC
                        """, (user_id, coin_symbol, closed_entry_time)
                    )
                else:
                    # CLOSED 포지션이 없으면 모든 OPEN 포지션 조회
                    cursor.execute(
                        """
                        SELECT entry_rate, 
                            kr_volume, 
                            kr_funds, 
                            fr_funds, 
                            kr_fee, 
                            fr_fee
                        FROM positions
                        WHERE user_id = %s 
                        AND coin_symbol = %s 
                        AND status = 'OPEN'
                        ORDER BY entry_time ASC
                        """, (user_id, coin_symbol)
                    )
                rows = cursor.fetchall()
                if not rows:
                    return None

                total_kr_volume = 0
                weighted_entry_sum = 0
                total_kr_funds = 0
                total_fr_funds = 0
                total_kr_fee = 0 
                total_fr_fee = 0

                for entry_rate, kr_volume, kr_funds, fr_funds, kr_fee, fr_fee in rows:
                    weighted_entry_sum += float(entry_rate) * float(kr_volume)
                    total_kr_volume += float(kr_volume)
                    total_kr_funds += float(kr_funds)
                    total_fr_funds += float(fr_funds)
                    total_kr_fee += float(kr_fee)
                    total_fr_fee += float(fr_fee)

                avg_entry_rate = weighted_entry_sum / total_kr_volume if total_kr_volume > 0 else 0
                avg_kr_price = total_kr_funds / total_kr_volume if total_kr_volume > 0 else 0
                avg_fr_price = total_fr_funds / total_kr_volume if total_kr_volume > 0 else 0

                return {
                    "avg_entry_rate": avg_entry_rate,
                    "avg_kr_price": avg_kr_price,
                    "avg_fr_price": avg_fr_price,
                    "total_kr_volume": total_kr_volume,
                    "total_kr_funds": total_kr_funds,
                    "total_fr_funds": total_fr_funds,
                    "total_kr_fee": total_kr_fee,
                    "total_fr_fee": total_fr_fee,
                    "positions_count": len(rows)
                }
        except Exception as e:
            logger.error(f"정산용 포지션 집계 중 에러: {e}")
            return None
       
    def insert_positions(self, user_id: int, **kwargs):
        """
        positions 테이블에 새로운 포지션을 삽입합니다.
        """
        try:
            # numeric(18,8) 필드 목록
            numeric_fields = [
                'entry_rate', 
                'exit_rate', 
                'kr_price', 
                'kr_volume', 
                'kr_funds', 
                'kr_fee',
                'fr_price', 
                'fr_original_price',
                'fr_volume', 
                'fr_funds', 
                'fr_fee', 
                'profit', 
                'profit_rate',
                'fr_slippage'
            ]
            field_scales = {
                'entry_rate': 2,
                'exit_rate': 2,
                'kr_price': 8,
                'kr_volume': 8,
                'kr_funds': 8,
                'kr_fee': 8,
                'fr_price': 8,
                'fr_original_price': 8,
                'fr_volume': 8,
                'fr_funds': 8,
                'fr_fee': 8,
                'profit': 2,
                'profit_rate': 2,
                'fr_slippage': 4
            }
            for key in numeric_fields:
                if key in kwargs:
                    kwargs[key] = str(safe_numeric(kwargs[key], scale=field_scales.get(key, 8)))

            with self._get_db_cursor() as cursor:
                columns = ', '.join(kwargs.keys())
                placeholders = ', '.join(['%s'] * len(kwargs))
                values = list(kwargs.values())
                values.insert(0, user_id)  # user_id를 맨 앞에 추가

                query = f"INSERT INTO positions (user_id, {columns}) VALUES (%s, {placeholders})"
                cursor.execute(query, values)
        except Exception as e:
            logger.error(f"DB에 positions 삽입 중 에러: {e}")
            print(e)
            
    def update_strategies(self, user_id: int, **kwargs):
        """
        유저의 strategies의 entry_count 값을 DB에 업데이트합니다.
        """
        try:
            with self._get_db_cursor() as cursor:
                for key, value in kwargs.items():
                    cursor.execute(
                        f"UPDATE strategies SET {key} = %s WHERE id = (SELECT active_strategy_id FROM users WHERE id = %s)",
                        (value, user_id)
                    )
        except Exception as e:
            logger.error(f"DB에서 strategies.entry_count 업데이트 중 에러: {e}")
            
    def update_users(self, user_id: int, **kwargs):
        """
        유저의 users 정보를 업데이트합니다.
        """
        try:
            with self._get_db_cursor() as cursor:
                for key, value in kwargs.items():
                    cursor.execute(
                        f"UPDATE users SET {key} = %s WHERE id = %s",
                        (value, user_id)
                    )
        except Exception as e:
            logger.error(f"DB에서 users 업데이트 중 에러: {e}")

    def get_common_tickers_from_db(self) -> list[tuple]:
        """
        db에서 공통 진입가능 티커를 반환합니다.
        """
        try:
            with self._get_db_cursor() as cursor:
                query = """
                    select T1.eng_name, T2.eng_name, T1.coin_symbol
                    from
                    (
                        select KoreanEx.eng_name, KoreanCoin.coin_symbol
                        from exchanges KoreanEx, coins_exchanges KoreanCoin
                        where koreanEx.type = 'KR'
                        and koreanEx.id = KoreanCoin.exchange_id
                        and KoreanCoin.deposit_yn = true
                        and KoreanCoin.withdraw_yn = true
                    ) T1,
                    (
                        select ForeignEx.eng_name, ForeignCoin.coin_symbol
                        from exchanges ForeignEx, coins_exchanges ForeignCoin
                        where ForeignEx.type = 'Overseas'
                        and ForeignEx.id = ForeignCoin.exchange_id
                        and ForeignCoin.deposit_yn = true
                        and ForeignCoin.withdraw_yn = true
                    ) T2
                    where T1.coin_symbol = T2.coin_symbol
                """
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB 에러: {e}")
            return []

    @staticmethod
    async def calc_exrate(ticker: str, seed: float):
        """
        upbit에서 seed(KRW)만큼의 특정 티커를 매수할 때, 매수가능수량을 계산하여
        해당 수량과 똑같은 수량을 bybit에서 매도할 때, upbit과 bybit의 환율을 계산합니다.
        """

        res = await asyncio.gather(
            UpbitExchange.get_ticker_orderbook([ticker]),
            BybitExchange.get_ticker_orderbook(ticker)
        )

        upbit_orderbook, bybit_orderbook = res

        # 업비트 주문가능수량 구하기
        remaining_seed = seed
        upbit_available_size = 0
        for unit in upbit_orderbook[0]["orderbook"]:
            ob_quote_volume = unit["ask_price"] * unit["ask_size"]
            if remaining_seed >= ob_quote_volume:
                upbit_available_size += unit["ask_size"]
                remaining_seed -= ob_quote_volume
            else:
                upbit_available_size += remaining_seed / unit["ask_price"]
                break

        # 바이비트에서 해당 주문가능수량만큼 매도할 때 필요한 금액 구하기
        remaining_size = upbit_available_size
        bybit_quote_volume = 0
        for unit in bybit_orderbook["orderbook"]:
            if remaining_size >= unit["bid_size"]:
                bybit_quote_volume += unit["bid_price"] * unit["bid_size"]
                remaining_size -= unit["bid_size"]
            else:
                bybit_quote_volume += unit["bid_price"] * remaining_size
                break
            
        # 방어 로직
        if upbit_available_size == 0 or bybit_quote_volume == 0:
            raise ValueError("Available size or quote volume is zero, cannot calculate exchange rate.")
        
        # 환율 계산 (Decimal, 소수점 2째자리 반올림)
        from decimal import Decimal, ROUND_HALF_UP
        exchange_rate = Decimal(str(seed)) / Decimal(str(bybit_quote_volume))
        exchange_rate = exchange_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return {
            "ticker": ticker,
            "exchange_rate": float(exchange_rate)
        }
        
    @staticmethod
    async def calc_exrate_batch(tickers: list[tuple[str, str, str]]):
        """
        여러 티커에 대해 여러 시드금액 기준 환율을 일괄 계산합니다.
        tickers: (exchange1, exchange2, coin_symbol) 형식의 튜플 리스트
        """
        def get_exchange_class(name):
            # 예: 'upbit' -> 'UpbitExchange', 'bybit' -> 'BybitExchange'
            class_name = name.lower().capitalize() + 'Exchange'
            return globals().get(class_name)

        if not tickers:
            return []
        
        # 거래소별로 그룹화
        korean_groups = {}  # {exchange_name: [coin_symbols]}
        foreign_requests = []  # [(exchange_class, coin_symbol, original_index)]
        
        for i, (korean_ex, foreign_ex, coin_symbol) in enumerate(tickers):
            # 한국거래소 그룹화
            if korean_ex not in korean_groups:
                korean_groups[korean_ex] = []
            korean_groups[korean_ex].append((coin_symbol, i))
            
            # 해외거래소 요청 준비
            foreign_ex_class = get_exchange_class(foreign_ex)
            if foreign_ex_class is None:
                raise ValueError(f"Unknown foreign exchange: {foreign_ex}")
            foreign_requests.append((foreign_ex_class, coin_symbol, i))
        
        # 한국거래소 배치 요청 준비
        korean_tasks = []
        korean_task_metadata = []  # (korean_ex_name, indices)를 저장
        
        for korean_ex_name, coin_data in korean_groups.items():
            korean_ex_class = get_exchange_class(korean_ex_name)
            if korean_ex_class is None:
                raise ValueError(f"Unknown Korean exchange: {korean_ex_name}")
            
            coin_symbols = [coin_symbol for coin_symbol, _ in coin_data]
            indices = [idx for _, idx in coin_data]
            
            # 한국거래소는 한 번의 요청으로 여러 코인 처리
            korean_tasks.append(korean_ex_class.get_ticker_orderbook(coin_symbols))
            korean_task_metadata.append((korean_ex_name, indices))
        
        # 해외거래소 요청 준비
        foreign_tasks = [
            foreign_ex_class.get_ticker_orderbook(coin_symbol)
            for foreign_ex_class, coin_symbol, _ in foreign_requests
        ]
        
        # 한국거래소와 해외거래소 요청을 동시에 실행
        all_results = await asyncio.gather(*korean_tasks, *foreign_tasks)
        
        # 결과를 한국거래소와 해외거래소로 분리
        korean_batch_results = all_results[:len(korean_tasks)]
        foreign_orderbooks = all_results[len(korean_tasks):]
        
        # 한국거래소 결과 매핑
        korean_results = {}  # {original_index: orderbook}
        for batch_result, (korean_ex_name, indices) in zip(korean_batch_results, korean_task_metadata):
            for orderbook, original_idx in zip(batch_result, indices):
                korean_results[original_idx] = orderbook
        
        # 해외거래소 결과 매핑
        foreign_results = {}
        for (foreign_ex_class, coin_symbol, original_idx), orderbook in zip(foreign_requests, foreign_orderbooks):
            foreign_results[original_idx] = orderbook
        
        # 환율 계산
        results = []
        seeds = [i for i in range(1000000, 100_000_001, 1000000)] # KRW
        
        for i, (korean_ex, foreign_ex, coin_symbol) in enumerate(tickers):
            ob1 = korean_results[i]
            ob2 = foreign_results[i]

            ex_rates = []
            for seed in seeds:
                available_size = 0
                remaining_seed = seed
                for unit in ob1["orderbook"]:
                    ob_quote_volume = unit["bid_price"] * unit["bid_size"]
                    if remaining_seed >= ob_quote_volume:
                        available_size += unit["bid_size"]
                        remaining_seed -= ob_quote_volume
                    else:
                        available_size += remaining_seed / unit["bid_price"]
                        break
                
                remaining_size = available_size
                quote_volume = 0
                for unit in ob2["orderbook"]:
                    if remaining_size >= unit["ask_size"]:
                        quote_volume += unit["ask_price"] * unit["ask_size"]
                        remaining_size -= unit["ask_size"]
                    else:
                        quote_volume += unit["ask_price"] * remaining_size
                        break
                
                if available_size == 0 or quote_volume == 0:
                    exchange_rate = None
                else:
                    exchange_rate = Decimal(str(seed)) / Decimal(str(quote_volume))
                    exchange_rate = exchange_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    exchange_rate = float(exchange_rate)

                ex_rates.append({
                    'seed': seed,
                    'ex_rate': exchange_rate
                })
                
            results.append({
                "name": ob1["ticker"],
                "korean_ex": korean_ex,
                "foreign_ex": foreign_ex,
                "ex_rates": ex_rates
            })
        
        return results

    @staticmethod
    async def exit_position(korean_ex: KoreanExchange, foreign_ex: ForeignExchange, ticker: str, size: float):
        '''
        한국거래소에서는 매수, 외국거래소에서는 매도 주문을 동시에 실행합니다.
        '''
        return await asyncio.gather(
            korean_ex.order(ticker, 'ask', size),
            foreign_ex.close_position(ticker)
        )
        
exMgr = ExchangeManager()
