import sqlite3
import logging
import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# --- SOZLAMALAR ---
API_TOKEN = '8833376973:AAEEN3P6c5_PLP6K6AaBmHvEacDlHrDDbe8'
ADMIN_ID = 8958302600 
CHANNEL_ID = -1003811189563 

logging.basicConfig(level=logging.ERROR)
bot = Bot(token=API_TOKEN, parse_mode='HTML')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- BAZA ---
conn = sqlite3.connect('bot_pro.db', check_same_thread=False)
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)''')
cur.execute('''CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, file_id TEXT, category TEXT)''')
cur.execute('''CREATE TABLE IF NOT EXISTS bans (user_id INTEGER)''')
cur.execute('''CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)''')
conn.commit()

# --- FUNKSIYALAR ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

@dp.channel_post_handler(content_types=['document'])
async def auto_add_file(message: types.Message):
    name = message.document.file_name.lower()
    cat = "Windows" if "win" in name else "Drayverlar" if "driver" in name else "O'yinlar" if "game" in name else "Soft"
    cur.execute("INSERT INTO files (name, file_id, category) VALUES (?, ?, ?)", (message.document.file_name, message.document.file_id, cat))
    conn.commit()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    cur.execute("INSERT OR IGNORE INTO users VALUES (?)", (message.from_user.id,))
    conn.commit()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💻 Windows", "🛠 Drayverlar", "💾 Soft", "🎮 O'yinlar")
    await message.answer("Xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=markup)

@dp.message_handler(commands=['stat', 'send', 'ban', 'addurl'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    if message.text.startswith('/stat'):
        cur.execute("SELECT count(*) FROM users")
        await message.answer(f"📊 Obunachilar: {cur.fetchone()[0]}")
        
    elif message.text.startswith('/send'):
        text = message.text.replace("/send", "").strip()
        cur.execute("SELECT id FROM users")
        for user in cur.fetchall():
            try: await bot.send_message(user[0], text)
            except: pass
        await message.answer("✅ Xabar yuborildi!")
        
    elif message.text.startswith('/ban') and message.reply_to_message:
        cur.execute("INSERT INTO bans VALUES (?)", (message.reply_to_message.from_user.id,))
        conn.commit()
        await message.answer("🚫 Foydalanuvchi banlandi.")

    elif message.text.startswith('/addurl'):
        args = message.text.split(maxsplit=2)
        if len(args) < 3: return await message.reply("Format: /addurl [link] [nomi]")
        async with aiohttp.ClientSession() as session:
            async with session.get(args[1]) as response:
                data = await response.read()
                msg = await bot.send_document(CHANNEL_ID, document=data, caption=args[2])
                cur.execute("INSERT INTO files (name, file_id, category) VALUES (?, ?, ?)", (args[2], msg.document.file_id, "Soft"))
                conn.commit()
                await message.answer("✅ Fayl kanalga qo'shildi!")

@dp.message_handler()
async def menu_handler(message: types.Message):
    if not await is_subscribed(message.from_user.id):
        return await message.answer(f"⚠️ Botdan foydalanish uchun kanalga obuna bo'ling!")
    
    cur.execute("SELECT user_id FROM bans WHERE user_id=?", (message.from_user.id,))
    if cur.fetchone(): return

    cat_map = {"💻 Windows": "Windows", "🛠 Drayverlar": "Drayverlar", "💾 Soft": "Soft", "🎮 O'yinlar": "O'yinlar"}
    cat = cat_map.get(message.text)
    
    if cat: cur.execute("SELECT name, file_id FROM files WHERE category=?", (cat,))
    else: cur.execute("SELECT name, file_id FROM files WHERE name LIKE ?", ('%' + message.text + '%',))
    
    files = cur.fetchmany(10)
    if not files: await message.answer("❌ Hech narsa topilmadi.")
    else:
        for f in files:
            try: await bot.send_document(message.chat.id, document=f[1], caption=f"📦 {f[0]}")
            except: pass

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
