#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы Kandinsky сервиса
"""

import asyncio
import httpx
import time
from pathlib import Path

KANDINSKY_URL = "http://localhost:8002"

async def test_health():
    """Тест проверки здоровья сервиса"""
    print("🔍 Проверка состояния сервиса...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{KANDINSKY_URL}/health")
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Сервис работает: {data}")
            return data.get("status") == "healthy" and data.get("models_loaded", False)
            
    except httpx.RequestError as e:
        print(f"❌ Ошибка подключения: {e}")
        return False
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP ошибка: {e.response.status_code}")
        return False

async def test_image_generation():
    """Тест генерации изображения"""
    print("🎨 Тестирование генерации изображения...")
    
    test_prompts = [
        "красивый закат над горами",
        "котенок играет с мячиком",
        "футуристический город",
        "цветочное поле весной"
    ]
    
    for i, prompt in enumerate(test_prompts):
        print(f"🖼️  Генерация {i+1}/4: {prompt}")
        
        payload = {
            "prompt": prompt,
            "negative_prompt": "low quality, blurry",
            "width": 512,  # Меньший размер для быстрого теста
            "height": 512,
            "num_inference_steps": 25,  # Меньше шагов для скорости
            "guidance_scale": 4.0
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{KANDINSKY_URL}/generate",
                    json=payload
                )
                response.raise_for_status()
                
                # Сохраняем изображение
                output_path = Path(f"test_image_{i+1}.png")
                output_path.write_bytes(response.content)
                
                elapsed = time.time() - start_time
                print(f"✅ Изображение сгенерировано за {elapsed:.1f}с: {output_path}")
                
        except httpx.RequestError as e:
            print(f"❌ Ошибка подключения: {e}")
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP ошибка: {e.response.status_code}")
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")

async def test_service_info():
    """Тест получения информации о сервисе"""
    print("ℹ️  Получение информации о сервисе...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{KANDINSKY_URL}/")
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Информация о сервисе: {data}")
            
    except httpx.RequestError as e:
        print(f"❌ Ошибка подключения: {e}")
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP ошибка: {e.response.status_code}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов Kandinsky сервиса\n")
    
    # Тест 1: Проверка состояния
    health_ok = await test_health()
    print()
    
    if not health_ok:
        print("❌ Сервис не готов к работе. Проверьте логи: docker logs kandinsky-service")
        return
    
    # Тест 2: Информация о сервисе
    await test_service_info()
    print()
    
    # Тест 3: Генерация изображений
    await test_image_generation()
    print()
    
    print("🎉 Тестирование завершено!")
    print("📁 Сгенерированные изображения сохранены как test_image_*.png")

if __name__ == "__main__":
    asyncio.run(main())
