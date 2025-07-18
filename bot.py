import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from neuroapi import neuroapi_client
from config import BOT_TOKEN, MODELS, DEFAULT_MODEL, YANDEX_VOICES
import io

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализируем бот и диспетчер
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Определяем состояния для генерации изображений
class ImageGenerationStates(StatesGroup):
    waiting_for_prompt = State()

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

def create_voice_keyboard() -> InlineKeyboardMarkup:
    """Создать клавиатуру с кнопками голосов"""
    keyboard = []
    for voice_id, voice_info in YANDEX_VOICES.items():
        button = InlineKeyboardButton(
            text=f"{voice_info['name']}",
            callback_data=f"voice_{voice_id}"
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
• Генерировать изображения по описанию

Доступные команды:
/start - показать это приветствие
/clear - очистить историю беседы
/help - показать справку
/models - список доступных моделей
/model - выбрать модель
/current - показать текущую модель
/generate_image - сгенерировать изображение

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
    voice_enabled = neuroapi_client.is_voice_mode_enabled(user_id)
    current_voice = neuroapi_client.get_user_voice(user_id)
    voice_name = YANDEX_VOICES[current_voice]["name"]
    
    help_text = f"""
📚 Справка по боту

Текущая модель: {current_model_name}
Голосовой режим: {'🔊 Включен' if voice_enabled else '🔇 Выключен'}
Текущий голос: {voice_name}

Я умею:
• Отвечать на вопросы по любым темам
• Помогать с учебой и работой  
• Писать тексты и код
• Переводить тексты
• Объяснять сложные концепции
• Вести диалог с запоминанием контекста
• Отвечать голосовыми сообщениями
• Генерировать изображения по описанию

Основные команды:
/start - приветствие и описание возможностей
/clear - очистить историю диалога
/help - эта справка
/models - показать список доступных моделей
/model - выбрать модель
/current - показать текущую модель
/generate_image - сгенерировать изображение

Голосовые команды:
/voice_mode_on - включить голосовые ответы
/voice_mode_off - выключить голосовые ответы
/voice - выбрать голос
/voices - список всех голосов
/voice_status - показать статус голосового режима

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

@dp.message(Command("voice"))
async def cmd_voice(message: Message):
    """Показать меню выбора голоса"""
    keyboard = create_voice_keyboard()
    await message.answer(
        "Выберите голос для синтеза речи:",
        reply_markup=keyboard
    )

@dp.message(Command("voices"))
async def cmd_voices(message: Message):
    """Показать список доступных голосов"""
    user_id = message.from_user.id
    current_voice = neuroapi_client.get_user_voice(user_id)
    
    voices_text = "<b>🎤 Доступные голоса:</b>\n\n"
    for voice_id, voice_info in YANDEX_VOICES.items():
        current_mark = "✅ " if voice_id == current_voice else ""
        voices_text += f"{current_mark}<b>{voice_info['name']}</b> (<code>{voice_id}</code>)\n"
        voices_text += f"└ {voice_info['description']}\n\n"
    
    voices_text += "\nДля выбора голоса используйте команду /voice"
    
    await message.answer(voices_text, parse_mode="HTML")

@dp.message(Command("voice_mode_on"))
@dp.message(Command("включить_голосовой_режим"))
async def cmd_enable_voice_mode(message: Message):
    """Включить голосовой режим"""
    user_id = message.from_user.id
    neuroapi_client.set_voice_mode(user_id, True)
    
    current_voice = neuroapi_client.get_user_voice(user_id)
    voice_name = YANDEX_VOICES[current_voice]["name"]
    
    await message.answer(
        f"🔊 Голосовой режим включен!\n\n"
        f"Текущий голос: {voice_name}\n"
        f"Теперь я буду отвечать голосовыми сообщениями.\n\n"
        f"Для смены голоса используйте /voice\n"
        f"Для отключения используйте /voice_mode_off"
    )

@dp.message(Command("voice_mode_off"))
@dp.message(Command("выключить_голосовой_режим"))
async def cmd_disable_voice_mode(message: Message):
    """Выключить голосовой режим"""
    user_id = message.from_user.id
    neuroapi_client.set_voice_mode(user_id, False)
    
    await message.answer(
        "🔇 Голосовой режим выключен.\n"
        "Теперь я буду отвечать текстовыми сообщениями."
    )

@dp.message(Command("voice_status"))
@dp.message(Command("статус_голоса"))
async def cmd_voice_status(message: Message):
    """Показать статус голосового режима"""
    user_id = message.from_user.id
    voice_enabled = neuroapi_client.is_voice_mode_enabled(user_id)
    current_voice = neuroapi_client.get_user_voice(user_id)
    voice_info = YANDEX_VOICES[current_voice]
    
    status_text = f"""
<b>🎤 Статус голосового режима:</b>

• Режим: {'🔊 Включен' if voice_enabled else '🔇 Выключен'}
• Текущий голос: <b>{voice_info['name']}</b>
• Описание: {voice_info['description']}

Команды:
/voice_mode_on или /включить_голосовой_режим - включить голосовые ответы
/voice_mode_off или /выключить_голосовой_режим - выключить голосовые ответы
/voice - выбрать голос
/voices - список всех голосов
"""
    await message.answer(status_text, parse_mode="HTML")

@dp.message(Command("generate_image"))
async def cmd_generate_image(message: Message, state: FSMContext):
    """Команда для генерации изображения"""
    await message.answer("🎨 Опишите изображение для генерации:")
    await state.set_state(ImageGenerationStates.waiting_for_prompt)

@dp.message(ImageGenerationStates.waiting_for_prompt)
async def process_image_prompt(message: Message, state: FSMContext):
    """Обработка описания для генерации изображения"""
    user_id = message.from_user.id
    prompt = message.text
    
    if not prompt:
        await message.answer("Пожалуйста, отправьте текстовое описание изображения.")
        return
    
    # Отправляем сообщение о начале генерации
    processing_message = await message.answer("🎨 Генерирую изображение, пожалуйста подождите...")
    
    try:
        await bot.send_chat_action(chat_id=message.chat.id, action="upload_photo")
        
        # Генерируем изображение
        image_data = await neuroapi_client.generate_image(prompt)
        
        if image_data:
            # Отправляем изображение
            from aiogram.types import BufferedInputFile
            
            image_file = BufferedInputFile(
                file=image_data,
                filename="generated_image.png"
            )
            
            await processing_message.delete()
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=image_file,
                caption=f"🎨 Сгенерированное изображение по запросу:\n<i>{prompt}</i>",
                parse_mode="HTML"
            )
        else:
            await processing_message.edit_text(
                "❌ Произошла ошибка при генерации изображения. "
                "Попробуйте еще раз или измените описание."
            )
    
    except Exception as e:
        logger.error(f"Ошибка при генерации изображения для пользователя {user_id}: {e}")
        await processing_message.edit_text(
            "❌ Произошла ошибка при генерации изображения. Попробуйте позже."
        )
    
    finally:
        # Сбрасываем состояние
        await state.clear()

@dp.callback_query(lambda c: c.data.startswith('voice_'))
async def process_voice_selection(callback_query: CallbackQuery):
    """Обработчик выбора голоса через инлайн-кнопки"""
    try:
        # Получаем ID выбранного голоса из callback_data
        voice_id = callback_query.data.replace('voice_', '')
        user_id = callback_query.from_user.id
        
        if voice_id not in YANDEX_VOICES:
            await callback_query.answer("❌ Ошибка: голос не найден")
            return
        
        # Устанавливаем выбранный голос
        neuroapi_client.set_user_voice(user_id, voice_id)
        voice_name = YANDEX_VOICES[voice_id]["name"]
        
        # Отвечаем пользователю
        await callback_query.message.edit_text(
            f"✅ Голос успешно изменен на {voice_name}.\n"
            f"Описание: {YANDEX_VOICES[voice_id]['description']}"
        )
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выборе голоса: {e}")
        await callback_query.answer("❌ Произошла ошибка при выборе голоса")

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
        
        # Проверяем, включен ли голосовой режим
        if neuroapi_client.is_voice_mode_enabled(user_id):
            # Удаляем сообщение с точками
            await typing_message.delete()
            
            # Отправляем сообщение о генерации голоса
            voice_message = await message.answer("🎤 Генерирую голосовое сообщение...")
            
            # Получаем голос пользователя
            user_voice = neuroapi_client.get_user_voice(user_id)
            
            # Синтезируем речь
            audio_data = await neuroapi_client.synthesize_speech(response, user_voice)
            
            if audio_data:
                # Отправляем голосовое сообщение
                from aiogram.types import BufferedInputFile
                
                audio_file = BufferedInputFile(
                    file=audio_data,
                    filename="voice_response.ogg"
                )
                
                await voice_message.delete()
                await bot.send_voice(
                    chat_id=message.chat.id,
                    voice=audio_file
                )
                
                # Также отправляем текстовую версию для удобства
                text_prefix = "<i>Текст:</i> "
                max_length = 4096 - len(text_prefix)
                
                if len(response) > max_length:
                    # Разбиваем на части
                    for i in range(0, len(response), max_length):
                        chunk = response[i:i+max_length]
                        if i == 0:
                            await message.answer(f"{text_prefix}{chunk}", parse_mode="HTML")
                        else:
                            await message.answer(chunk)
                else:
                    await message.answer(f"{text_prefix}{response}", parse_mode="HTML")
            else:
                # Если не удалось синтезировать речь, отправляем текстом
                await voice_message.edit_text(
                    f"❌ Не удалось синтезировать речь. Отправляю текстом:\n\n{response}"
                )
        else:
            # Обычный текстовый режим
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
        
        # Проверяем, включен ли голосовой режим
        if neuroapi_client.is_voice_mode_enabled(user_id):
            # Удаляем сообщение с точками
            await typing_message.delete()
            
            # Отправляем сообщение о генерации голоса
            voice_message = await message.answer("🎤 Генерирую голосовое сообщение...")
            
            # Получаем голос пользователя
            user_voice = neuroapi_client.get_user_voice(user_id)
            
            # Синтезируем речь
            audio_data = await neuroapi_client.synthesize_speech(response, user_voice)
            
            if audio_data:
                # Отправляем голосовое сообщение
                from aiogram.types import BufferedInputFile
                
                audio_file = BufferedInputFile(
                    file=audio_data,
                    filename="voice_response.ogg"
                )
                
                await voice_message.delete()
                await bot.send_voice(
                    chat_id=message.chat.id,
                    voice=audio_file
                )
                
                # Также отправляем текстовую версию для удобства
                text_prefix = "<i>Текст:</i> "
                max_length = 4096 - len(text_prefix)
                
                if len(response) > max_length:
                    # Разбиваем на части
                    for i in range(0, len(response), max_length):
                        chunk = response[i:i+max_length]
                        if i == 0:
                            await message.answer(f"{text_prefix}{chunk}", parse_mode="HTML")
                        else:
                            await message.answer(chunk)
                else:
                    await message.answer(f"{text_prefix}{response}", parse_mode="HTML")
            else:
                # Если не удалось синтезировать речь, отправляем текстом
                await voice_message.edit_text(
                    f"❌ Не удалось синтезировать речь. Отправляю текстом:\n\n{response}"
                )
        else:
            # Обычный текстовый режим
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
