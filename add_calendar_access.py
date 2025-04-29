#!/usr/bin/env python3
from services.calendar_service import GoogleCalendarService
import os
import sys

# 確保環境變數設置正確
os.environ['GOOGLE_CALENDAR_CREDENTIALS'] = 'credentials/google_calendar_credentials.json'
os.environ['FIREBASE_CREDENTIALS'] = 'credentials/firebase_credentials.json'

def add_calendar_access(user_email):
    print(f"開始添加用戶 {user_email} 的日曆訪問權限...")
    
    # 初始化 Google Calendar 服務
    calendar_service = GoogleCalendarService()
    calendar_id = calendar_service.calendar_id
    
    # 創建訪問規則
    rule = {
        'scope': {
            'type': 'user',
            'value': user_email
        },
        'role': 'reader'  # 或 'writer' 如果需要寫入權限
    }
    
    try:
        # 添加訪問權限
        created_rule = calendar_service.service.acl().insert(
            calendarId=calendar_id,
            body=rule
        ).execute()
        
        print(f"成功添加訪問權限！")
        print(f"規則 ID: {created_rule.get('id')}")
        print(f"用戶: {created_rule.get('scope', {}).get('value')}")
        print(f"角色: {created_rule.get('role')}")
        
        # 提供訂閱該日曆的連結
        calendar_link = f"https://calendar.google.com/calendar/r?cid={calendar_id}"
        print(f"\n請使用以下連結訂閱該日曆:")
        print(calendar_link)
        
        return created_rule
    except Exception as e:
        print(f"添加訪問權限失敗: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python3 add_calendar_access.py 用戶郵箱地址")
    else:
        user_email = sys.argv[1]
        add_calendar_access(user_email) 