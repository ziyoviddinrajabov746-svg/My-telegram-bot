import os
import logging
import requests
import io
import aiohttp
import time
import threading
import asyncio
from datetime import datetime
from gtts import gTTS
from pydub import AudioSegment
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask

# ==================== КОНФИГУРАЦИЯ ====================
app = Flask(__name__)

# Настройка продвинутого логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Получаем токены
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# ==================== СИСТЕМА ПАМЯТИ ====================
user_models = {}
user_stats = {}  # Статистика по пользователям
conversation_history = {}  # История диалогов

# ==================== МОДЕЛИ AI ====================
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

# ==================== FLASK РОУТЫ ====================
@app.route('/')
def home():
    return "🤖 Multi-AI Bot is running! 🚀"

@app.route('/healthz')
def health_check():
    return {"status": "OK", "timestamp": datetime.now().isoformat()}, 200

@app.route('/stats')
def stats():
    """Статистика бота"""
    return {
        "users_count": len(user_models),
        "active_users": len(user_stats),
        "timestamp": datetime.now().isoformat()
    }

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

# ==================== СИСТЕМА АКТИВНОСТИ ====================
def keep_bot_awake():
    """Периодически пингует сам себя чтобы не засыпать"""
    def ping():
        time.sleep(30)  # Ждем запуска Flask
        while True:
            try:
                requests.get("http://localhost:5000/healthz", timeout=10)
                logger.info("✅ Keep-alive ping sent")
            except Exception as e:
                logger.warning(f"⚠️ Keep-alive ping failed: {e}")
            time.sleep(300)  # Каждые 5 минут
    
    ping_thread = threading.Thread(target=ping)
    ping_thread.daemon = True
    ping_thread.start()

# ==================== УТИЛИТЫ ====================
async def text_to_speech(text: str, lang: str = 'ru') -> io.BytesIO:
    """Преобразует текст в голосовое сообщение"""
    try:
        # Ограничиваем длину текста для голосового сообщения
        if len(text) > 500:
            text = text[:497] + "..."
            
        tts = gTTS(text=text, lang=lang, slow=False)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        audio = AudioSegment.from_mp3(mp3_fp)
        ogg_fp = io.BytesIO()
        audio.export(ogg_fp, format="ogg")
        ogg_fp.seek(0)
        
        return ogg_fp
        
    except Exception as e:
        logger.error(f"❌ Ошибка TTS: {e}")
        return None

def update_user_stats(user_id: int):
    """Обновляет статистику пользователя"""
    if user_id not in user_stats:
        user_stats[user_id] = {
            'first_seen': datetime.now(),
            'message_count': 0,
            'last_active': datetime.now()
        }
    user_stats[user_id]['message_count'] += 1
    user_stats[user_id]['last_active'] = datetime.now()

