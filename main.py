import os
import logging
import requests
import io
import aiohttp
from gtts import gTTS
from pydub import AudioSegment
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading

# Создаем Flask приложение для Health Check
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Multi-AI Bot is running!"

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

# Доступные модели AI
AVAILABLE_MODELS = {
    'deepseek': {
        'name': '🧠 DeepSeek Chat',
        'id': 'deepseek/deepseek-chat',
        'description': 'Умная и эффективная модель для общих задач'
    },
    'deepseek-coder': {
        'name': '💻 DeepSeek Coder',
        'id': 'deepseek/deepseek-coder', 
        'description': 'Специализирована на программировании и коде'
    },
    'gpt': {
        'name': '🤖 GPT-3.5 Turbo',
        'id': 'openai/gpt-3.5-turbo',
        'description': 'Быстрая и умная модель от OpenAI'
    },
    'claude': {
        'name': '🎭 Claude Haiku',
        'id': 'anthropic/claude-3-haiku',
        'description': 'Быстрая и креативная модель от Anthropic'
    },
    'gemini': {
        'name': '💎 Gemini Pro',
        'id': 'google/gemini-pro',
        'description': 'Мощная модель от Google'
    }
}

# Хранилище выбранных моделей для пользователей
user_models = {}

print("🔧 Проверка переменных окружения...")
print(f"TELEGRAM_TOKEN: {'✅ Установлен' if TELEGRAM_TOKEN else '❌ Отсутствует'}")
print(f"OPENROUTER_API_KEY: {'✅ Установлен' if OPENROUTER_API_KEY else '❌ Отсутствует'}")

# Функция для преобразования текста в речь
async def text_to_speech(text: str, lang: str = 'ru') -> io.BytesIO:
    """Преобразует текст в голосовое сообщение"""
    try:
        # Создаем TTS объект
        tts = gTTS(text=text, lang=lang, slow=False)
        
        # Сохраняем в байтовый поток
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        # Конвертируем MP3 в OGG (Telegram предпочитает OGG для голосовых)
        audio = AudioSegment.from_mp3(mp3_fp)
        ogg_fp = io.BytesIO()
        audio.export(ogg_fp, format="ogg")
        ogg_fp.seek(0)
        
        return ogg_fp
        
    except Exception as e:
        print(f"Ошибка TTS: {e}")
        return None

# Функция для обработки голосовых сообщений
async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает голосовые сообщения от пользователя"""
    voice = update.message.voice
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Получаем информацию о файле голосового сообщения
        voice_file = await voice.get_file()
        
        # Скачиваем голосовое сообщение
        async with aiohttp.ClientSession() as session:
            async with session.get(voice_file.file_path) as response:
                if response.status == 200:
                    voice_data = await response.read()
                    
                    # Здесь можно добавить распознавание речи (STT)
                    # Пока просто отвечаем текстом, что получили голосовое
                    response_text = "🎤 Я получил ваше голосовое сообщение! Пока я умею только отвечать голосом на текстовые сообщения. Используйте команду /voice"
                    
                    # Отправляем текстовый ответ
                    await update.message.reply_text(response_text)
                    
                else:
                    await update.message.reply_text("❌ Не удалось обработать голосовое сообщение")
    
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка обработки голоса: {str(e)}")

# Команда /voice - преобразует текст в голосовое сообщение
async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Преобразует текстовый ответ AI в голосовое сообщение"""
    user_message = ' '.join(context.args)
    
    if not user_message:
        await update.message.reply_text(
            "🎤 **Голосовые ответы**\n\n"
            "Напишите текст после команды /voice\n"
            "Например: /voice привет, как дела?\n\n"
            "Или просто напишите сообщение, и я отвечу голосом!"
        )
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
    
    try:
        # Получаем ответ от AI (используем существующую логику)
        user_id = update.effective_user.id
        current_model_key = user_models.get(user_id, 'deepseek')
        model_id = AVAILABLE_MODELS[current_model_key]['id']
        model_name = AVAILABLE_MODELS[current_model_key]['name']
        
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model_id,
            'messages': [{'role': 'user', 'content': user_message}],
            'max_tokens': 500  # Укороченный ответ для голосового сообщения
        }
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions', 
            headers=headers, 
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Обрезаем длинный ответ (голосовые сообщения не должны быть слишком длинными)
            if len(ai_response) > 500:
                ai_response = ai_response[:497] + "..."
            
            # Преобразуем ответ в голос
            voice_audio = await text_to_speech(ai_response)
            
            if voice_audio:
                # Отправляем голосовое сообщение
                await update.message.reply_voice(
                    voice=voice_audio,
                    caption=f"🎤 {model_name}: {ai_response}"
                )
            else:
                await update.message.reply_text(f"🤖 {model_name}:\n\n{ai_response}")
        else:
            await update.message.reply_text("❌ Ошибка подключения к AI")
            
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Устанавливаем модель по умолчанию для нового пользователя
    user_models[user_id] = 'deepseek'
    
    await update.message.reply_text(
        '🤖 Привет! Я мульти-AI бот с **голосовыми ответами**! 🎤\n\n'
        '**Новые возможности:**\n'
        '• 🎤 Отвечаю голосом на любые сообщения\n'
        '• /voice [текст] - преобразую текст в голосовое\n'
        '• 🎙️ Можете отправлять голосовые сообщения\n\n'
        '**Основные команды:**\n'
        '/models - список всех моделей\n'
        '/model <имя> - выбрать модель\n'
        '/current - текущая модель\n'
        '/voice - голосовые ответы\n'
        '/help - помощь\n\n'
        'Просто напишите мне что-нибудь, и я отвечу голосом! 🎵'
    )

