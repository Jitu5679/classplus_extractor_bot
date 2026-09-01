import asyncio
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import Message

# Render Port Binding
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Live!")

def run_port():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleServer)
    server.serve_forever()

threading.Thread(target=run_port, daemon=True).start()

# Event Loop Fix for Python 3.12+
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Telegram Bot Client Setup
api_id = int(os.environ.get("API_ID", 21567814))
api_hash = os.environ.get("API_HASH", "cd7dc5431d449fd795683c550d7bfb7e")
bot_token = os.environ.get("BOT_TOKEN", "8078418472:AAHN8O2dz1uLZX2D9g3URDT1ic6W7IX0Fb4")

bot = Client(
    "classplus_bot",
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)

@bot.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    await message.reply_text("👋 Welcome to Classplus Extractor Bot!")

bot.run()
