from flask import Flask, request, abort
import os
from dotenv import load_dotenv
import json
from services.chatgpt_service import ChatGPTService
from services.calendar_service import GoogleCalendarService
from services.firebase_service import FirebaseService
from services.user_service import UserService
import logging

# v3 SDK imports
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient, ReplyMessageRequest, TextMessage as V3TextMessage
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# 載入環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.error(f"處理 LINE 訊息發生錯誤: {str(e)}")
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
    response = None  # 初始化 response 變數

    logger.info(f"收到用戶 {user_id} 訊息: {user_message}")
    logger.info(f"目前用戶資料: {user_info}")

    greetings = ['你好', '哈囉', 'hi', 'hello', '您好', '嗨', '哈囉～', '哈囉!']
    in_booking_flow = (user_info.get('state') in ['booking_ask_date', 'booking_ask_time']) or ("預約" in user_message)

    # 如果是初次互動或打招呼，展示品牌形象
    if user_message.lower() in greetings:
        if not user_info.get('name'):
            response = "哈囉！歡迎來到 Fanny Beauty 美學 💄 我是您的專屬美容顧問！請問我可以怎麼稱呼您呢？😊"
        else:
            response = f"嗨，{user_info.get('name')}！歡迎回到 Fanny Beauty 美學，有什麼我可以幫助你的嗎？💖"
    # 建檔流程
    elif not in_booking_flow:
        if not user_info.get('name') and user_message.lower() not in greetings and not user_message.isdigit():
            user_service.update_user_info(user_id, {'name': user_message})
            logger.info(f"已寫入用戶 {user_id} 的暱稱：{user_message}")
            print(f"[LOG] 已寫入用戶 {user_id} 的暱稱：{user_message}")
            updated = True
        elif not user_info.get('phone') and user_message.isdigit() and 8 <= len(user_message) <= 12:
            user_service.update_user_info(user_id, {'phone': user_message})
            logger.info(f"已寫入用戶 {user_id} 的電話：{user_message}")
            print(f"[LOG] 已寫入用戶 {user_id} 的電話：{user_message}")
            updated = True

    if updated:
        user_info = user_service.get_user_info(user_id)
        logger.info(f"更新後用戶資料: {user_info}")

    # 建檔流程結束後自動引導預約
    if not response and not in_booking_flow and user_info.get('name') and user_info.get('phone'):
        user_service.set_state(user_id, 'booking_ask_date')
        name = user_info.get('name', '').strip()
        logger.info(f"用戶完成建檔，名字為: '{name}'")
        response = f"謝謝你，{name}！請問你想預約哪一天呢？（例如：2025-05-03 或 5/3）💖"
    # 預約流程
    elif not response and (user_info.get('state') == 'booking_ask_date' or ("預約" in user_message)):
        # 處理日期時間組合型輸入，例如 "5/5 14:00" 或 "5/5 2.半"
        # 先嘗試分離日期和時間
        combined_match = re.search(r"(\d{1,2})[/\-.](\d{1,2})(?:[^\d]+(\d{1,2})(?:[:.點](\d{1,2}))?(?:分|半)?)?", user_message)
        
        if combined_match:
            # 提取日期部分
            month = int(combined_match.group(1))
            day = int(combined_match.group(2))
            year = datetime.now().year
            date_str = f"{year}-{month:02d}-{day:02d}"
            logger.info(f"日期匹配: 年={year}, 月={month}, 日={day}, 格式化={date_str}")
            
            # 檢查是否也提供了時間
            if combined_match.group(3):  # 有小時部分
                hour = int(combined_match.group(3))
                
                # 處理特殊的"半"情況
                if "半" in user_message:
                    minute = 30
                elif combined_match.group(4):  # 有分鐘部分
                    minute = int(combined_match.group(4))
                else:
                    minute = 0
                    
                time_str = f"{hour:02d}:{minute:02d}"
                logger.info(f"時間匹配: 時={hour}, 分={minute}, 格式化={time_str}")
                
                # 設置狀態並繼續預約流程
                user_service.set_state(user_id, 'booking_ask_time', booking_date=date_str)
                
                try:
                    logger.info(f"查詢 Google Calendar {date_str} 可用時段")
                    slots = calendar_service.get_available_slots_by_date(date_str)
                    logger.info(f"可用時段: {slots}")
                    
                    if time_str in slots:
                        # 直接預約
                        try:
                            start_dt = datetime.strptime(date_str + ' ' + time_str, "%Y-%m-%d %H:%M")
                            end_dt = start_dt.replace(minute=start_dt.minute+30 if start_dt.minute < 30 else 0, 
                                                    hour=start_dt.hour if start_dt.minute < 30 else start_dt.hour+1)
                            logger.info(f"嘗試創建預約：開始={start_dt}, 結束={end_dt}")
                            print(f"[LOG] 嘗試創建預約：開始={start_dt}, 結束={end_dt}")
                            
                            event_link = calendar_service.create_booking(start_dt, end_dt, user_info, '美容服務預約')
                            logger.info(f"Google Calendar 預約創建成功: {event_link}")
                            print(f"[LOG] Google Calendar 預約創建成功: {event_link}")
                            
                            booking_data = {
                                'start_time': start_dt.isoformat(),
                                'end_time': end_dt.isoformat(),
                                'service': '美容服務預約',
                                'status': 'confirmed',
                                'created_at': datetime.now().isoformat()
                            }
                            user_service.add_booking(user_id, booking_data)
                            user_service.set_state(user_id, '', booking_date='', booking_time='')
                            response = f"預約成功！🎉\n已幫你預約 {date_str} {time_str}，期待在 Fanny Beauty 與你相見！\n如需更改請隨時告訴我。"
                        except Exception as e:
                            logger.error(f"預約失敗: {str(e)}")
                            print(f"[ERROR] 預約失敗: {e}")
                            response = "抱歉，預約時發生錯誤，請稍後再試。"
                    else:
                        # 告知用戶該時段不可用
                        if slots:
                            slot_text = '\n'.join([f"{s}" for s in slots[:10]])
                            response = f"抱歉，{time_str} 時段已被預約。這天目前可預約的時段有：\n{slot_text}\n請問你想選哪一個時段呢？😊"
                        else:
                            response = f"抱歉，{date_str} 這天已無可預約時段，請換一天試試看喔！🥲"
                except Exception as e:
                    logger.error(f"查詢可用時段失敗: {str(e)}")
                    print(f"[ERROR] 查詢可用時段失敗: {e}")
                    response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
            else:
                # 只有日期，沒有時間
                # 支援多種日期格式
                date_match = re.search(r"(20\d{2})[-/.年 ]?(\d{1,2})[-/.月 ]?(\d{1,2})日?", user_message)
                if not date_match:
                    date_match = re.search(r"(\d{1,2})[-/.月 ]?(\d{1,2})日?", user_message)
                    if date_match:
                        year = datetime.now().year
                        month = int(date_match.group(1))
                        day = int(date_match.group(2))
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        logger.info(f"日期匹配: 年={year}, 月={month}, 日={day}, 格式化={date_str}")
                    else:
                        logger.info("日期匹配失敗，重新要求日期")
                        user_service.set_state(user_id, 'booking_ask_date')
                        response = "請問你想預約哪一天呢？（例如：2025-05-03 或 5/3）🌸"
                else:
                    if len(date_match.groups()) == 3:
                        year = int(date_match.group(1)) if len(date_match.group(1)) == 4 else datetime.now().year
                        month = int(date_match.group(2))
                        day = int(date_match.group(3))
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        logger.info(f"日期匹配: 年={year}, 月={month}, 日={day}, 格式化={date_str}")
                    else:
                        date_str = None
                        logger.info("日期格式異常")
                
                if date_str and not response:
                    user_service.set_state(user_id, 'booking_ask_time', booking_date=date_str)
                    logger.info(f"設置用戶狀態為 booking_ask_time，預約日期為 {date_str}")
                    try:
                        logger.info(f"查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                        print(f"[LOG] 查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                        slots = calendar_service.get_available_slots_by_date(date_str)
                        logger.info(f"查詢結果：{slots}")
                        print(f"[LOG] 查詢結果：{slots}")
                        # 如果大部分時段都空，直接請客人輸入想要的時段
                        if len(slots) > 10:
                            response = f"這天大部分時段都還有空位唷！請直接輸入你想預約的時間（例如：14:00 或 2點半）😊"
                        elif slots:
                            slot_text = '\n'.join([f"{s}" for s in slots])
                            response = f"這天目前可預約的時段有：\n{slot_text}\n請問你想選哪一個時段呢？😊"
                        else:
                            response = f"這天目前已無可預約時段，請換一天試試看喔！🥲"
                    except Exception as e:
                        logger.error(f"Google Calendar 查詢失敗：{str(e)}")
                        print(f"[ERROR] Google Calendar 查詢失敗：{e}")
                        response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
        else:
            # 支援多種日期格式
            date_match = re.search(r"(20\d{2})[-/.年 ]?(\d{1,2})[-/.月 ]?(\d{1,2})日?", user_message)
            if not date_match:
                date_match = re.search(r"(\d{1,2})[-/.月 ]?(\d{1,2})日?", user_message)
                if date_match:
                    year = datetime.now().year
                    month = int(date_match.group(1))
                    day = int(date_match.group(2))
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    logger.info(f"日期匹配: 年={year}, 月={month}, 日={day}, 格式化={date_str}")
                else:
                    logger.info("日期匹配失敗，重新要求日期")
                    user_service.set_state(user_id, 'booking_ask_date')
                    response = "請問你想預約哪一天呢？（例如：2025-05-03 或 5/3）🌸"
            else:
                if len(date_match.groups()) == 3:
                    year = int(date_match.group(1)) if len(date_match.group(1)) == 4 else datetime.now().year
                    month = int(date_match.group(2))
                    day = int(date_match.group(3))
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    logger.info(f"日期匹配: 年={year}, 月={month}, 日={day}, 格式化={date_str}")
                else:
                    date_str = None
                    logger.info("日期格式異常")
            
            if date_str and not response:
                user_service.set_state(user_id, 'booking_ask_time', booking_date=date_str)
                logger.info(f"設置用戶狀態為 booking_ask_time，預約日期為 {date_str}")
                try:
                    logger.info(f"查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                    print(f"[LOG] 查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                    slots = calendar_service.get_available_slots_by_date(date_str)
                    logger.info(f"查詢結果：{slots}")
                    print(f"[LOG] 查詢結果：{slots}")
                    # 如果大部分時段都空，直接請客人輸入想要的時段
                    if len(slots) > 10:
                        response = f"這天大部分時段都還有空位唷！請直接輸入你想預約的時間（例如：14:00 或 2點半）😊"
                    elif slots:
                        slot_text = '\n'.join([f"{s}" for s in slots])
                        response = f"這天目前可預約的時段有：\n{slot_text}\n請問你想選哪一個時段呢？😊"
                    else:
                        response = f"這天目前已無可預約時段，請換一天試試看喔！🥲"
                except Exception as e:
                    logger.error(f"Google Calendar 查詢失敗：{str(e)}")
                    print(f"[ERROR] Google Calendar 查詢失敗：{e}")
                    response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
    elif not response and user_info.get('state') == 'booking_ask_time' and user_info.get('booking_date'):
        # 支援多種時間格式
        logger.info(f"用戶輸入時間：{user_message}，預約日期：{user_info.get('booking_date')}")
        
        # 處理特殊表達方式如 "2點半"
        half_match = re.search(r"(\d{1,2})(?:點|:|\.)半", user_message)
        if half_match:
            hour = int(half_match.group(1))
            minute = 30
            time_str = f"{hour:02d}:{minute:02d}"
            logger.info(f"特殊時間格式匹配 (X點半): 時={hour}, 分={minute}, 格式化={time_str}")
        else:
            # 標準時間格式
            time_match = re.search(r"(\d{1,2})[:\.](\d{1,2})", user_message)
            if not time_match:
                time_match = re.search(r"(\d{1,2})點(?:(\d{1,2})分?)?", user_message)
            
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.lastindex > 1 and time_match.group(2) else 0
                time_str = f"{hour:02d}:{minute:02d}"
                logger.info(f"時間匹配: 時={hour}, 分={minute}, 格式化={time_str}")
            else:
                # 直接數字可能是小時
                digit_match = re.search(r"^(\d{1,2})$", user_message)
                if digit_match:
                    hour = int(digit_match.group(1))
                    minute = 0
                    time_str = f"{hour:02d}:{minute:02d}"
                    logger.info(f"純數字時間匹配: 時={hour}, 分={minute}, 格式化={time_str}")
                else:
                    time_str = None
                    logger.info(f"無法匹配時間格式: {user_message}")
                    response = "請輸入你想預約的時間（例如：14:00、2點半）😊"
        
        if time_str and not response:
            # 檢查該時段是否可預約
            try:
                slots = calendar_service.get_available_slots_by_date(user_info.get('booking_date'))
                logger.info(f"可用時段: {slots}")
                print(f"[LOG] 可用時段: {slots}")
                
                if time_str in slots:
                    # 建立 Google Calendar 預約
                    try:
                        start_dt = datetime.strptime(user_info.get('booking_date') + ' ' + time_str, "%Y-%m-%d %H:%M")
                        end_dt = start_dt.replace(minute=start_dt.minute+30 if start_dt.minute < 30 else 0, hour=start_dt.hour if start_dt.minute < 30 else start_dt.hour+1)
                        logger.info(f"嘗試創建預約：開始={start_dt}, 結束={end_dt}")
                        print(f"[LOG] 嘗試創建預約：開始={start_dt}, 結束={end_dt}")
                        
                        event_link = calendar_service.create_booking(start_dt, end_dt, user_info, '美容服務預約')
                        logger.info(f"Google Calendar 預約創建成功: {event_link}")
                        print(f"[LOG] Google Calendar 預約創建成功: {event_link}")
                        
                        # 寫入 Firebase booking history
                        booking_data = {
                            'start_time': start_dt.isoformat(),
                            'end_time': end_dt.isoformat(),
                            'service': '美容服務預約',
                            'status': 'confirmed',
                            'created_at': datetime.now().isoformat()
                        }
                        logger.info(f"嘗試寫入 Firebase: {booking_data}")
                        print(f"[LOG] 嘗試寫入 Firebase: {booking_data}")
                        
                        user_service.add_booking(user_id, booking_data)
                        logger.info(f"Firebase 寫入成功")
                        print(f"[LOG] Firebase 寫入成功")
                        
                        user_service.set_state(user_id, '', booking_date='', booking_time='')
                        response = f"預約成功！🎉\n已幫你預約 {user_info.get('booking_date')} {time_str}，期待在 Fanny Beauty 與你相見！\n如需更改請隨時告訴我。"
                    except Exception as e:
                        logger.error(f"Google Calendar/Firebase 寫入失敗：{str(e)}")
                        print(f"[ERROR] Google Calendar/Firebase 寫入失敗：{e}")
                        response = "抱歉，預約時發生錯誤，請稍後再試。"
                else:
                    logger.info(f"時段 {time_str} 不在可用時段中")
                    print(f"[LOG] 時段 {time_str} 不在可用時段中")
                    response = f"這個時段已被預約或不存在，請再輸入一次你想預約的時間（例如：14:00 或 2點半）😊"
            except Exception as e:
                logger.error(f"檢查可用時段失敗: {str(e)}")
                print(f"[ERROR] 檢查可用時段失敗: {e}")
                response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
        
    # 其他一般對話
    if not response:
        response = chatgpt_service.process_message(
            user_message,
            user_info=user_info
        )
        
    logger.info(f"回覆用戶: {response}")
    
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