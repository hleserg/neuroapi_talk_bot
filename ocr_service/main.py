import logging
import io
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import pytesseract
import cv2
import uvicorn

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="Tesseract Russian Text Recognition Service",
    description="OCR сервис для распознавания русского текста с изображений на базе Tesseract",
    version="1.0.0"
)

def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Продвинутая предобработка изображения для максимального качества OCR
    Автоматически применяет все рекомендуемые преобразования:
    - Повышение разрешения до 300+ DPI
    - Улучшение контрастности текста и фона
    - Коррекция наклона и искажений
    - Устранение размытия и повышение четкости
    """
    try:
        logger.info(f"Начальное изображение: {image.size}, режим: {image.mode}")
        
        # Конвертируем в RGB если необходимо
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 1. ПОВЫШЕНИЕ РАЗРЕШЕНИЯ ДО 300+ DPI
        original_size = image.size
        min_dimension = 1200  # Минимальное разрешение для качественного OCR
        
        if max(original_size) < min_dimension:
            # Увеличиваем изображение с сохранением пропорций
            scale_factor = min_dimension / max(original_size)
            new_size = (int(original_size[0] * scale_factor), int(original_size[1] * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"Изображение увеличено: {original_size} -> {new_size}")
        
        # 2. УСТРАНЕНИЕ РАЗМЫТИЯ И ПОВЫШЕНИЕ ЧЕТКОСТИ
        # Применяем фильтр для повышения резкости
        sharpening_filter = ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=3)
        image = image.filter(sharpening_filter)
        
        # Дополнительное повышение резкости через PIL
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.8)  # Увеличено с 1.2 до 1.8
        
        # 3. УЛУЧШЕНИЕ КОНТРАСТНОСТИ ТЕКСТА И ФОНА
        # Автоматическая коррекция контрастности
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.8)  # Увеличено с 1.5 до 1.8
        
        # Коррекция яркости для лучшего контраста
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)
        
        # Конвертируем в оттенки серого
        gray_image = image.convert('L')
        
        # Конвертируем в OpenCV для продвинутой обработки
        cv_image = np.array(gray_image)
        
        # 4. КОРРЕКЦИЯ НАКЛОНА И ИСКАЖЕНИЙ
        # Детекция и коррекция наклона текста
        cv_image = correct_skew(cv_image)
        
        # 5. ДОПОЛНИТЕЛЬНАЯ ОБРАБОТКА ДЛЯ УЛУЧШЕНИЯ КОНТРАСТА
        # Применяем CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cv_image = clahe.apply(cv_image)
        
        # 6. АДАПТИВНАЯ БИНАРИЗАЦИЯ
        # Применяем адаптивную бинаризацию для лучшего разделения текста и фона
        binary_image = cv2.adaptiveThreshold(
            cv_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 
            blockSize=15, C=8  # Увеличены параметры для лучшего качества
        )
        
        # 7. МОРФОЛОГИЧЕСКАЯ ОБРАБОТКА ДЛЯ УДАЛЕНИЯ ШУМА
        # Удаляем мелкий шум, сохраняя структуру текста
        kernel = np.ones((2, 2), np.uint8)
        
        # Закрытие для соединения разорванных букв
        binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel)
        
        # Открытие для удаления мелкого шума
        kernel_opening = np.ones((1, 1), np.uint8)
        binary_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel_opening)
        
        # Медианная фильтрация для дополнительного удаления шума
        binary_image = cv2.medianBlur(binary_image, 3)
        
        # 8. ФИНАЛЬНАЯ ОПТИМИЗАЦИЯ
        # Применяем гауссово размытие для сглаживания краев
        binary_image = cv2.GaussianBlur(binary_image, (1, 1), 0)
        
        # Конвертируем обратно в PIL
        processed_image = Image.fromarray(binary_image)
        
        logger.info(f"Изображение обработано: финальный размер {processed_image.size}")
        
        return processed_image
        
    except Exception as e:
        logger.warning(f"Ошибка при предобработке изображения: {e}. Используем базовую обработку.")
        # Возвращаем базовую обработку при ошибке
        try:
            if image.mode != 'L':
                image = image.convert('L')
            return image
        except:
            logger.error("Критическая ошибка обработки изображения")
            raise


def correct_skew(image: np.ndarray) -> np.ndarray:
    """
    Автоматическая коррекция наклона текста в изображении
    
    Args:
        image: Изображение в оттенках серого
        
    Returns:
        Изображение с исправленным наклоном
    """
    try:
        # Применяем детекцию краев для поиска линий текста
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        
        # Используем преобразование Хафа для поиска линий
        lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
        
        if lines is not None and len(lines) > 0:
            # Вычисляем средний угол наклона
            angles = []
            for rho, theta in lines[:10]:  # Берем первые 10 линий
                angle = theta - np.pi/2
                angles.append(angle)
            
            if angles:
                # Средний угол в градусах
                mean_angle = np.mean(angles) * 180 / np.pi
                
                # Корректируем только если угол значительный (больше 0.5 градуса)
                if abs(mean_angle) > 0.5:
                    logger.info(f"Корректируем наклон на {mean_angle:.2f} градусов")
                    
                    # Поворачиваем изображение
                    h, w = image.shape
                    center = (w // 2, h // 2)
                    rotation_matrix = cv2.getRotationMatrix2D(center, mean_angle, 1.0)
                    
                    # Вычисляем новые границы изображения
                    cos_val = abs(rotation_matrix[0, 0])
                    sin_val = abs(rotation_matrix[0, 1])
                    new_w = int((h * sin_val) + (w * cos_val))
                    new_h = int((h * cos_val) + (w * sin_val))
                    
                    # Корректируем центр поворота
                    rotation_matrix[0, 2] += (new_w / 2) - center[0]
                    rotation_matrix[1, 2] += (new_h / 2) - center[1]
                    
                    # Применяем поворот
                    rotated = cv2.warpAffine(image, rotation_matrix, (new_w, new_h), 
                                           flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                    return rotated
        
        return image
        
    except Exception as e:
        logger.warning(f"Ошибка при коррекции наклона: {e}")
        return image


def enhance_image_quality(image: np.ndarray) -> np.ndarray:
    """
    Дополнительное улучшение качества изображения для OCR
    
    Args:
        image: Изображение в оттенках серого
        
    Returns:
        Улучшенное изображение
    """
    try:
        # Удаление шума с помощью Non-local Means Denoising
        denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
        
        # Применяем bilateral filter для сохранения краев при сглаживании
        filtered = cv2.bilateralFilter(denoised, 9, 75, 75)
        
        return filtered
        
    except Exception as e:
        logger.warning(f"Ошибка при улучшении качества: {e}")
        return image

def initialize_tesseract():
    """Проверка инициализации Tesseract"""
    try:
        logger.info("Проверка инициализации Tesseract OCR...")
        
        # Проверяем доступность Tesseract
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract версия: {version}")
        
        # Проверяем доступные языки
        languages = pytesseract.get_languages()
        logger.info(f"Доступные языки: {languages}")
        
        if 'rus' not in languages:
            logger.warning("Русский язык (rus) не найден в Tesseract")
            return False
        
        logger.info("Tesseract успешно инициализирован для русского языка")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации Tesseract: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Событие запуска приложения"""
    logger.info("Запуск OCR сервиса...")
    success = initialize_tesseract()
    if not success:
        logger.error("Не удалось инициализировать Tesseract")
        raise Exception("Ошибка инициализации OCR")

