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

# 載入環境變數
load_dotenv()

app = Flask(__name__)

# Line Bot 設定
line_bot_api = LineBotApi(os.getenv('A3vlvshjY8RHWunjEB6iaDBNJCwTvlWs2NzTnbxx6HaGdjMK0R1fE8LMujfILl4zqIvGuvaPfRSYPbIecBdGfm6gR6G1yFQFoT88TMZ4yEIQNlvosyQ133OfS/eDKtAYBIPB0ARloaEKDXHL8IV4+QdB04t89/1O/w1cDnyilFU='))
handler = WebhookHandler(os.getenv('db9f1a6b91531c453831854db54c4e72'))

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 