main.pyimport os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Твои ключи (их настроим позже)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Когда пишешь /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🤖 Привет! Я твой DeepSeek бот! Просто напиши мне что-нибудь!')

# Когда пишешь сообщение
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    # Отправляем запрос к DeepSeek
    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'deepseek/deepseek-chat',
        'messages': [{'role': 'user', 'content': user_message}]
    }
    
    try:
        response = requests.post('https://openrouter.ai/api/v1/chat/completions', 
                               headers=headers, json=data)
        result = response.json()
        bot_response = result['choices'][0]['message']['content']
    except:
        bot_response = "Извини, я сейчас не могу ответить 😔"
    
    await update.message.reply_text(bot_response)

# Запуск бота
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    print("🎉 Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
