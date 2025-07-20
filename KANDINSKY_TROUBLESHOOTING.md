# Устранение проблем с Kandinsky сервисом

## Проблемы с зависимостями Python

### Ошибка: "Cannot install -r requirements.txt ... conflicting dependencies"

**Причина:** Конфликт версий между пакетами diffusers, transformers, accelerate и huggingface-hub.

**Решение 1 (автоматическое):**
Dockerfile уже настроен для автоматического решения этой проблемы:
```bash
docker-compose up --build kandinsky-service
```

**Решение 2 (ручное):**
Если автоматическое решение не сработало:
```bash
cd kandinsky_service
# Использовать минимальные версии без конфликтов
cp requirements-minimal.txt requirements.txt
docker-compose build kandinsky-service
```

**Решение 3 (полностью ручное):**
```bash
cd kandinsky_service
# Создать совместимые версии
cat > requirements-fixed.txt << EOF
fastapi==0.104.1
uvicorn[standard]==0.24.0
torch
torchvision
diffusers
transformers
accelerate
safetensors
Pillow
pydantic
httpx
EOF

# Использовать новый файл
cp requirements-fixed.txt requirements.txt
docker-compose build kandinsky-service
```

## Проблемы с памятью

### Ошибка: "CUDA out of memory"

**Решение:**
1. Уменьшите размер изображения в запросе:
```json
{
  "width": 512,
  "height": 512
}
```

2. Уменьшите количество шагов:
```json
{
  "num_inference_steps": 25
}
```

## Проблемы с GPU

### GPU не обнаружен

**Проверка:**
```bash
# Проверить доступность GPU на хосте
nvidia-smi

# Проверить в контейнере
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

**Решение:**
1. Установить NVIDIA Container Toolkit
2. Перезапустить Docker daemon
3. Проверить конфигурацию docker-compose.yml

## Проблемы с сетью

### Timeout при загрузке моделей

**Решение:**
```bash
# Увеличить timeout в docker-compose.yml
healthcheck:
  timeout: 60s
  interval: 120s
```

## Быстрая диагностика

```bash
# 1. Проверить статус сервисов
docker-compose ps

# 2. Проверить логи
docker-compose logs kandinsky-service

# 3. Проверить использование ресурсов
docker stats kandinsky-service

# 4. Тест API
curl http://localhost:8002/health

# 5. Полный перезапуск
docker-compose down
docker-compose up --build -d
```

## Альтернативные варианты запуска

### Запуск без GPU (только CPU)
```yaml
# В docker-compose.yml удалить:
# devices:
#   - driver: nvidia
#     count: 1
#     capabilities: [gpu]
```

### Локальный запуск (без Docker)
```bash
cd kandinsky_service
pip install -r requirements-minimal.txt
python main.py
```

## Контакты для поддержки

При сложных проблемах создайте issue в репозитории с:
1. Логами: `docker-compose logs kandinsky-service`
2. Конфигурацией системы: `nvidia-smi`, `docker version`
3. Описанием ошибки и шагами воспроизведения
