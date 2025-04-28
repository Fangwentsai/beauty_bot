import os
from openai import OpenAI
from datetime import datetime

class ChatGPTService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.system_prompt = """你是一個專業的美容預約助手，負責協助客人預約美容服務。
        請注意以下幾點：
        1. 使用親切友善的語氣，避免過於制式的回答
        2. 記住客人的偏好和習慣
        3. 提供專業的美容建議
        4. 協助管理預約時間
        5. 回答關於美容服務的問題
        請用繁體中文回覆。"""

    def process_message(self, message, user_info=None):
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        if user_info:
            user_context = f"""用戶資訊：
            姓名：{user_info.get('name', '未知')}
            手機：{user_info.get('phone', '未知')}
            常用服務：{', '.join(user_info.get('favorite_services', []))}
            上次預約：{user_info.get('last_booking', '未知')}
            """
            messages.append({"role": "system", "content": user_context})
        
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"抱歉，處理您的訊息時發生錯誤：{str(e)}"

    def format_booking_response(self, response, available_slots):
        if not available_slots:
            return response + "\n\n目前沒有可預約的時段，請稍後再試。"
        
        slots_text = "\n可預約時段：\n"
        for slot in available_slots:
            slots_text += f"- {slot}\n"
        
        return response + slots_text 