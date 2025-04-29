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

# 品牌介紹
BRAND_INTRO = """哈囉！歡迎來到 𝔽𝕒𝕟𝕟𝕪 𝕓𝕖𝕒𝕦𝕥𝕪 美學 💄

我是您的專屬美容顧問，可以為您安排各種美容服務的預約，包括美睫、霧眉、霧唇等項目。

請問我可以怎麼稱呼您呢？😊"""

# 歡迎回訪訊息
WELCOME_BACK = """{name}您好！歡迎回到 𝔽𝕒𝕟𝕟𝕪 𝕓𝕖𝕒𝕦𝕥𝕪 美學 💖

很高興能再次為您服務！我們提供日式美睫、霧眉、霧唇等多項專業服務。

請問今天有什麼可以為您效勞的嗎？😊"""

# 服務介紹
SERVICE_INTRO = """𝔽𝕒𝕟𝕟𝕪 𝕓𝕖𝕒𝕦𝕥𝕪 提供的專業服務：

✨ 日式美睫 (2小時)
日式輕柔嫁接技術，打造自然捲翹的睫毛，讓您的眼睛更加迷人有神。

✨ 睫毛管理 (1小時)
專業護理與修剪，保持睫毛健康，延長睫毛嫁接的使用壽命。

✨ 霧唇 (3小時)
半永久性定妝技術，打造自然漸層唇色，讓您的雙唇呈現完美色澤。

✨ 霧眉 (3小時) 
精細的眉型設計與半永久霧染，告別每日畫眉困擾，眉形自然持久。

✨ 髮際線 (3小時)
修飾髮際線，讓額頭更加自然勻稱，改善髮線後退問題。

✨ 美睫教學 (4小時)
專業美睫師培訓課程，學習嫁接技巧與經營秘訣。

請選擇您想預約的服務，或輸入「預約」開始預約流程。"""

# 電話用途說明
PHONE_PURPOSE = """感謝您的信任！為了能夠在預約前後與您聯繫，以及在服務日有任何變動時能及時通知您，我們需要您的聯絡電話。

您的個人資料將受到嚴格保密，僅用於預約相關的必要聯繫。請問您的聯絡電話是？"""

app = Flask(__name__)