@app.get("/")
async def root():
    """Проверка работоспособности сервиса"""
    return {
        "message": "Tesseract Russian Text Recognition Service", 
        "status": "online",
        "version": "1.0.0",
        "engine": "Tesseract OCR"
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверяем доступность Tesseract
        version = pytesseract.get_tesseract_version()
        languages = pytesseract.get_languages()
        
        return {
            "status": "healthy",
            "ocr_ready": True,
            "tesseract_version": str(version),
            "russian_support": 'rus' in languages,
            "available_languages": languages
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "ocr_ready": False,
            "error": str(e)
        }

@app.post("/ocr/extract_text")
async def extract_text_from_image(file: UploadFile = File(...)):
    """
    Извлечение текста из изображения с детальной информацией
    
    Args:
        file: Загруженный файл изображения
        
    Returns:
        JSON с распознанным текстом и дополнительной информацией
    """
    # Проверяем тип файла
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")
    
    try:
        # Читаем файл изображения
        image_data = await file.read()
        
        # Конвертируем в PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Предварительная обработка изображения
        processed_image = preprocess_image(image)
        
        # Выполняем OCR с получением детальной информации
        logger.info("Выполняем распознавание текста с помощью Tesseract...")
        
        # Конфигурация Tesseract для русского языка
        custom_config = r'--oem 3 --psm 6 -l rus+eng'
        
        # Получаем текст
        extracted_text = pytesseract.image_to_string(
            processed_image, 
            config=custom_config,
            lang='rus+eng'
        ).strip()
        
        # Получаем детальную информацию о распознанных блоках
        try:
            data = pytesseract.image_to_data(
                processed_image, 
                config=custom_config,
                lang='rus+eng',
                output_type=pytesseract.Output.DICT
            )
            
            # Обрабатываем результаты
            text_blocks = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 30:  # Фильтруем по уверенности > 30%
                    text = data['text'][i].strip()
                    if text:  # Игнорируем пустые строки
                        text_blocks.append({
                            "text": text,
                            "confidence": float(data['conf'][i]) / 100.0,  # Нормализуем 0-1
                            "coordinates": {
                                "x": int(data['left'][i]),
                                "y": int(data['top'][i]),
                                "width": int(data['width'][i]),
                                "height": int(data['height'][i])
                            }
                        })
            
        except Exception as detail_error:
            logger.warning(f"Не удалось получить детальную информацию: {detail_error}")
            text_blocks = []
        
        logger.info(f"Распознано текстовых блоков: {len(text_blocks)}")
        
        # Если основной текст пустой, пробуем альтернативную конфигурацию
        if not extracted_text and len(text_blocks) == 0:
            logger.info("Пробуем альтернативную конфигурацию OCR...")
            alternative_config = r'--oem 3 --psm 3 -l rus+eng'
            extracted_text = pytesseract.image_to_string(
                processed_image,
                config=alternative_config,
                lang='rus+eng'
            ).strip()
        
        return {
            "success": True,
            "text": extracted_text,
            "blocks": text_blocks,
            "total_blocks": len(text_blocks),
            "engine": "Tesseract OCR"
        }
        
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка OCR: {str(e)}")

@app.post("/ocr/extract_text_simple")
async def extract_text_simple(file: UploadFile = File(...)):
    """
    Упрощенное извлечение текста из изображения (только текст)
    
    Args:
        file: Загруженный файл изображения
        
    Returns:
        JSON с распознанным текстом
    """
    result = await extract_text_from_image(file)
    
    return {
        "success": result["success"],
        "text": result["text"],
        "engine": "Tesseract OCR"
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
