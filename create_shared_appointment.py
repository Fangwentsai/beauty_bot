#!/usr/bin/env python3
from datetime import datetime, timedelta
from services.calendar_service import GoogleCalendarService
import os
import json

# 確保環境變數設置正確
os.environ['GOOGLE_CALENDAR_CREDENTIALS'] = 'credentials/google_calendar_credentials.json'
os.environ['FIREBASE_CREDENTIALS'] = 'credentials/firebase_credentials.json'

def create_shared_appointment():
    print("開始創建共享的測試預約...")
    
    # 初始化 Google Calendar 服務
    calendar_service = GoogleCalendarService()
    
    # 獲取日曆 ID (服務帳戶的主日曆)
    calendar_id = calendar_service.calendar_id
    print(f"使用日曆 ID: {calendar_id}")
    
    # 設置預約時間 - 2025年5月5日 15:00-17:00 (換一個時間，以區別之前的預約)
    start_dt = datetime.strptime("2025-05-05 15:00", "%Y-%m-%d %H:%M")
    # 日式美睫服務時長為 2 小時
    end_dt = start_dt + timedelta(hours=2)
    
    # 測試用戶信息
    test_user = {
        'name': '測試用戶2',
        'phone': '0912345678'
    }
    
    # 服務類型
    service_type = "日式美睫 (測試2)"
    
    print(f"準備創建預約：{service_type} 於 {start_dt} 至 {end_dt}")
    
    try:
        # 創建具有共享設置的事件
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
            # 添加共享設置
            'transparency': 'transparent',  # 不顯示為忙碌
            'visibility': 'public',        # 公開可見
        }
        
        print(f"事件詳情: {json.dumps(event, ensure_ascii=False, indent=2)}")
        
        # 使用 API 直接創建事件
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
        
        # 嘗試獲取事件訪問控制列表
        try:
            acl = calendar_service.service.acl().list(calendarId=calendar_id).execute()
            print("\n日曆訪問控制列表:")
            print(json.dumps(acl, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"獲取訪問控制列表失敗: {str(e)}")
        
        # 嘗試添加訪問權限（需要輸入要共享的用戶郵箱）
        print("\n要添加特定用戶的訪問權限，請運行以下命令：")
        print('python3 -c "from services.calendar_service import GoogleCalendarService; import os; os.environ[\'GOOGLE_CALENDAR_CREDENTIALS\']=\'credentials/google_calendar_credentials.json\'; calendar_service = GoogleCalendarService(); rule = {\'scope\':{\'type\':\'user\',\'value\':\'用戶郵箱地址\'},\'role\':\'reader\'}; calendar_service.service.acl().insert(calendarId=\'' + calendar_id + '\', body=rule).execute()"')
        
        return created_event
    except Exception as e:
        print(f"創建預約失敗: {str(e)}")
        return None

if __name__ == "__main__":
    create_shared_appointment() 