# Line Bot v3 設定
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 如果在 Render 環境中，將憑證寫入臨時文件
if os.getenv('RENDER'):
    # Google Calendar 憑證
    if os.getenv('GOOGLE_CALENDAR_CREDENTIALS'):
        try:
            logger.info("開始處理 Google Calendar 憑證")
            print("[LOG] 開始處理 Google Calendar 憑證")
            calendar_creds_json = os.getenv('GOOGLE_CALENDAR_CREDENTIALS')
            logger.info(f"憑證環境變數長度: {len(calendar_creds_json)}")
            print(f"[LOG] 憑證環境變數長度: {len(calendar_creds_json)}")
            
            calendar_creds = json.loads(calendar_creds_json)
            logger.info(f"憑證 JSON 解析成功，包含的鍵: {', '.join(calendar_creds.keys())}")
            print(f"[LOG] 憑證 JSON 解析成功，包含的鍵: {', '.join(calendar_creds.keys())}")
            
            with open('google_calendar_credentials.json', 'w') as f:
                json.dump(calendar_creds, f)
            
            # 檢查文件是否生成成功
            if os.path.exists('google_calendar_credentials.json'):
                file_size = os.path.getsize('google_calendar_credentials.json')
                logger.info(f"憑證檔案建立成功，大小: {file_size} 字節")
                print(f"[LOG] 憑證檔案建立成功，大小: {file_size} 字節")
            else:
                logger.error("憑證檔案未成功建立")
                print("[ERROR] 憑證檔案未成功建立")
                
            os.environ['GOOGLE_CALENDAR_CREDENTIALS'] = 'google_calendar_credentials.json'
            logger.info(f"GOOGLE_CALENDAR_CREDENTIALS 環境變數設置為: {os.getenv('GOOGLE_CALENDAR_CREDENTIALS')}")
            print(f"[LOG] GOOGLE_CALENDAR_CREDENTIALS 環境變數設置為: {os.getenv('GOOGLE_CALENDAR_CREDENTIALS')}")
        except json.JSONDecodeError as e:
            logger.error(f"Google Calendar 憑證 JSON 解析失敗: {str(e)}")
            print(f"[ERROR] Google Calendar 憑證 JSON 解析失敗: {str(e)}")
        except Exception as e:
            logger.error(f"處理 Google Calendar 憑證時發生錯誤: {str(e)}")
            print(f"[ERROR] 處理 Google Calendar 憑證時發生錯誤: {str(e)}")
    else:
        logger.error("GOOGLE_CALENDAR_CREDENTIALS 環境變數未設置")
        print("[ERROR] GOOGLE_CALENDAR_CREDENTIALS 環境變數未設置")
    
    # Firebase 憑證
    if os.getenv('FIREBASE_CREDENTIALS'):
        try:
            logger.info("開始處理 Firebase 憑證")
            print("[LOG] 開始處理 Firebase 憑證")
            firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS')
            firebase_creds = json.loads(firebase_creds_json)
            
            with open('firebase_credentials.json', 'w') as f:
                json.dump(firebase_creds, f)
                
            # 檢查文件是否生成成功
            if os.path.exists('firebase_credentials.json'):
                file_size = os.path.getsize('firebase_credentials.json')
                logger.info(f"Firebase 憑證檔案建立成功，大小: {file_size} 字節")
                print(f"[LOG] Firebase 憑證檔案建立成功，大小: {file_size} 字節")
            
            os.environ['FIREBASE_CREDENTIALS'] = 'firebase_credentials.json'
            logger.info(f"FIREBASE_CREDENTIALS 環境變數設置為: {os.getenv('FIREBASE_CREDENTIALS')}")
            print(f"[LOG] FIREBASE_CREDENTIALS 環境變數設置為: {os.getenv('FIREBASE_CREDENTIALS')}")
        except Exception as e:
            logger.error(f"處理 Firebase 憑證時發生錯誤: {str(e)}")
            print(f"[ERROR] 處理 Firebase 憑證時發生錯誤: {str(e)}")
    else:
        logger.error("FIREBASE_CREDENTIALS 環境變數未設置")
        print("[ERROR] FIREBASE_CREDENTIALS 環境變數未設置")

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

    # 記錄最後互動時間
    current_time = datetime.now()
    last_interaction = user_info.get('last_interaction')
    
    # 如果這是一個新的對話（超過30分鐘沒有互動）
    is_new_session = False
    if not last_interaction:
        is_new_session = True
    else:
        try:
            last_time = datetime.fromisoformat(last_interaction)
            # 如果距離上次互動超過30分鐘，視為新的對話
            if (current_time - last_time).total_seconds() > 1800:  # 30分鐘 = 1800秒
                is_new_session = True
        except ValueError:
            is_new_session = True
    
    # 更新最後互動時間
    user_service.update_user_info(user_id, {'last_interaction': current_time.isoformat()})
    
    greetings = ['你好', '哈囉', 'hi', 'hello', '您好', '嗨', '哈囉～', '哈囉!']
    in_booking_flow = (user_info.get('state') in ['booking_ask_service', 'booking_ask_date', 'booking_ask_time']) or ("預約" in user_message)
    
    # 如果是新的對話階段且用戶已有名字，發送歡迎回訪訊息
    if is_new_session and user_info.get('name') and not response:
        welcome_msg = WELCOME_BACK.format(name=user_info.get('name'))
        response = welcome_msg
    
    # 檢查是否是服務查詢
    if ("服務" in user_message and ("項目" in user_message or "介紹" in user_message or "有哪些" in user_message)) or "服務介紹" in user_message:
        response = SERVICE_INTRO
        user_service.set_state(user_id, 'booking_ask_service')
    # 檢查是否要取消預約
    elif ("取消" in user_message or "不要" in user_message or "算了" in user_message) and ("預約" in user_message or user_info.get('state') in ['booking_ask_date', 'booking_ask_time', 'booking_ask_service']):
        # 清除預約狀態
        user_service.set_state(user_id, '')
        user_service.update_user_info(user_id, {
            'booking_date': '',
            'booking_time': '',
            'selected_service': ''
        })
        logger.info(f"用戶 {user_id} 取消了預約")
        print(f"[LOG] 用戶 {user_id} 取消了預約")
        response = "已取消本次預約。若您改變主意，隨時可以重新開始預約流程。😊"
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
            response = BRAND_INTRO
        else:
            response = WELCOME_BACK.format(name=user_info.get('name'))
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
            response = PHONE_PURPOSE
            updated = True
        elif not user_info.get('phone') and user_message.isdigit() and 8 <= len(user_message) <= 12:
            user_service.update_user_info(user_id, {'phone': user_message})
            logger.info(f"已寫入用戶 {user_id} 的電話：{user_message}")
            print(f"[LOG] 已寫入用戶 {user_id} 的電話：{user_message}")
            updated = True

    if updated:
        user_info = user_service.get_user_info(user_id)
        logger.info(f"更新後用戶資料: {user_info}")

    # 處理服務選擇階段
    if not response and user_info.get('state') == 'booking_ask_service':
        selected_service = None
        for service in SERVICE_DURATIONS.keys():
            if service in user_message:
                selected_service = service
                break
        
        if selected_service:
            user_service.update_user_info(user_id, {'selected_service': selected_service})
            user_service.set_state(user_id, 'booking_ask_date')
            logger.info(f"用戶選擇服務: {selected_service}")
            response = f"您選擇了「{selected_service}」服務（{SERVICE_DURATIONS[selected_service]}小時）✨\n\n請問您希望預約哪一天呢？（例如：5/15 或 2025-05-15）💖"
        else:
            response = f"抱歉，我們沒有找到您提到的服務。以下是我們提供的服務項目：\n{SERVICE_LIST}\n請選擇其中一項服務進行預約。"

    # 建檔流程結束後自動引導預約
    if not response and not in_booking_flow and user_info.get('name') and user_info.get('phone'):
        # 進入服務選擇階段
        user_service.set_state(user_id, 'booking_ask_service')
        name = user_info.get('name', '').strip()
        logger.info(f"用戶完成建檔，名字為: '{name}'")
        response = f"謝謝你，{name}！\n\n以下是我們提供的專業服務：\n{SERVICE_INTRO}"
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
                    
                    # 顯示可用時段
                    if len(slots) > 10:
                        morning_slots = [s for s in slots if int(s.split(':')[0]) < 12]
                        afternoon_slots = [s for s in slots if 12 <= int(s.split(':')[0]) < 18]
                        evening_slots = [s for s in slots if int(s.split(':')[0]) >= 18]
                        
                        slots_summary = f"早上: {', '.join(morning_slots[:3])}...\n下午: {', '.join(afternoon_slots[:3])}...\n晚上: {', '.join(evening_slots[:3])}..."
                        response = f"{date_str} 這天大部分時段都還有空位！\n\n{slots_summary}\n\n請直接告訴我您想要的時間（例如：14:00 或 2點半）😊"
                    elif slots:
                        # 如果時段較少，全部顯示
                        slot_text = '\n'.join([f"{s}" for s in slots])
                        response = f"{date_str} 這天目前可預約的時段有：\n{slot_text}\n\n請問您想選哪一個時段呢？😊"
                    else:
                        response = f"{date_str} 這天目前已無可預約時段，請換一天試試看喔！🥲"
                    
                    # 檢查選擇的時段是否可用
                    if time_str in slots:
                        # 獲取所選服務的時長
                        selected_service = user_info.get('selected_service', '美容服務預約')
                        duration_hours = SERVICE_DURATIONS.get(selected_service, 1)  # 默認1小時
                        
                        response = f"您選擇了 {date_str} {time_str} 的「{selected_service}」服務（{duration_hours}小時）。\n\n正在為您預約中...⏳"
                        
                        # 保存時間信息到用戶資料中
                        user_service.update_user_info(user_id, {'booking_time': time_str, 'last_message': response})
                    else:
                        if slots:
                            morning_slots = [s for s in slots if int(s.split(':')[0]) < 12]
                            afternoon_slots = [s for s in slots if 12 <= int(s.split(':')[0]) < 18]
                            evening_slots = [s for s in slots if int(s.split(':')[0]) >= 18]
                            
                            slots_summary = f"早上: {', '.join(morning_slots[:3] if morning_slots else ['無'])}\n下午: {', '.join(afternoon_slots[:3] if afternoon_slots else ['無'])}\n晚上: {', '.join(evening_slots[:3] if evening_slots else ['無'])}"
                            response = f"抱歉，{time_str} 時段已被預約。\n\n{date_str} 可預約的時段有：\n{slots_summary}\n\n請選擇其他時段或輸入新的日期。"
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
                        morning_slots = [s for s in slots if int(s.split(':')[0]) < 12]
                        afternoon_slots = [s for s in slots if 12 <= int(s.split(':')[0]) < 18]
                        evening_slots = [s for s in slots if int(s.split(':')[0]) >= 18]
                        
                        slots_summary = f"早上: {', '.join(morning_slots[:3])}...\n下午: {', '.join(afternoon_slots[:3])}...\n晚上: {', '.join(evening_slots[:3])}..."
                        response = f"{date_str} 這天大部分時段都還有空位！\n\n{slots_summary}\n\n請直接告訴我您想要的時間（例如：14:00 或 2點半）😊"
                    elif slots:
                        # 如果時段較少，全部顯示
                        slot_text = '\n'.join([f"{s}" for s in slots])
                        response = f"{date_str} 這天目前可預約的時段有：\n{slot_text}\n\n請問您想選哪一個時段呢？😊"
                    else:
                        response = f"{date_str} 這天目前已無可預約時段，請換一天試試看喔！🥲"
                except Exception as e:
                    logger.error(f"Google Calendar 查詢失敗：{str(e)}")
                    print(f"[ERROR] Google Calendar 查詢失敗：{e}")
                    response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"

        # 如果沒有匹配到日期時間組合，嘗試單獨匹配日期
        elif not response:
            # 支援多種日期格式
            date_str = None  # 初始化 date_str 變量
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
                    response = "請問您想預約哪一天呢？（例如：5/15 或 2025-05-15）🌸"
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
                        morning_slots = [s for s in slots if int(s.split(':')[0]) < 12]
                        afternoon_slots = [s for s in slots if 12 <= int(s.split(':')[0]) < 18]
                        evening_slots = [s for s in slots if int(s.split(':')[0]) >= 18]
                        
                        slots_summary = f"早上: {', '.join(morning_slots[:3])}...\n下午: {', '.join(afternoon_slots[:3])}...\n晚上: {', '.join(evening_slots[:3])}..."
                        response = f"{date_str} 這天大部分時段都還有空位！\n\n{slots_summary}\n\n請直接告訴我您想要的時間（例如：14:00 或 2點半）😊"
                    elif slots:
                        # 如果時段較少，全部顯示
                        slot_text = '\n'.join([f"{s}" for s in slots])
                        response = f"{date_str} 這天目前可預約的時段有：\n{slot_text}\n\n請問您想選哪一個時段呢？😊"
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
                
                # 檢查選擇的時段是否可用
                if time_str in slots:
                    # 獲取所選服務的時長
                    selected_service = user_info.get('selected_service', '美容服務預約')
                    duration_hours = SERVICE_DURATIONS.get(selected_service, 1)  # 默認1小時
                    
                    response = f"您選擇了 {date_str} {time_str} 的「{selected_service}」服務（{duration_hours}小時）。\n\n正在為您預約中...⏳"
                    
                    # 保存時間信息到用戶資料中
                    user_service.update_user_info(user_id, {'booking_time': time_str, 'last_message': response})
                else:
                    if slots:
                        morning_slots = [s for s in slots if int(s.split(':')[0]) < 12]
                        afternoon_slots = [s for s in slots if 12 <= int(s.split(':')[0]) < 18]
                        evening_slots = [s for s in slots if int(s.split(':')[0]) >= 18]
                        
                        slots_summary = f"早上: {', '.join(morning_slots[:3] if morning_slots else ['無'])}\n下午: {', '.join(afternoon_slots[:3] if afternoon_slots else ['無'])}\n晚上: {', '.join(evening_slots[:3] if evening_slots else ['無'])}"
                        response = f"抱歉，{time_str} 時段已被預約。\n\n{date_str} 可預約的時段有：\n{slots_summary}\n\n請選擇其他時段或輸入新的日期。"
                    else:
                        response = f"抱歉，{date_str} 這天已無可預約時段，請換一天試試看喔！🥲"
            except Exception as e:
                logger.error(f"檢查可用時段失敗: {str(e)}")
                print(f"[ERROR] 檢查可用時段失敗: {e}")
                response = "抱歉，查詢預約時段時發生錯誤，請稍後再試。"
    # 前一步可能只是確認時間，實際創建預約
    if not response and "正在為您預約中" in user_info.get('last_message', ''):
        logger.info(f"繼續處理預約流程")
        print(f"[LOG] 繼續處理預約流程")
        
        # 檢查是否有完整預約信息
        booking_date = user_info.get('booking_date')
        booking_time = user_info.get('booking_time')
        selected_service = user_info.get('selected_service', '美容服務預約')
        
        logger.info(f"預約資訊：日期={booking_date}, 時間={booking_time}, 服務={selected_service}")
        print(f"[LOG] 預約資訊：日期={booking_date}, 時間={booking_time}, 服務={selected_service}")
        
        if booking_date and booking_time:
            try:
                # 再次檢查時段是否可用
                logger.info(f"再次檢查 {booking_date} {booking_time} 是否可預約")
                print(f"[LOG] 再次檢查 {booking_date} {booking_time} 是否可預約")
                slots = calendar_service.get_available_slots_by_date(booking_date)
                logger.info(f"可用時段: {slots}")
                print(f"[LOG] 可用時段: {slots}")
                
                if booking_time in slots:
                    # 建立 Google Calendar 預約
                    try:
                        duration_hours = SERVICE_DURATIONS.get(selected_service, 1)
                        start_dt = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
                        end_dt = start_dt + timedelta(hours=duration_hours)
                        
                        logger.info(f"嘗試創建預約：服務={selected_service}, 時長={duration_hours}小時, 開始={start_dt}, 結束={end_dt}")
                        print(f"[LOG] 嘗試創建預約：服務={selected_service}, 時長={duration_hours}小時, 開始={start_dt}, 結束={end_dt}")
                        
                        # 檢查用戶資訊
                        logger.info(f"用戶資訊：{json.dumps(user_info, ensure_ascii=False)}")
                        print(f"[LOG] 用戶資訊：{json.dumps(user_info, ensure_ascii=False)}")
                        
                        # 檢查 calendar_service 狀態
                        logger.info(f"Calendar service 類型: {type(calendar_service).__name__}")
                        print(f"[LOG] Calendar service 類型: {type(calendar_service).__name__}")
                        
                        # 創建預約前的紀錄點
                        logger.info("即將調用 create_booking 方法")
                        print("[LOG] 即將調用 create_booking 方法")
                        
                        event_result = calendar_service.create_booking(start_dt, end_dt, user_info, selected_service)
                        
                        logger.info(f"create_booking 調用成功返回: {json.dumps(event_result, ensure_ascii=False)}")
                        print(f"[LOG] create_booking 調用成功返回: {json.dumps(event_result, ensure_ascii=False)}")
                        
                        # 確認事件已成功建立
                        event_id = event_result.get('id')
                        event_link = event_result.get('link')
                        
                        if not event_id:
                            logger.error("無法獲取預約 ID")
                            print("[ERROR] 無法獲取預約 ID")
                            raise Exception("無法獲取預約 ID，預約可能未成功建立")
                        
                        # 驗證一次事件確實存在
                        logger.info(f"驗證事件 {event_id} 是否存在")
                        print(f"[LOG] 驗證事件 {event_id} 是否存在")
                        verified_event = calendar_service.get_event_by_id(event_id)
                        
                        if verified_event:
                            logger.info(f"驗證成功：事件存在 - {json.dumps(verified_event, ensure_ascii=False)}")
                            print(f"[LOG] 驗證成功：事件存在")
                        else:
                            logger.error(f"無法驗證事件存在: {event_id}")
                            print(f"[ERROR] 無法驗證事件存在: {event_id}")
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
                        logger.info(f"嘗試寫入 Firebase: {json.dumps(booking_data, ensure_ascii=False)}")
                        print(f"[LOG] 嘗試寫入 Firebase: {json.dumps(booking_data, ensure_ascii=False)}")
                        
                        user_service.add_booking(user_id, booking_data)
                        logger.info(f"Firebase 寫入成功")
                        print(f"[LOG] Firebase 寫入成功")
                        
                        # 重置狀態但保留預約記錄到 last_booking
                        user_service.set_state(user_id, '')
                        user_service.update_user_info(user_id, {
                            'booking_date': '',
                            'booking_time': '',
                            'selected_service': '',
                            'last_booking': booking_data
                        })
                        logger.info("用戶狀態已重置，預約記錄已保存")
                        print("[LOG] 用戶狀態已重置，預約記錄已保存")
                        
                        response = f"預約成功！🎉\n已幫您預約 {booking_date} {booking_time} 的「{selected_service}」服務（{duration_hours}小時），期待在 Fanny Beauty 與您相見！\n\n🗓️ 行事曆連結：{event_link}\n\n如需更改請隨時告訴我。"
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"預約失敗: {error_msg}")
                        print(f"[ERROR] 預約失敗: {error_msg}")
                        
                        # 詳細診斷信息
                        logger.error(f"異常類型: {type(e).__name__}")
                        print(f"[ERROR] 異常類型: {type(e).__name__}")
                        
                        import traceback
                        tb = traceback.format_exc()
                        logger.error(f"堆疊追蹤:\n{tb}")
                        print(f"[ERROR] 堆疊追蹤:\n{tb}")
                        
                        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
                            response = "抱歉，Google Calendar 憑證可能有問題，請聯繫管理員。"
                        else:
                            response = f"抱歉，預約時發生錯誤：{error_msg}。請稍後再試。"
                else:
                    # 時段已不可用
                    response = f"抱歉，{booking_time} 時段已被預約。請選擇其他時段。"
            except Exception as e:
                error_msg = str(e)
                logger.error(f"預約流程發生錯誤: {error_msg}")
                print(f"[ERROR] 預約流程發生錯誤: {error_msg}")
                
                import traceback
                tb = traceback.format_exc()
                logger.error(f"堆疊追蹤:\n{tb}")
                print(f"[ERROR] 堆疊追蹤:\n{tb}")
                
                response = "抱歉，預約過程中發生問題，請稍後再試。"
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

