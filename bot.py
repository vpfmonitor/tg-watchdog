import time
import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiohttp import web

# ====== НАЛАШТУВАННЯ ======
BOT_TOKEN = os.getenv("BOT_TOKEN")

CHAT_ID_SOURCE = -1003673154910
CHAT_ID_ALERT = -5282615788  

TIMEOUT_SECONDS = 60
CHECK_INTERVAL = 20
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

last_message_time = time.time()


@dp.message()
async def handle_messages(message: Message):
    global last_message_time
    if message.chat.id == CHAT_ID_SOURCE:
        last_message_time = time.time()


async def watchdog():
    global last_message_time
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        if time.time() - last_message_time > TIMEOUT_SECONDS:
            try:
                await bot.send_message(
                    CHAT_ID_ALERT,
                    "⚠️ Протягом 10 хвилин не було повідомлень"
                )
            except Exception as e:
                print("Failed to send alert:", e)

            last_message_time = time.time()


async def health(request):
    return web.Response(text="OK")


async def start_webserver(port: int):
    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    port = int(os.getenv("PORT", 8080))
    await start_webserver(port)
    asyncio.create_task(watchdog())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

