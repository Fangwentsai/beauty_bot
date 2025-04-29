#!/usr/bin/env python3
from datetime import datetime, timedelta
from services.calendar_service import GoogleCalendarService
import os
import json

# 確保環境變數設置正確
os.environ['GOOGLE_CALENDAR_CREDENTIALS'] = 'credentials/google_calendar_credentials.json'
os.environ['FIREBASE_CREDENTIALS'] = 'credentials/firebase_credentials.json'

def test_public_calendar():
    print("開始測試公開日曆功能...")
    
    # 初始化 Google Calendar 服務
    calendar_service = GoogleCalendarService()
    
    # 檢查默認日曆 ID
    print(f"默認使用的日曆 ID: {calendar_service.calendar_id}")
    
    # 查詢日曆信息
    try:
        calendar_info = calendar_service.service.calendars().get(
            calendarId=calendar_service.calendar_id
        ).execute()
        print(f"日曆信息: {json.dumps(calendar_info, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"獲取日曆信息失敗: {str(e)}")
    
    # 創建測試事件
    start_dt = datetime.strptime("2025-05-10 10:00", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(hours=2)
    
    test_user = {
        'name': '測試整合後',
        'phone': '0912345678'
    }
    
    service_type = "日式美睫 (整合測試)"
    
    print(f"準備創建預約：{service_type} 於 {start_dt} 至 {end_dt}")
    
    try:
        # 創建預約
        result = calendar_service.create_booking(
            start_time=start_dt,
            end_time=end_dt,
            user_info=test_user,
            service=service_type
        )
        
        print("=== 預約創建成功 ===")
        print(f"事件 ID: {result.get('id')}")
        print(f"連結: {result.get('link')}")
        print(f"開始時間: {result.get('start')}")
        print(f"結束時間: {result.get('end')}")
        print(f"摘要: {result.get('summary')}")
        
        return result
    except Exception as e:
        print(f"創建預約失敗: {str(e)}")
        return None
        
if __name__ == "__main__":
    test_public_calendar() 