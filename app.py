from flask import Flask, request, abort
import os
from dotenv import load_dotenv
import json
from services.chatgpt_service import ChatGPTService
from services.calendar_service import GoogleCalendarService
from services.firebase_service import FirebaseService
from services.user_service import UserService

# v3 SDK imports
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage as V3TextMessage
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# Line Bot v3 設定
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 如果在 Render 環境中，將憑證寫入臨時文件
if os.getenv('RENDER'):
    # Google Calendar 憑證
    if os.getenv('GOOGLE_CALENDAR_CREDENTIALS'):
        calendar_creds = json.loads(os.getenv('GOOGLE_CALENDAR_CREDENTIALS'))
        with open('google_calendar_credentials.json', 'w') as f:
            json.dump(calendar_creds, f)
        os.environ['GOOGLE_CALENDAR_CREDENTIALS'] = 'google_calendar_credentials.json'
    
    # Firebase 憑證
    if os.getenv('FIREBASE_CREDENTIALS'):
        firebase_creds = json.loads(os.getenv('FIREBASE_CREDENTIALS'))
        with open('firebase_credentials.json', 'w') as f:
            json.dump(firebase_creds, f)
        os.environ['FIREBASE_CREDENTIALS'] = 'firebase_credentials.json'

# 初始化服務
chatgpt_service = ChatGPTService()
calendar_service = GoogleCalendarService()
firebase_service = FirebaseService()
user_service = UserService(firebase_service)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except Exception as e:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    import re
    from datetime import datetime
    user_id = event.source.user_id
    user_info = user_service.get_user_info(user_id)
    user_message = event.message.text.strip()
    updated = False

    greetings = ['你好', '哈囉', 'hi', 'hello', '您好', '嗨', '哈囉～', '哈囉!']
    in_booking_flow = (user_info.get('state') in ['booking_ask_date', 'booking_ask_time']) or ("預約" in user_message)

    # 建檔流程
    if not in_booking_flow:
        if not user_info.get('name') and user_message.lower() not in greetings and not user_message.isdigit():
            user_service.update_user_info(user_id, {'name': user_message})
            print(f"[LOG] 已寫入用戶 {user_id} 的暱稱：{user_message}")
            updated = True
        elif not user_info.get('phone') and user_message.isdigit() and 8 <= len(user_message) <= 12:
            user_service.update_user_info(user_id, {'phone': user_message})
            print(f"[LOG] 已寫入用戶 {user_id} 的電話：{user_message}")
            updated = True

    if updated:
        user_info = user_service.get_user_info(user_id)

    # 建檔流程結束後自動引導預約
    if not in_booking_flow and user_info.get('name') and user_info.get('phone'):
        user_service.set_state(user_id, 'booking_ask_date')
        response = f"謝謝你，{user_info.get('name')}！請問你想預約哪一天呢？（例如：2025-05-03 或 5/3）💖"
    # 預約流程
    elif user_info.get('state') == 'booking_ask_date' or ("預約" in user_message):
        # 支援多種日期格式
        date_match = re.search(r"(20\d{2})[-/.年 ]?(\d{1,2})[-/.月 ]?(\d{1,2})日?", user_message)
        if not date_match:
            date_match = re.search(r"(\d{1,2})[-/.月 ]?(\d{1,2})日?", user_message)
            if date_match:
                year = datetime.now().year
                month = int(date_match.group(1))
                day = int(date_match.group(2))
                date_str = f"{year}-{month:02d}-{day:02d}"
            else:
                user_service.set_state(user_id, 'booking_ask_date')
                response = "請問你想預約哪一天呢？（例如：2025-05-03 或 5/3）🌸"
        else:
            if len(date_match.groups()) == 3:
                year = int(date_match.group(1)) if len(date_match.group(1)) == 4 else datetime.now().year
                month = int(date_match.group(2))
                day = int(date_match.group(3))
                date_str = f"{year}-{month:02d}-{day:02d}"
            else:
                date_str = None
            if date_str:
                user_service.set_state(user_id, 'booking_ask_time', booking_date=date_str)
                try:
                    print(f"[LOG] 查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                    slots = calendar_service.get_available_slots_by_date(date_str)
                    print(f"[LOG] 查詢結果：{slots}")
                    # 如果大部分時段都空，直接請客人輸入想要的時段
                    if len(slots) > 10:
                        response = f"這天大部分時段都還有空位唷！請直接輸入你想預約的時間（例如：14:00）😊"
                    elif slots:
                        slot_text = '\n'.join([f"{s}" for s in slots])
                        response = f"這天目前可預約的時段有：\n{slot_text}\n請問你想選哪一個時段呢？😊"
                    else:
                        response = f"這天目前已無可預約時段，請換一天試試看喔！🥲"
                except Exception as e:
                    print(f"[ERROR] Google Calendar 查詢失敗：{e}")
                    response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
            else:
                user_service.set_state(user_id, 'booking_ask_date')
                response = "請問你想預約哪一天呢？（例如：2025-05-03 或 5/3）🌸"
    elif user_info.get('state') == 'booking_ask_time' and user_info.get('booking_date'):
        # 支援多種時間格式
        time_match = re.search(r"(\d{1,2}):(\d{2})", user_message)
        if not time_match:
            time_match = re.search(r"(\d{1,2})點(\d{1,2})?分?", user_message)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.lastindex and time_match.group(2) else 0
            time_str = f"{hour:02d}:{minute:02d}"
            # 檢查該時段是否可預約
            slots = calendar_service.get_available_slots_by_date(user_info.get('booking_date'))
            if time_str in slots:
                # 建立 Google Calendar 預約
                try:
                    start_dt = datetime.strptime(user_info.get('booking_date') + ' ' + time_str, "%Y-%m-%d %H:%M")
                    end_dt = start_dt.replace(minute=start_dt.minute+30 if start_dt.minute < 30 else 0, hour=start_dt.hour if start_dt.minute < 30 else start_dt.hour+1)
                    event_link = calendar_service.create_booking(start_dt, end_dt, user_info, '美容服務預約')
                    # 寫入 Firebase booking history
                    user_service.add_booking(user_id, {
                        'start_time': start_dt.isoformat(),
                        'end_time': end_dt.isoformat(),
                        'service': '美容服務預約',
                        'status': 'confirmed',
                        'created_at': datetime.now().isoformat()
                    })
                    user_service.set_state(user_id, '', booking_date='', booking_time='')
                    response = f"預約成功！🎉\n已幫你預約 {user_info.get('booking_date')} {time_str}，期待在 Fanny Beauty 與你相見！\n如需更改請隨時告訴我。"
                except Exception as e:
                    print(f"[ERROR] Google Calendar/Firebase 寫入失敗：{e}")
                    response = "抱歉，預約時發生錯誤，請稍後再試。"
            else:
                response = f"這個時段已被預約或不存在，請再輸入一次你想預約的時間（例如：14:00）😊"
        else:
            response = "請輸入你想預約的時間（例如：14:00）😊"
    else:
        response = chatgpt_service.process_message(
            user_message,
            user_info=user_info
        )
    with ApiClient(configuration) as api_client:
        messaging_api = MessagingApi(api_client)
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[V3TextMessage(text=response)]
            )
        )

# 添加健康檢查端點
@app.route("/health", methods=['GET'])
def health_check():
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 