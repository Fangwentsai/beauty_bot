from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from dotenv import load_dotenv
from services.chatgpt_service import ChatGPTService
from services.calendar_service import GoogleCalendarService
from services.firebase_service import FirebaseService
from services.user_service import UserService
import json

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# Line Bot 設定
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
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
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    
    # 獲取用戶資訊
    user_info = user_service.get_user_info(user_id)
    
    # 使用 ChatGPT 處理訊息
    response = chatgpt_service.process_message(
        event.message.text,
        user_info=user_info
    )
    
    # 檢查是否包含預約相關指令
    if "預約" in event.message.text:
        available_slots = calendar_service.get_available_slots()
        response = chatgpt_service.format_booking_response(response, available_slots)
    
    # 發送回應
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response)
    )

# 添加健康檢查端點
@app.route("/health", methods=['GET'])
def health_check():
    return 'OK'

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 