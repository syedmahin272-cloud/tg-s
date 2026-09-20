from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import SessionPasswordNeeded
import os

# ==========================================
# ⚙️ অ্যাডমিন এবং বটের কনফিগারেশন
# ==========================================
ADMIN_ID = 7266067201
BOT_TOKEN = "8703137018:AAGEPyMzb6OUG8TUVuMbV7xNTxJyOIENG74"

API_ID = 39403096
API_HASH = "3ad6e3cff0e091be1acf3d98ad830df5"

# ==========================================
# 🌐 প্রক্সি সেটআপ (পেইড প্রক্সির জন্য রেডি)
# ==========================================
# পেইড প্রক্সি পেলে নিচের তথ্যগুলো পরিবর্তন করে নিবেন।
# প্রক্সি ছাড়া চালাতে চাইলে লিখবেন: PROXY = None
PROXY = {
    "scheme": "socks5",             # পেইড প্রক্সি SOCKS5 হলে "socks5" লিখবেন
    "hostname": "207.174.105.101",  # এখানে প্রক্সির IP বসাবেন
    "port": 2222,                 # এখানে প্রক্সির Port বসাবেন
    "usernae": "uajl7hc17i5-country-CO",    # পেইড প্রক্সির ইউজারনেম থাকলে সামনের # সরিয়ে এখানে বসাবেন
    "password": "ubj6z01ta1tu"     # পেইড প্রক্সির পাসওয়ার্ড থাকলে সামনের # সরিয়ে এখানে বসাবেন
}

# ==========================================
# 📂 ডাটাবেস ও ভ্যারিয়েবল
# ==========================================
USED_NUMBERS_FILE = "used_numbers.txt"
user_steps = {}
temp_clients = {}

bot = Client("SessionGenBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- হেল্পার ফাংশন ---
def is_number_used(phone):
    if not os.path.exists(USED_NUMBERS_FILE):
        return False
    with open(USED_NUMBERS_FILE, "r") as f:
        return phone in f.read().splitlines()

def mark_number_as_used(phone):
    with open(USED_NUMBERS_FILE, "a") as f:
        f.write(phone + "\n")

# ==========================================
# 🤖 বটের কমান্ড এবং মেসেজ হ্যান্ডলিং
# ==========================================
@bot.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start_cmd(client, message: Message):
    await message.reply("👋 **অ্যাডমিন সেশন জেনারেটরে স্বাগতম!**\n\nআপনার টেলিগ্রাম নম্বর দিন (Country code সহ, যেমন: +8801...):")
    user_steps[message.from_user.id] = "wait_phone"

@bot.on_message(filters.text & filters.user(ADMIN_ID))
async def handle_text(client, message: Message):
    user_id = message.from_user.id
    step = user_steps.get(user_id)

    if step == "wait_phone":
        phone = message.text.replace(" ", "")
        
        if is_number_used(phone):
            await message.reply("⚠️ এই নম্বর দিয়ে আগেই সেশন তৈরি করা হয়েছে! দয়া করে নতুন কোনো নম্বর দিন।")
            user_steps[user_id] = None
            return

        if PROXY:
            await message.reply("⏳ প্রক্সির মাধ্যমে কানেক্ট করা হচ্ছে, দয়া করে অপেক্ষা করুন...")
        else:
            await message.reply("⏳ কানেক্ট করা হচ্ছে, দয়া করে অপেক্ষা করুন...")
        
        user_client = Client(
            f"temp_{user_id}", 
            api_id=API_ID, 
            api_hash=API_HASH, 
            in_memory=True,
            proxy=PROXY
        )
        
        try:
            await user_client.connect()
            sent_code = await user_client.send_code(phone)
            temp_clients[user_id] = {
                "client": user_client, 
                "phone": phone, 
                "phone_code_hash": sent_code.phone_code_hash
            }
            await message.reply("✅ আপনার নম্বরে OTP পাঠানো হয়েছে।\n\nদয়া করে OTP দিন (মাঝে স্পেস দিয়ে লিখুন, যেমন: 1 2 3 4 5):")
            user_steps[user_id] = "wait_otp"
        except Exception as e:
            await message.reply(f"❌ কানেকশন বা নম্বরে সমস্যা (প্রক্সি স্লো বা ডেড হতে পারে):\n`{e}`")
            user_steps[user_id] = None
            
    elif step == "wait_otp":
        otp = message.text.replace(" ", "")
        user_data = temp_clients.get(user_id)
        if not user_data:
            return
            
        user_client = user_data["client"]
        phone = user_data["phone"]
        try:
            await user_client.sign_in(
                phone_number=phone,
                phone_code_hash=user_data["phone_code_hash"],
                phone_code=otp
            )
            
            session_string = await user_client.export_session_string()
            await message.reply(f"✅ **আপনার সেশন সফলভাবে তৈরি হয়েছে!**\n\n`{session_string}`\n\n*(উপরের টেক্সটটিতে ক্লিক করে কপি করুন)*")
            
            mark_number_as_used(phone)
            await user_client.disconnect()
            user_steps[user_id] = None
            del temp_clients[user_id]
            
        except SessionPasswordNeeded:
            await message.reply("🔐 আপনার অ্যাকাউন্টে 2-Step Verification চালু আছে। আপনার পাসওয়ার্ড দিন:")
            user_steps[user_id] = "wait_password"
        except Exception as e:
            await message.reply(f"❌ OTP ভুল বা এরর:\n`{e}`")
            user_steps[user_id] = None
            
    elif step == "wait_password":
        password = message.text
        user_data = temp_clients.get(user_id)
        user_client = user_data["client"]
        phone = user_data["phone"]
        
        try:
            await user_client.check_password(password)
            
            session_string = await user_client.export_session_string()
            await message.reply(f"✅ **আপনার সেশন সফলভাবে তৈরি হয়েছে!**\n\n`{session_string}`\n\n*(উপরের টেক্সটটিতে ক্লিক করে কপি করুন)*")
            
            mark_number_as_used(phone)
            await user_client.disconnect()
            user_steps[user_id] = None
            del temp_clients[user_id]
        except Exception as e:
            await message.reply(f"❌ পাসওয়ার্ড ভুল বা এরর:\n`{e}`")
            user_steps[user_id] = None

print("✅ বট সফলভাবে চালু হয়েছে! টেলিগ্রামে গিয়ে /start দিন।")
bot.run()
