import os
import logging
from dotenv import load_dotenv
from aiogram import Bot
import aiohttp

logger = logging.getLogger(__name__)

load_dotenv()

# Telegram 봇 설정
bot_id = os.getenv('TELEGRAM_BOT_TOKEN')

if not bot_id:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables.")

bot = Bot(token=bot_id)

async def send_telegram(chat_id, message, message_type='text', parse_mode='Markdown'):
    if not bot_id or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment variables.")
    
    result = ""   
    try:        
        if message_type == 'text':
            # 메시지 포맷팅 개선
            formatted_message = format_telegram_message(message)
            result = await bot.send_message(
                chat_id=chat_id, 
                text=formatted_message, 
                parse_mode=parse_mode
            )
        elif message_type == 'photo':
            result = await bot.send_photo(chat_id=chat_id, photo=message)
    except aiohttp.ClientError as e:
        logger.error(f"Error occurred while sending telegram : {e}")
    except Exception as e:
        logger.error(f"Error occurred while sending telegram : {e}")
    return result

async def send_telegram_to_admin(message, message_type='text', parse_mode='Markdown'):
    admin_bot_id = os.getenv('TELEGRAM_ADMIN_BOT_TOKEN')
    admin_chat_id = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
    if not admin_bot_id or not admin_chat_id:
        raise ValueError("TELEGRAM_ADMIN_BOT_TOKEN and TELEGRAM_ADMIN_CHAT_ID must be set in environment variables.")
    
    bot = Bot(token=admin_bot_id)
    
    result = ""
    try:
        if message_type == 'text':
            # 메시지 포맷팅 개선
            formatted_message = format_telegram_message(message)
            result = await bot.send_message(
                chat_id=admin_chat_id, 
                text=formatted_message, 
                parse_mode=parse_mode
            )
        elif message_type == 'photo':
            result = await bot.send_photo(chat_id=admin_chat_id, photo=message)
    except aiohttp.ClientError as e:
        logger.error(f"Error occurred while sending telegram to admin: {e}")
    except Exception as e:
        logger.error(f"Error occurred while sending telegram to admin: {e}")
    return result

def format_telegram_message(message):
    """
    텔레그램 메시지 포맷팅을 개선합니다.
    """
    # 불필요한 공백 제거 및 코드 블록으로 감싸기
    lines = message.strip().split('\n')
    formatted_lines = []
    
    for line in lines:
        # 각 줄의 앞뒤 공백 제거하되 내용은 유지
        cleaned_line = line.strip()
        if cleaned_line:
            formatted_lines.append(cleaned_line)
    
    # 코드 블록으로 감싸서 포맷팅 유지
    if formatted_lines:
        return "```\n" + '\n'.join(formatted_lines) + "\n```"
    return message

if __name__ == "__main__":
    # 예시: 텔레그램 메시지 보내기 (포맷팅 테스트)
    import asyncio
    
    test_message = '''
═══════════════════════
✅ 포지션 진입 성공
═══════════════════════
👤 유저 : test_user
🇰🇷 한국거래소 : UPBIT
📊 한국 체결량 : 10.5
💰 한국 체결금액 : 50000₩
🌍 해외거래소 : BYBIT
📊 해외 체결량 : 10.5
💰 주문 체결금액 : 35.2$
⚡ 레버리지 : 3x
═══════════════════════
📊 주문환율 : 1420.5
💰 테더가격 : 1415.2
═══════════════════════
    '''
    
    # asyncio.run(send_telegram(test_message))
    # asyncio.run(bot.session.close())