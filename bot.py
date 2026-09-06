import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, PeerIdInvalid, ChannelInvalid
from config import Config
from database import db

bot = Client(
    "ForwardingBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

user_states = {}

def parse_link(link: str):
    """
    Parses a Telegram link. Returns a dict with chat_id, message_id.
    """
    if "t.me/+" in link or "joinchat" in link:
        return {"error": "Invite links (t.me/+) are NOT allowed. Send a public @username or a direct message link."}
        
    if "t.me/c/" in link:
        # Private chat message link: t.me/c/123456789/100
        parts = link.split("/")
        try:
            chat_id = int("-100" + parts[4])
            msg_id = int(parts[-1])
            return {"chat_id": chat_id, "msg_id": msg_id}
        except:
            return {"error": "Invalid private message link format."}
            
    elif "t.me/" in link:
        # Public chat message link: t.me/username/100
        parts = link.split("/")
        try:
            chat_id = parts[3]
            msg_id = int(parts[-1])
            return {"chat_id": chat_id, "msg_id": msg_id}
        except:
            # Maybe just a username?
            return {"chat_id": parts[3], "msg_id": None}
            
    return {"error": "Unrecognized link format."}

@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    if await db.is_user_authorized(message.from_user.id):
        await message.reply_text("Hello! I am ready to forward messages.\nUse /forward to start.")
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Request Access", callback_data=f"request_access_{message.from_user.id}")]
        ])
        await message.reply_text("You are not authorized to use this bot.", reply_markup=keyboard)

@bot.on_callback_query(filters.regex(r"^request_access_"))
async def request_access(client, callback_query):
    user_id = int(callback_query.data.split("_")[2])
    user_mention = callback_query.from_user.mention
    
    await callback_query.answer("Request sent to admin!", show_alert=True)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Approve", callback_data=f"approve_{user_id}"),
         InlineKeyboardButton("Reject", callback_data=f"reject_{user_id}")]
    ])
    await client.send_message(Config.ADMIN_ID, f"User {user_mention} (ID: `{user_id}`) requested access.", reply_markup=keyboard)

@bot.on_callback_query(filters.regex(r"^approve_"))
async def approve_user(client, callback_query):
    if callback_query.from_user.id != Config.ADMIN_ID:
        return await callback_query.answer("Not allowed", show_alert=True)
    
    user_id = int(callback_query.data.split("_")[1])
    await db.add_user(user_id)
    await callback_query.edit_message_text(f"User `{user_id}` approved.")
    await client.send_message(user_id, "Your access request has been approved! Use /forward to start.")

@bot.on_callback_query(filters.regex(r"^reject_"))
async def reject_user(client, callback_query):
    if callback_query.from_user.id != Config.ADMIN_ID:
        return await callback_query.answer("Not allowed", show_alert=True)
    
    user_id = int(callback_query.data.split("_")[1])
    await callback_query.edit_message_text(f"User `{user_id}` rejected.")
    await client.send_message(user_id, "Your access request was rejected.")

@bot.on_message(filters.command("revoke") & filters.user(Config.ADMIN_ID))
async def revoke_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /revoke user_id")
    user_id = int(message.command[1])
    await db.remove_user(user_id)
    await message.reply_text(f"Access revoked for `{user_id}`.")

@bot.on_message(filters.command("forward") & filters.private)
async def forward_cmd(client, message):
    if not await db.is_user_authorized(message.from_user.id):
        return await message.reply_text("You are not authorized.")
    
    user_states[message.from_user.id] = {"step": "dest_links"}
    msg = (
        "**STEP 1: Destination Chat(s)**\n\n"
        "Bhejein us group ya channel ka link jahan messages forward karne hain.\n\n"
        "⚠️ **IMPORTANT:**\n"
        "1. Bot wahan **ADMIN** hona chahiye.\n"
        "2. **Invite links (t.me/+) KAAM NAHI KARENGE.**\n"
        "3. Private chat ke liye us chat ke kisi bhi **MESSAGE KA LINK** bhejein (jaise: `https://t.me/c/123456789/5`).\n"
        "4. Public chat ke liye direct link bhejein (jaise: `https://t.me/movies`).\n\n"
        "Agar multiple jagah bhejna hai toh space dekar links dalein."
    )
    await message.reply_text(msg)

