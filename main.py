import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading

# Создаем Flask приложение для Health Check
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 DeepSeek Bot is running!"

@app.route('/healthz')
def health_check():
    return "OK", 200

# Функция для запуска Flask в отдельном потоке
def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токены
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

print("🔧 Проверка переменных окружения...")
print(f"TELEGRAM_TOKEN: {'✅ Установлен' if TELEGRAM_TOKEN else '❌ Отсутствует'}")
print(f"OPENROUTER_API_KEY: {'✅ Установлен' if OPENROUTER_API_KEY else '❌ Отсутствует'}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🤖 Привет! Я DeepSeek бот. Задайте мне вопрос!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    await update.message.reply_text(f'🔍 Вы написали: "{user_message}"\n\nСейчас добавлю AI функционал...')

def main():
    if not TELEGRAM_TOKEN:
        print("❌ ОШИБКА: TELEGRAM_TOKEN не установлен!")
        return
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print("✅ Flask сервер запущен на порту 5000")
    
    print("🚀 Запуск Telegram бота...")
    app_bot = Application.builder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот успешно запущен!")
    app_bot.run_polling()

if __name__ == '__main__':
    main()
