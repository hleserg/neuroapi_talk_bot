# Настройка Whisper Medium сервиса

Этот документ описывает настройку и использование локального сервиса распознавания речи на основе OpenAI Whisper Medium модели.

## Обзор

Whisper сервис заменяет внешний API Hugging Face на локальную модель Whisper Medium, обеспечивая:
- Полную конфиденциальность обработки аудио
- Более быстрое распознавание речи
- Независимость от внешних сервисов
- Поддержку GPU для ускорения
- Высокое качество распознавания русской речи

## Архитектура

```
Telegram Bot → Whisper Service (Docker) → Whisper Medium Model
```

## Требования к системе

### Минимальные требования
- **CPU**: 4 ядра
- **RAM**: 6GB свободной памяти
- **Место**: 3GB для модели Whisper Medium
- **Docker**: версия 20.10+
- **Docker Compose**: версия 2.0+

### Рекомендуемые требования
- **GPU**: NVIDIA GPU с поддержкой CUDA (для ускорения)
- **VRAM**: 4GB+ (при использовании GPU)
- **RAM**: 8GB+ свободной памяти
- **CPU**: 6+ ядер

## Файлы сервиса

### 1. whisper_service/Dockerfile
```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Предварительная загрузка модели Whisper Medium
RUN python -c "import whisper; whisper.load_model('medium')"

EXPOSE 8003

CMD ["python", "main.py"]
```

### 2. whisper_service/requirements.txt
```
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
openai-whisper==20231117
torch==2.1.0
torchaudio==2.1.0
numpy==1.24.3
pydub==0.25.1
```

### 3. whisper_service/main.py
FastAPI сервер с эндпоинтами для транскрибации аудио.

## Настройка

### 1. Переменные окружения

Добавьте в `.env` файл:
```bash
# Whisper сервис (опционально - URL будет автоматически установлен в Docker)
WHISPER_SERVICE_URL=http://localhost:8003
```

### 2. Docker Compose конфигурация

Сервис автоматически добавлен в `docker-compose.yml`:

```yaml
whisper-service:
  build: ./whisper_service
  container_name: whisper-service
  restart: unless-stopped
  environment:
    - PYTHONUNBUFFERED=1
    - CUDA_LAUNCH_BLOCKING=1
  networks:
    - bot-network
  ports:
    - "8003:8003"
  healthcheck:
    test: ["CMD", "python3", "-c", "import requests; requests.get('http://localhost:8003/health', timeout=10)"]
    interval: 60s
    timeout: 30s
    retries: 3
  deploy:
    resources:
      limits:
        memory: 6G
        cpus: '3.0'
      reservations:
        memory: 3G
        cpus: '1.5'
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

## Запуск

### 1. Сборка и запуск через Docker Compose

```bash
# Сборка всех сервисов
docker-compose build

# Запуск всех сервисов
docker-compose up -d

# Просмотр логов Whisper сервиса
docker-compose logs -f whisper-service
```

### 2. Запуск только Whisper сервиса

```bash
# Сборка Whisper сервиса
docker-compose build whisper-service

# Запуск только Whisper сервиса
docker-compose up -d whisper-service
```

## API эндпоинты

### Основные эндпоинты

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Информация о сервисе |
| GET | `/health` | Проверка работоспособности |
| POST | `/transcribe` | Транскрибация аудио (полный ответ) |
| POST | `/transcribe_simple` | Транскрибация аудио (только текст) |

### Примеры использования

#### 1. Проверка статуса
```bash
curl http://localhost:8003/health
```

Ответ:
```json
{
  "status": "healthy",
  "device": "cuda",
  "model_loaded": true
}
```

#### 2. Транскрибация аудио
```bash
curl -X POST \
  -F "file=@voice.ogg" \
  http://localhost:8003/transcribe
```

Ответ:
```json
{
  "success": true,
  "text": "Привет, как дела?",
  "language": "ru",
  "segments_count": 1
}
```

## Мониторинг

### Проверка работы сервиса

```bash
# Статус контейнера
docker-compose ps whisper-service

