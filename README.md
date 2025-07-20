# Telegram Bot с поддержкой голосового режима

Telegram бот-ассистент с поддержкой нескольких моделей ИИ и голосового режима на базе Yandex Cloud TTS.

## Возможности

- 🤖 Поддержка множества моделей ИИ (GPT, Claude, Gemini, DeepSeek и др.)
- 🎤 Распознавание голосовых сообщений
- 🔊 Голосовой режим с синтезом речи через Yandex Cloud
- 🎭 Выбор голоса для синтеза речи
- 💬 Сохранение контекста беседы
- 🌐 Полная поддержка русского языка
- 📸 **Распознавание текста с изображений (OCR)** - Tesseract OCR с поддержкой русского языка
- 🎨 Генерация изображений по описанию

## Установка и настройка

### 1. Клонирование репозитория

```bash
git clone https://github.com/hleserg/neuroapi_talk_bot.git
cd neuroapi_talk_bot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Скопируйте файл `.env.example` в `.env` и заполните необходимые переменные:

```bash
cp .env.example .env
```

Отредактируйте файл `.env`:

```env
# Telegram Bot Token (получить у @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# NeuroAPI Key (получить на https://neuroapi.host)
NEUROAPI_API_KEY=your_neuroapi_key_here

# Hugging Face API Key (получить на https://huggingface.co/settings/tokens)
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Yandex Cloud Folder ID (получить в консоли Yandex Cloud)
YANDEX_FOLDER_ID=your_yandex_folder_id_here
```

### 4. Настройка Yandex Cloud для голосового режима

Для работы голосового режима необходимо настроить Yandex Cloud:

1. **Создайте аккаунт в Yandex Cloud** и получите Folder ID
2. **Установите Yandex Cloud CLI**:
   ```bash
   # Windows
   iex (New-Object System.Net.WebClient).DownloadString('https://storage.yandexcloud.net/yandexcloud-yc/install.ps1')
   
   # Linux/macOS
   curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
   ```

3. **Инициализируйте CLI**:
   ```bash
   yc init
   ```

4. **Настройте права доступа** для Speech Kit в консоли Yandex Cloud

### 5. Запуск бота

#### Локальный запуск
```bash
python bot.py
```

#### Запуск в Docker
```bash
# С Docker Compose (рекомендуется)
docker-compose up -d --build

# Или с обычным Docker
docker build -t telegram-voice-bot .
docker run -d --env-file .env telegram-voice-bot
```

Подробная инструкция по Docker: [DOCKER.md](DOCKER.md)

## Команды бота

### Основные команды
- `/start` - приветствие и описание возможностей
- `/help` - справка по всем командам
- `/clear` - очистить историю беседы

### Управление моделями
- `/models` - показать список доступных моделей
- `/model` - выбрать модель через меню
- `/current` - показать текущую модель

### Голосовые команды
- `/включить_голосовой_режим` - включить голосовые ответы
- `/выключить_голосовой_режим` - выключить голосовые ответы
- `/voice` - выбрать голос для синтеза речи
- `/voices` - показать список всех доступных голосов
- `/статус_голоса` - показать статус голосового режима

## Доступные голоса

Бот поддерживает следующие голоса Yandex Cloud:

- **Алёна** (alena) - женский голос, нейтральная интонация
- **Филипп** (filipp) - мужской голос, нейтральная интонация
- **Ермил** (ermil) - мужской голос, нейтральная интонация
- **Джейн** (jane) - женский голос, нейтральная интонация
- **Мадирус** (madirus) - мужской голос, нейтральная интонация
- **Омаж** (omazh) - женский голос, нейтральная интонация
- **Захар** (zahar) - мужской голос, нейтральная интонация

## Поддерживаемые модели ИИ

- GPT-4.1, GPT-4.1 Mini, GPT-4.1 Nano
- ChatGPT-4 Optimized, GPT-4O Mini
- Claude Opus 4, Claude Sonnet
- Gemini 2.5 Pro
- DeepSeek V3, DeepSeek R1
- Grok 3, Grok 3 Reasoner
- O3, O4 Mini

## Использование

1. **Текстовый режим**: Просто отправьте текстовое сообщение боту
2. **Голосовые сообщения**: Отправьте голосовое сообщение - бот распознает речь и ответит
3. **Голосовой режим**: Включите командой `/включить_голосовой_режим` - бот будет отвечать голосом
4. **Выбор голоса**: Используйте `/voice` для выбора предпочитаемого голоса
5. **Распознавание текста**: Отправьте изображение с текстом - бот извлечет и проанализирует содержимое
6. **Генерация изображений**: Используйте `/generate_image` для создания изображений по описанию

### OCR (Распознавание текста)

Бот автоматически распознает русский текст с отправленных изображений:
- Поддерживаются форматы: JPG, PNG, BMP, TIFF, WebP
- Оптимизировано для русского языка (кириллица)
- Автоматическое определение ориентации текста
- ИИ анализирует распознанный текст и предоставляет релевантные ответы

Подробная документация: [OCR_SETUP.md](OCR_SETUP.md)

## Структура проекта

```
my_new_bot/
├── bot.py              # Основной файл бота
├── neuroapi.py         # Клиент для работы с API
├── config.py           # Конфигурация и настройки
├── requirements.txt    # Зависимости Python
├── docker-compose.yml  # Docker Compose конфигурация
├── Dockerfile          # Docker образ для основного бота
├── .env.example       # Пример файла переменных окружения
├── .env               # Файл переменных окружения (создается вручную)
├── ocr_service/       # OCR сервис (Tesseract)
│   ├── Dockerfile     # Docker образ для OCR сервиса
│   ├── main.py        # FastAPI приложение OCR
│   └── requirements.txt # Зависимости OCR сервиса
├── logs/              # Директория для логов
├── OCR_SETUP.md       # Документация по OCR
└── README.md          # Этот файл
```

## Требования

- Python 3.8+
- Telegram Bot Token
- NeuroAPI Key
- Hugging Face API Key
- Yandex Cloud аккаунт и Folder ID
- Yandex Cloud CLI (для генерации IAM токенов)

## Лицензия

MIT License

## Поддержка

При возникновении проблем создайте issue в репозитории GitHub.
