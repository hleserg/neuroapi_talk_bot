# Запуск бота в Docker с поддержкой голосового режима

## Быстрый старт

### 1. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните все необходимые переменные:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Основные токены
TELEGRAM_BOT_TOKEN=ваш_токен_бота
NEUROAPI_API_KEY=ваш_ключ_neuroapi
HUGGINGFACE_API_KEY=ваш_ключ_huggingface

# Yandex Cloud для голосового режима
YANDEX_FOLDER_ID=ваш_folder_id

# Аутентификация Yandex Cloud (выберите один вариант)
YC_TOKEN=ваш_oauth_токен
# или
# YC_SERVICE_ACCOUNT_KEY_FILE=/app/service-account-key.json
```

### 2. Запуск с Docker Compose

```bash
# Сборка и запуск
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### 3. Запуск с Docker

```bash
# Сборка образа
docker build -t telegram-voice-bot .

# Запуск контейнера
docker run -d \
  --name telegram-voice-bot \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  telegram-voice-bot
```

## Настройка аутентификации Yandex Cloud

### Вариант 1: OAuth токен (рекомендуется для разработки)

1. Получите OAuth токен по ссылке:
   https://oauth.yandex.ru/authorize?response_type=token&client_id=1a6990aa636648e9b2ef855fa7bec2fb

2. Добавьте в `.env`:
   ```env
   YC_TOKEN=ваш_oauth_токен
   ```

### Вариант 2: Сервисный аккаунт (рекомендуется для продакшена)

1. Создайте сервисный аккаунт в Yandex Cloud Console
2. Назначьте роли: `ai.speechkit-tts.user`, `iam.serviceAccounts.tokenCreator`
3. Создайте и скачайте ключ в формате JSON
4. Поместите ключ в проект (например, `service-account-key.json`)
5. Добавьте в `.env`:
   ```env
   YC_SERVICE_ACCOUNT_KEY_FILE=/app/service-account-key.json
   ```
6. Обновите docker-compose.yml для монтирования ключа:
   ```yaml
   volumes:
     - ./service-account-key.json:/app/service-account-key.json:ro
   ```

## Проверка работы

### Проверка статуса контейнера
```bash
docker-compose ps
```

### Просмотр логов
```bash
# Все логи
docker-compose logs

# Логи в реальном времени
docker-compose logs -f

# Последние 100 строк
docker-compose logs --tail=100
```

### Проверка голосового режима
1. Запустите бота
2. Отправьте команду `/voice_status`
3. Если настройки корректны, должно показать статус Yandex Cloud

## Устранение неполадок

### Проблема: "IAM токен не создается"
- Проверьте правильность OAuth токена или ключа сервисного аккаунта
- Убедитесь, что сервисный аккаунт имеет необходимые роли
- Проверьте, что файл ключа доступен в контейнере

### Проблема: "Yandex Cloud CLI не найден"
- Пересоберите образ: `docker-compose build --no-cache`
- Проверьте логи сборки на ошибки установки CLI

### Проблема: "Голосовые сообщения не генерируются"
- Проверьте переменную `YANDEX_FOLDER_ID`
- Убедитесь, что аутентификация настроена корректно
- Проверьте логи на ошибки синтеза речи

### Проверка переменных окружения в контейнере
```bash
docker-compose exec telegram-bot env | grep YC
```

### Проверка Yandex Cloud CLI в контейнере
```bash
docker-compose exec telegram-bot yc --version
docker-compose exec telegram-bot yc iam create-token
```

## Мониторинг

### Health Check
Docker Compose настроен с автоматической проверкой здоровья:
- Интервал: 30 секунд
- Таймаут: 10 секунд
- Повторы: 3

### Ресурсы
Настроены лимиты ресурсов:
- Память: 512MB (лимит), 256MB (резерв)
- CPU: 0.5 ядра (лимит), 0.25 ядра (резерв)

### Автоперезапуск
- Политика: `unless-stopped`
- При ошибке: до 3 попыток с задержкой 5 секунд

## Безопасность

- Бот запускается от непривилегированного пользователя `app`
- Логи записываются в отдельный том
- Переменные окружения изолированы в контейнере
- Сетевая изоляция через Docker network

## Обновление

```bash
# Остановка
docker-compose down

# Обновление кода
git pull

# Пересборка и запуск
docker-compose up -d --build
