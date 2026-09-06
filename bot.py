import asyncio
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from config import Config
from database import db

bot = Client(
    "ForwardingBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

user_states = {}

def get_chat_and_topic(link: str):
    # Parses t.me/c/chat_id/topic_id/msg_id or t.me/chat_name/msg_id
    if "t.me/c/" in link:
        parts = link.split("/")
        chat_id = int("-100" + parts[4])
        return chat_id
    elif "t.me/" in link:
        parts = link.split("/")
        chat_username = parts[3]
        return chat_username
    return None

def extract_msg_id(link: str):
    try:
        return int(link.split("/")[-1])
    except:
        return None

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
    
    user_states[message.from_user.id] = {"step": "source_link"}
    await message.reply_text("Send me the link to the SOURCE chat (or a message in it).")

@bot.on_message(filters.private & ~filters.command("start") & ~filters.command("revoke") & ~filters.command("forward"))
async def handle_states(client, message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    
    if state["step"] == "source_link":
        state["source_chat"] = get_chat_and_topic(message.text)
        state["step"] = "dest_links"
        await message.reply_text("Send me the DESTINATION chat link(s), separated by space.")
        
    elif state["step"] == "dest_links":
        links = message.text.split()
        dests = []
        for link in links:
            chat = get_chat_and_topic(link)
            if chat:
                dests.append(chat)
        if not dests:
            return await message.reply_text("Invalid links. Try again.")
            
        state["dest_chats"] = dests
        state["step"] = "ask_range"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Specific Range", callback_data="range_yes"),
             InlineKeyboardButton("Cancel", callback_data="range_cancel")]
        ])
        await message.reply_text("Do you want to forward a specific range of messages?", reply_markup=keyboard)

@bot.on_callback_query(filters.regex(r"^range_yes$"))
async def range_yes(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_states:
        user_states[user_id]["step"] = "start_msg"
        await callback_query.edit_message_text("Send me the link to the FIRST message to forward.")

@bot.on_callback_query(filters.regex(r"^range_cancel$"))
async def range_cancel(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_states:
        del user_states[user_id]
        await callback_query.edit_message_text("Forwarding cancelled.")

@bot.on_message(filters.private & filters.text)
async def handle_range(client, message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    if state["step"] == "start_msg":
        state["start_id"] = extract_msg_id(message.text)
        state["step"] = "end_msg"
        await message.reply_text("Now send me the link to the LAST message to forward.")
        
    elif state["step"] == "end_msg":
        state["end_id"] = extract_msg_id(message.text)
        await message.reply_text("Starting to forward...")
        asyncio.create_task(process_forward(client, user_id, state))
        del user_states[user_id]

async def process_forward(client, user_id, state):
    source = state["source_chat"]
    dests = state["dest_chats"]
    start_id = state.get("start_id")
    end_id = state.get("end_id")
    
    if not start_id or not end_id:
        return await client.send_message(user_id, "Error in message IDs.")
        
    for msg_id in range(start_id, end_id + 1):
        try:
            msg = await client.get_messages(source, msg_id)
            if msg.empty:
                continue
                
            for dest in dests:
                try:
                    fwd_msg = await msg.copy(dest)
                    if msg.pinned_message:
                        try:
                            await fwd_msg.pin()
                        except:
                            pass
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    fwd_msg = await msg.copy(dest)
                except Exception as e:
                    print(f"Failed to copy to {dest}: {e}")
                    
            await asyncio.sleep(2) # Prevent flood waits
        except Exception as e:
            print(f"Error fetching message {msg_id}: {e}")
            
    await client.send_message(user_id, "✅ Forwarding completed successfully!")
