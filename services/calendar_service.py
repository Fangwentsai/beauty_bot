import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import logging
import json

# 設置日誌
logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        try:
            creds_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS')
            logger.info(f"使用憑證路徑: {creds_path}")
            print(f"[LOG] 初始化 GoogleCalendarService 使用憑證路徑: {creds_path}")
            creds = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=SCOPES
            )
            self.service = build('calendar', 'v3', credentials=creds)
            
            # 默認使用主要日曆，但也提供日曆ID的環境變數支持
            calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
            self.calendar_id = calendar_id
            
            logger.info(f"使用日曆ID: {self.calendar_id}")
            print(f"[LOG] 使用日曆ID: {self.calendar_id}")
            
            logger.info("Google Calendar 服務初始化成功")
            print("[LOG] Google Calendar 服務初始化成功")
            
            # 初始化後立即檢查日曆信息
            self._check_calendar_info()
        except Exception as e:
            logger.error(f"Google Calendar 服務初始化失敗: {str(e)}")
            print(f"[ERROR] Google Calendar 服務初始化失敗: {str(e)}")
            raise

    def get_available_slots(self, days_ahead=7):
        """獲取未來幾天內的可用時段"""
        now = datetime.utcnow()
        end_time = now + timedelta(days=days_ahead)
        
        # 獲取已預約的時段
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=now.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        booked_slots = []
        for event in events_result.get('items', []):
            start = event['start'].get('dateTime')
            if start:
                booked_slots.append(datetime.fromisoformat(start.replace('Z', '+00:00')))

        # 生成可用時段（這裡假設營業時間為 10:00-20:00）
        available_slots = []
        current = now.replace(hour=10, minute=0, second=0, microsecond=0)
        
        while current < end_time:
            if current.hour < 20 and current not in booked_slots:
                available_slots.append(current.strftime('%Y-%m-%d %H:%M'))
            current += timedelta(minutes=30)
            
        return available_slots

    def create_booking(self, start_time, end_time, user_info, service):
        """創建預約"""
        try:
            # 確保時間格式正確，帶有時區信息
            start_iso = start_time.isoformat()
            end_iso = end_time.isoformat()
            
            logger.info(f"準備創建預約，開始時間: {start_iso}, 結束時間: {end_iso}")
            print(f"[LOG] 準備創建預約，開始時間: {start_iso}, 結束時間: {end_iso}")
            
            event = {
                'summary': f'{user_info["name"]} - {service}',
                'description': f'客戶：{user_info["name"]}\n電話：{user_info["phone"]}\n服務：{service}',
                'start': {
                    'dateTime': start_iso,
                    'timeZone': 'Asia/Taipei',
                },
                'end': {
                    'dateTime': end_iso,
                    'timeZone': 'Asia/Taipei',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 120},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            logger.info(f"預約事件詳情: {json.dumps(event, ensure_ascii=False)}")
            print(f"[LOG] 預約事件詳情: {json.dumps(event, ensure_ascii=False)}")
            
            # 檢查憑證和服務狀態
            try:
                # 檢查服務是否正確初始化
                if not self.service:
                    logger.error("Google Calendar 服務未初始化")
                    print("[ERROR] Google Calendar 服務未初始化")
                    raise Exception("Google Calendar 服務未初始化")
                
                logger.info(f"Calendar service 狀態: {self.service._baseUrl}")
                print(f"[LOG] Calendar service 狀態: {self.service._baseUrl}")
                
                # 確認calendar_id是否設置
                logger.info(f"使用行事曆ID: {self.calendar_id}")
                print(f"[LOG] 使用行事曆ID: {self.calendar_id}")
                
                # 創建請求並執行
                logger.info("開始構建API請求")
                print("[LOG] 開始構建API請求")
                request = self.service.events().insert(calendarId=self.calendar_id, body=event)
                logger.info("API請求構建完成，準備執行")
                print("[LOG] API請求構建完成，準備執行")
                
                # 執行API請求
                created_event = request.execute()
                logger.info(f"事件創建成功: {json.dumps(created_event, ensure_ascii=False)}")
                print(f"[LOG] 事件創建成功: {json.dumps(created_event, ensure_ascii=False)}")
                
                event_id = created_event.get('id')
                event_link = created_event.get('htmlLink')
                
                # 確認預約已成功建立
                if not event_id:
                    logger.error("無法獲取預約 ID，預約可能未成功建立")
                    print("[ERROR] 無法獲取預約 ID，預約可能未成功建立")
                    raise Exception("無法獲取預約 ID，預約可能未成功建立")
                
                logger.info(f"成功建立預約 - ID: {event_id}, 連結: {event_link}")
                print(f"[LOG] 成功建立預約 - ID: {event_id}, 連結: {event_link}")
                
                # 返回成功結果
                return {
                    'id': event_id,
                    'link': event_link,
                    'summary': created_event.get('summary'),
                    'start': created_event['start'].get('dateTime'),
                    'end': created_event['end'].get('dateTime')
                }
                
            except Exception as api_error:
                # 處理API異常
                error_detail = str(api_error)
                logger.error(f"Google Calendar API 調用異常: {error_detail}")
                print(f"[ERROR] Google Calendar API 調用異常: {error_detail}")
                
                # 導入並提取完整堆疊追蹤
                import traceback
                tb = traceback.format_exc()
                logger.error(f"堆疊追蹤:\n{tb}")
                print(f"[ERROR] 堆疊追蹤:\n{tb}")
                
                # 檢查憑證問題
                if 'credentials' in error_detail.lower() or 'unauthorized' in error_detail.lower():
                    logger.error("發現憑證問題")
                    print("[ERROR] 發現憑證問題")
                    self._check_credentials()
                
                raise Exception(f"Google Calendar API 調用失敗: {error_detail}")
                
        except Exception as e:
            error_detail = str(e)
            logger.error(f"創建預約過程中發生錯誤: {error_detail}")
            print(f"[ERROR] 創建預約過程中發生錯誤: {error_detail}")
            raise Exception(f'創建預約失敗：{error_detail}')
    
    def _check_credentials(self):
        """檢查憑證狀態"""
        try:
            cred_path = os.getenv('GOOGLE_CALENDAR_CREDENTIALS')
            logger.info(f"檢查憑證路徑: {cred_path}")
            print(f"[LOG] 檢查憑證路徑: {cred_path}")
            
            if not cred_path:
                logger.error("憑證環境變數未設置")
                print("[ERROR] 憑證環境變數未設置")
                return
                
            if os.path.exists(cred_path):
                file_size = os.path.getsize(cred_path)
                logger.info(f"憑證文件存在，大小: {file_size} 字節")
                print(f"[LOG] 憑證文件存在，大小: {file_size} 字節")
                
                # 嘗試讀取憑證文件內容
                try:
                    with open(cred_path, 'r') as f:
                        cred_content = f.read()
                    if len(cred_content) < 100:
                        logger.error(f"憑證文件內容可能不完整: {cred_content[:50]}...")
                        print(f"[ERROR] 憑證文件內容可能不完整")
                    else:
                        logger.info(f"憑證文件讀取成功，內容長度: {len(cred_content)}")
                        print(f"[LOG] 憑證文件讀取成功，內容長度: {len(cred_content)}")
                except Exception as read_error:
                    logger.error(f"讀取憑證文件失敗: {str(read_error)}")
                    print(f"[ERROR] 讀取憑證文件失敗: {str(read_error)}")
            else:
                logger.error(f"憑證文件不存在: {cred_path}")
                print(f"[ERROR] 憑證文件不存在: {cred_path}")
                
        except Exception as e:
            logger.error(f"檢查憑證時出錯: {str(e)}")
            print(f"[ERROR] 檢查憑證時出錯: {str(e)}")

    def verify_event_created(self, event_id):
        """驗證事件是否已成功建立在 Google Calendar 中"""
        try:
            logger.info(f"調用 Google Calendar API 獲取事件 {event_id}")
            print(f"[LOG] 調用 Google Calendar API 獲取事件 {event_id}")
            event = self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()
            
            if event and event.get('id') == event_id:
                logger.info(f"驗證成功：行事曆項目 {event_id} 存在")
                print(f"[LOG] 驗證成功：行事曆項目 {event_id} 存在")
                return True
            else:
                logger.error(f"驗證失敗：找不到行事曆項目 {event_id}")
                print(f"[ERROR] 驗證失敗：找不到行事曆項目 {event_id}")
                return False
        except Exception as e:
            error_msg = str(e)
            logger.error(f"驗證行事曆項目時發生錯誤: {error_msg}")
            print(f"[ERROR] 驗證行事曆項目時發生錯誤: {error_msg}")
            raise Exception(f"驗證行事曆項目失敗: {error_msg}")

    def get_event_by_id(self, event_id):
        """根據 ID 獲取事件詳情"""
        try:
            return self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()
        except Exception as e:
            logger.error(f"獲取行事曆項目失敗: {str(e)}")
            return None

    def get_available_slots_by_date(self, date):
        """查詢指定日期的可用時段（10:00-20:00，每30分鐘）"""
        try:
            date_start = datetime.strptime(date, "%Y-%m-%d").replace(hour=10, minute=0, second=0, microsecond=0)
            date_end = date_start.replace(hour=20, minute=0)
            
            # 注意：將時區信息加入到ISO格式字符串中
            timeMin = date_start.isoformat()
            timeMax = date_end.isoformat()
            
            logger.info(f"查詢時間範圍: {timeMin} 到 {timeMax}")
            print(f"[LOG] 查詢時間範圍: {timeMin} 到 {timeMax}")
            
            try:
                logger.info(f"調用 Google Calendar API 列出事件")
                print(f"[LOG] 調用 Google Calendar API 列出事件")
                events_result = self.service.events().list(
                    calendarId=self.calendar_id,
                    timeMin=timeMin,
                    timeMax=timeMax,
                    timeZone='Asia/Taipei',
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                logger.info(f"Google Calendar API 返回結果: {json.dumps(events_result.get('items', []), ensure_ascii=False)}")
                print(f"[LOG] Google Calendar API 列出事件成功，找到 {len(events_result.get('items', []))} 個事件")
            except Exception as api_error:
                logger.error(f"調用 Google Calendar API 列出事件失敗: {str(api_error)}")
                print(f"[ERROR] 調用 Google Calendar API 列出事件失敗: {str(api_error)}")
                raise
                
                booked_slots = []
                for event in events_result.get('items', []):
                    start = event['start'].get('dateTime')
                    if start:
                        try:
                            # 處理時區
                            event_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                            # 轉換為當地時間格式的字符串，僅保留時分
                            booked_time_str = event_time.strftime('%H:%M')
                            booked_slots.append(booked_time_str)
                            logger.info(f"找到已預約時段: {event_time} -> {booked_time_str}")
                            print(f"[LOG] 找到已預約時段: {event_time} -> {booked_time_str}")
                        except Exception as time_error:
                            logger.error(f"解析事件時間失敗: {str(time_error)}, 原始時間字符串: {start}")
                            print(f"[ERROR] 解析事件時間失敗: {str(time_error)}, 原始時間字符串: {start}")
            
                available_slots = []
                current = date_start
                while current < date_end:
                    # 檢查當前時段是否已被預約
                    current_time_str = current.strftime('%H:%M')
                    if current_time_str not in booked_slots:
                        available_slots.append(current_time_str)
                    
                    current += timedelta(minutes=30)
            
            logger.info(f"可用時段數量: {len(available_slots)}")
            print(f"[LOG] 可用時段數量: {len(available_slots)}")
            
            return available_slots
            
        except Exception as e:
            logger.error(f"獲取可用時段失敗: {str(e)}")
            print(f"[ERROR] 獲取可用時段失敗: {str(e)}")
            # 返回空列表而不是拋出異常，避免中斷對話流程
            return []

    def test_connection(self):
        """測試Google Calendar API連接"""
        try:
            logger.info("開始測試Google Calendar API連接")
            print("[LOG] 開始測試Google Calendar API連接")
            
            # 測試1: 獲取日曆列表
            logger.info("嘗試獲取日曆列表")
            print("[LOG] 嘗試獲取日曆列表")
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            if calendars:
                logger.info(f"成功獲取日曆列表，找到 {len(calendars)} 個日曆")
                print(f"[LOG] 成功獲取日曆列表，找到 {len(calendars)} 個日曆")
                for calendar in calendars:
                    logger.info(f"日曆: {calendar.get('summary')} (ID: {calendar.get('id')})")
                    print(f"[LOG] 日曆: {calendar.get('summary')} (ID: {calendar.get('id')})")
            else:
                logger.warning("未找到任何日曆")
                print("[WARNING] 未找到任何日曆")
            
            # 測試2: 獲取主日曆信息
            logger.info(f"嘗試獲取主日曆信息 (ID: {self.calendar_id})")
            print(f"[LOG] 嘗試獲取主日曆信息 (ID: {self.calendar_id})")
            primary_calendar = self.service.calendars().get(calendarId=self.calendar_id).execute()
            logger.info(f"主日曆信息: {json.dumps(primary_calendar, ensure_ascii=False)}")
            print(f"[LOG] 主日曆信息: {json.dumps(primary_calendar, ensure_ascii=False)}")
            
            # 測試3: 查詢近期事件
            logger.info("嘗試查詢近期事件")
            print("[LOG] 嘗試查詢近期事件")
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            if events:
                logger.info(f"成功獲取事件列表，找到 {len(events)} 個事件")
                print(f"[LOG] 成功獲取事件列表，找到 {len(events)} 個事件")
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    logger.info(f"事件: {event.get('summary')} (開始時間: {start})")
                    print(f"[LOG] 事件: {event.get('summary')} (開始時間: {start})")
            else:
                logger.info("未找到近期事件")
                print("[LOG] 未找到近期事件")
            
            logger.info("Google Calendar API連接測試完成，所有測試通過")
            print("[LOG] Google Calendar API連接測試完成，所有測試通過")
            return True
            
        except Exception as e:
            error_detail = str(e)
            logger.error(f"Google Calendar API連接測試失敗: {error_detail}")
            print(f"[ERROR] Google Calendar API連接測試失敗: {error_detail}")
            
            # 詳細診斷
            import traceback
            tb = traceback.format_exc()
            logger.error(f"堆疊追蹤:\n{tb}")
            print(f"[ERROR] 堆疊追蹤:\n{tb}")
            
            # 檢查憑證
            self._check_credentials()
            
            return False 

    def _check_calendar_info(self):
        """檢查當前使用的日曆信息"""
        try:
            logger.info(f"檢查日曆 {self.calendar_id} 的詳細信息")
            print(f"[LOG] 檢查日曆 {self.calendar_id} 的詳細信息")
            
            if self.calendar_id == 'primary':
                # 獲取主日曆詳細信息
                calendar_info = self.service.calendars().get(calendarId=self.calendar_id).execute()
                logger.info(f"主日曆信息: {json.dumps(calendar_info, ensure_ascii=False)}")
                print(f"[LOG] 主日曆信息: {json.dumps(calendar_info, ensure_ascii=False)}")
                logger.info(f"當前使用的日曆: {calendar_info.get('summary')} (ID: {self.calendar_id})")
                print(f"[LOG] 當前使用的日曆: {calendar_info.get('summary')} (ID: {self.calendar_id})")
            else:
                # 獲取指定ID日曆的詳細信息
                try:
                    calendar_info = self.service.calendars().get(calendarId=self.calendar_id).execute()
                    logger.info(f"指定日曆信息: {json.dumps(calendar_info, ensure_ascii=False)}")
                    print(f"[LOG] 指定日曆信息: {json.dumps(calendar_info, ensure_ascii=False)}")
                    logger.info(f"當前使用的日曆: {calendar_info.get('summary')} (ID: {self.calendar_id})")
                    print(f"[LOG] 當前使用的日曆: {calendar_info.get('summary')} (ID: {self.calendar_id})")
                except Exception as cal_error:
                    logger.error(f"獲取指定日曆信息失敗: {str(cal_error)}")
                    print(f"[ERROR] 獲取指定日曆信息失敗: {str(cal_error)}")
                    
                    # 嘗試列出所有可用的日曆
                    self._list_available_calendars()
                    
                    # 如果指定的日曆ID不可用，回退到使用主日曆
                    logger.warning(f"自動回退到使用主日曆")
                    print(f"[WARNING] 自動回退到使用主日曆")
                    self.calendar_id = 'primary'
                    
                    # 再次獲取主日曆信息
                    calendar_info = self.service.calendars().get(calendarId=self.calendar_id).execute()
                    logger.info(f"主日曆信息: {json.dumps(calendar_info, ensure_ascii=False)}")
                    print(f"[LOG] 主日曆信息: {json.dumps(calendar_info, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"檢查日曆信息失敗: {str(e)}")
            print(f"[ERROR] 檢查日曆信息失敗: {str(e)}")
    
    def _list_available_calendars(self):
        """列出所有可用的日曆"""
        try:
            logger.info("獲取所有可用日曆")
            print("[LOG] 獲取所有可用日曆")
            calendar_list = self.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            if calendars:
                logger.info(f"找到 {len(calendars)} 個可用日曆:")
                print(f"[LOG] 找到 {len(calendars)} 個可用日曆:")
                for calendar in calendars:
                    logger.info(f"- {calendar.get('summary')} (ID: {calendar.get('id')})")
                    print(f"[LOG] - {calendar.get('summary')} (ID: {calendar.get('id')})")
            else:
                logger.warning("未找到任何可用日曆")
                print("[WARNING] 未找到任何可用日曆")
                
        except Exception as e:
            logger.error(f"列出可用日曆失敗: {str(e)}")
            print(f"[ERROR] 列出可用日曆失敗: {str(e)}")
                
    def set_calendar_id(self, calendar_id):
        """設置要使用的日曆ID"""
        try:
            logger.info(f"嘗試切換日曆ID從 {self.calendar_id} 到 {calendar_id}")
            print(f"[LOG] 嘗試切換日曆ID從 {self.calendar_id} 到 {calendar_id}")
            
            # 驗證日曆ID是否有效
            try:
                calendar_info = self.service.calendars().get(calendarId=calendar_id).execute()
                self.calendar_id = calendar_id
                logger.info(f"成功切換到日曆: {calendar_info.get('summary')} (ID: {calendar_id})")
                print(f"[LOG] 成功切換到日曆: {calendar_info.get('summary')} (ID: {calendar_id})")
                return True
            except Exception as e:
                logger.error(f"切換日曆失敗: {str(e)}")
                print(f"[ERROR] 切換日曆失敗: {str(e)}")
                logger.warning("保持使用原有日曆ID")
                print(f"[WARNING] 保持使用原有日曆ID: {self.calendar_id}")
                return False
                
        except Exception as e:
            logger.error(f"設置日曆ID時發生錯誤: {str(e)}")
            print(f"[ERROR] 設置日曆ID時發生錯誤: {str(e)}")
            return False 