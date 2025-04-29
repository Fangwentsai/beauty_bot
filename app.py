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

# 服務項目及時長（小時）
SERVICE_DURATIONS = {
    "日式美睫": 2,
    "睫毛管理": 1,
    "霧唇": 3,
    "霧眉": 3, 
    "髮際線": 3,
    "美睫教學": 4,
    "美容服務預約": 1  # 默認服務
}

# 服務列表格式化顯示
SERVICE_LIST = """
𝔽𝕒𝕟𝕟𝕪 𝕓𝕖𝕒𝕦𝕥𝕪 服務項目：
✨ 日式美睫 (2小時)
✨ 睫毛管理 (1小時)
✨ 霧唇 (3小時)
✨ 霧眉 (3小時)
✨ 髮際線 (3小時)
✨ 美睫教學 (4小時)
"""

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
    from datetime import datetime, timedelta
    user_id = event.source.user_id
    user_info = user_service.get_user_info(user_id)
    user_message = event.message.text.strip()
    updated = False
    response = None  # 初始化 response 變數

    logger.info(f"收到用戶 {user_id} 訊息: {user_message}")
    logger.info(f"目前用戶資料: {user_info}")

    greetings = ['你好', '哈囉', 'hi', 'hello', '您好', '嗨', '哈囉～', '哈囉!']
    in_booking_flow = (user_info.get('state') in ['booking_ask_service', 'booking_ask_date', 'booking_ask_time']) or ("預約" in user_message)
    
    # 檢查是否是服務查詢
    if "服務" in user_message and ("項目" in user_message or "介紹" in user_message or "有哪些" in user_message):
        response = f"{SERVICE_LIST}\n請問您想預約哪項服務呢？"
        user_service.set_state(user_id, 'booking_ask_service')
    # 檢查是否詢問預約進度或確認
    elif "預約" in user_message and ("狀態" in user_message or "進度" in user_message or "確認" in user_message):
        # 檢查用戶是否有進行中的預約
        if user_info.get('state') == 'booking_ask_time' and user_info.get('booking_date'):
            date_str = user_info.get('booking_date')
            response = f"您正在預約 {date_str} 的服務，請選擇時間完成預約。如需重新預約，請輸入「重新預約」。"
        elif user_info.get('last_booking'):
            last_booking = user_info.get('last_booking')
            service = last_booking.get('service', '美容服務')
            start_time = datetime.fromisoformat(last_booking.get('start_time')).strftime('%Y-%m-%d %H:%M')
            response = f"您上次的預約是 {start_time} 的「{service}」服務。若要重新預約，請直接告訴我日期和時間。"
        else:
            response = "您目前沒有任何預約記錄。若要預約服務，請告訴我您希望的日期。"
    # 如果是初次互動或打招呼，展示品牌形象
    elif user_message.lower() in greetings:
        if not user_info.get('name'):
            response = "哈囉！歡迎來到 Fanny Beauty 美學 💄 我是您的專屬美容顧問！請問我可以怎麼稱呼您呢？😊"
        else:
            response = f"嗨，{user_info.get('name')}！歡迎回到 Fanny Beauty 美學，有什麼我可以幫助你的嗎？💖"
    # 建檔流程
    elif not in_booking_flow:
        # 處理同時輸入名字和電話的情況
        name_phone_pattern = re.search(r'([^\d]+)\s*(?:電話)?(\d{8,12})', user_message)
        if name_phone_pattern:
            name = name_phone_pattern.group(1).strip()
            phone = name_phone_pattern.group(2).strip()
            
            user_service.update_user_info(user_id, {'name': name})
            logger.info(f"已寫入用戶 {user_id} 的暱稱：{name}")
            print(f"[LOG] 已寫入用戶 {user_id} 的暱稱：{name}")
            
            user_service.update_user_info(user_id, {'phone': phone})
            logger.info(f"已寫入用戶 {user_id} 的電話：{phone}")
            print(f"[LOG] 已寫入用戶 {user_id} 的電話：{phone}")
            
            updated = True
        elif not user_info.get('name') and user_message.lower() not in greetings and not user_message.isdigit():
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
        # 從簡化流程，如果客戶沒有明確選擇服務，設置默認服務為"美容服務預約"
        user_service.set_state(user_id, 'booking_ask_date')
        user_service.update_user_info(user_id, {'selected_service': '美容服務預約'})
        
        name = user_info.get('name', '').strip()
        logger.info(f"用戶完成建檔，名字為: '{name}'")
        # 暫時跳過服務選擇，直接進入預約日期階段
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
                    print(f"[LOG] 查詢 Google Calendar {date_str} 可用時段")
                    slots = calendar_service.get_available_slots_by_date(date_str)
                    logger.info(f"可用時段: {slots}")
                    print(f"[LOG] 可用時段: {slots}")
                    
                    # 始終顯示可用時段，幫助用戶選擇
                    slots_text = ""
                    if slots:
                        slots_text = "\n".join([f"{s}" for s in slots[:10]])
                        slots_text = f"\n\n這天目前可預約的時段有：\n{slots_text}"
                    
                    # 檢查選擇的時段是否可用
                    if time_str in slots:
                        # 獲取所選服務的時長
                        selected_service = user_info.get('selected_service', '美容服務預約')
                        duration_hours = SERVICE_DURATIONS.get(selected_service, 1)  # 默認1小時
                        
                        response = f"您選擇了 {date_str} {time_str} 的「{selected_service}」服務（{duration_hours}小時）。\n\n正在為您預約中...⏳"
                    else:
                        if slots:
                            response = f"抱歉，{time_str} 時段已被預約。{slots_text}\n\n請選擇其他時段或輸入新的日期。"
                        else:
                            response = f"抱歉，{date_str} 這天已無可預約時段，請換一天試試看喔！🥲"
                except Exception as e:
                    logger.error(f"查詢可用時段失敗: {str(e)}")
                    print(f"[ERROR] 查詢可用時段失敗: {e}")
                    response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
            else:
                # 只有日期，沒有時間
                # 查詢該日期的可用時段
                try:
                    user_service.set_state(user_id, 'booking_ask_time', booking_date=date_str)
                    logger.info(f"設置用戶狀態為 booking_ask_time，預約日期為 {date_str}")
                    print(f"[LOG] 設置用戶狀態為 booking_ask_time，預約日期為 {date_str}")
                    
                    logger.info(f"查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                    print(f"[LOG] 查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                    slots = calendar_service.get_available_slots_by_date(date_str)
                    logger.info(f"查詢結果：{slots}")
                    print(f"[LOG] 查詢結果：{slots}")
                    
                    # 顯示可用時段
                    if len(slots) > 10:
                        slot_text = '\n'.join([f"{s}" for s in slots[:10]])
                        response = f"{date_str} 這天大部分時段都還有空位唷！以下是部分可預約時段：\n{slot_text}\n\n請直接輸入你想預約的時間（例如：14:00 或 2點半）😊"
                    elif slots:
                        slot_text = '\n'.join([f"{s}" for s in slots])
                        response = f"{date_str} 這天目前可預約的時段有：\n{slot_text}\n\n請問你想選哪一個時段呢？😊"
                    else:
                        response = f"{date_str} 這天目前已無可預約時段，請換一天試試看喔！🥲"
                except Exception as e:
                    logger.error(f"Google Calendar 查詢失敗：{str(e)}")
                    print(f"[ERROR] Google Calendar 查詢失敗：{e}")
                    response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"

        # 如果沒有匹配到日期時間組合，嘗試單獨匹配日期
        elif not response:
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
                try:
                    user_service.set_state(user_id, 'booking_ask_time', booking_date=date_str)
                    logger.info(f"設置用戶狀態為 booking_ask_time，預約日期為 {date_str}")
                    print(f"[LOG] 設置用戶狀態為 booking_ask_time，預約日期為 {date_str}")
                    
                    logger.info(f"查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                    print(f"[LOG] 查詢 Google Calendar {date_str} 可預約時段 for user {user_id}")
                    slots = calendar_service.get_available_slots_by_date(date_str)
                    logger.info(f"查詢結果：{slots}")
                    print(f"[LOG] 查詢結果：{slots}")
                    
                    # 顯示可用時段
                    if len(slots) > 10:
                        slot_text = '\n'.join([f"{s}" for s in slots[:10]])
                        response = f"{date_str} 這天大部分時段都還有空位唷！以下是部分可預約時段：\n{slot_text}\n\n請直接輸入你想預約的時間（例如：14:00 或 2點半）😊"
                    elif slots:
                        slot_text = '\n'.join([f"{s}" for s in slots])
                        response = f"{date_str} 這天目前可預約的時段有：\n{slot_text}\n\n請問你想選哪一個時段呢？😊"
                    else:
                        response = f"{date_str} 這天目前已無可預約時段，請換一天試試看喔！🥲"
                except Exception as e:
                    logger.error(f"Google Calendar 查詢失敗：{str(e)}")
                    print(f"[ERROR] Google Calendar 查詢失敗：{e}")
                    response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
    elif not response and user_info.get('state') == 'booking_ask_time' and user_info.get('booking_date'):
        # 支援多種時間格式
        logger.info(f"用戶輸入時間：{user_message}，預約日期：{user_info.get('booking_date')}")
        print(f"[LOG] 用戶輸入時間：{user_message}，預約日期：{user_info.get('booking_date')}")
        
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
                    print(f"[LOG] 無法匹配時間格式: {user_message}")
                    response = "請輸入你想預約的時間（例如：14:00、2點半）😊"
        
        if time_str and not response:
            # 檢查該時段是否可預約
            try:
                date_str = user_info.get('booking_date')
                logger.info(f"查詢 {date_str} {time_str} 是否可預約")
                print(f"[LOG] 查詢 {date_str} {time_str} 是否可預約")
                
                slots = calendar_service.get_available_slots_by_date(date_str)
                logger.info(f"可用時段: {slots}")
                print(f"[LOG] 可用時段: {slots}")
                
                # 前一步可能只是確認時間，實際創建預約
                if "正在為您預約中" in user_info.get('last_message', ''):
                    logger.info(f"繼續處理預約流程")
                    time_str = user_info.get('booking_time', time_str)
                
                if time_str in slots:
                    # 建立 Google Calendar 預約
                    try:
                        # 獲取所選服務的時長
                        selected_service = user_info.get('selected_service', '美容服務預約')
                        duration_hours = SERVICE_DURATIONS.get(selected_service, 1)  # 默認1小時
                        
                        start_dt = datetime.strptime(date_str + ' ' + time_str, "%Y-%m-%d %H:%M")
                        end_dt = start_dt + timedelta(hours=duration_hours)
                        
                        logger.info(f"嘗試創建預約：服務={selected_service}, 時長={duration_hours}小時, 開始={start_dt}, 結束={end_dt}")
                        print(f"[LOG] 嘗試創建預約：服務={selected_service}, 時長={duration_hours}小時, 開始={start_dt}, 結束={end_dt}")
                        
                        # 保存到用戶信息中，防止丟失
                        user_service.update_user_info(user_id, {'booking_time': time_str})
                        
                        try:
                            event_result = calendar_service.create_booking(start_dt, end_dt, user_info, selected_service)
                            logger.info(f"Google Calendar 預約創建成功: {event_result}")
                            print(f"[LOG] Google Calendar 預約創建成功: {event_result}")
                            
                            # 確認事件已成功建立
                            event_id = event_result.get('id')
                            event_link = event_result.get('link')
                            
                            if not event_id:
                                logger.error("無法獲取預約 ID")
                                raise Exception("無法獲取預約 ID，預約可能未成功建立")
                            
                            # 驗證一次事件確實存在
                            verified_event = calendar_service.get_event_by_id(event_id)
                            if not verified_event:
                                logger.error(f"無法驗證事件存在: {event_id}")
                                raise Exception("無法確認預約已建立，請稍後再試")
                            
                            # 寫入 Firebase booking history
                            booking_data = {
                                'service': selected_service,
                                'start_time': start_dt.isoformat(),
                                'end_time': end_dt.isoformat(),
                                'status': 'confirmed',
                                'created_at': datetime.now().isoformat(),
                                'calendar_event_id': event_id,
                                'calendar_event_link': event_link
                            }
                            logger.info(f"嘗試寫入 Firebase: {booking_data}")
                            print(f"[LOG] 嘗試寫入 Firebase: {booking_data}")
                            
                            user_service.add_booking(user_id, booking_data)
                            logger.info(f"Firebase 寫入成功")
                            print(f"[LOG] Firebase 寫入成功")
                            
                            user_service.set_state(user_id, '', booking_date='', booking_time='', selected_service='')
                            response = f"預約成功！🎉\n已幫你預約 {date_str} {time_str} 的「{selected_service}」服務（{duration_hours}小時），期待在 Fanny Beauty 與你相見！\n\n🗓️ 行事曆連結：{event_link}\n\n如需更改請隨時告訴我。"
                            
                            # 保存最後的回覆訊息
                            user_service.update_user_info(user_id, {'last_message': response})
                        except Exception as e:
                            error_msg = str(e)
                            logger.error(f"預約失敗: {error_msg}")
                            print(f"[ERROR] 預約失敗: {error_msg}")
                            
                            if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
                                response = "抱歉，Google Calendar 憑證可能有問題，請聯繫管理員。"
                            else:
                                response = f"抱歉，預約時發生錯誤：{error_msg[:50]}...\n請稍後再試。"
                    except Exception as e:
                        logger.error(f"預約創建失敗：{str(e)}")
                        print(f"[ERROR] 預約創建失敗：{e}")
                        response = "抱歉，創建預約時出現問題，請稍後再試。"
                else:
                    # 顯示可用時段
                    if slots:
                        slot_text = '\n'.join([f"{s}" for s in slots[:10]])
                        response = f"抱歉，{time_str} 時段已被預約。\n\n{date_str} 目前可預約的時段有：\n{slot_text}\n\n請選擇其他時段或輸入新的日期。"
                    else:
                        response = f"抱歉，{date_str} 這天已無可預約時段，請換一天試試看喔！🥲"
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