# Логи
docker-compose logs whisper-service

# Использование ресурсов
docker stats whisper-service
```

### Health check

Сервис автоматически проверяется каждые 60 секунд:
```bash
# Ручная проверка
curl http://localhost:8003/health
```

## Производительность

### Время загрузки модели
- **CPU**: 30-60 секунд
- **GPU**: 15-30 секунд

### Время транскрибации
- **CPU**: 2-5 секунд для 10-секундного аудио
- **GPU**: 0.5-2 секунды для 10-секундного аудио

### Потребление ресурсов
- **RAM**: 3-4GB при загрузке модели
- **VRAM**: 2-3GB при использовании GPU
- **CPU**: зависит от длительности аудио

## Поддерживаемые форматы

### Аудио форматы
- OGG (рекомендуется для Telegram)
- MP3
- WAV
- M4A
- FLAC

### Качество распознавания
- **Русский язык**: отличное
- **Английский язык**: отличное
- **Другие языки**: хорошее (автоопределение)

## Оптимизация

### Для GPU
1. Убедитесь, что установлен NVIDIA Container Toolkit
2. Проверьте доступность GPU: `nvidia-smi`
3. В логах должно быть: "Используется устройство: cuda"

### Для CPU
1. Увеличьте количество CPU ядер в docker-compose.yml
2. Уменьшите memory limits если нужно

### Настройки модели
В `main.py` можно изменить параметры транскрибации:
```python
result = model.transcribe(
    audio_path,
    language="ru",  # Язык (auto для автоопределения)
    temperature=0.0,  # Детерминистичность (0.0-1.0)
    beam_size=5,  # Качество vs скорость
    best_of=5  # Количество попыток
)
```

## Устранение неполадок

### Частые проблемы

#### 1. Модель не загружается
```bash
# Проверить доступное место
df -h

# Проверить логи
docker-compose logs whisper-service
```

#### 2. Медленная работа
- Проверить использование GPU
- Увеличить ресурсы в docker-compose.yml
- Уменьшить параметры качества модели

#### 3. Ошибки памяти
- Увеличить memory limits
- Перезапустить сервис: `docker-compose restart whisper-service`

#### 4. Ошибка сети
```bash
# Проверить, что порт 8003 доступен
netstat -tulpn | grep 8003

# Проверить сеть Docker
docker network ls
```

## Логи и отладка

### Полезные команды

```bash
# Подробные логи с временными метками
docker-compose logs -f --timestamps whisper-service

# Вход в контейнер для отладки
docker-compose exec whisper-service bash

# Проверка загрузки модели
docker-compose exec whisper-service python -c "import whisper; print('OK')"
```

### Уровни логирования

В `main.py` можно изменить уровень логирования:
```python
logging.basicConfig(level=logging.DEBUG)  # Для детальной отладки
```

## Интеграция с ботом

Бот автоматически использует локальный Whisper сервис вместо Hugging Face API. Функция `transcribe_audio` в `neuroapi.py` была изменена для работы с новым сервисом.

### Настройки в config.py
```python
WHISPER_SERVICE_URL = os.getenv('WHISPER_SERVICE_URL', 'http://localhost:8003')
```

### Использование в коде
```python
# Транскрибация происходит автоматически при получении голосового сообщения
transcribed_text = await neuroapi_client.transcribe_audio(voice_data)
```

## Безопасность

1. **Приватность**: Все аудио обрабатывается локально
2. **Сеть**: Сервис работает только в внутренней Docker сети
3. **Порты**: Порт 8003 открыт только для отладки (можно закрыть)

## Масштабирование

Для высокой нагрузки рассмотрите:
1. Использование нескольких экземпляров сервиса
2. Добавление очереди задач (Redis/RabbitMQ)
3. Балансировщик нагрузки (nginx)

## Обновления

При обновлении модели или зависимостей:
```bash
# Пересборка образа
docker-compose build --no-cache whisper-service

# Перезапуск сервиса
docker-compose up -d whisper-service