async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    models_text = "🛠 **Доступные модели AI:**\n\n"
    
    for key, model in AVAILABLE_MODELS.items():
        models_text += f"**{model['name']}**\n"
        models_text += f"Ключ: `{key}`\n"
        models_text += f"Описание: {model['description']}\n\n"
    
    models_text += "Используйте: `/model ключ` для выбора"
    
    await update.message.reply_text(models_text)

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите модель. Например: `/model deepseek`\n"
            "Посмотреть все модели: /models"
        )
        return
    
    model_key = context.args[0].lower()
    
    if model_key not in AVAILABLE_MODELS:
        await update.message.reply_text(
            f"❌ Модель `{model_key}` не найдена.\n"
            "Посмотреть доступные модели: /models"
        )
        return
    
    user_models[user_id] = model_key
    model_info = AVAILABLE_MODELS[model_key]
    
    await update.message.reply_text(
        f"✅ Модель изменена на: **{model_info['name']}**\n\n"
        f"{model_info['description']}"
    )

async def current_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_model_key = user_models.get(user_id, 'deepseek')
    model_info = AVAILABLE_MODELS[current_model_key]
    
    await update.message.reply_text(
        f"🔮 **Текущая модель:** {model_info['name']}\n"
        f"📝 **Описание:** {model_info['description']}\n\n"
        "Изменить модель: /models"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Получаем выбранную модель пользователя (по умолчанию deepseek)
    current_model_key = user_models.get(user_id, 'deepseek')
    model_id = AVAILABLE_MODELS[current_model_key]['id']
    model_name = AVAILABLE_MODELS[current_model_key]['name']
    
    # Показываем что бот "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Отправляем запрос к выбранной модели через OpenRouter
        headers = {
            'Authorization': f'Bearer {OPENROUTER_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': model_id,
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
            # Добавляем информацию о модели в ответ
            bot_response = f"🤖 **{model_name}**:\n\n{bot_response}"
        else:
            bot_response = f"❌ Ошибка подключения к {model_name}. Попробуйте позже."
            
    except Exception as e:
        bot_response = f"⚠️ Ошибка в модели {model_name}: {str(e)}"
    
    await update.message.reply_text(bot_response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **Помощь по мульти-AI боту:**\n\n"
        "**Основные команды:**\n"
        "/start - начать работу\n"
        "/models - список всех моделей AI\n" 
        "/model <ключ> - выбрать модель\n"
        "/current - текущая модель\n"
        "/voice - голосовые ответы\n"
        "/help - эта справка\n\n"
        "**Примеры:**\n"
        "`/model gpt` - переключиться на GPT\n"
        "`/model claude` - использовать Claude\n"
        "`/voice привет` - получить голосовой ответ"
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
    
    print("🚀 Запуск мульти-AI бота...")
    app_bot = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики команд
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("models", models_command))
    app_bot.add_handler(CommandHandler("model", model_command))
    app_bot.add_handler(CommandHandler("current", current_command))
    app_bot.add_handler(CommandHandler("voice", voice_command))
    app_bot.add_handler(CommandHandler("help", help_command))
    app_bot.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Мульти-AI бот успешно запущен!")
    app_bot.run_polling()

if __name__ == '__main__':
    main()
