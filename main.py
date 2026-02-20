import os
import requests
import time
import threading
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ===== ПЕРЕМЕННЫЕ ИЗ ОКРУЖЕНИЯ =====
ID_INSTANCE = os.environ.get('ID_INSTANCE')
API_TOKEN = os.environ.get('API_TOKEN')
MAX_CHAT_ID = os.environ.get('MAX_CHAT_ID')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
# ===================================

# Проверка наличия переменных
if not all([ID_INSTANCE, API_TOKEN, MAX_CHAT_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    missing = [v for v in ['ID_INSTANCE', 'API_TOKEN', 'MAX_CHAT_ID', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'] 
               if not os.environ.get(v)]
    raise ValueError(f"❌ Отсутствуют: {', '.join(missing)}")

# ===== НАСТРОЙКА БАЗЫ ДАННЫХ SQLITE =====
DB_FILE = 'messages.db'

def init_database():
    """Создаёт таблицу для хранения связей сообщений"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_links (
            max_message_id TEXT PRIMARY KEY,
            tg_message_id INTEGER NOT NULL,
            max_chat_id TEXT NOT NULL,
            sender_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print("🗄️ База данных SQLite инициализирована")

def save_message_link(max_message_id, tg_message_id, max_chat_id, sender_name=''):
    """Сохраняет связь между ID сообщения в Max и ID в Telegram"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO message_links (max_message_id, tg_message_id, max_chat_id, sender_name) VALUES (?, ?, ?, ?)",
            (str(max_message_id), tg_message_id, max_chat_id, sender_name)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения в БД: {e}")
        return False

def get_tg_message_id(max_message_id):
    """Получает ID сообщения в Telegram по ID из Max"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tg_message_id FROM message_links WHERE max_message_id = ?",
            (str(max_message_id),)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"❌ Ошибка чтения из БД: {e}")
        return None

# Инициализируем БД при старте
init_database()
# =========================================

# ===== ВЕБ-СЕРВЕР =====
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bridge is running")
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
        
    def log_message(self, format, *args): pass

def run_http_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"🌐 Веб-сервер запущен на порту {port}")
    server.serve_forever()

web_thread = threading.Thread(target=run_http_server, daemon=True)
web_thread.start()
# =====================

print("=" * 50)
print("🚀 МОСТ MAX → TELEGRAM (С SQLITE)")
print("=" * 50)
print(f"📱 Инстанс: {ID_INSTANCE}")
print(f"💬 Чат MAX: {MAX_CHAT_ID}")
print(f"📬 Чат Telegram: {TELEGRAM_CHAT_ID}")
print("=" * 50)
print("🟢 Запущено. Жду сообщения...\n")

receive_url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/receiveNotification/{API_TOKEN}"

while True:
    try:
        response = requests.get(receive_url, timeout=30)
        
        if response.status_code == 200 and response.text and response.text != "null":
            data = response.json()
            receipt_id = data.get('receiptId')
            
            if receipt_id:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔔 Получено уведомление!")
                
                body = data.get('body', {})
                sender_data = body.get('senderData', {})
                message_data = body.get('messageData', {})
                
                chat_id = sender_data.get('chatId')
                print(f"📨 Чат: {chat_id}")
                
                if chat_id == MAX_CHAT_ID:
                    print("✅ Сообщение из нужного чата!")
                    
                    # Определяем тип сообщения
                    msg_type = message_data.get('typeMessage', '')
                    
                    # Получаем ID сообщения в Max (если есть)
                    max_message_id = data.get('idMessage') or str(int(time.time() * 1000))
                    
                    # 📝 ТЕКСТОВЫЕ СООБЩЕНИЯ (С ПОДДЕРЖКОЙ ОТВЕТОВ)
                    if msg_type == 'textMessage' and 'textMessageData' in message_data:
                        text = message_data['textMessageData'].get('textMessage')
                        if text:
                            sender_name = sender_data.get('senderName', 'Неизвестно')
                            
                            # Проверяем, есть ли ответ на сообщение
                            reply_to_tg_id = None
                            if 'quotedMessage' in message_data:
                                quoted = message_data['quotedMessage']
                                quoted_id = quoted.get('idMessage')
                                if quoted_id:
                                    reply_to_tg_id = get_tg_message_id(quoted_id)
                                    if reply_to_tg_id:
                                        print(f"↪️ Это ответ на сообщение {quoted_id}")
                            
                            print(f"👤 От: {sender_name}")
                            print(f"📝 Текст: {text}")
                            
                            # Формируем сообщение для Telegram
                            full_message = f"📨 <b>MAX от {sender_name}:</b>\n{text}"
                            
                            # Отправляем в Telegram
                            tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                            tg_data = {
                                "chat_id": TELEGRAM_CHAT_ID,
                                "text": full_message,
                                "parse_mode": "HTML"
                            }
                            
                            # Если есть ID сообщения, на которое отвечаем, добавляем reply_parameters
                            if reply_to_tg_id:
                                tg_data["reply_parameters"] = {
                                    "message_id": reply_to_tg_id
                                }
                                print(f"↪️ Отправляется как ответ на сообщение {reply_to_tg_id}")
                            
                            tg_response = requests.post(tg_url, json=tg_data)
                            
                            if tg_response.status_code == 200:
                                tg_message_id = tg_response.json()['result']['message_id']
                                save_message_link(max_message_id, tg_message_id, chat_id, sender_name)
                                print("✅ Текст отправлен в Telegram!")
                            else:
                                print(f"❌ Ошибка Telegram: {tg_response.text}")
                    
                    # 🖼️ МЕДИА СООБЩЕНИЯ (ФОТО, ВИДЕО, ДОКУМЕНТЫ)
                    elif msg_type in ['imageMessage', 'videoMessage', 'documentMessage', 'audioMessage']:
                        file_data = message_data.get('fileMessageData', {})
                        download_url = file_data.get('downloadUrl')
                        caption = file_data.get('caption', '')
                        file_name = file_data.get('fileName', 'media')
                        
                        if download_url:
                            sender_name = sender_data.get('senderName', 'Неизвестно')
                            file_type = {
                                'imageMessage': '🖼️ Фото',
                                'videoMessage': '🎥 Видео',
                                'documentMessage': '📄 Документ',
                                'audioMessage': '🎵 Аудио'
                            }.get(msg_type, '📎 Медиа')
                            
                            print(f"👤 От: {sender_name}")
                            print(f"{file_type}: {file_name}")
                            
                            # Проверяем, есть ли ответ на сообщение
                            reply_to_tg_id = None
                            if 'quotedMessage' in message_data:
                                quoted = message_data['quotedMessage']
                                quoted_id = quoted.get('idMessage')
                                if quoted_id:
                                    reply_to_tg_id = get_tg_message_id(quoted_id)
                            
                            # Скачиваем файл
                            file_response = requests.get(download_url)
                            
                            if file_response.status_code == 200:
                                # Отправляем в Telegram
                                full_caption = f"📨 MAX от {sender_name}"
                                if caption:
                                    full_caption += f"\n{caption}"
                                
                                if msg_type == 'imageMessage':
                                    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                                    files = {'photo': (file_name, file_response.content)}
                                    data = {
                                        'chat_id': TELEGRAM_CHAT_ID,
                                        'caption': full_caption,
                                        'parse_mode': 'HTML'
                                    }
                                    if reply_to_tg_id:
                                        data["reply_parameters"] = {"message_id": reply_to_tg_id}
                                    tg_response = requests.post(tg_url, data=data, files=files)
                                else:
                                    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
                                    files = {'document': (file_name, file_response.content)}
                                    data = {
                                        'chat_id': TELEGRAM_CHAT_ID,
                                        'caption': f"{full_caption}\n{file_type}",
                                        'parse_mode': 'HTML'
                                    }
                                    if reply_to_tg_id:
                                        data["reply_parameters"] = {"message_id": reply_to_tg_id}
                                    tg_response = requests.post(tg_url, data=data, files=files)
                                
                                if tg_response.status_code == 200:
                                    tg_message_id = tg_response.json()['result']['message_id']
                                    save_message_link(max_message_id, tg_message_id, chat_id, sender_name)
                                    print(f"✅ {file_type} отправлен в Telegram!")
                                else:
                                    print(f"❌ Ошибка отправки: {tg_response.text}")
                            else:
                                print(f"❌ Не удалось скачать файл")
                        else:
                            print("⏭️ Нет ссылки на файл")
                    else:
                        print(f"⏭️ Неподдерживаемый тип: {msg_type}")
                else:
                    print(f"⏭️ Не тот чат (жду {MAX_CHAT_ID})")
                
                # Удаляем уведомление
                delete_url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/deleteNotification/{API_TOKEN}/{receipt_id}"
                requests.delete(delete_url)
                print("🗑️ Уведомление удалено")
        else:
            print(".", end="", flush=True)
            
    except requests.exceptions.Timeout:
        print("t", end="", flush=True)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        time.sleep(5)
    
    time.sleep(1)
