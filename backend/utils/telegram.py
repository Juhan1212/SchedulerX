import os
import logging
from dotenv import load_dotenv
from aiogram import Bot
import aiohttp

logger = logging.getLogger(__name__)

load_dotenv()

# Telegram 봇 설정
bot_id = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

if not bot_id or not chat_id:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment variables.")

bot = Bot(token=bot_id)

async def send_telegram(message, message_type='text'):
    if not bot_id or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment variables.")
    
    result = ""   
    try:        
        if message_type == 'text':
            result = await bot.send_message(chat_id=chat_id, text=message)
        elif message_type == 'photo':
            result = await bot.send_photo(chat_id=chat_id, photo=message)
    except aiohttp.ClientError as e:
        logger.error(f"Error occurred while sending telegram : {e}")
    except Exception as e:
        logger.error(f"Error occurred while sending telegram : {e}")
    return result

if __name__ == "__main__":
    # 예시: 텔레그램 메시지 보내기
    import asyncio
    asyncio.run(send_telegram("Hello, this is a test message from the bot!"))
    asyncio.run(bot.session.close())