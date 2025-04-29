#!/usr/bin/env python3
from datetime import datetime, timedelta
from services.calendar_service import GoogleCalendarService
import os
import json
import sys

# 確保環境變數設置正確
os.environ['GOOGLE_CALENDAR_CREDENTIALS'] = 'credentials/google_calendar_credentials.json'
os.environ['FIREBASE_CREDENTIALS'] = 'credentials/firebase_credentials.json'

def create_event_in_specific_calendar(calendar_id):
    print(f"開始在日曆 {calendar_id} 上創建測試預約...")
    
    # 初始化 Google Calendar 服務
    calendar_service = GoogleCalendarService()
    
    # 設置預約時間 - 2025年5月5日 16:00-18:00
    start_dt = datetime.strptime("2025-05-05 16:00", "%Y-%m-%d %H:%M")
    # 日式美睫服務時長為 2 小時
    end_dt = start_dt + timedelta(hours=2)
    
    # 測試用戶信息
    test_user = {
        'name': '測試用戶3',
        'phone': '0912345678'
    }
    
    # 服務類型
    service_type = "日式美睫 (測試3)"
    
    print(f"準備創建預約：{service_type} 於 {start_dt} 至 {end_dt}")
    
    try:
        # 創建事件
        event = {
            'summary': f'{test_user["name"]} - {service_type}',
            'description': f'客戶：{test_user["name"]}\n電話：{test_user["phone"]}\n服務：{service_type}',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Asia/Taipei',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
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
        
        # 使用 API 直接創建事件在指定日曆
        created_event = calendar_service.service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        print("=== 預約創建成功 ===")
        print(f"事件 ID: {created_event.get('id')}")
        print(f"連結: {created_event.get('htmlLink')}")
        print(f"開始時間: {created_event['start'].get('dateTime')}")
        print(f"結束時間: {created_event['end'].get('dateTime')}")
        print(f"摘要: {created_event.get('summary')}")
        
        return created_event
    except Exception as e:
        print(f"創建預約失敗: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 create_event_in_specific_calendar.py 日曆ID")
        print("例如: python3 create_event_in_specific_calendar.py your_email@gmail.com")
    else:
        calendar_id = sys.argv[1]
        create_event_in_specific_calendar(calendar_id) 