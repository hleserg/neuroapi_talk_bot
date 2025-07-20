import io
import asyncio
import torch
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from diffusers import KandinskyV22PriorPipeline, KandinskyV22Pipeline
from diffusers.utils import logging as diffusers_logging
from typing import Optional
import uvicorn

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Отключаем лишние логи от diffusers
diffusers_logging.set_verbosity_error()

app = FastAPI(title="Kandinsky 2.2 Image Generation API", version="1.0.0")

# Глобальные переменные для пайплайнов
prior_pipeline = None
decoder_pipeline = None
device = None

class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = "low quality, bad quality"
    width: int = 768
    height: int = 768
    num_inference_steps: int = 50
    guidance_scale: float = 4.0
    prior_guidance_scale: float = 1.0

class HealthResponse(BaseModel):
    status: str
    device: str
    models_loaded: bool

def load_models():
    """Загрузка моделей Kandinsky 2.2"""
    global prior_pipeline, decoder_pipeline, device
    
    try:
        # Определяем устройство
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Используется устройство: {device}")
        
        # Загружаем prior pipeline
        logger.info("Загружаем Kandinsky 2.2 Prior Pipeline...")
        prior_pipeline = KandinskyV22PriorPipeline.from_pretrained(
            "kandinsky-community/kandinsky-2-2-prior",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        )
        prior_pipeline.to(device)
        
        # Загружаем decoder pipeline
        logger.info("Загружаем Kandinsky 2.2 Decoder Pipeline...")
        decoder_pipeline = KandinskyV22Pipeline.from_pretrained(
            "kandinsky-community/kandinsky-2-2-decoder",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        )
        decoder_pipeline.to(device)
        
        # Оптимизации для экономии памяти
        if device == "cuda":
            prior_pipeline.enable_model_cpu_offload()
            decoder_pipeline.enable_model_cpu_offload()
            
        logger.info("Модели успешно загружены!")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке моделей: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Событие запуска приложения"""
    logger.info("Запуск сервиса Kandinsky 2.2...")
    try:
        success = load_models()
        if not success:
            logger.error("Не удалось загрузить модели!")
            raise RuntimeError("Ошибка загрузки моделей")
        logger.info("Сервис Kandinsky 2.2 успешно запущен!")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")
        raise

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    models_loaded = prior_pipeline is not None and decoder_pipeline is not None
    return HealthResponse(
        status="healthy" if models_loaded else "unhealthy",
        device=device or "unknown",
        models_loaded=models_loaded
    )

@app.post("/generate")
async def generate_image(request: ImageGenerationRequest):
    """Генерация изображения по текстовому описанию"""
    if prior_pipeline is None or decoder_pipeline is None:
        raise HTTPException(status_code=503, detail="Модели не загружены")
    
    try:
        logger.info(f"Генерация изображения по промпту: {request.prompt}")
        
        # Генерируем эмбеддинги через prior pipeline
        logger.info("Генерация image embeddings...")
        image_embeds, negative_image_embeds = prior_pipeline(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            guidance_scale=request.prior_guidance_scale,
            num_inference_steps=25
        ).to_tuple()
        
        # Генерируем изображение через decoder pipeline
        logger.info("Генерация изображения...")
        images = decoder_pipeline(
            image_embeds=image_embeds,
            negative_image_embeds=negative_image_embeds,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale
        ).images
        
        # Сохраняем изображение в BytesIO
        image_io = io.BytesIO()
        images[0].save(image_io, format="PNG")
        image_io.seek(0)
        
        logger.info("Изображение успешно сгенерировано!")
        
        return Response(
            content=image_io.getvalue(),
            media_type="image/png",
            headers={
                "Content-Disposition": "inline; filename=generated_image.png"
            }
        )
        
    except Exception as e:
        logger.error(f"Ошибка при генерации изображения: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")

@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "Kandinsky 2.2 Image Generation API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Проверка статуса сервиса",
            "/generate": "POST - Генерация изображения",
            "/docs": "Swagger документация"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
