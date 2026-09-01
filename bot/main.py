import os
import re
import asyncio
import aiohttp
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Render Web Port Binding Server
class SimpleServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Live & Active!")

def run_port():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleServer)
    server.serve_forever()

threading.Thread(target=run_port, daemon=True).start()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "region": "IN",
    "api-version": "3"
}

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Concept RNA (OTP Download) 📱", callback_data="cp_otp_mode")],
        [InlineKeyboardButton("🔑 Direct Token Download 🔑", callback_data="cp_token_mode")]
    ])
    await message.reply_text(
        f"👋 **Namaste {message.from_user.first_name}!**\n\nNeeche option select karein:",
        reply_markup=markup
    )

@bot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    chat_id = query.message.chat.id
    if query.data == "cp_otp_mode":
        user_states[chat_id] = {"step": "ASK_PHONE", "org_code": "nbhom", "course_id": "756679"}
        await query.message.reply_text(
            "📱 **Apna 10-digit Mobile Number bhejein** (Example: `9876543210`):"
        )
        await query.answer()
    elif query.data == "cp_token_mode":
        user_states[chat_id] = {"step": "ASK_TOKEN", "course_id": "756679"}
        await query.message.reply_text(
            "🔑 **Apna Access Token / Bearer Token paste karein:**"
        )
        await query.answer()

@bot.on_message(filters.text & filters.private)
async def text_handler(client: Client, message: Message):
    chat_id = message.chat.id
    text = message.text.strip()
    state = user_states.get(chat_id, {})
    step = state.get("step")

    # Flow 1: Phone number se OTP bhejna
    if step == "ASK_PHONE":
        phone = text.replace("+91", "").replace(" ", "").replace("-", "")
        if not re.match(r'^\d{10}$', phone):
            await message.reply_text("❌ Kripya 10 digit ka valid Indian mobile number bhejein.")
            return

        state["phone"] = phone
        state["step"] = "WAITING_OTP"
        status_msg = await message.reply_text("⏳ Concept RNA Org details verify karke OTP bhej rahe hain...")

        async with aiohttp.ClientSession() as session:
            try:
                # 1. Resolve exact numeric Org ID
                org_url = f"https://api.classplusapp.com/v2/orgs/details?orgCode={state['org_code']}"
                org_id = None
                async with session.get(org_url, headers=BASE_HEADERS, timeout=12) as o_res:
                    if o_res.status == 200:
                        o_data = await o_res.json(content_type=None)
                        org_id = o_data.get("data", {}).get("orgId")
                
                if not org_id:
                    org_id = 11119  # Concept RNA standard org id fallback
                
                state["org_id"] = org_id

                # 2. Generate OTP
                otp_url = "https://api.classplusapp.com/v2/otp/generate"
                payload = {
                    "mobile": phone,
                    "countryExt": "91",
                    "orgCode": state["org_code"],
                    "orgId": int(org_id),
                    "viaSms": 1,
                    "fingerprintId": "tele-web-session"
                }

                async with session.post(otp_url, json=payload, headers=BASE_HEADERS, timeout=15) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status == 200 and (data.get("status") == "success" or data.get("success") is True):
                        state["session_id"] = data.get("data", {}).get("sessionId")
                        await status_msg.edit_text(f"✅ **OTP bhej diya gaya hai number {phone} par!**\n\n🔢 **OTP yahan bhejein:**")
                    else:
                        msg = data.get("message") or str(data)
                        await status_msg.edit_text(f"❌ OTP Error: {msg}\n\n💡 *Tip: Agar OTP block ho, to aap 'Direct Token Download' button use kar sakte hain.*")
            except Exception as e:
                await status_msg.edit_text(f"❌ Connection Error: {e}")

    # Flow 2: OTP Verify and Course Download
    elif step == "WAITING_OTP":
        otp = text
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
            "orgId": int(org_id),
            "fingerprintId": "tele-web-session"
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=BASE_HEADERS, timeout=15) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status != 200 or not (data.get("status") == "success" or data.get("success") is True):
                        msg = data.get("message", "Galat OTP ya expired session.")
                        await status_msg.edit_text(f"❌ Error: {msg}")
                        return

                    token = data.get("data", {}).get("token")
            except Exception as e:
                await status_msg.edit_text(f"❌ Login error: {e}")
                return

            await extract_course_content(client, chat_id, status_msg, token, course_id)

    # Flow 3: Direct Token Input
    elif step == "ASK_TOKEN":
        token = text.replace("Bearer ", "").strip()
        course_id = state.get("course_id", "756679")
        status_msg = await message.reply_text("⏳ Token verify karke course scan shuru kiya ja raha hai...")
        await extract_course_content(client, chat_id, status_msg, token, course_id)

async def extract_course_content(client: Client, chat_id: int, status_msg: Message, token: str, course_id: str):
    await status_msg.edit_text("🔍 **Course Scanning in Progress...**\nFolders aur lectures scan ho rahe hain...")

    auth_headers = {
        "x-access-token": token,
        "User-Agent": "Mobile-Android",
        "accept": "application/json",
        "region": "IN",
        "api-version": "2"
    }

    extracted_items = []
    queue = [(0, "Root")]
    visited = set()

    async with aiohttp.ClientSession() as session:
        while queue:
            current_folder_id, path = queue.pop(0)
            if current_folder_id in visited:
                continue
            visited.add(current_folder_id)

            content_url = f"https://api.classplusapp.com/v2/course/content/get?courseId={course_id}&folderId={current_folder_id}"
            try:
                async with session.get(content_url, headers=auth_headers, timeout=15) as c_resp:
                    if c_resp.status == 200:
                        c_data = await c_resp.json(content_type=None)
                        contents = c_data.get("data", {}).get("courseContent", [])
                        for item in contents:
                            item_type = item.get("contentType")
                            item_name = item.get("name", "Untitled")

                            if item_type == 1:  # Folder
                                sub_id = item.get("id")
                                queue.append((sub_id, f"{path} > {item_name}"))
                            elif item_type == 2:  # Video
                                v_url = item.get("url") or item.get("streamUrl") or item.get("videoUrl", "")
                                extracted_items.append(f"📹 [{path}] {item_name} : {v_url}")
                            elif item_type == 3:  # PDF / Doc
                                d_url = item.get("url") or item.get("documentUrl", "")
                                extracted_items.append(f"📄 [{path}] {item_name} : {d_url}")
            except Exception as err:
                logger.error(f"Folder fetch error: {err}")

    if not extracted_items:
        await status_msg.edit_text("❌ Course access nahi ho paya ya course content blank hai. Token verify karein.")
        return

    file_path = f"downloads/ConceptRNA_Course_{course_id}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"=== CONCEPT RNA EXTRACTED COURSE ({course_id}) ===\n")
        f.write(f"Total Files Found: {len(extracted_items)}\n\n")
        for line in extracted_items:
            f.write(line + "\n")

    await status_msg.edit_text(f"🎉 **Extraction Complete!** Total **{len(extracted_items)}** files mil gayi hain.")
    await client.send_document(
        chat_id,
        file_path,
        caption=f"📚 **Concept RNA Course ID:** `{course_id}`\n📦 **Total Content:** {len(extracted_items)} items"
    )

if __name__ == "__main__":
    bot.run()
    
