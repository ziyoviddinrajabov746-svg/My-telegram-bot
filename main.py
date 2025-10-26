import os
import logging
import requests
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
    await update.message.reply_text(
        '🤖 Привет! Я DeepSeek бот с искусственным интеллектом!\n\n'
        'Задайте мне любой вопрос, и я постараюсь помочь!'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Показываем что бот "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Отправляем запрос к DeepSeek через OpenRouter
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'deepseek/deepseek-chat',
            'messages': [
                {'role': 'user', 'content': user_message}
            ],
            'max_tokens': 1000
        }
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions', 
            headers=headers, 
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            bot_response = result['choices'][0]['message']['content']
        else:
            bot_response = "❌ Извините, не могу подключиться к AI. Попробуйте позже."
            
    except Exception as e:
        bot_response = f"⚠️ Произошла ошибка: {str(e)}"
    
    await update.message.reply_text(bot_response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **Помощь по боту:**\n\n"
        "Просто напишите мне сообщение, и я отвечу с помощью DeepSeek AI!\n\n"
        "**Команды:**\n"
        "/start - начать общение\n"
        "/help - показать эту справку"
    )

def main():
    if not TELEGRAM_TOKEN:
        print("❌ ОШИБКА: TELEGRAM_TOKEN не установлен!")
        return
    
    if not OPENROUTER_API_KEY:
        print("❌ ОШИБКА: OPENROUTER_API_KEY не установлен!")
        return
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    print("✅ Flask сервер запущен на порту 5000")
    
    print("🚀 Запуск Telegram бота...")
    app_bot = Application.builder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("help", help_command))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот успешно запущен!")
    app_bot.run_polling()

if __name__ == '__main__':
    main()