@bot.on_message(filters.private & ~filters.command("start") & ~filters.command("revoke") & ~filters.command("forward"))
async def handle_states(client, message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    
    if state["step"] == "dest_links":
        links = message.text.split()
        dests = []
        for link in links:
            parsed = parse_link(link)
            if "error" in parsed:
                return await message.reply_text(f"Error in link `{link}`: {parsed['error']}\n\nTry /forward again.")
            dests.append(parsed["chat_id"])
            
        state["dest_chats"] = dests
        state["step"] = "start_msg"
        
        msg = (
            "**STEP 2: First Message Link**\n\n"
            "Ab uss **pehle message ka link** bhejein jahan se forwarding shuru karni hai.\n"
            "Example: `https://t.me/c/2985458258/1122`"
        )
        await message.reply_text(msg)
        
    elif state["step"] == "start_msg":
        parsed = parse_link(message.text)
        if "error" in parsed:
            return await message.reply_text(parsed["error"])
        if not parsed["msg_id"]:
            return await message.reply_text("You must send a MESSAGE link, not just a chat link. It should have a number at the end.")
            
        state["source_chat"] = parsed["chat_id"]
        state["start_id"] = parsed["msg_id"]
        state["step"] = "end_msg"
        
        msg = (
            "**STEP 3: Last Message Link**\n\n"
            "Ab uss **aakhiri message ka link** bhejein jahan tak forward karna hai.\n"
            "Agar sirf wahi ek message bhejna hai, toh dobara wahi same link bhej dein."
        )
        await message.reply_text(msg)
        
    elif state["step"] == "end_msg":
        parsed = parse_link(message.text)
        if "error" in parsed:
            return await message.reply_text(parsed["error"])
        if not parsed["msg_id"]:
            return await message.reply_text("You must send a MESSAGE link. Try again.")
            
        if parsed["chat_id"] != state["source_chat"]:
            return await message.reply_text("The end message must be from the same chat as the start message! Try again.")
            
        state["end_id"] = parsed["msg_id"]
        await message.reply_text("⏳ Starting to forward... Please wait. I will notify you when it's done or if an error occurs.")
        
        # Start background task
        asyncio.create_task(process_forward(client, user_id, state))
        del user_states[user_id]

async def process_forward(client, user_id, state):
    source = state["source_chat"]
    dests = state["dest_chats"]
    start_id = state.get("start_id")
    end_id = state.get("end_id")
    
    success_count = 0
    fail_count = 0
    
    # Ensure start_id is smaller than end_id
    if start_id > end_id:
        start_id, end_id = end_id, start_id
        
    for msg_id in range(start_id, end_id + 1):
        try:
            msg = await client.get_messages(source, msg_id)
            if msg.empty:
                fail_count += 1
                continue
                
            for dest in dests:
                try:
                    fwd_msg = await msg.copy(dest)
                    success_count += 1
                    if msg.pinned_message:
                        try:
                            await fwd_msg.pin()
                        except:
                            pass
                except FloodWait as e:
                    await asyncio.sleep(e.value + 1)
                    await msg.copy(dest)
                    success_count += 1
                except Exception as e:
                    print(f"Failed to copy to {dest}: {e}")
                    fail_count += 1
                    
            await asyncio.sleep(2) # Prevent flood waits
            
        except Exception as e:
            error_msg = str(e)
            if "PEER_ID_INVALID" in error_msg or "CHANNEL_INVALID" in error_msg:
                await client.send_message(user_id, f"❌ ERROR: Bot cannot access the chat `{source}`. Make sure it is public OR the bot is an admin there.")
                return
            print(f"Error fetching message {msg_id}: {e}")
            fail_count += 1
            
    await client.send_message(user_id, f"✅ **Forwarding Completed!**\n\nSuccessful: {success_count}\nFailed/Skipped: {fail_count}")
