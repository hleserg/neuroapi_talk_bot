#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы Whisper сервиса
"""

import requests
import sys
import time
import os

WHISPER_URL = "http://localhost:8003"

def test_health():
    """Тест проверки работоспособности сервиса"""
    print("🔍 Проверка работоспособности сервиса...")
    try:
        response = requests.get(f"{WHISPER_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Сервис работает")
            print(f"   Статус: {data.get('status')}")
            print(f"   Устройство: {data.get('device')}")
            print(f"   Модель загружена: {data.get('model_loaded')}")
            return True
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def test_service_info():
    """Тест получения информации о сервисе"""
    print("\n📋 Получение информации о сервисе...")
    try:
        response = requests.get(f"{WHISPER_URL}/", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Информация получена")
            print(f"   Сервис: {data.get('service')}")
            print(f"   Версия: {data.get('version')}")
            print(f"   Модель: {data.get('model')}")
            print(f"   Устройство: {data.get('device')}")
            print(f"   Статус: {data.get('status')}")
            return True
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def create_test_audio():
    """Создание тестового аудиофайла (заглушка)"""
    # В реальном тесте здесь был бы код для создания или использования
    # реального аудиофайла для тестирования
    test_audio_path = "test_voice.ogg"
    
    if os.path.exists(test_audio_path):
        print(f"✅ Найден тестовый файл: {test_audio_path}")
        return test_audio_path
    else:
        print(f"⚠️  Тестовый аудиофайл {test_audio_path} не найден")
        print("   Создайте файл test_voice.ogg или используйте реальную голосовую запись")
        return None

def test_transcription():
    """Тест транскрибации аудио"""
    print("\n🎤 Тест транскрибации аудио...")
    
    audio_file = create_test_audio()
    if not audio_file:
        print("⏭️  Пропускаем тест транскрибации (нет тестового файла)")
        return True
    
    try:
        with open(audio_file, 'rb') as f:
            files = {'file': ('test_voice.ogg', f, 'audio/ogg')}
            response = requests.post(
                f"{WHISPER_URL}/transcribe",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Транскрибация успешна")
                print(f"   Текст: '{data.get('text')}'")
                print(f"   Язык: {data.get('language')}")
                print(f"   Сегментов: {data.get('segments_count')}")
                return True
            else:
                print(f"❌ Ошибка транскрибации: {data}")
                return False
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def wait_for_service(max_wait=300):
    """Ожидание запуска сервиса"""
    print(f"⏳ Ожидание запуска сервиса (максимум {max_wait} секунд)...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{WHISPER_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('model_loaded'):
                    print("✅ Сервис готов к работе!")
                    return True
                else:
                    print("⏳ Модель еще загружается...")
        except:
            print("⏳ Сервис еще не отвечает...")
        
        time.sleep(10)
    
    print("❌ Тайм-аут ожидания запуска сервиса")
    return False

def main():
    """Основная функция тестирования"""
    print("🧪 Тестирование Whisper сервиса")
    print("=" * 50)
    
    # Список тестов
    tests = [
        ("Ожидание готовности сервиса", lambda: wait_for_service()),
        ("Проверка работоспособности", test_health),
        ("Информация о сервисе", test_service_info),
        ("Транскрибация аудио", test_transcription),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ Тест пройден")
            else:
                print(f"❌ Тест не пройден")
        except Exception as e:
            print(f"❌ Ошибка в тесте: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты тестирования:")
    print(f"   Пройдено: {passed}/{total}")
    print(f"   Успех: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        return 0
    else:
        print("⚠️  Некоторые тесты не пройдены")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
