import time
import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiohttp import web

# ====== НАЛАШТУВАННЯ ======
# Беремо ENV і прибираємо пробіли
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHAT_ID_SOURCE = os.getenv("CHAT_ID_SOURCE", "").strip()
CHAT_ID_ALERT = os.getenv("CHAT_ID_ALERT", "").strip()

TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60").strip())
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "20").strip())
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", "300").strip())
# =========================
print("BOT_TOKEN:", repr(BOT_TOKEN))
print("CHAT_ID_SOURCE:", repr(CHAT_ID_SOURCE))
print("CHAT_ID_ALERT:", repr(CHAT_ID_ALERT))


# ====== ПЕРЕВІРКИ ENV ======
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not CHAT_ID_SOURCE or not CHAT_ID_ALERT:
    raise RuntimeError(f"CHAT_ID_SOURCE or CHAT_ID_ALERT is not set. "
                       f"SOURCE={CHAT_ID_SOURCE}, ALERT={CHAT_ID_ALERT}")

# Перетворюємо в int
try:
    CHAT_ID_SOURCE = int(CHAT_ID_SOURCE)
    CHAT_ID_ALERT = int(CHAT_ID_ALERT)
except ValueError as e:
    raise RuntimeError(f"CHAT_ID_SOURCE and CHAT_ID_ALERT must be integers. Error: {e}")

# ===========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# час останнього повідомлення
last_message_time = time.time()

# коли востаннє надсилали алерт про тишу
last_alert_time = 0

# стан чату: True = чат активний, False = мовчить
chat_active = True

# ====== Обробник повідомлень ======
@dp.message()
async def handle_messages(message: Message):
    global last_message_time, last_alert_time, chat_active

    if message.chat.id == CHAT_ID_SOURCE:
        last_message_time = time.time()

        # якщо чат був у стані тиші, але з’явилося повідомлення
        if not chat_active:
            try:
                await bot.send_message(
                    CHAT_ID_ALERT,
                    "✅ Повідомлення знову з’явилися в чаті!"
                )
                print("Alert: чат знову активний")
            except Exception as e:
                print("Failed to send alert:", e)

            chat_active = True
            last_alert_time = time.time()

# ====== Watchdog ======
async def watchdog():
    global last_message_time, last_alert_time, chat_active

    while True:
        await asyncio.sleep(CHECK_INTERVAL)

        silence_time = time.time() - last_message_time

        if silence_time > TIMEOUT_SECONDS:
            # перевіряємо cooldown для алерту
            if time.time() - last_alert_time >= ALERT_COOLDOWN:
                try:
                    await bot.send_message(
                        CHAT_ID_ALERT,
                        f"⚠️ В чаті немає повідомлень вже {int(silence_time)} секунд"
                    )
                    print(f"Alert sent: чат мовчить {int(silence_time)} секунд")
                except Exception as e:
                    print("Failed to send alert:", e)

                last_alert_time = time.time()
                chat_active = False

# ====== Healthcheck для Railway ======
async def health(request):
    return web.Response(text="OK")

async def start_webserver(port: int):
    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# ====== Main ======
async def main():
    port = int(os.getenv("PORT", 8080))
    await start_webserver(port)
    asyncio.create_task(watchdog())
    await dp.start_polling(bot, allowed_updates=["message"])

if __name__ == "__main__":
    asyncio.run(main())