# ==================== КОМАНДЫ БОТА ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user_id = update.effective_user.id
        user_models[user_id] = 'deepseek'
        update_user_stats(user_id)
        
        welcome_text = (
            '🤖 **Привет! Я улучшенный мульти-AI бот!** 🚀\n\n'
            '✨ **Новые возможности:**\n'
            '• 🧠 **Улучшенная память** - помню ваши предпочтения\n'
            '• 📊 **Статистика** - отслеживаю активность\n'
            '• ⚡ **Стабильная работа** - не засыпаю\n'
            '• 🎤 **Голосовые ответы** - говорю голосом\n\n'
            '🔧 **Основные команды:**\n'
            '/start - начать работу\n'
            '/models - список моделей AI\n'
            '/model <имя> - выбрать модель\n'
            '/current - текущая модель\n'
            '/voice <текст> - голосовой ответ\n'
            '/stats - моя статистика\n'
            '/help - помощь\n\n'
            'Просто напишите мне вопрос! 😊'
        )
        
        await update.message.reply_text(welcome_text)
        logger.info(f"🎯 Новый пользователь: {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в start: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при запуске")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику пользователя"""
    try:
        user_id = update.effective_user.id
        update_user_stats(user_id)
        
        if user_id in user_stats:
            stats = user_stats[user_id]
            current_model = user_models.get(user_id, 'deepseek')
            model_name = AVAILABLE_MODELS[current_model]['name']
            
            stats_text = (
                f"📊 **Ваша статистика:**\n\n"
                f"• 🤖 **Модель по умолчанию:** {model_name}\n"
                f"• 💬 **Отправлено сообщений:** {stats['message_count']}\n"
                f"• 🕐 **Первое использование:** {stats['first_seen'].strftime('%d.%m.%Y %H:%M')}\n"
                f"• ⏰ **Последняя активность:** {stats['last_active'].strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Всего пользователей: {len(user_stats)}"
            )
        else:
            stats_text = "📊 Статистика пока недоступна"
            
        await update.message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в stats_command: {e}")
        await update.message.reply_text("⚠️ Ошибка при получении статистики")

async def models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список доступных моделей"""
    try:
        update_user_stats(update.effective_user.id)
        
        models_text = "🛠 **Доступные модели AI:**\n\n"
        
        for key, model in AVAILABLE_MODELS.items():
            models_text += f"**{model['name']}**\n"
            models_text += f"Ключ: `{key}`\n"
            models_text += f"Описание: {model['description']}\n\n"
        
        models_text += "Используйте: `/model ключ` для выбора"
        await update.message.reply_text(models_text)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в models_command: {e}")
        await update.message.reply_text("⚠️ Ошибка при получении списка моделей")

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменяет выбранную модель"""
    try:
        user_id = update.effective_user.id
        update_user_stats(user_id)
        
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
            f"✅ **Модель изменена на:** {model_info['name']}\n\n"
            f"{model_info['description']}\n\n"
            f"Теперь я буду использовать {model_info['name']} для ответов!"
        )
        logger.info(f"🔄 Пользователь {user_id} сменил модель на {model_key}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в model_command: {e}")
        await update.message.reply_text("⚠️ Ошибка при смене модели")

async def current_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущую модель"""
    try:
        user_id = update.effective_user.id
        update_user_stats(user_id)
        
        current_model_key = user_models.get(user_id, 'deepseek')
        model_info = AVAILABLE_MODELS[current_model_key]
        
        await update.message.reply_text(
            f"🔮 **Текущая модель:** {model_info['name']}\n"
            f"📝 **Описание:** {model_info['description']}\n\n"
            "Изменить модель: /models"
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в current_command: {e}")
        await update.message.reply_text("⚠️ Ошибка при получении текущей модели")

async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Преобразует текст в голосовое сообщение"""
    try:
        user_id = update.effective_user.id
        update_user_stats(user_id)
        user_message = ' '.join(context.args)
        
        if not user_message:
            await update.message.reply_text(
                "🎤 **Голосовые ответы**\n\n"
                "Напишите текст после команды:\n"
                "`/voice Привет! Как дела?`\n\n"
                "Или просто напишите сообщение, и я отвечу текстом!"
            )
            return
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
        
        # Получаем ответ от AI
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
            'max_tokens': 500
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
            
            # Преобразуем ответ в голос
            voice_audio = await text_to_speech(ai_response)
            
            if voice_audio:
                await update.message.reply_voice(
                    voice=voice_audio,
                    caption=f"🎤 {model_name}: {ai_response}"
                )
                logger.info(f"🎤 Отправлен голосовой ответ пользователю {user_id}")
            else:
                await update.message.reply_text(f"🤖 {model_name}:\n\n{ai_response}")
        else:
            await update.message.reply_text("❌ Ошибка подключения к AI. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"❌ Ошибка в voice_command: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при создании голосового сообщения")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения"""
    try:
        user_id = update.effective_user.id
        user_message = update.message.text
        update_user_stats(user_id)
        
        # Получаем выбранную модель пользователя
        current_model_key = user_models.get(user_id, 'deepseek')
        model_id = AVAILABLE_MODELS[current_model_key]['id']
        model_name = AVAILABLE_MODELS[current_model_key]['name']
        
        # Показываем что бот "печатает"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
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
            # Без звёздочек в форматировании
            bot_response = f"🤖 {model_name}:\n\n{bot_response}"
            
            # Сохраняем в историю
            if user_id not in conversation_history:
                conversation_history[user_id] = []
            conversation_history[user_id].append({
                'question': user_message,
                'answer': bot_response,
                'timestamp': datetime.now()
            })
            
        else:
            bot_response = f"❌ Ошибка подключения к {model_name}. Попробуйте позже."
            
    except requests.exceptions.Timeout:
        bot_response = "⏰ Таймаут при подключении к AI. Попробуйте позже."
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_message: {e}")
        bot_response = f"⚠️ Ошибка в модели {model_name}: {str(e)}"
    
    await update.message.reply_text(bot_response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку"""
    try:
        update_user_stats(update.effective_user.id)
        
        help_text = (
            "🆘 **Помощь по улучшенному AI-боту:**\n\n"
            "**Основные команды:**\n"
            "/start - начать работу\n"
            "/models - список всех моделей AI\n" 
            "/model <ключ> - выбрать модель\n"
            "/current - текущая модель\n"
            "/voice <текст> - голосовой ответ\n"
            "/stats - ваша статистика\n"
            "/help - эта справка\n\n"
            "**Примеры:**\n"
            "`/model gpt` - переключиться на GPT\n"
            "`/model claude` - использовать Claude\n"
            "`/voice Привет!` - получить голосовой ответ\n"
            "`/stats` - посмотреть статистику\n\n"
            "**Просто напишите вопрос** - и я отвечу! 🚀"
        )
        
        await update.message.reply_text(help_text)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в help_command: {e}")
        await update.message.reply_text("⚠️ Ошибка при показе справки")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    error = context.error
    logger.error(f"🔥 Глобальная ошибка: {error}", exc_info=True)
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 Произошла непредвиденная ошибка. "
                "Попробуйте еще раз или используйте команду /help"
            )
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке сообщения об ошибке: {e}")

# ==================== ЗАПУСК БОТА ====================
def main():
    """Основная функция запуска бота"""
    print("🚀 Запуск улучшенного мульти-AI бота...")
    
    if not TELEGRAM_TOKEN:
        logger.error("❌ ОШИБКА: TELEGRAM_TOKEN не установлен!")
        return
    
    if not OPENROUTER_API_KEY:
        logger.error("❌ ОШИБКА: OPENROUTER_API_KEY не установлен!")
        return
    
    try:
        # Запускаем Flask в отдельном потоке
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        logger.info("✅ Flask сервер запущен на порту 5000")
        
        # Запускаем систему поддержания активности
        keep_bot_awake()
        logger.info("✅ Система keep-alive запущена")
        
        # Создаем и настраиваем бота
        app_bot = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Добавляем глобальный обработчик ошибок
        app_bot.add_error_handler(error_handler)
        
        # Добавляем обработчики команд
        handlers = [
            CommandHandler("start", start),
            CommandHandler("models", models_command),
            CommandHandler("model", model_command),
            CommandHandler("current", current_command),
            CommandHandler("voice", voice_command),
            CommandHandler("stats", stats_command),
            CommandHandler("help", help_command),
            MessageHandler(filters.VOICE, handle_voice_message),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ]
        
        for handler in handlers:
            app_bot.add_handler(handler)
        
        logger.info("✅ Все обработчики добавлены")
        logger.info("🤖 Бот успешно запущен и готов к работе!")
        
        # Запускаем бота
        app_bot.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при запуске бота: {e}")
        raise

if __name__ == '__main__':
    main()                     
