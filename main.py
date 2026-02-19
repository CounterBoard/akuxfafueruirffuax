import requests
import time
from datetime import datetime

# ===== ТВОИ ДАННЫЕ =====
ID_INSTANCE = "3100522242"
API_TOKEN = "ff2c2e1b33094666ad55ad03b4741240618374a110e34efd82"
MAX_CHAT_ID = "-68524048501490"
TELEGRAM_BOT_TOKEN = "8267269021:AAGR4uRS9UhWygaR4GIMVJTHnrJANPdw2Tk"
TELEGRAM_CHAT_ID = "-1003813727475"
# =======================

print("=" * 50)
print("🚀 ФИНАЛЬНЫЙ МОСТ С ЗАЩИТОЙ ОТ ТАЙМАУТОВ")
print("=" * 50)
print(f"📱 Инстанс: {ID_INSTANCE}")
print(f"💬 Чат MAX: {MAX_CHAT_ID}")
print(f"📬 Чат Telegram: {TELEGRAM_CHAT_ID}")
print("=" * 50)
print("🟢 Запущено. Скрипт будет автоматически повторять запросы при ошибках.\n")

receive_url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/receiveNotification/{API_TOKEN}"

# Счётчик для таймаутов
timeout_count = 0

while True:
    try:
        # Увеличил таймаут до 30 секунд
        response = requests.get(receive_url, timeout=30)
        
        # Если ответ успешный - сбрасываем счётчик
        timeout_count = 0
        
        if response.status_code == 200 and response.text and response.text != "null":
            data = response.json()
            receipt_id = data.get('receiptId')
            
            if receipt_id:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔔 Получено уведомление!")
                
                # Разбираем данные
                body = data.get('body', {})
                sender_data = body.get('senderData', {})
                message_data = body.get('messageData', {})
                
                # Проверяем ID чата
                chat_id = sender_data.get('chatId')
                print(f"📨 Чат: {chat_id}")
                
                # Если это наш чат - обрабатываем
                if chat_id == MAX_CHAT_ID:
                    print("✅ Сообщение из нужного чата!")
                    
                    # Получаем текст
                    text = None
                    if 'textMessageData' in message_data:
                        text = message_data['textMessageData'].get('textMessage')
                    
                    if text:
                        sender_name = sender_data.get('senderName', 'Неизвестно')
                        print(f"👤 От: {sender_name}")
                        print(f"📝 Текст: {text}")
                        
                        # Отправляем в Telegram
                        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                        tg_data = {
                            "chat_id": TELEGRAM_CHAT_ID,
                            "text": f"📨 MAX от {sender_name}:\n{text}"
                        }
                        tg_response = requests.post(tg_url, json=tg_data)
                        
                        if tg_response.status_code == 200:
                            print("✅ Отправлено в Telegram!")
                        else:
                            print(f"❌ Ошибка Telegram: {tg_response.text}")
                    else:
                        print("⏭️ Не текстовое сообщение")
                else:
                    print(f"⏭️ Не тот чат (жду {MAX_CHAT_ID})")
                
                # Удаляем уведомление из очереди
                delete_url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/deleteNotification/{API_TOKEN}/{receipt_id}"
                requests.delete(delete_url)
                print("🗑️ Уведомление удалено")
        else:
            print(".", end="", flush=True)
            
    except requests.exceptions.Timeout:
        timeout_count += 1
        print(f"\n⏱️ Таймаут #{timeout_count} (сервер не отвечает). Повтор через 5 секунд...")
        time.sleep(5)
    except requests.exceptions.ConnectionError:
        timeout_count += 1
        print(f"\n🔌 Ошибка соединения #{timeout_count}. Повтор через 10 секунд...")
        time.sleep(10)
    except KeyboardInterrupt:
        print("\n\n👋 Пока! Удачи на ЕГЭ!")
        break
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        time.sleep(5)
    
    time.sleep(1)