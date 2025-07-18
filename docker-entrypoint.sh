#!/bin/bash

# Скрипт инициализации для Docker контейнера с поддержкой Yandex Cloud CLI

set -e

echo "🚀 Запуск Telegram бота с поддержкой голосового режима..."

# Проверяем наличие необходимых переменных окружения
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен"
    exit 1
fi

if [ -z "$NEUROAPI_API_KEY" ]; then
    echo "❌ Ошибка: NEUROAPI_API_KEY не установлен"
    exit 1
fi

if [ -z "$HUGGINGFACE_API_KEY" ]; then
    echo "❌ Ошибка: HUGGINGFACE_API_KEY не установлен"
    exit 1
fi

# Проверяем настройки для голосового режима
if [ -z "$YANDEX_FOLDER_ID" ]; then
    echo "⚠️  Предупреждение: YANDEX_FOLDER_ID не установлен - голосовой режим будет недоступен"
else
    echo "✅ Yandex Cloud Folder ID настроен"
fi

# Проверяем доступность Yandex Cloud CLI
if command -v yc &> /dev/null; then
    echo "✅ Yandex Cloud CLI установлен"
    
    # Настраиваем yc CLI с переданными учетными данными
    if [ ! -z "$YC_TOKEN" ]; then
        echo "🔑 Настраиваем yc CLI с OAuth токеном..."
        yc config set token "$YC_TOKEN"
        if yc iam create-token &> /dev/null; then
            echo "✅ OAuth токен настроен и IAM токен успешно создан"
        else
            echo "❌ Ошибка: OAuth токен недействителен"
        fi
    elif [ ! -z "$YC_SERVICE_ACCOUNT_KEY_FILE" ] && [ -f "$YC_SERVICE_ACCOUNT_KEY_FILE" ]; then
        echo "🔑 Настраиваем yc CLI с ключом сервисного аккаунта..."
        yc config set service-account-key "$YC_SERVICE_ACCOUNT_KEY_FILE"
        if yc iam create-token &> /dev/null; then
            echo "✅ Ключ сервисного аккаунта настроен и IAM токен успешно создан"
        else
            echo "❌ Ошибка: Ключ сервисного аккаунта недействителен"
        fi
    else
        echo "⚠️  Предупреждение: Учетные данные Yandex Cloud не настроены"
        echo "   Для работы голосового режима необходимо настроить:"
        echo "   - YC_TOKEN (OAuth токен) или"
        echo "   - YC_SERVICE_ACCOUNT_KEY_FILE (путь к ключу сервисного аккаунта)"
        echo "   Голосовой режим будет недоступен."
    fi
else
    echo "❌ Yandex Cloud CLI не найден"
fi

# Создаем директорию для логов если её нет
mkdir -p /app/logs

echo "🎤 Запускаем бота..."
exec python bot.py
