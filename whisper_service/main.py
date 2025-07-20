import os
import tempfile
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import whisper
import torch
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Whisper Speech Recognition Service", version="1.0.0")

# Проверка доступности GPU
device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Используется устройство: {device}")

# Глобальная переменная для модели
model = None
executor = ThreadPoolExecutor(max_workers=2)

def load_whisper_model():
    """Загрузка модели Whisper Medium"""
    global model
    try:
        logger.info("Загрузка модели Whisper Medium...")
        model = whisper.load_model("medium", device=device)
        logger.info(f"Модель Whisper Medium успешно загружена на {device}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели Whisper: {e}")
        return False

def transcribe_sync(audio_path: str) -> dict:
    """Синхронная транскрибация аудио"""
    try:
        if model is None:
            raise Exception("Модель Whisper не загружена")
        
        # Транскрибация с базовыми настройками для русского языка
        result = model.transcribe(
            audio_path,
            language="ru",  # Русский язык
            task="transcribe",
            fp16=torch.cuda.is_available(),  # Используем fp16 если есть CUDA
            temperature=0.0,  # Детерминистичный результат
            beam_size=5,  # Beam search для лучшего качества
            best_of=5,  # Выбираем лучший из 5 вариантов
            word_timestamps=False  # Не нужны временные метки для каждого слова
        )
        
        return {
            "success": True,
            "text": result["text"].strip(),
            "language": result.get("language", "ru"),
            "segments": len(result.get("segments", []))
        }
    except Exception as e:
        logger.error(f"Ошибка при транскрибации: {e}")
        return {
            "success": False,
            "text": "",
            "error": str(e)
        }

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервиса"""
    logger.info("Запуск сервиса Whisper...")
    
    # Загружаем модель в отдельном потоке
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(executor, load_whisper_model)
    
    if not success:
        logger.error("Не удалось загрузить модель Whisper. Сервис не готов к работе.")
    else:
        logger.info("Сервис Whisper готов к работе!")

@app.get("/")
async def root():
    """Корневой эндпоинт для проверки состояния сервиса"""
    return {
        "service": "Whisper Speech Recognition",
        "version": "1.0.0",
        "model": "medium",
        "device": device,
        "status": "ready" if model is not None else "loading"
    }

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "healthy" if model is not None else "loading",
        "device": device,
        "model_loaded": model is not None
    }

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Транскрибация аудиофайла"""
    if model is None:
        raise HTTPException(status_code=503, detail="Модель Whisper еще не загружена. Попробуйте позже.")
    
    # Проверяем тип файла
    if not file.content_type or not file.content_type.startswith("audio/"):
        # Разрешаем также некоторые другие типы, которые могут содержать аудио
        allowed_types = ["application/octet-stream", "application/ogg", "video/ogg"]
        if file.content_type not in allowed_types:
            logger.warning(f"Неподдерживаемый тип файла: {file.content_type}")
    
    temp_file_path = None
    try:
        # Читаем содержимое файла
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Пустой аудиофайл")
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        logger.info(f"Обработка аудиофайла размером {len(file_content)} байт")
        
        # Выполняем транскрибацию в отдельном потоке
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, transcribe_sync, temp_file_path)
        
        if result["success"]:
            logger.info(f"Транскрибация завершена: '{result['text'][:100]}...'")
            return JSONResponse(content={
                "success": True,
                "text": result["text"],
                "language": result["language"],
                "segments_count": result["segments"]
            })
        else:
            logger.error(f"Ошибка транскрибации: {result['error']}")
            raise HTTPException(status_code=500, detail=f"Ошибка транскрибации: {result['error']}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка при обработке аудио: {e}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
    
    finally:
        # Удаляем временный файл
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {temp_file_path}: {e}")

@app.post("/transcribe_simple")
async def transcribe_simple(file: UploadFile = File(...)):
    """Упрощенный эндпоинт транскрибации - возвращает только текст"""
    result = await transcribe_audio(file)
    response_data = result.body.decode() if hasattr(result, 'body') else result
    
    if isinstance(response_data, str):
        import json
        response_data = json.loads(response_data)
    
    return {"text": response_data.get("text", "")}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        workers=1,  # Важно: только 1 worker, так как модель загружается в память
        log_level="info"
    )
