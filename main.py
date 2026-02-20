import os
import requests
import time
import threading
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
print("🚀 МОСТ MAX → TELEGRAM (С ЦИТИРОВАНИЕМ)")
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
                    
                    # 📝 ТЕКСТОВЫЕ СООБЩЕНИЯ (С ЦИТИРОВАНИЕМ)
                    if msg_type == 'textMessage' and 'textMessageData' in message_data:
                        text = message_data['textMessageData'].get('textMessage')
                        if text:
                            sender_name = sender_data.get('senderName', 'Неизвестно')
                            
                            # 👇 ПРОВЕРЯЕМ, ЕСТЬ ЛИ ОТВЕТ НА СООБЩЕНИЕ
                            reply_text = ""
                            quoted_sender_display = ""
                            if 'quotedMessage' in message_data:
                                quoted = message_data['quotedMessage']
                                quoted_text = quoted.get('textMessage', '')
                                # Пробуем получить имя отправителя из разных мест
                                quoted_sender = quoted.get('senderName') or quoted.get('participant') or quoted.get('pushName', '')
                                
                                # Если имя не найдено, оставляем поле пустым
                                if quoted_sender:
                                    quoted_sender_display = quoted_sender
                                
                                if quoted_text:
                                    # Формируем строку с ответом
                                    if quoted_sender_display:
                                        reply_text = f"↪️ <b>В ответ на</b> сообщение от {quoted_sender_display}:\n> {quoted_text[:100]}{'...' if len(quoted_text) > 100 else ''}\n\n"
                                    else:
                                        reply_text = f"↪️ <b>В ответ на</b> сообщение:\n> {quoted_text[:100]}{'...' if len(quoted_text) > 100 else ''}\n\n"
                            
                            print(f"👤 От: {sender_name}")
                            print(f"📝 Текст: {text}")
                            if quoted_sender_display:
                                print(f"↪️ Ответ на сообщение от {quoted_sender_display}")
                            elif reply_text:
                                print(f"↪️ Ответ на сообщение (без имени)")
                            
                            # Формируем сообщение для Telegram
                            full_message = f"{reply_text}📨 <b>MAX от {sender_name}:</b>\n{text}"
                            
                            tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                            tg_data = {
                                "chat_id": TELEGRAM_CHAT_ID,
                                "text": full_message,
                                "parse_mode": "HTML"
                            }
                            requests.post(tg_url, json=tg_data)
                            print("✅ Текст отправлен в Telegram!")
                    
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
                            
                            # Проверяем, есть ли ответ на сообщение (для медиа)
                            reply_text = ""
                            if 'quotedMessage' in message_data:
                                quoted = message_data['quotedMessage']
                                quoted_text = quoted.get('textMessage', '')
                                quoted_sender = quoted.get('senderName', '')
                                if quoted_text:
                                    if quoted_sender:
                                        reply_text = f"↪️ <b>В ответ на</b> сообщение от {quoted_sender}:\n> {quoted_text[:100]}{'...' if len(quoted_text) > 100 else ''}\n\n"
                                    else:
                                        reply_text = f"↪️ <b>В ответ на</b> сообщение:\n> {quoted_text[:100]}{'...' if len(quoted_text) > 100 else ''}\n\n"
                            
                            # Скачиваем файл
                            file_response = requests.get(download_url)
                            
                            if file_response.status_code == 200:
                                # Отправляем в Telegram как фото (если это изображение)
                                if msg_type == 'imageMessage':
                                    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                                    files = {'photo': (file_name, file_response.content)}
                                    full_caption = f"{reply_text}📨 MAX от {sender_name}"
                                    if caption:
                                        full_caption += f"\n{caption}"
                                    data = {
                                        'chat_id': TELEGRAM_CHAT_ID,
                                        'caption': full_caption,
                                        'parse_mode': 'HTML'
                                    }
                                    requests.post(tg_url, data=data, files=files)
                                    print("✅ Фото отправлено в Telegram!")
                                else:
                                    # Для видео/документов/аудио отправляем как документ
                                    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
                                    files = {'document': (file_name, file_response.content)}
                                    full_caption = f"{reply_text}📨 MAX от {sender_name}\n{file_type}"
                                    if caption:
                                        full_caption += f"\n{caption}"
                                    data = {
                                        'chat_id': TELEGRAM_CHAT_ID,
                                        'caption': full_caption,
                                        'parse_mode': 'HTML'
                                    }
                                    requests.post(tg_url, data=data, files=files)
                                    print(f"✅ {file_type} отправлен в Telegram!")
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
