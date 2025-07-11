import os
from dotenv import load_dotenv
from typing import Dict, Any

# Загружаем переменные окружения из файла .env
load_dotenv()

# Конфигурация бота
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
NEUROAPI_API_KEY = os.getenv('NEUROAPI_API_KEY')

# Проверяем наличие необходимых токенов
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

if not NEUROAPI_API_KEY:
    raise ValueError("NEUROAPI_API_KEY не найден в переменных окружения")

# URL API NeuroAPI
NEUROAPI_URL = "https://neuroapi.host/v1/chat/completions"

# Конфигурации моделей
MODELS: Dict[str, Dict[str, Any]] = {
    "gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "model": "gemini-2.5-pro",
        "max_tokens": 50000,
        "temperature": 0.7,
        "description": "Мощная модель от Google с широкими возможностями"
    },
    "gpt-4.1": {
        "name": "GPT-4.1",
        "model": "gpt-4.1",
        "max_tokens": 32000,
        "temperature": 0.7,
        "description": "Передовая модель с расширенным контекстным окном"
    },
    "claude-opus-4-thinking-all": {
        "name": "Claude Opus 4",
        "model": "claude-opus-4-thinking-all",
        "max_tokens": 200000,
        "temperature": 0.7,
        "description": "Продвинутая модель Claude с улучшенными аналитическими способностями"
    },
    "chatgpt-4o-latest": {
        "name": "ChatGPT-4 Optimized",
        "model": "chatgpt-4o-latest",
        "max_tokens": 16000,
        "temperature": 0.7,
        "description": "Оптимизированная версия ChatGPT-4 с улучшенной производительностью"
    },
    "gpt-4.1-mini": {
        "name": "GPT-4.1 Mini",
        "model": "gpt-4.1-mini",
        "max_tokens": 16000,
        "temperature": 0.7,
        "description": "Компактная версия GPT-4.1 с хорошим балансом скорости и качества"
    },
    "gpt-4.1-nano": {
        "name": "GPT-4.1 Nano",
        "model": "gpt-4.1-nano",
        "max_tokens": 8000,
        "temperature": 0.7,
        "description": "Сверхлегкая версия GPT-4.1 для быстрых ответов"
    },
    "gpt-4o-mini": {
        "name": "GPT-4O Mini",
        "model": "gpt-4o-mini",
        "max_tokens": 16000,
        "temperature": 0.7,
        "description": "Компактная версия оптимизированного GPT-4"
    },
    "deepseek-v3-250324": {
        "name": "DeepSeek V3",
        "model": "deepseek-v3-250324",
        "max_tokens": 16000,
        "temperature": 0.7,
        "description": "Новая версия DeepSeek с улучшенным пониманием контекста"
    },
    "deepseek-r1-250528": {
        "name": "DeepSeek R1",
        "model": "deepseek-r1-250528",
        "max_tokens": 8192,
        "temperature": 0.7,
        "description": "Модель с глубоким пониманием контекста"
    },
    "grok-3-all": {
        "name": "Grok 3",
        "model": "grok-3-all",
        "max_tokens": 128000,
        "temperature": 0.7,
        "description": "Универсальная модель Grok с широким спектром возможностей"
    },
    "grok-3-reasoner": {
        "name": "Grok 3 Reasoner",
        "model": "grok-3-reasoner",
        "max_tokens": 128000,
        "temperature": 0.7,
        "description": "Специализированная версия Grok для сложных рассуждений"
    },
    "o4-mini": {
        "name": "O4 Mini",
        "model": "o4-mini",
        "max_tokens": 4096,
        "temperature": 0.7,
        "description": "Компактная и быстрая модель"
    },
    "o3": {
        "name": "O3",
        "model": "o3",
        "max_tokens": 4096,
        "temperature": 0.7,
        "description": "Универсальная модель для различных задач"
    },
    "claude-sonnet-4-thinking-all": {
        "name": "Claude Sonnet",
        "model": "claude-sonnet-4-thinking-all",
        "max_tokens": 12000,
        "temperature": 0.7,
        "description": "Продвинутая модель с аналитическими способностями"
    }
}

# Модель по умолчанию
DEFAULT_MODEL = "gpt-4.1-mini"

# Системный промпт для моделей
SYSTEM_PROMPT = """
Ты - умный и дружелюбный помощник, который общается на русском языке. 
Отвечай всегда на русском языке, независимо от языка вопроса.
Будь вежливым, полезным и информативным. 
Если не знаешь ответа на вопрос, честно признайся в этом.
Старайся давать развернутые и понятные ответы.
Поддерживай дружелюбную беседу и помогай пользователю во всех его вопросах.
"""

# Максимальное количество сообщений в контексте для каждого пользователя
MAX_CONTEXT_MESSAGES = 500
