import logging
import io
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import numpy as np
from paddleocr import PaddleOCR
import uvicorn

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="PaddleOCR Russian Text Recognition Service",
    description="OCR сервис для распознавания русского текста с изображений",
    version="1.0.0"
)

# Глобальная переменная для хранения модели OCR
ocr_model = None

def initialize_ocr():
    """Инициализация модели PaddleOCR для русского языка"""
    global ocr_model
    try:
        logger.info("Инициализация PaddleOCR для русского языка...")
        # Используем язык 'cyrillic' для поддержки русского текста
        ocr_model = PaddleOCR(
            lang='cyrillic',  # Поддержка кириллицы (русский язык)
            use_gpu=False,    # Используем CPU
            use_angle_cls=True,  # Классификация ориентации текста
            show_log=False,   # Отключаем детальные логи PaddleOCR
            det_model_dir=None,  # Используем модель по умолчанию
            rec_model_dir=None   # Используем модель по умолчанию
        )
        logger.info("PaddleOCR успешно инициализирован для русского языка")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации PaddleOCR: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Событие запуска приложения"""
    logger.info("Запуск OCR сервиса...")
    success = initialize_ocr()
    if not success:
        logger.error("Не удалось инициализировать OCR модель")
        raise Exception("Ошибка инициализации OCR")

@app.get("/")
async def root():
    """Проверка работоспособности сервиса"""
    return {
        "message": "PaddleOCR Russian Text Recognition Service", 
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "ocr_ready": ocr_model is not None
    }

@app.post("/ocr/extract_text")
async def extract_text_from_image(file: UploadFile = File(...)):
    """
    Извлечение текста из изображения
    
    Args:
        file: Загруженный файл изображения
        
    Returns:
        JSON с распознанным текстом и координатами
    """
    if ocr_model is None:
        raise HTTPException(status_code=500, detail="OCR модель не инициализирована")
    
    # Проверяем тип файла
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")
    
    try:
        # Читаем файл изображения
        image_data = await file.read()
        
        # Конвертируем в PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Конвертируем в RGB если необходимо
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Конвертируем в numpy array для PaddleOCR
        image_array = np.array(image)
        
        # Выполняем OCR
        logger.info("Выполняем распознавание текста...")
        result = ocr_model.ocr(image_array, cls=True)
        
        # Обрабатываем результат
        extracted_text = ""
        text_blocks = []
        
        if result and len(result) > 0 and result[0]:
            for line in result[0]:
                if line and len(line) > 1:
                    # line[0] содержит координаты, line[1] содержит (текст, уверенность)
                    coordinates = line[0]
                    text_info = line[1]
                    
                    if text_info and len(text_info) > 0:
                        text = text_info[0]
                        confidence = text_info[1] if len(text_info) > 1 else 0.0
                        
                        extracted_text += text + " "
                        
                        text_blocks.append({
                            "text": text,
                            "confidence": round(confidence, 3),
                            "coordinates": coordinates
                        })
        
        # Убираем лишние пробелы
        extracted_text = extracted_text.strip()
        
        logger.info(f"Распознано текстовых блоков: {len(text_blocks)}")
        
        return {
            "success": True,
            "text": extracted_text,
            "blocks": text_blocks,
            "total_blocks": len(text_blocks)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка OCR: {str(e)}")

@app.post("/ocr/extract_text_simple")
async def extract_text_simple(file: UploadFile = File(...)):
    """
    Упрощенное извлечение текста из изображения (только текст без координат)
    
    Args:
        file: Загруженный файл изображения
        
    Returns:
        JSON с распознанным текстом
    """
    result = await extract_text_from_image(file)
    
    return {
        "success": result["success"],
        "text": result["text"]
    }

if __name__ == "__main__":
    # Запуск сервера
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        access_log=True
    )
