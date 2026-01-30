# main.py
from flask import Flask
import threading
import os
import telebot
from telebot import types

# ---- FLASK ----
app = Flask(__name__)  # вот здесь обязательно __name__

@app.route("/")
def home():
    return "OK"

def run_web():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

threading.Thread(target=run_web).start()

# ---- TELEGRAM BOT ----
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ---- ТАРИФЫ ----
TARIFFS = {
    "AMФ": {1: 290, 2: 370, 3: 400, 5: 450, 10: 650, 20: 1110, 50: 2050, 100: 3350},
    "СК": {1: 300, 2: 430, 3: 470, 5: 500, 10: 730, 20: 1250, 50: 2550, 100: 3850}
}

# ---- ОСТАТКИ ----
STOCK = {"AMФ": 80, "СК": 70}
stats = {"total": 0, "items": {}}
user_state = {}
refill_state = {}

# ---- КНОПКИ ----
def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📦 AMФ", "📦 СК")
    kb.add("📈 Отчёт", "🚯 Сброс")
    kb.add("🤝 Пополнить")
    return kb

def numbers_keyboard(product):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row = []
    for w in sorted(TARIFFS[product].keys()):
        row.append(types.KeyboardButton(str(w)))
        if len(row) == 4:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add("⬅️ Главное меню")
    return kb

# ---- /start ----
@bot.message_handler(commands=["start"])
def start(msg):
    bot.send_message(msg.chat.id,
                     f"█ SYSTEM INIT █\n📦 Остатки: AMФ={STOCK['AMФ']} СК={STOCK['СК']}\nВыбери товар:",
                     reply_markup=main_keyboard())

# ---- выбор продукта ----
@bot.message_handler(func=lambda m: m.text in ["📦 AMФ", "📦 СК"])
def select_product(msg):
    product = "AMФ" if "AMФ" in msg.text else "СК"
    user_state[msg.chat.id] = product
    bot.send_message(msg.chat.id,
                     f"> Выбран {product}\n> Выбери вес/тип:",
                     reply_markup=numbers_keyboard(product))

# ---- добавление заказа ----
@bot.message_handler(func=lambda m: m.chat.id in user_state)
def add_order(msg):
    product = user_state[msg.chat.id]
    if msg.text == "⬅️ Главное меню":
        del user_state[msg.chat.id]
        bot.send_message(msg.chat.id, "> Главное меню", reply_markup=main_keyboard())
        return
    try:
        weight = int(msg.text)
        if weight not in TARIFFS[product]:
            bot.send_message(msg.chat.id, "❌ Нет такого типа")
            return
        if STOCK[product] < weight:
            bot.send_message(msg.chat.id, f"❌ Недостаточно на складе! Остаток: {STOCK[product]}")
            return

        price = TARIFFS[product][weight]
        stats["total"] += price
        stats["items"].setdefault(product, {})
        stats["items"][product][weight] = stats["items"][product].get(weight, 0) + 1
        STOCK[product] -= weight

        bot.send_message(msg.chat.id,
                         f"█ SYSTEM LOG: ORDER ADDED █\n> Товар: {product}\n> Вес: {weight}\n> Цена: {price}\n> ИТОГО: {stats['total']}\n> Остаток: {STOCK[product]}",
                         reply_markup=main_keyboard())
        del user_state[msg.chat.id]
    except:
        bot.send_message(msg.chat.id, "❌ Введите число")

# ---- отчёт ----
@bot.message_handler(func=lambda m: m.text == "📈 Отчёт")
def report(msg):
    if not stats["items"]:
        bot.send_message(msg.chat.id, "█ SYSTEM REPORT █\nНет данных")
        return
    text = "███ SYSTEM REPORT ███\n"
    for p, t in stats["items"].items():
        text += f"\n> {p}:\n"
        for k, c in t.items():
            text += f"  {k}: {c} шт\n"
    text += f"\n⚡ TOTAL: {stats['total']}\n📦 STOCK: AMФ={STOCK['AMФ']} СК={STOCK['СК']}"
    bot.send_message(msg.chat.id, text)

# ---- сброс ----
@bot.message_handler(func=lambda m: m.text == "🚯 Сброс")
def reset(msg):
    stats["total"] = 0
    stats["items"] = {}
    user_state.clear()
    refill_state.clear()
    STOCK["AMФ"] = 0
    STOCK["СК"] = 0
    bot.send_message(msg.chat.id, "█ SYSTEM RESET █\n> Статистика и остатки сброшены", reply_markup=main_keyboard())

# ---- пополнение ----
@bot.message_handler(func=lambda m: m.text == "🤝 Пополнить")
def refill_start(msg):
    refill_state[msg.chat.id] = {"step": 1}
    bot.send_message(msg.chat.id, "> Введите количество для пополнения AMФ:")

@bot.message_handler(func=lambda m: m.chat.id in refill_state)
def refill_input(msg):
    try:
        amount = int(msg.text)
        if amount <= 0:
            bot.send_message(msg.chat.id, "❌ Введите число больше 0")
            return
    except:
        bot.send_message(msg.chat.id, "❌ Введите число")
        return

    step = refill_state[msg.chat.id]["step"]
    if step == 1:
        STOCK["AMФ"] += amount
        refill_state[msg.chat.id]["step"] = 2
        bot.send_message(msg.chat.id, f"> AMФ пополнен на {amount}. Остаток: {STOCK['AMФ']}\nВведите количество для СК:")
    elif step == 2:
        STOCK["СК"] += amount
        bot.send_message(msg.chat.id, f"> СК пополнен на {amount}. Остаток: {STOCK['СК']}", reply_markup=main_keyboard())
        del refill_state[msg.chat.id]

# ---- START BOT ----
bot.infinity_polling()
