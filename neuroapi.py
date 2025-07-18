import httpx
import logging
from typing import List, Dict, Any
from config import NEUROAPI_URL, NEUROAPI_API_KEY, MODELS, DEFAULT_MODEL, SYSTEM_PROMPT, MAX_CONTEXT_MESSAGES, WHISPER_API_URL, HUGGINGFACE_API_KEY

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
        """Транскрибация аудио с помощью Whisper API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.huggingface_api_key}",
                "Content-Type": "audio/ogg"
            }
            
            async with httpx.AsyncClient(timeout=240.0) as client:
                response = await client.post(
                    self.whisper_api_url,
                    headers=headers,
                    content=audio_data
                )
                response.raise_for_status()
            
            response_data = response.json()
            
            if "text" in response_data:
                return response_data["text"]
            else:
                logger.error(f"Неожиданный формат ответа от Whisper API: {response_data}")
                return "Ошибка: не удалось распознать речь."

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка при запросе к Whisper API: {e.response.status_code} - {e.response.text}")
            return "Ошибка: сервис распознавания речи временно недоступен."
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при запросе к Whisper API: {e}")
            return "Ошибка: проблема с сетевым подключением к сервису распознавания."
        except Exception as e:
            logger.error(f"Неожиданная ошибка при транскрибации аудио: {e}")
            return "Ошибка: произошла непредвиденная ошибка при обработке аудио."
    
    async def close(self):
        """Закрыть HTTP клиент"""
        await self.client.aclose()

# Глобальный экземпляр клиента
neuroapi_client = NeuroAPIClient()
