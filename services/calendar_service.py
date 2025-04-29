import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import logging

# 設置日誌
logger = logging.getLogger(__name__)

class GoogleCalendarService:
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_file(
            os.getenv('GOOGLE_CALENDAR_CREDENTIALS'),
            scopes=SCOPES
        )
        self.service = build('calendar', 'v3', credentials=creds)
        self.calendar_id = 'primary'  # 使用主要行事曆

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
        event = {
            'summary': f'{user_info["name"]} - {service}',
            'description': f'客戶：{user_info["name"]}\n電話：{user_info["phone"]}\n服務：{service}',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Taipei',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Taipei',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 60},
                ],
            },
        }
        
        try:
            # 創建預約
            created_event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            event_id = created_event.get('id')
            event_link = created_event.get('htmlLink')
            
            # 確認預約已成功建立
            if not event_id:
                raise Exception("無法獲取預約 ID，預約可能未成功建立")
            
            # 驗證預約是否存在於行事曆中
            self.verify_event_created(event_id)
            
            logger.info(f"成功建立預約 - ID: {event_id}, 連結: {event_link}")
            return {
                'id': event_id,
                'link': event_link,
                'summary': created_event.get('summary'),
                'start': created_event['start'].get('dateTime'),
                'end': created_event['end'].get('dateTime')
            }
        except Exception as e:
            logger.error(f"創建預約失敗: {str(e)}")
            raise Exception(f'創建預約失敗：{str(e)}')
            
    def verify_event_created(self, event_id):
        """驗證事件是否已成功建立在 Google Calendar 中"""
        try:
            event = self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()
            if event and event.get('id') == event_id:
                logger.info(f"驗證成功：行事曆項目 {event_id} 存在")
                return True
            else:
                logger.error(f"驗證失敗：找不到行事曆項目 {event_id}")
                return False
        except Exception as e:
            logger.error(f"驗證行事曆項目時發生錯誤: {str(e)}")
            raise Exception(f"驗證行事曆項目失敗: {str(e)}")
            
    def get_event_by_id(self, event_id):
        """根據 ID 獲取事件詳情"""
        try:
            return self.service.events().get(calendarId=self.calendar_id, eventId=event_id).execute()
        except Exception as e:
            logger.error(f"獲取行事曆項目失敗: {str(e)}")
            return None

    def get_available_slots_by_date(self, date):
        """查詢指定日期的可用時段（10:00-20:00，每30分鐘）"""
        date_start = datetime.strptime(date, "%Y-%m-%d").replace(hour=10, minute=0, second=0, microsecond=0)
        date_end = date_start.replace(hour=20, minute=0)
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=date_start.isoformat() + 'Z',
            timeMax=date_end.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        booked_slots = []
        for event in events_result.get('items', []):
            start = event['start'].get('dateTime')
            if start:
                booked_slots.append(datetime.fromisoformat(start.replace('Z', '+00:00')))
        available_slots = []
        current = date_start
        while current < date_end:
            if current not in booked_slots:
                available_slots.append(current.strftime('%H:%M'))
            current += timedelta(minutes=30)
        return available_slots 