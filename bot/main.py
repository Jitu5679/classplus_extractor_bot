import os
import re
import asyncio
import aiohttp
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Render Web Port Binding
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Live & Running!")

def run_port():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleServer)
    server.serve_forever()

threading.Thread(target=run_port, daemon=True).start()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_ID = int(os.environ.get("API_ID", "21567814"))
API_HASH = os.environ.get("API_HASH", "cd7dc5431d449fd795683c550d7bfb7e")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8078418472:AAHN8O2dz1uLZX2D9g3URDT1ic6W7IX0Fb4")

os.makedirs("downloads", exist_ok=True)

bot = Client(
    "classplus_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_states = {}

COMMON_HEADERS = {
    "User-Agent": "Mobile-Android",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "region": "IN",
    "api-version": "2"
}

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Concept RNA (Direct OTP Download) 📱", callback_data="cp_otp_mode")]
    ])
    await message.reply_text(
        f"👋 **Namaste {message.from_user.first_name}!**\n\nNeeche diye gaye button par tap karein:",
        reply_markup=markup
    )

@bot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.data == "cp_otp_mode":
        user_states[chat_id] = {"step": "ASK_PHONE", "org_code": "nbhom", "course_id": "756679"}
        await query.message.reply_text(
            "📱 **Apna 10-digit Mobile Number bhejein** (jis par Concept RNA account hai):"
        )
        await query.answer()

@bot.on_message(filters.text & filters.private)
async def text_handler(client: Client, message: Message):
    chat_id = message.chat.id
    state = user_states.get(chat_id, {})
    step = state.get("step")

    # Flow 1: Phone number se OTP bhejna
    if step == "ASK_PHONE":
        phone = message.text.strip().replace("+91", "").replace(" ", "")
        if not re.match(r'^\d{10}$', phone):
            await message.reply_text("❌ Kripya 10 digit ka valid mobile number bhejein.")
            return

        state["phone"] = phone
        state["step"] = "WAITING_OTP"
        status_msg = await message.reply_text("⏳ OTP request process ki ja rahi hai...")

        async with aiohttp.ClientSession() as session:
            try:
                # Step 1: Resolve Org Data dynamically
                org_url = "https://api.classplusapp.com/v2/orgs/details?orgCode=nbhom"
                org_id = 11119
                async with session.get(org_url, headers=COMMON_HEADERS, timeout=10) as o_res:
                    if o_res.status == 200:
                        o_data = await o_res.json(content_type=None)
                        org_id = o_data.get("data", {}).get("orgId", 11119)
                
                state["org_id"] = org_id

                # Step 2: Request OTP
                otp_url = "https://api.classplusapp.com/v2/otp/generate"
                payload = {
                    "mobile": phone,
                    "countryExt": "91",
                    "orgCode": "nbhom",
                    "orgId": org_id,
                    "viaSms": 1
                }

                async with session.post(otp_url, json=payload, headers=COMMON_HEADERS, timeout=15) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status == 200 and (data.get("status") == "success" or data.get("success") is True):
                        state["session_id"] = data.get("data", {}).get("sessionId")
                        await status_msg.edit_text("✅ OTP bhej diya gaya hai!\n\n🔢 **OTP yahan enter karein:**")
                    else:
                        msg = data.get("message", "OTP request fail ho gayi.")
                        await status_msg.edit_text(f"❌ Error: {msg}")
            except Exception as e:
                await status_msg.edit_text(f"❌ Error: {e}")

    # Flow 2: OTP Verify and Extract
    elif step == "WAITING_OTP":
        otp = message.text.strip()
        session_id = state.get("session_id")
        org_id = state.get("org_id", 11119)
        course_id = state.get("course_id", "756679")
        phone = state.get("phone")

        status_msg = await message.reply_text("⏳ OTP verify kiya ja raha hai...")

        url = "https://api.classplusapp.com/v2/users/verify"
        payload = {
            "mobile": phone,
            "otp": otp,
            "sessionId": session_id,
            "countryExt": "91",
            "orgCode": "nbhom",
            "orgId": org_id,
            "fingerprintId": "tele-render-session"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=COMMON_HEADERS, timeout=15) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status != 200 or not (data.get("status") == "success" or data.get("success") is True):
                        msg = data.get("message", "Galat OTP ya verification failed.")
                        await status_msg.edit_text(f"❌ Error: {msg}")
                        return

                    token = data.get("data", {}).get("token")
            except Exception as e:
                await status_msg.edit_text(f"❌ Login error: {e}")
                return

            await status_msg.edit_text("✅ Login successful! Course scanning shuru ho gayi hai...")

            # Extract full course recursively
            auth_headers = {
                "x-access-token": token,
                "User-Agent": "Mobile-Android",
                "accept": "application/json",
                "region": "IN",
                "api-version": "2"
            }

            extracted_items = []
            queue = [(0, "Root")]
            visited_folders = set()

            while queue:
                current_folder_id, path = queue.pop(0)
                if current_folder_id in visited_folders:
                    continue
                visited_folders.add(current_folder_id)

                content_url = f"https://api.classplusapp.com/v2/course/content/get?courseId={course_id}&folderId={current_folder_id}"
                try:
                    async with session.get(content_url, headers=auth_headers, timeout=15) as c_resp:
                        if c_resp.status == 200:
                            c_data = await c_resp.json(content_type=None)
                            contents = c_data.get("data", {}).get("courseContent", [])
                            for item in contents:
                                item_type = item.get("contentType")
                                item_name = item.get("name", "Untitled")

                                if item_type == 1:
                                    sub_id = item.get("id")
                                    queue.append((sub_id, f"{path} > {item_name}"))
                                elif item_type == 2:
                                    v_url = item.get("url") or item.get("streamUrl") or item.get("videoUrl", "")
                                    extracted_items.append(f"📹 {item_name} : {v_url}")
                                elif item_type == 3:
                                    d_url = item.get("url") or item.get("documentUrl", "")
                                    extracted_items.append(f"📄 {item_name} : {d_url}")
                except Exception as err:
                    logging.error(f"Folder fetch error: {err}")

            if not extracted_items:
                await status_msg.edit_text("❌ Course access nahi hua ya folder empty hai.")
                return

            file_path = f"downloads/ConceptRNA_{course_id}.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"--- Concept RNA Batch ({course_id}) ---\n\n")
                for line in extracted_items:
                    f.write(line + "\n")

            await status_msg.edit_text(f"✅ Extraction complete! Total {len(extracted_items)} files mili.")
            await client.send_document(
                chat_id,
                file_path,
                caption=f"📚 **Course ID:** `{course_id}`\n✨ **Total Files:** {len(extracted_items)}"
            )

if __name__ == "__main__":
    bot.run()
