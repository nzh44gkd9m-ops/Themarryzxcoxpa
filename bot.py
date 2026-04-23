import os
import sqlite3
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, executor, types

TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# --- БАЗА ---
conn = sqlite3.connect("love_bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    code TEXT,
    xp INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS pairs (
    user1 INTEGER,
    user2 INTEGER,
    created_at TEXT
)
""")

conn.commit()

# --- ДАННЫЕ ---
questions = [
    "Что тебе больше всего нравится во мне?",
    "Какой наш лучший момент?",
    "Когда ты понял(а), что любишь меня?"
]

tasks = [
    "Обнимитесь 1 минуту ❤️",
    "Скажите друг другу 3 комплимента",
    "Напишите друг другу милое сообщение"
]

waiting_for_message = {}

# --- XP ---
def add_xp(user_id, amount):
    cursor.execute("UPDATE users SET xp = xp + ? WHERE user_id=?", (amount, user_id))
    conn.commit()

def get_level(xp):
    return xp // 100 + 1

# --- КНОПКИ ---
def main_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("💌 Вопрос", callback_data="question"))
    kb.add(types.InlineKeyboardButton("🎯 Задание", callback_data="task"))
    kb.add(types.InlineKeyboardButton("💬 Написать", callback_data="chat"))
    kb.add(types.InlineKeyboardButton("❤️ Мы", callback_data="about"))
    kb.add(types.InlineKeyboardButton("🔗 Подключиться", callback_data="connect"))
    return kb

# --- СТАРТ ---
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    code = str(msg.from_user.id)[-4:]

    cursor.execute("INSERT OR IGNORE INTO users (user_id, code) VALUES (?, ?)", (msg.from_user.id, code))
    conn.commit()

    await msg.answer(f"Твой код: {code}\nОтправь партнёру ❤️", reply_markup=main_menu())

# --- CALLBACK ---
@dp.callback_query_handler(lambda c: True)
async def callbacks(call: types.CallbackQuery):
    user_id = call.from_user.id
    data = call.data

    if data == "question":
        add_xp(user_id, 10)
        await call.message.edit_text(random.choice(questions), reply_markup=main_menu())

    elif data == "task":
        add_xp(user_id, 15)
        await call.message.edit_text(random.choice(tasks), reply_markup=main_menu())

    elif data == "chat":
        waiting_for_message[user_id] = True
        await call.message.edit_text("Напиши сообщение партнёру 💬")

    elif data == "connect":
        await call.message.edit_text("Введи код партнёра:")

    elif data == "about":
        cursor.execute("SELECT user2, created_at FROM pairs WHERE user1=?", (user_id,))
        pair = cursor.fetchone()

        if pair:
            partner_id, created_at = pair
            start_date = datetime.strptime(created_at, "%Y-%m-%d")
            days = (datetime.now() - start_date).days

            cursor.execute("SELECT xp FROM users WHERE user_id=?", (user_id,))
            xp = cursor.fetchone()[0]
            level = get_level(xp)

            text = f"❤️ Вы вместе: {days} дней\n💞 Уровень: {level}\n✨ XP: {xp}"
        else:
            text = "Вы не подключили пару 😢"

        await call.message.edit_text(text, reply_markup=main_menu())

# --- СООБЩЕНИЯ ---
@dp.message_handler()
async def handle(msg: types.Message):
    user_id = msg.from_user.id
    text = msg.text

    # отправка сообщения
    if waiting_for_message.get(user_id):
        cursor.execute("SELECT user2 FROM pairs WHERE user1=?", (user_id,))
        res = cursor.fetchone()

        if res:
            partner_id = res[0]
            add_xp(user_id, 5)

            await bot.send_message(partner_id, f"💌 Сообщение:\n\n{text}")
            await msg.answer("Отправлено ❤️", reply_markup=main_menu())
        else:
            await msg.answer("Сначала подключите пару")

        waiting_for_message[user_id] = False
        return

    # подключение
    cursor.execute("SELECT user_id FROM users WHERE code=?", (text,))
    partner = cursor.fetchone()

    if partner:
        partner_id = partner[0]
        now = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("INSERT INTO pairs VALUES (?, ?, ?)", (user_id, partner_id, now))
        cursor.execute("INSERT INTO pairs VALUES (?, ?, ?)", (partner_id, user_id, now))
        conn.commit()

        await msg.answer("Вы теперь пара ❤️", reply_markup=main_menu())
        await bot.send_message(partner_id, "Ваша пара подключена ❤️")

# --- ЗАПУСК ---
if __name__ == "__main__":
    print("Бот запущен 🚀")
    executor.start_polling(dp, skip_updates=True)
