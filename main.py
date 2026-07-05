# -*- coding: utf-8 -*-
"""
ELBEKSOFTUZ / TOSHKENTOVUZ - Yakuniy Professional Telegram Bot
Direct Video Streaming + Real Withdrawal & Ad Management System
Language: Uzbek
"""

import os
import logging
import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# Logging sozlamalari (Serverda xatoliklarni kuzatish uchun)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- KONFIGURATSIYA ---
BOT_TOKEN = "8877993639:AAEQDEjX6jIDNPsekieiu9054YyAmDcAJ5E"  # BotFather'dan olgan tokeningizni yozing
ADMIN_ID =8958302600   # O'zingizning Telegram ID raqamingizni yozing

MIN_WITHDRAWAL = 120000     # Minimal pul yechish: 50,000 so'm
BASE_VIDEO_REWARD = 100   # Har bir video uchun boshlang'ich mukofot: 500 so'm

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- STATIK MA'LUMOTLAR OMBORI (Xotirada saqlanadi) ---
users_db = {}
advertisements = {}
admin_stats = {
    "total_users": 0,
    "total_ads": 0,
    "pending_ads": 0,
    "total_payouts": 0
}

# --- ASOSIY VIDEO LINKLAR RO'YXATI (Boshlang'ich namunalar) ---
video_links_pool = [
    "https://www.youtube.com/shorts/v3b8f_example",
    "https://www.tiktok.com/@user/video/1234567890",
    "https://www.instagram.com/reels/C4_example/"
]

# --- FSM HOLATLARI (Ketma-ketlik jarayonlari) ---
class AdUploadStates(StatesGroup):
    waiting_for_link = State()
    waiting_for_payment = State()

class AdminStates(StatesGroup):
    waiting_for_link = State()

class WithdrawStates(StatesGroup):
    waiting_for_card = State()

# --- AQLLI DINAMIK NARX TIZIMI ---
def get_dynamic_reward(user_id):
    user_data = users_db.get(user_id, {"watched_count": 0})
    watched = user_data.get("watched_count", 0)
    if watched < 100:
        return BASE_VIDEO_REWARD
    elif watched < 100:
        return int(BASE_VIDEO_REWARD * 1.1)  # 550 so'm
    else:
        return int(BASE_VIDEO_REWARD * 1.25) # 625 so'm

# --- START BUYRUG'I ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Foydalanuvchi"
    
    if user_id not in users_db:
        users_db[user_id] = {"username": username, "balance": 0, "watched_count": 0}
        admin_stats["total_users"] += 1

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Reels Videolarni ko'rish", callback_data="watch_video_link")],
        [
            InlineKeyboardButton(text="💰 Balans va Pul yechish", callback_data="check_balance"),
            InlineKeyboardButton(text="📢 Reklama berish", callback_data="buy_ad_link")
        ]
    ])
    
    await message.answer(
        text=f"✨ **ELBEKSOFTUZ / TOSHKENTOVUZ** Reels loyihasiga xush kelibsiz!\n\n"
             f"Ushbu botda Reels va Shorts videolarni to'g'ridan-to'g'ri tomosha qilib haqiqiy pul ishlashingiz mumkin!\n\n"
             f"💰 Boshlang'ich mukofot: {BASE_VIDEO_REWARD} so'mdan boshlanadi\n"
             f"💳 Minimal pul yechish summasi: {MIN_WITHDRAWAL:,} so'm",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# --- REELS KO'RISH TIZIMI (Link Preview integratsiyasi) ---
@dp.callback_query(F.data == "watch_video_link")
async def watch_video_link_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if not video_links_pool:
        return await callback.message.answer(
            "😔 Hozircha yangi videolar mavjud emas. Birozdan so'ng urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_menu")]])
        )
    
    selected_link = random.choice(video_links_pool)
    reward = get_dynamic_reward(user_id)
    
    users_db[user_id]["balance"] += reward
    users_db[user_id]["watched_count"] += 1
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Keyingi video", callback_data="watch_video_link")],
        [InlineKeyboardButton(text="⬅️ Asosiy menyu", callback_data="back_to_menu")]
    ])
    
    # prefer_large_media=True video pleyerni Telegram ichida katta va qulay qilib ochadi
    await callback.message.answer(
        text=f"🎬 **Reels Striming**\n\n"
             f"🔗 [Videoni ko'rish uchun bu yerga bosing]({selected_link})\n\n"
             f"✅ Balansga qo'shildi: **{reward:,} so'm**\n"
             f"📊 Jami ko'rilgan videolar: {users_db[user_id]['watched_count']} ta",
        reply_markup=keyboard,
        parse_mode="Markdown",
        link_preview_options=LinkPreviewOptions(is_disabled=False, prefer_large_media=True)
    )
    await callback.answer()

# --- BALANS VA HAQIQIY PUL YECHISH TIZIMI ---
@dp.callback_query(F.data == "check_balance")
async def check_balance_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = users_db[user_id]["balance"]
    
    text = f"💳 **Sizning balansingiz:** {balance:,} so'm\n"
    text += f"📊 Ko'rilgan videolar: {users_db[user_id]['watched_count']} ta\n\n"
    
    buttons = []
    if balance >= MIN_WITHDRAWAL:
        text += "🎉 Tabriklaymiz! Balansingiz yetarli. Pulni yechib olishingiz mumkin."
        buttons.append([InlineKeyboardButton(text="💳 Pulni yechish (Karta orqali)", callback_data="withdraw_money")])
    else:
        text += f"⚠️ Pul yechish uchun yana {(MIN_WITHDRAWAL - balance):,} so'm yig'ishingiz kerak (Minimal: {MIN_WITHDRAWAL:,} so'm)."
        
    buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# --- PUL YECHISH JARAYONI (FSM) ---
