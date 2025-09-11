import asyncio
from decimal import ROUND_DOWN, Decimal
import logging
from typing import List
from backend.core.ex_manager import exMgr
from backend.exchanges.base import ForeignExchange, KoreanExchange


logger = logging.getLogger(__name__)

class TradingService:
    def __init__(self, korean_ex_str: str, foreign_ex_str: str, usdt_price: float):
        self.korean_ex_str = korean_ex_str
        self.foreign_ex_str = foreign_ex_str
        self.usdt_price = usdt_price
        self.korean_ex: KoreanExchange = exMgr.exchanges.get(korean_ex_str)
        self.foreign_ex: ForeignExchange = exMgr.exchanges.get(foreign_ex_str)

    async def check_and_handle_positions(self, item: dict, user: dict):
        positionsDB = exMgr.get_user_open_position(user['id'], item['name'])
        if positionsDB:
            await self._handle_existing_position(item, user, positionsDB)
        else:
            await self._handle_new_position(item, user)

    async def _handle_existing_position(self, item: dict, user: dict, positionsDB: list):
        position_real = await self.foreign_ex.get_position_info(item['name'])
        position = [p for p in position_real.get('list', []) if float(p.get('size', 0)) > 0]

        if not position:
            logger.info(f"User: {user['id']}, Exchange: {self.foreign_ex_str}, Ticker: {item['name']}. Karbit order exists but no actual position.")
            # Handle discrepancy, maybe delete DB position
            return

        exit_position_flag = self._should_exit_position(item, user, positionsDB)
        if exit_position_flag:
            await self._exit_position(item, user, position[0], positionsDB)

    def _should_exit_position(self, item: dict, user: dict, positionsDB: list) -> bool:
        current_ex_rate = self._get_current_ex_rate(item, user['seed_amount'])
        if not current_ex_rate:
            return False

        coin_mode = user['coin_mode']
        exit_rate = user['exit_rate']
        entry_rate = positionsDB[0].get('entry_rate')

        if coin_mode == 'custom':
            return current_ex_rate >= float(exit_rate)
        else: # auto mode
            return current_ex_rate >= float(entry_rate) * 1.01

    async def _exit_position(self, item: dict, user: dict, position: dict, positionsDB: list):
        exit_results = await exMgr.exit_position(self.korean_ex, self.foreign_ex, item['name'], position['size'])
        fr_exit_result, kr_exit_result = exit_results

        fr_order_id = fr_exit_result.get('result', {}).get('orderId')
        kr_order_id = kr_exit_result.get('uuid')

        if not fr_order_id or not kr_order_id:
            logger.error("Failed to create exit orders.")
            return

        fr_order_details, kr_order_details = await asyncio.gather(
            self.foreign_ex.get_orders(item['name'], fr_order_id),
            self.korean_ex.get_orders(item['name'], kr_order_id)
        )

        exit_rate_actual = self._calculate_actual_exit_rate(fr_order_details, kr_order_details)

        logger.info(f"User: {user['id']}, Ticker: {item['name']}, Exit Rate: {exit_rate_actual}")
        
        exMgr.delete_position(positionsDB[0]['id'])
        exMgr.update_entry_count(user['id'], -1)
        exMgr.update_total_entry_count(user['id'], 1)
        exMgr.update_total_order_amount(user['id'], positionsDB[0]['margin'])


    def _calculate_actual_exit_rate(self, fr_order_details: list, kr_order_details: list) -> Decimal:
        fr_price = Decimal(str(fr_order_details[0].get('price', 0)))
        fr_qty = Decimal(str(fr_order_details[0].get('qty', 0)))
        fr_exit_usdt = (fr_price * fr_qty).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

        kr_exit_krw = Decimal(str(kr_order_details[0].get('executed_funds', 0)))

        return (kr_exit_krw / fr_exit_usdt).quantize(Decimal('0.01'), rounding=ROUND_DOWN) if fr_exit_usdt else Decimal(0)

    async def _handle_new_position(self, item: dict, user: dict):
        entry_position_flag = self._should_enter_position(item, user)
        if not entry_position_flag:
            return

        balance = await self.foreign_ex.get_available_balance()
        if balance < round(float(user['seed_amount']) / self.usdt_price, 2):
            logger.info(f"User: {user['id']}, Insufficient balance.")
            return

        if user['seed_division'] <= user['entry_count']:
            logger.info(f"User: {user['id']}, Entry count exceeded.")
            return

        await self._enter_position(item, user)

    def _should_enter_position(self, item: dict, user: dict) -> bool:
        current_ex_rate = self._get_current_ex_rate(item, user['seed_amount'])
        if not current_ex_rate:
            return False

        coin_mode = user['coin_mode']
        entry_rate = user['entry_rate']

        if coin_mode == 'custom':
            if current_ex_rate <= float(entry_rate):
                return True
        else: # auto mode
            if current_ex_rate <= float(self.usdt_price) * 0.99:
                return True
        return False

    def _get_current_ex_rate(self, item: dict, seed: int) -> float | None:
        ex_rate_info = next((rate for rate in item.get('ex_rates', []) if rate.get('seed') == seed), None)
        if not ex_rate_info:
            logger.debug(f"No matching ex_rate found for seed {seed} in item {item['name']}.")
            return None
        return ex_rate_info['ex_rate']

    async def _enter_position(self, item: dict, user: dict):
        order_amount = int(user['seed_amount'] / user['seed_division'])
        kr_order = await self.korean_ex.order(item['name'], 'bid', order_amount)
        kr_order_id = kr_order.get('uuid')

        if not kr_order_id:
            logger.error(f"User: {user['id']}, Korean exchange order failed.")
            return

        kr_order_result = await self.korean_ex.get_orders(item['name'], kr_order_id)
        kr_order_volume = kr_order_result[0].get('executed_volume')
        kr_order_funds = kr_order_result[0].get('executed_funds')

        if not kr_order_volume or not kr_order_funds:
            logger.error(f"User: {user['id']}, Could not find volume in Korean exchange order result.")
            return

        lot_size = await self.foreign_ex.get_lot_size(item['name'])
        if lot_size is None:
            logger.error(f"User: {user['id']}, Failed to get lot size from foreign exchange.")
            return
            
        rounded_volume = (float(kr_order_volume) // lot_size) * lot_size
        if rounded_volume <= 0:
            logger.error(f"User: {user['id']}, Volume is less than minimum order quantity.")
            return

        await self.foreign_ex.set_leverage(user['leverage'])
        fr_order = await self.foreign_ex.order(item['name'], 'ask', rounded_volume)
        fr_order_id = fr_order.get('result', {}).get('orderId')

        if not fr_order_id:
            logger.error(f"User: {user['id']}, Foreign exchange order failed.")
            return
            
        # ... (logging and DB updates)
