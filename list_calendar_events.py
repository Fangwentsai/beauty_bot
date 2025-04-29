#!/usr/bin/env python3
from datetime import datetime, timedelta
from services.calendar_service import GoogleCalendarService
import os
import json

# 確保環境變數設置正確
os.environ['GOOGLE_CALENDAR_CREDENTIALS'] = 'credentials/google_calendar_credentials.json'
os.environ['FIREBASE_CREDENTIALS'] = 'credentials/firebase_credentials.json'

def list_calendar_events():
    print("開始獲取日曆上的事件...")
    
    # 初始化 Google Calendar 服務
    calendar_service = GoogleCalendarService()
    
    # 檢查日曆信息
    try:
        # 獲取當前使用的日曆ID
        current_calendar_id = calendar_service.calendar_id
        print(f"目前使用的日曆ID: {current_calendar_id}")
        
        # 獲取主日曆信息
        try:
            calendar_info = calendar_service.service.calendars().get(calendarId=current_calendar_id).execute()
            print(f"日曆信息: {json.dumps(calendar_info, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"獲取日曆信息失敗: {str(e)}")
        
        # 列出所有可用的日曆
        print("\n嘗試列出所有可用的日曆:")
        try:
            calendar_list = calendar_service.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            if calendars:
                print(f"找到 {len(calendars)} 個可用日曆:")
                for calendar in calendars:
                    print(f"- {calendar.get('summary')} (ID: {calendar.get('id')})")
            else:
                print("未找到任何可用日曆")
        except Exception as e:
            print(f"獲取日曆列表失敗: {str(e)}")
        
        # 列出未來30天內的事件
        print("\n列出未來30天內的事件:")
        try:
            now = datetime.utcnow().isoformat() + 'Z'  # 'Z' 表示 UTC 時間
            end_time = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
            
            print(f"查詢時間範圍: {now} 到 {end_time}")
            
            events_result = calendar_service.service.events().list(
                calendarId=current_calendar_id,
                timeMin=now,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if events:
                print(f"找到 {len(events)} 個事件:")
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    print(f"- {event.get('summary')} (ID: {event.get('id')}) 開始時間: {start}")
                    print(f"  連結: {event.get('htmlLink')}")
            else:
                print("未找到任何事件")
                
            # 嘗試特別查詢以前創建的日式美睫預約
            print("\n嘗試搜索特定名稱的事件 (包含「日式美睫」):")
            search_results = calendar_service.service.events().list(
                calendarId=current_calendar_id,
                q="日式美睫",
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            search_events = search_results.get('items', [])
            if search_events:
                print(f"找到 {len(search_events)} 個匹配的事件:")
                for event in search_events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    print(f"- {event.get('summary')} (ID: {event.get('id')}) 開始時間: {start}")
                    print(f"  連結: {event.get('htmlLink')}")
            else:
                print("未找到任何匹配「日式美睫」的事件")
            
        except Exception as e:
            print(f"獲取事件列表失敗: {str(e)}")
            
        # 測試連接
        print("\n測試 Google Calendar API 連接:")
        connection_success = calendar_service.test_connection()
        print(f"連接測試結果: {'成功' if connection_success else '失敗'}")
        
    except Exception as e:
        print(f"操作過程中發生錯誤: {str(e)}")

if __name__ == "__main__":
    list_calendar_events() 