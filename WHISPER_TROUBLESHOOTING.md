# Решение проблем Whisper сервиса

Этот документ описывает решение типичных проблем при работе с Whisper сервисом.

## Проблема с CUDA: "no kernel image is available for execution on the device"

### Описание проблемы

Ошибка `CUDA error: no kernel image is available for execution on the device` возникает из-за несовместимости версий:
- PyTorch был скомпилирован для определенной версии CUDA
- На вашей системе установлена другая версия CUDA
- NVIDIA драйвера устарели

### Автоматическое решение

Обновленный Whisper сервис автоматически переключается на CPU при проблемах с CUDA:

```
whisper-service | CUDA доступен. Используется устройство: cuda
whisper-service | Ошибка загрузки на CUDA: ...
whisper-service | Переключение на CPU режим...
whisper-service | Модель Whisper Medium успешно загружена на cpu
```

### Ручные решения

#### 1. Проверка совместимости CUDA

```bash
# Проверить версию CUDA на системе
nvidia-smi

# Проверить версию CUDA для которой скомпилирован PyTorch
docker run --rm python:3.11-slim bash -c "pip install torch && python -c 'import torch; print(torch.version.cuda)'"
```

#### 2. Принудительное использование CPU

Если хотите принудительно использовать CPU, добавьте в docker-compose.yml:

```yaml
whisper-service:
  environment:
    - CUDA_VISIBLE_DEVICES=""  # Отключает CUDA
    - TORCH_HOME=/app/.cache/torch
```

#### 3. Обновление NVIDIA драйверов

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nvidia-driver-535

# Проверка после установки
nvidia-smi
```

#### 4. Установка NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

#### 5. Использование совместимой версии PyTorch

В `whisper_service/requirements.txt` уже используются совместимые версии:

```
torch==2.0.1
torchaudio==2.0.2
```

## Другие проблемы

### Проблема: Медленная загрузка модели

**Симптомы:**
- Долгая загрузка при первом запуске
- Timeout при health check

**Решение:**

1. **Увеличить timeout в docker-compose.yml:**
```yaml
healthcheck:
  start_period: 180s  # Увеличить с 120s
```

2. **Предварительно загрузить модель:**
```bash
# Запустить только сборку без запуска
docker-compose build whisper-service

# Модель уже будет в образе
```

### Проблема: Нехватка памяти

**Симптомы:**
- OOMKilled в логах
- Контейнер перезапускается

**Решение:**

1. **Увеличить лимиты памяти:**
```yaml
deploy:
  resources:
    limits:
      memory: 8G  # Увеличить с 6G
```

2. **Освободить память системы:**
```bash
# Очистить кэш Docker
docker system prune -f

# Проверить использование памяти
free -h
```

### Проблема: Ошибки сети между контейнерами

**Симптомы:**
- Connection refused между bot и whisper-service
- Timeout ошибки

**Решение:**

1. **Проверить сеть Docker:**
```bash
docker network ls
docker network inspect my_new_bot_bot-network
```

2. **Проверить порты:**
```bash
# Внутри сети должен быть whisper-service:8003
docker-compose exec telegram-bot curl http://whisper-service:8003/health
```

3. **Перезапустить сетевой стек:**
```bash
docker-compose down
docker-compose up -d
```

### Проблема: Неподдерживаемый формат аудио

**Симптомы:**
- Ошибки при обработке определенных аудиофайлов
- "Неподдерживаемый тип файла"

**Решение:**

1. **Проверить поддерживаемые форматы:**
- OGG (рекомендуется)
- MP3
- WAV
- M4A
- FLAC

2. **Обновить ffmpeg в контейнере:**
```dockerfile
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-extra
```

## Мониторинг и отладка

### Полезные команды

```bash
# Проверка статуса всех сервисов
docker-compose ps

# Логи Whisper сервиса
docker-compose logs -f whisper-service

# Проверка health check
curl http://localhost:8003/health

# Вход в контейнер для отладки
docker-compose exec whisper-service bash

# Проверка использования ресурсов
docker stats whisper-service

# Тест транскрибации
python whisper_service/test_whisper.py
```

### Включение отладочного режима

В `whisper_service/main.py` измените уровень логирования:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Оптимизация производительности

### Для CPU режима

1. **Увеличить количество CPU:**
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'  # Увеличить количество ядер
```

2. **Оптимизировать параметры модели:**
```python
# В main.py уменьшить качество для скорости
result = model.transcribe(
    audio_path,
    beam_size=1,  # Уменьшить с 5
    best_of=1,    # Уменьшить с 5
)
```

### Для GPU режима

1. **Раскомментировать GPU настройки в docker-compose.yml:**
```yaml
runtime: nvidia
environment:
  - NVIDIA_VISIBLE_DEVICES=all
  - NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

2. **Проверить доступность GPU:**
```bash
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi
```

## Часто задаваемые вопросы

### Q: Можно ли использовать другую модель Whisper?

**A:** Да, в `main.py` замените `"medium"` на:
- `"tiny"` - быстрая, меньше качества
- `"base"` - баланс скорости и качества
- `"small"` - хорошее качество
- `"large"` - лучшее качество, медленнее

### Q: Как ускорить обработку коротких аудио?

**A:** Для коротких сообщений используйте модель `"base"` или оптимизируйте параметры:

```python
result = model.transcribe(
    audio_path,
    language="ru",
    temperature=0.0,
    beam_size=1,
    best_of=1,
    condition_on_previous_text=False
)
```

### Q: Поддерживается ли распознавание других языков?

**A:** Да, измените в `main.py`:
```python
language="auto"  # Автоопределение
# или
language="en"    # Английский
```

### Q: Как узнать, используется ли GPU?

**A:** Проверьте логи при запуске:
```bash
docker-compose logs whisper-service | grep "устройство"
```

Или через API:
```bash
curl http://localhost:8003/health
```

## Обновление и миграция

### Обновление модели

```bash
# Остановить сервис
docker-compose stop whisper-service

# Пересобрать с очисткой кэша
docker-compose build --no-cache whisper-service

# Запустить снова
docker-compose up -d whisper-service
```

### Бэкап настроек

```bash
# Сохранить кэш модели
docker run --rm -v whisper_cache:/cache -v $(pwd):/backup alpine tar czf /backup/whisper_backup.tar.gz -C /cache .

# Восстановить кэш
docker run --rm -v whisper_cache:/cache -v $(pwd):/backup alpine tar xzf /backup/whisper_backup.tar.gz -C /cache
```

## Контакты для поддержки

При возникновении проблем:

1. Проверьте логи: `docker-compose logs whisper-service`
2. Запустите тесты: `python whisper_service/test_whisper.py`
3. Создайте issue в репозитории GitHub с приложением логов
