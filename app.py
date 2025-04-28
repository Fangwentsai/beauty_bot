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
    user_id = event.source.user_id
    user_info = user_service.get_user_info(user_id)
    user_message = event.message.text.strip()
    updated = False

    # 避免將打招呼詞當作名字
    greetings = ['你好', '哈囉', 'hi', 'hello', '您好', '嗨', '哈囉～', '哈囉!']
    # 只有在未進入預約流程時才進行新用戶建檔
    in_booking_flow = ("預約" in user_message) or (user_info.get('state') == 'booking_ask_date')

    if not in_booking_flow:
        # 如果還沒暱稱且訊息不像電話且不是打招呼詞，當作暱稱
        if not user_info.get('name') and user_message.lower() not in greetings and not user_message.isdigit():
            user_service.update_user_info(user_id, {'name': user_message})
            print(f"[LOG] 已寫入用戶 {user_id} 的暱稱：{user_message}")
            updated = True
        # 如果還沒電話且訊息像電話（8~12碼數字）
        elif not user_info.get('phone') and user_message.isdigit() and 8 <= len(user_message) <= 12:
            user_service.update_user_info(user_id, {'phone': user_message})
            print(f"[LOG] 已寫入用戶 {user_id} 的電話：{user_message}")
            updated = True

    # 重新取得最新 user_info
    if updated:
        user_info = user_service.get_user_info(user_id)

    # 預約流程：先問日期，再查詢當天時段
    if ("預約" in user_message) or (user_info.get('state') == 'booking_ask_date'):
        import re
        date_match = re.match(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", user_message)
        if user_info.get('state') == 'booking_ask_date' and date_match:
            date_str = f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
            user_service.set_state(user_id, '', booking_date=date_str)
            try:
                print(f"[LOG] 查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                slots = calendar_service.get_available_slots_by_date(date_str)
                print(f"[LOG] 查詢結果：{slots}")
                if slots:
                    slot_text = '\n'.join([f"{s}" for s in slots])
                    response = f"這天目前可預約的時段有：\n{slot_text}\n請問你想選哪一個時段呢？😊"
                else:
                    response = f"這天目前已無可預約時段，請換一天試試看喔！🥲"
            except Exception as e:
                print(f"[ERROR] Google Calendar 查詢失敗：{e}")
                response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
        else:
            user_service.set_state(user_id, 'booking_ask_date')
            response = "請問你想預約哪一天呢？（例如：2025-05-03）🌸"
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