import httpx
import logging
import subprocess
import io
from typing import List, Dict, Any, Optional
from config import (
    NEUROAPI_URL, NEUROAPI_API_KEY, MODELS, DEFAULT_MODEL, SYSTEM_PROMPT, 
    MAX_CONTEXT_MESSAGES, WHISPER_API_URL, HUGGINGFACE_API_KEY,
    YANDEX_TTS_URL, YANDEX_VOICES, DEFAULT_VOICE, YANDEX_FOLDER_ID,
    KANDINSKY_SERVICE_URL, OCR_SERVICE_URL, WHISPER_SERVICE_URL
)

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeuroAPIClient:
    def __init__(self):
        """Инициализация клиента NeuroAPI"""
        self.api_url = NEUROAPI_URL
        self.api_key = NEUROAPI_API_KEY
        self.huggingface_api_key = HUGGINGFACE_API_KEY
        self.whisper_api_url = WHISPER_API_URL
        
        # Хранилище контекста и выбранной модели для каждого пользователя
        self.user_contexts: Dict[int, List[Dict[str, str]]] = {}
        self.user_models: Dict[int, str] = {}
        
        # Хранилище настроек голосового режима для каждого пользователя
        self.user_voice_mode: Dict[int, bool] = {}
        self.user_voices: Dict[int, str] = {}
        
        # HTTP клиент
        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            },
            timeout=240.0
        )

    def _get_user_context(self, user_id: int) -> List[Dict[str, str]]:
        """Получить контекст беседы для пользователя"""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = []
        return self.user_contexts[user_id]
    
    def _get_user_model(self, user_id: int) -> str:
        """Получить текущую модель пользователя"""
        return self.user_models.get(user_id, DEFAULT_MODEL)
    
    def _add_to_context(self, user_id: int, role: str, content: str):
        """Добавить сообщение в контекст пользователя"""
        context = self._get_user_context(user_id)
        context.append({"role": role, "content": content})
        
        # Ограничиваем размер контекста
        if len(context) > MAX_CONTEXT_MESSAGES:
            if context[0]["role"] == "system":
                context.pop(1)
            else:
                context.pop(0)
    
    def set_user_model(self, user_id: int, model_id: str) -> bool:
        """Установить модель для пользователя"""
        if model_id in MODELS:
            self.user_models[user_id] = model_id
            return True
        return False
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Получить список доступных моделей"""
        return MODELS
    
    def clear_context(self, user_id: int):
        """Очистить контекст беседы для пользователя"""
        if user_id in self.user_contexts:
            self.user_contexts[user_id] = []
            logger.info(f"Контекст для пользователя {user_id} очищен")
    
    def _prepare_messages(self, user_id: int, new_message: str) -> List[Dict[str, str]]:
        """Подготовить список сообщений для отправки в API"""
        context = self._get_user_context(user_id)
        
        # Всегда начинаем с системного промпта
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Добавляем существующий контекст
        messages.extend(context)
        
        # Добавляем новое сообщение пользователя
        messages.append({"role": "user", "content": new_message})
        
        return messages
    
    async def generate_response(self, user_id: int, message: str) -> str:
        """Генерация ответа с учетом контекста беседы"""
        try:
            # Получаем модель пользователя и её настройки
            model_id = self._get_user_model(user_id)
            model_config = MODELS[model_id]
            
            # Подготавливаем сообщения для API
            messages = self._prepare_messages(user_id, message)
            
            # Формируем запрос к API
            payload = {
                "model": model_config["model"],
                "messages": messages,
                "max_tokens": model_config["max_tokens"],
                "temperature": model_config["temperature"]
            }
            
            # Отправляем запрос
            response = await self.client.post(self.api_url, json=payload)
            response.raise_for_status()
            
            # Парсим ответ
            response_data = response.json()
            
            if "choices" in response_data and len(response_data["choices"]) > 0:
                assistant_message = response_data["choices"][0]["message"]["content"]
                
                # Добавляем сообщения в контекст
                self._add_to_context(user_id, "user", message)
                self._add_to_context(user_id, "assistant", assistant_message)
                
                return assistant_message
            else:
                logger.error(f"Неожиданный формат ответа от API: {response_data}")
                return "Извините, произошла ошибка при получении ответа от ИИ."
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при запросе к API: {e.response.status_code} - {e.response.text}")
            return "Извините, произошла ошибка при обращении к сервису ИИ. Попробуйте позже."
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при запросе к API: {e}")
            return "Извините, произошла ошибка сети. Проверьте подключение к интернету."
        except Exception as e:
            logger.error(f"Неожиданная ошибка при генерации ответа: {e}")
            return "Извините, произошла неожиданная ошибка. Попробуйте еще раз."

    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Транскрибация аудио с помощью локального Whisper Medium сервиса"""
        try:
            # Формируем данные для отправки
            files = {'file': ('voice.ogg', audio_data, 'audio/ogg')}
            
            async with httpx.AsyncClient(timeout=240.0) as client:
                response = await client.post(
                    f"{WHISPER_SERVICE_URL}/transcribe",
                    files=files
                )
                response.raise_for_status()
            
            response_data = response.json()
            
            if response_data.get("success") and "text" in response_data:
                transcribed_text = response_data["text"].strip()
                if transcribed_text:
                    logger.info(f"Whisper транскрибация успешна: '{transcribed_text[:100]}...'")
                    return transcribed_text
                else:
                    logger.warning("Whisper вернул пустой текст")
                    return "Ошибка: не удалось распознать речь в аудио."
            else:
                logger.error(f"Неожиданный формат ответа от Whisper сервиса: {response_data}")
                return "Ошибка: не удалось распознать речь."

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при запросе к Whisper сервису: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 503:
                return "Ошибка: Whisper сервис еще загружается. Попробуйте через минуту."
            return "Ошибка: сервис распознавания речи временно недоступен."
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при запросе к Whisper сервису: {e}")
            return "Ошибка: проблема с подключением к сервису распознавания речи."
        except Exception as e:
            logger.error(f"Неожиданная ошибка при транскрибации аудио: {e}")
            return "Ошибка: произошла непредвиденная ошибка при обработке аудио."

    def fetch_iam_token(self) -> Optional[str]:
        """Получить IAM токен для Yandex Cloud через yc CLI"""
        try:
            result = subprocess.run(
                ['yc', 'iam', 'create-token'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                timeout=20
            )
            if result.returncode == 0:
                token = result.stdout.strip()
                if token:
                    logging.info('IAM токен успешно получен через yc CLI')
                    return token
                else:
                    logging.error('Пустой IAM токен от yc CLI')
            else:
                logging.error(f'Ошибка yc CLI: {result.stderr}')
        except Exception as e:
            logging.error(f'Ошибка получения IAM токена: {e}')
        return None

    async def synthesize_speech(self, text: str, voice: str = DEFAULT_VOICE) -> Optional[bytes]:
        """Синтез речи с помощью Yandex Cloud TTS"""
        try:
            # Получаем IAM токен
            iam_token = self.fetch_iam_token()
            if not iam_token:
                logger.error("Не удалось получить IAM токен для Yandex Cloud")
                return None

            # Проверяем наличие folder_id
            if not YANDEX_FOLDER_ID:
                logger.error("YANDEX_FOLDER_ID не установлен в переменных окружения")
                return None

            # Получаем настройки голоса
            voice_config = YANDEX_VOICES.get(voice, YANDEX_VOICES[DEFAULT_VOICE])
            
            # Подготавливаем данные для запроса
            data = {
                'text': text,
                'lang': 'ru-RU',
                'voice': voice_config['voice'],
                'emotion': voice_config['emotion'],
                'speed': '1.0',
                'format': 'oggopus',
                'folderId': YANDEX_FOLDER_ID
            }

            headers = {
                'Authorization': f'Bearer {iam_token}',
            }

            # Отправляем запрос к Yandex TTS
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    YANDEX_TTS_URL,
                    headers=headers,
                    data=data
                )
                response.raise_for_status()

            # Возвращаем аудио данные
            return response.content

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при запросе к Yandex TTS: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при запросе к Yandex TTS: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при синтезе речи: {e}")
            return None

    def is_voice_mode_enabled(self, user_id: int) -> bool:
        """Проверить, включен ли голосовой режим для пользователя"""
        return self.user_voice_mode.get(user_id, False)

    def set_voice_mode(self, user_id: int, enabled: bool):
        """Включить/выключить голосовой режим для пользователя"""
        self.user_voice_mode[user_id] = enabled
        logger.info(f"Голосовой режим для пользователя {user_id}: {'включен' if enabled else 'выключен'}")

    def get_user_voice(self, user_id: int) -> str:
        """Получить текущий голос пользователя"""
        return self.user_voices.get(user_id, DEFAULT_VOICE)

    def set_user_voice(self, user_id: int, voice_id: str) -> bool:
        """Установить голос для пользователя"""
        if voice_id in YANDEX_VOICES:
            self.user_voices[user_id] = voice_id
            logger.info(f"Голос для пользователя {user_id} установлен: {YANDEX_VOICES[voice_id]['name']}")
            return True
        return False

    def get_available_voices(self) -> Dict[str, Dict[str, Any]]:
        """Получить список доступных голосов"""
        return YANDEX_VOICES

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """Генерация изображения с помощью Kandinsky 2.2 через локальный сервис"""
        try:
            payload = {
                "prompt": prompt,
                "negative_prompt": "low quality, bad quality, blurry, pixelated",
                "width": 768,
                "height": 768,
                "num_inference_steps": 50,
                "guidance_scale": 4.0,
                "prior_guidance_scale": 1.0
            }
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{KANDINSKY_SERVICE_URL}/generate",
                    json=payload
                )
                response.raise_for_status()
            
            # Возвращаем байты изображения
            return response.content
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при генерации изображения через Kandinsky: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при запросе к Kandinsky сервису: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при генерации изображения через Kandinsky: {e}")
            return None

    async def extract_text_from_image(self, image_data: bytes) -> str:
        """Извлечение текста из изображения с помощью PaddleOCR сервиса"""
        try:
            # Формируем данные для отправки
            files = {'file': ('image.jpg', image_data, 'image/jpeg')}
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{OCR_SERVICE_URL}/ocr/extract_text_simple",
                    files=files
                )
                response.raise_for_status()
            
            response_data = response.json()
            
            if response_data.get("success"):
                return response_data.get("text", "")
            else:
                logger.error("OCR сервис вернул ошибку")
                return "Ошибка: не удалось распознать текст на изображении."

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при запросе к OCR сервису: {e.response.status_code} - {e.response.text}")
            return "Ошибка: OCR сервис временно недоступен."
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при запросе к OCR сервису: {e}")
            return "Ошибка: проблема с подключением к OCR сервису."
        except Exception as e:
            logger.error(f"Неожиданная ошибка при распознавании изображения: {e}")
            return "Ошибка: произошла непредвиденная ошибка при обработке изображения."
    
    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()

# Глобальный экземпляр клиента
neuroapi_client = NeuroAPIClient()
