# Исправления Docker конфигурации для PaddleOCR

## Внесенные изменения

### 1. Исправлен базовый образ Docker
**Файл:** `ocr_service/Dockerfile`
- **Было:** `FROM paddlepaddle/paddle:3.0.0-cpu` (образ не существует)
- **Стало:** `FROM paddlepaddle/paddle:3.0.0` (стабильная версия)

### 2. Обновлена версия PaddleOCR
**Файл:** `ocr_service/requirements.txt`
- **Было:** `paddleocr==3.0.1` (несовместимо с PaddlePaddle 3.0.0)
- **Стало:** `paddleocr>=2.7.0,<3.0.0` (совместимая версия)

### 3. Исправлен health check
**Файл:** `docker-compose.yml`
- **Было:** `curl -f http://localhost:8001/health` (curl может отсутствовать)
- **Стало:** `python3 -c "import requests; requests.get('http://localhost:8001/health', timeout=5)"`

### 4. Добавлена зависимость requests
**Файл:** `ocr_service/requirements.txt`
- **Добавлено:** `requests==2.31.0` (для health check)

## Проверенные образы PaddlePaddle

Доступные стабильные версии на Docker Hub:
- `paddlepaddle/paddle:3.1.0` (новейшая, 23 дня назад)
- `paddlepaddle/paddle:3.0.0` (стабильная, 3 месяца назад) ✅ **Используется**
- `paddlepaddle/paddle:2.6.2` (предыдущая стабильная)

## Запуск после исправлений

```bash
# Сборка и запуск всей системы
docker-compose up --build

# Проверка статуса сервисов
docker-compose ps

# Проверка логов OCR сервиса
docker-compose logs paddleocr-service

# Проверка health check
curl http://localhost:8001/health
```

## Ожидаемый результат

После успешного запуска:
1. OCR сервис будет доступен по адресу `http://localhost:8001`
2. Telegram бот будет автоматически подключаться к OCR сервису
3. Пользователи смогут отправлять изображения для распознавания текста

## Возможные проблемы и решения

### 1. Медленная сборка образа
- **Причина:** Загрузка моделей PaddleOCR при сборке
- **Решение:** Это нормально для первой сборки (5-10 минут)

### 2. Высокое потребление памяти
- **Причина:** PaddleOCR загружает модели в память
- **Решение:** Убедитесь, что доступно минимум 2GB RAM

### 3. Ошибки совместимости
- **Причина:** Конфликт версий Python пакетов
- **Решение:** Используйте точные версии из requirements.txt

## Мониторинг

```bash
# Проверка использования ресурсов
docker stats

# Проверка состояния health check
docker-compose ps

# Просмотр логов в реальном времени
docker-compose logs -f paddleocr-service