# 添加Google Calendar API測試端點
@app.route("/test-calendar", methods=['GET'])
def test_calendar_api():
    try:
        logger.info("開始測試Google Calendar API連接")
        print("[LOG] 開始測試Google Calendar API連接")
        
        # 檢查憑證環境變數
        credentials_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS')
        if not credentials_path:
            return {
                'status': 'error',
                'message': 'GOOGLE_CALENDAR_CREDENTIALS環境變數未設置'
            }, 500
            
        logger.info(f"GOOGLE_CALENDAR_CREDENTIALS環境變數: {credentials_path}")
        print(f"[LOG] GOOGLE_CALENDAR_CREDENTIALS環境變數: {credentials_path}")
        
        # 檢查憑證文件
        if os.path.exists(credentials_path):
            file_size = os.path.getsize(credentials_path)
            logger.info(f"憑證文件存在，大小: {file_size} 字節")
            print(f"[LOG] 憑證文件存在，大小: {file_size} 字節")
        else:
            return {
                'status': 'error',
                'message': f'憑證文件不存在: {credentials_path}'
            }, 500
        
        # 執行API連接測試
        connection_test = calendar_service.test_connection()
        
        if connection_test:
            # 測試創建一個測試事件
            logger.info("嘗試創建測試事件")
            print("[LOG] 嘗試創建測試事件")
            
            # 創建明天的測試事件
            from datetime import datetime, timedelta
            start_dt = datetime.now() + timedelta(days=1)
            start_dt = start_dt.replace(hour=10, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(hours=1)
            
            # 模擬用戶信息
            test_user = {
                'name': '測試用戶',
                'phone': '0912345678'
            }
            
            # 創建事件
            test_event = calendar_service.create_booking(
                start_dt, 
                end_dt, 
                test_user, 
                '測試服務'
            )
            
            return {
                'status': 'success',
                'message': 'Google Calendar API連接測試成功',
                'test_event': test_event
            }
        else:
            return {
                'status': 'error',
                'message': 'Google Calendar API連接測試失敗'
            }, 500
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"測試Google Calendar API時發生錯誤: {error_msg}")
        print(f"[ERROR] 測試Google Calendar API時發生錯誤: {error_msg}")
        
        return {
            'status': 'error',
            'message': f'測試發生錯誤: {error_msg}'
        }, 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 