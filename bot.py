import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from neuroapi import neuroapi_client
from config import BOT_TOKEN, MODELS, DEFAULT_MODEL

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализируем бот и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def create_model_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру с кнопками моделей"""
    keyboard = []
    for model_id, model_info in MODELS.items():
        button = InlineKeyboardButton(
            text=f"{model_info['name']}",
            callback_data=f"model_{model_id}"
        )
        keyboard.append([button])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_name = message.from_user.first_name or "Пользователь"
    welcome_text = f"""
Привет, {user_name}! 👋

Я бот-ассистент с поддержкой нескольких моделей ИИ. Я могу:
• Отвечать на ваши вопросы
• Вести диалог с сохранением контекста
• Помогать с различными задачами
• Общаться на русском языке

Доступные команды:
/start - показать это приветствие
/clear - очистить историю беседы
/help - показать справку
/models - список доступных моделей
/model - выбрать модель
/current - показать текущую модель

Текущая модель: {MODELS[DEFAULT_MODEL]["name"]}
"""
    await message.answer(welcome_text)

@dp.message(Command("models"))
async def cmd_models(message: Message):
    """Показать список доступных моделей"""
    user_id = message.from_user.id
    current_model = neuroapi_client._get_user_model(user_id)
    
    models_text = "<b>📋 Доступные модели:</b>\n\n"
    for model_id, model_info in MODELS.items():
        current_mark = "✅ " if model_id == current_model else ""
        models_text += f"{current_mark}<b>{model_info['name']}</b> (<code>{model_id}</code>)\n"
        models_text += f"└ {model_info['description']}\n\n"
    
    models_text += "\nДля выбора модели используйте команду:\n<code>/model [id_модели]</code>"
    
    await message.answer(models_text, parse_mode="HTML")

@dp.message(Command("model"))
async def cmd_model(message: Message):
    """Показать меню выбора модели"""
    keyboard = create_model_keyboard()
    await message.answer(
        "Выберите модель для общения:",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith('model_'))
async def process_model_selection(callback_query: CallbackQuery):
    """Обработчик выбора модели через инлайн-кнопки"""
    try:
        # Получаем ID выбранной модели из callback_data
        model_id = callback_query.data.replace('model_', '')
        user_id = callback_query.from_user.id
        
        if model_id not in MODELS:
            await callback_query.answer("❌ Ошибка: модель не найдена")
            return
        
        # Устанавливаем выбранную модель
        neuroapi_client.set_user_model(user_id, model_id)
        model_name = MODELS[model_id]["name"]
        
        # Отвечаем пользователю
        await callback_query.message.edit_text(
            f"✅ Модель успешно изменена на {model_name}.\n"
            "Контекст беседы сохранен."
        )
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выборе модели: {e}")
        await callback_query.answer("❌ Произошла ошибка при выборе модели")

@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    """Обработчик команды /clear - очистка контекста беседы"""
    user_id = message.from_user.id
    neuroapi_client.clear_context(user_id)
    await message.answer("✅ История беседы очищена. Можем начать заново!")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    user_id = message.from_user.id
    current_model = neuroapi_client._get_user_model(user_id)
    current_model_name = MODELS[current_model]["name"]
    
    help_text = f"""
📚 Справка по боту

Текущая модель: {current_model_name}

Я умею:
• Отвечать на вопросы по любым темам
• Помогать с учебой и работой  
• Писать тексты и код
• Переводить тексты
• Объяснять сложные концепции
• Вести диалог с запоминанием контекста

Команды:
/start - приветствие и описание возможностей
/clear - очистить историю диалога
/help - эта справка
/models - показать список доступных моделей
/model [id] - выбрать модель
/current - показать текущую модель

Просто напишите мне любое сообщение, и я отвечу!
"""
    await message.answer(help_text)

@dp.message(Command("current"))
async def cmd_current(message: Message):
    """Показать текущую выбранную модель"""
    user_id = message.from_user.id
    current_model = neuroapi_client._get_user_model(user_id)
    model_info = MODELS[current_model]
    
    current_text = f"""
<b>Текущая модель:</b>

• Название: <b>{model_info['name']}</b>
• ID: <code>{current_model}</code>
• Описание: {model_info['description']}
• Максимальная длина: {model_info['max_tokens']} токенов
• Температура: {model_info['temperature']}

Для смены модели используйте команду /model
"""
    await message.answer(current_text, parse_mode="HTML")

@dp.message(F.voice)
async def handle_voice_message(message: Message):
    """Обработчик голосовых сообщений"""
    user_id = message.from_user.id
    
    # Отправляем сообщение о том, что аудио получено
    processing_message = await message.answer("🎤 Аудио получено, обрабатываю...")
    
    try:
        # Скачиваем аудиофайл
        voice_file = await bot.get_file(message.voice.file_id)
        voice_io = await bot.download_file(voice_file.file_path)
        
        # Распознаем речь
        transcribed_text = await neuroapi_client.transcribe_audio(voice_io.read())
        
        if transcribed_text.startswith("Ошибка:"):
            await processing_message.edit_text(transcribed_text)
            return
            
        # Показываем распознанный текст
        await processing_message.edit_text(f"<i>Распознанный текст:</i>\n{transcribed_text}", parse_mode="HTML")
        
        # Отправляем "печатает..."
        typing_message = await message.answer("...")
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Генерируем ответ
        response = await neuroapi_client.generate_response(user_id, transcribed_text)
        
        # Отправляем ответ
        if len(response) > 4096:
            await typing_message.delete()
            for i in range(0, len(response), 4096):
                await message.answer(response[i:i+4096])
        else:
            await typing_message.edit_text(response)

    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения от {user_id}: {e}")
        await processing_message.edit_text("Произошла ошибка при обработке вашего голосового сообщения.")


@dp.message(F.text)
async def handle_text_message(message: Message):
    """Обработчик всех текстовых сообщений"""
    user_id = message.from_user.id
    user_text = message.text
    
    if not user_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Отправляем сообщение с точками для показа процесса "печати"
    typing_message = await message.answer("...")
    
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # Получаем ответ от выбранной модели
        response = await neuroapi_client.generate_response(user_id, user_text)
        
        current_model = neuroapi_client._get_user_model(user_id)
        if current_model in ['gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano']:
            parse_mode = "Markdown"
        else:
            parse_mode = None
        
        # Заменяем сообщение с точками на финальный ответ
        if len(response) > 4096:
            # Если сообщение слишком длинное, удаляем сообщение с точками и отправляем по частям
            await typing_message.delete()
            for i in range(0, len(response), 4096):
                await message.answer(response[i:i+4096])
        else:
            await typing_message.edit_text(response)

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения от пользователя {user_id}: {e}")
        try:
            await typing_message.edit_text(
                "Извините, произошла ошибка при обработке вашего сообщения. "
                "Попробуйте еще раз или используйте /clear для сброса контекста."
            )
        except:
            await message.answer(
                "Извините, произошла ошибка при обработке вашего сообщения. "
                "Попробуйте еще раз или используйте /clear для сброса контекста."
            )

async def main():
    """Основная функция для запуска бота"""
    logger.info("Запуск бота...")
    
    try:
        # Удаляем вебхуки (на случай если они были установлены ранее)
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем поллинг
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Закрываем HTTP клиент NeuroAPI
        await neuroapi_client.close()
        # Закрываем сессию бота
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
