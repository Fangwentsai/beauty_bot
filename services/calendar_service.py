import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

class GoogleCalendarService:
    def __init__(self):
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_file(
            os.getenv('GOOGLE_CALENDAR_CREDENTIALS'),
            scopes=SCOPES
        )
        self.service = build('calendar', 'v3', credentials=creds)

    def get_available_slots(self, days_ahead=7):
        """獲取未來幾天內的可用時段"""
        now = datetime.utcnow()
        end_time = now + timedelta(days=days_ahead)
        
        # 獲取已預約的時段
        events_result = self.service.events().list(
            calendarId='primary',
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
        }
        
        try:
            event = self.service.events().insert(calendarId='primary', body=event).execute()
            return event.get('htmlLink')
        except Exception as e:
            raise Exception(f'創建預約失敗：{str(e)}')

    def get_available_slots_by_date(self, date):
        """查詢指定日期的可用時段（10:00-20:00，每30分鐘）"""
        date_start = datetime.strptime(date, "%Y-%m-%d").replace(hour=10, minute=0, second=0, microsecond=0)
        date_end = date_start.replace(hour=20, minute=0)
        events_result = self.service.events().list(
            calendarId='primary',
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