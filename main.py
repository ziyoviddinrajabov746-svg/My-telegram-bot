import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
    await update.message.reply_text('🤖 Бот работает! Тест успешен!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'✅ Получил ваше сообщение: "{update.message.text}"')

def main():
    if not TELEGRAM_TOKEN:
        print("❌ ОШИБКА: TELEGRAM_TOKEN не установлен!")
        return
    
    print("🚀 Запуск бота...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    print("✅ Бот успешно запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
