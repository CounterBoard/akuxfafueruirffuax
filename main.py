import os
import requests
import time
import json
from datetime import datetime

# ===== ПЕРЕМЕННЫЕ ИЗ ОКРУЖЕНИЯ =====
ID_INSTANCE = os.environ.get('ID_INSTANCE')
API_TOKEN = os.environ.get('API_TOKEN')
MAX_CHAT_ID = os.environ.get('MAX_CHAT_ID')
# ===================================

def get_recent_messages(count=5):
    """Получает последние сообщения и ищет ответы"""
    url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/GetChatHistory/{API_TOKEN}"
    payload = {
        "chatId": MAX_CHAT_ID,
        "count": count
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

print("🔍 ПОИСК СООБЩЕНИЙ С ОТВЕТАМИ")
print("=" * 60)

messages = get_recent_messages(20)

found = 0
for msg in messages:
    # Проверяем, есть ли в сообщении поле, похожее на ответ
    if 'quotedMessage' in msg or 'replyTo' in msg or 'contextInfo' in msg:
        found += 1
        print(f"\n🔥 СООБЩЕНИЕ #{found}")
        print(f"📝 Текст: {msg.get('textMessage', 'Нет текста')}")
        print("📦 Полная структура:")
        print(json.dumps(msg, indent=2, ensure_ascii=False))
        print("-" * 60)

if found == 0:
    print("\n❌ Сообщений с ответами не найдено")
    print("Возможно, в истории нет ответов или они хранятся иначе")