@dp.callback_query(F.data == "withdraw_money")
async def start_withdrawal(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if users_db[user_id]["balance"] < MIN_WITHDRAWAL:
        return await callback.answer("Mablag' yetarli emas!", show_alert=True)
        
    await callback.message.answer(
        "📝 **Pul yechishni rasmiylashtirish**\n\n"
        "Iltimos, o'zingizning **Plastik karta raqamingizni** va **Ism-familiyangizni** yozib yuboring:\n"
        "Misol: `8600 1234 5678 9012 - Elbek Toshkentov`"
    )
    await state.set_state(WithdrawStates.waiting_for_card)
    await callback.answer()

@dp.message(WithdrawStates.waiting_for_card)
async def card_received_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    card_details = message.text
    user_balance = users_db[user_id]["balance"]
    
    # Adminga (Sizga) to'lov so'rovi yuboriladi
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"💰 **YANGI PUL YECHISH SO'ROVI!**\n\n"
             f"👤 Foydalanuvchi: {users_db[user_id]['username']} (ID: {user_id})\n"
             f"💵 Yechiladigan summa: {user_balance:,} so'm\n"
             f"💳 Karta ma'lumotlari: `{card_details}`\n\n"
             f"Pulni o'tkazib berganingizdan so'ng foydalanuvchiga xabar bering.",
        parse_mode="Markdown"
    )
    
    admin_stats["total_payouts"] += user_balance
    users_db[user_id]["balance"] = 0  # Balans nollanadi
    
    await message.answer("✅ So'rovingiz adminga yuborildi! Tez orada plastik kartangizga pul tushirib beriladi va bot orqali bildirishnoma olasiz.")
    await state.clear()

# --- ASOSIY MENYUGA QAYTISH ---
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Reels Videolarni ko'rish", callback_data="watch_video_link")],
        [
            InlineKeyboardButton(text="💰 Balans va Pul yechish", callback_data="check_balance"),
            InlineKeyboardButton(text="📢 Reklama berish", callback_data="buy_ad_link")
        ]
    ])
    await callback.message.answer("✨ **Asosiy menyu**", reply_markup=keyboard)
    await callback.answer()

# --- REKLAMA QABUL QILISH TIZIMI ---
@dp.callback_query(F.data == "buy_ad_link")
async def start_ad_link_placement(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 **Yangi reklama:** Iltimos, videongiz havolasini (YouTube, TikTok yoki Instagram linkini) yuboring:")
    await state.set_state(AdUploadStates.waiting_for_link)
    await callback.answer()

@dp.message(AdUploadStates.waiting_for_link, F.text.startswith("http"))
async def ad_link_received(message: types.Message, state: FSMContext):
    await state.update_data(video_url=message.text)
    await message.answer("💳 Plastik kartaga to'lovni bajaring va bu yerga **To'lov chekini (rasmini)** yuboring:")
    await state.set_state(AdUploadStates.waiting_for_payment)

@dp.message(AdUploadStates.waiting_for_payment, F.photo)
async def ad_payment_link_received(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    video_url = user_data.get("video_url")
    payment_photo_id = message.photo[-1].file_id
    
    ad_id = message.message_id
    advertisements[ad_id] = {"user_id": message.from_user.id, "video_url": video_url, "status": "pending"}
    admin_stats["pending_ads"] += 1
    
    await message.answer("✅ Reklama havolasi va chek adminga yuborildi. Tasdiqlanishini kuting.")
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [[InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"ln_ap_{ad_id}"),
          InlineKeyboardButton(text="❌ Rad etish", callback_data=f"ln_rj_{ad_id}")]]
    ])
    await bot.send_photo(chat_id=ADMIN_ID, photo=payment_photo_id, 
                         caption=f"🔔 **Yangi reklama linki!**\nHavola: {video_url}\nTasdiqlaysizmi?", reply_markup=admin_keyboard)
    await state.clear()

@dp.callback_query(F.data.startswith("ln_ap_"))
async def admin_approve_link_ad(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    ad_id = int(callback.data.split("_")[2])
    
    if ad_id in advertisements:
        advertisements[ad_id]["status"] = "approved"
        video_links_pool.append(advertisements[ad_id]["video_url"])
        admin_stats["pending_ads"] -= 1
        admin_stats["total_ads"] += 1
        await callback.message.edit_caption(caption="✅ Havola tasdiqlandi va aylanmaga qo'shildi!")
    await callback.answer()

# --- ADMIN TEZKOR LINK QO'SHISH VA PANEL ---
@dp.message(Command("addlink"))
async def add_link_command(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("🔗 Qo'shmoqchi bo'lgan yangi Reels/Shorts video havolasini yuboring:")
    await state.set_state(AdminStates.waiting_for_link)

@dp.message(AdminStates.waiting_for_link, F.text.startswith("http"))
async def admin_link_received(message: types.Message, state: FSMContext):
    video_links_pool.append(message.text)
    await message.answer("✅ Havola ro'yxatga muvaffaqiyatli qo'shildi!")
    await state.clear()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(
        f"📊 **ELBEKSOFTUZ / TOSHKENTOVUZ Admin Paneli**\n\n"
        f"👥 Umumiy foydalanuvchilar: {admin_stats['total_users']}\n"
        f"🔗 Jami faol video havolalar: {len(video_links_pool)} ta\n"
        f"💳 Jami yechilgan pullar: {admin_stats['total_payouts']:,} so'm\n\n"
        f"👉 Yangi video link qo'shish uchun buyruq: /addlink",
        parse_mode="Markdown"
    )

# --- MAIN ---
async def main():
    print("Bot muvaffaqiyatli ishga tushdi...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
