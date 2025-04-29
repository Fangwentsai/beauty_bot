#!/usr/bin/env python3
from datetime import datetime, timedelta
from services.calendar_service import GoogleCalendarService
import os

# 確保環境變數設置正確
os.environ['GOOGLE_CALENDAR_CREDENTIALS'] = 'credentials/google_calendar_credentials.json'
os.environ['FIREBASE_CREDENTIALS'] = 'credentials/firebase_credentials.json'

def create_test_appointment():
    print("開始創建測試預約...")
    
    # 初始化 Google Calendar 服務
    calendar_service = GoogleCalendarService()
    
    # 設置預約時間 - 2025年5月5日 14:00-16:00
    start_dt = datetime.strptime("2025-05-05 14:00", "%Y-%m-%d %H:%M")
    # 日式美睫服務時長為 2 小時
    end_dt = start_dt + timedelta(hours=2)
    
    # 測試用戶信息
    test_user = {
        'name': '測試用戶',
        'phone': '0912345678'
    }
    
    # 服務類型
    service_type = "日式美睫"
    
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
    create_test_appointment() 