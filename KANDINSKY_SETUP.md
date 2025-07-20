# Настройка Kandinsky 2.2 для генерации изображений

Этот документ описывает миграцию с FLUX.1-dev на Kandinsky 2.2 Prior для генерации изображений.

## Что изменилось

### Старая система
- Использовала Hugging Face API с моделью FLUX.1-dev
- Внешний API-сервис
- Ограничения по скорости запросов

### Новая система
- Использует Kandinsky 2.2 Prior + Decoder
- Локальный сервис в Docker контейнере
- Полный контроль над процессом генерации
- Возможность настройки параметров

## Архитектура

```
Telegram Bot → NeuroAPI Client → Kandinsky Service (Docker) → Kandinsky 2.2 Models
```

## Структура файлов

```
kandinsky_service/
├── main.py           # FastAPI сервис
├── requirements.txt  # Python зависимости
└── Dockerfile       # Docker образ
```

## Конфигурация

### Docker Compose
- Новый сервис `kandinsky-service` на порту 8002
- GPU поддержка с NVIDIA Container Toolkit
- 8GB RAM, 4 CPU cores
- Автоматическая загрузка моделей при старте

### Переменные окружения
- `KANDINSKY_SERVICE_URL` - URL сервиса (по умолчанию: http://localhost:8002)

## API эндпоинты Kandinsky сервиса

### POST /generate
Генерация изображения по текстовому описанию.

**Параметры:**
```json
{
  "prompt": "описание изображения",
  "negative_prompt": "что исключить (опционально)",
  "width": 768,
  "height": 768,
  "num_inference_steps": 50,
  "guidance_scale": 4.0,
  "prior_guidance_scale": 1.0
}
```

**Ответ:** PNG изображение в бинарном формате

### GET /health
Проверка состояния сервиса.

**Ответ:**
```json
{
  "status": "healthy|unhealthy",
  "device": "cuda|cpu",
  "models_loaded": true|false
}
```

### POST /reload
Повторная загрузка моделей (полезно при сетевых ошибках).

**Ответ:**
```json
{
  "status": "success",
  "message": "Модели успешно загружены"
}
```

### GET /
Информация о сервисе и доступных эндпоинтах.

## Требования к системе

### Минимальные требования
- 8GB RAM
- 4 CPU cores
- 10GB свободного места на диске

### Рекомендуемые требования
- NVIDIA GPU с 8GB+ VRAM
- 16GB RAM
- SSD с 20GB+ свободного места

## Установка и запуск

### 1. Сборка и запуск через Docker Compose
```bash
docker-compose up --build kandinsky-service
```

### 2. Проверка работоспособности
```bash
curl http://localhost:8002/health
```

### 3. Тест генерации изображения
```bash
curl -X POST http://localhost:8002/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "красивый пейзаж с горами"}' \
  --output test_image.png
```

## Мониторинг

### Логи сервиса
```bash
docker logs kandinsky-service
```

### Использование ресурсов
```bash
docker stats kandinsky-service
```

## Оптимизация производительности

### GPU ускорение
- Убедитесь, что установлен NVIDIA Container Toolkit
- Проверьте доступность GPU: `nvidia-smi`

### Экономия памяти
- Сервис использует `enable_model_cpu_offload()` для экономии VRAM
- При нехватке памяти модели будут выгружаться на CPU

### Настройка параметров генерации
- `num_inference_steps`: меньше = быстрее, но хуже качество
- `guidance_scale`: влияет на соответствие промпту
- `prior_guidance_scale`: влияет на качество эмбеддингов

## Устранение неполадок

### Сервис не запускается
1. **Конфликты зависимостей Python**: 
   - Dockerfile автоматически попробует альтернативные версии
   - Проверьте логи сборки: `docker-compose logs kandinsky-service`
2. **Проблемы с GPU**: `docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi`
3. **Недостаток места**: `df -h`
4. **Общие логи**: `docker logs kandinsky-service`

### Проблемы с зависимостями
Если возникают конфликты версий пакетов:
```bash
# Альтернативная сборка с минимальными версиями
cd kandinsky_service
docker build -t kandinsky-minimal -f Dockerfile .
```

### Ошибки при генерации
1. Недостаток VRAM - уменьшите размер изображения
2. Timeout - увеличьте `num_inference_steps` или улучшите железо
3. Некорректный промпт - используйте английский язык для лучших результатов

### Медленная генерация
1. Используйте GPU вместо CPU
2. Уменьшите `num_inference_steps`
3. Уменьшите разрешение изображения

## Сравнение с FLUX.1-dev

| Параметр | FLUX.1-dev | Kandinsky 2.2 |
|----------|------------|---------------|
| Местоположение | External API | Local Docker |
| Скорость | Зависит от API | Зависит от железа |
| Стоимость | По запросам | Только ресурсы |
| Контроль | Ограниченный | Полный |
| Качество | Высокое | Высокое |
| Стиль | Реалистичный | Художественный |

## Дополнительные возможности

### Расширенные параметры
Можно добавить поддержку дополнительных параметров:
- Различные schedulers
- Поддержка ControlNet
- Batch генерация
- Upscaling

### Интеграция с другими моделями
Сервис можно расширить для поддержки:
- Kandinsky 3.0
- Stable Diffusion
- DALL-E локальные реализации

## Обновления

### Обновление моделей
Модели загружаются автоматически из Hugging Face при первом запуске и кешируются локально.

### Обновление кода
```bash
docker-compose build kandinsky-service
docker-compose up -d kandinsky-service
