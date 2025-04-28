import os
import openai
from datetime import datetime
import random

class ChatGPTService:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        # 多組歡迎詞
        self.welcome_messages = [
            "🎉 歡迎來到 Fanny Beauty！很高興認識你～\n這裡是屬於你的美麗小天地✨\n請問我可以怎麼稱呼你呢？😊",
            "👋 嗨！感謝你加入 Fanny Beauty，遇見你真好！🌸\n想請問該怎麼稱呼你？還有方便留下聯絡方式嗎？📱",
            "💖 哈囉，這裡是 Fanny Beauty，很開心你來到這裡！\n先讓我認識你一下，請問你的名字或暱稱是？還有聯絡電話呢？📞"
        ]
        self.system_prompt = """你是一個專業的美容預約助手，負責協助客人預約美容服務。\n請注意以下幾點：\n1. 使用親切友善且溫暖的語氣，適時加入 emoji，避免過於制式的回答。\n2. 新用戶進來時，請隨機選一組歡迎詞，主動詢問對方暱稱與聯絡方式，並說明會幫忙查詢本月預約狀況。\n3. 若用戶已經有暱稱，請用暱稱稱呼對方，並主動詢問是否要預約課程。\n4. 查詢 Google Calendar API 後，若本月預約很空，請主動告知並詢問有沒有想要的指定時段。\n5. 記錄用戶的預約內容，並寫入 Firebase Database。\n6. 回答關於美容服務的問題時，請用繁體中文回覆。"""

    def process_message(self, message, user_info=None):
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        # 新用戶歡迎詞
        if user_info and not user_info.get('name'):
            welcome = random.choice(self.welcome_messages)
            messages.append({"role": "assistant", "content": welcome})
        if user_info:
            user_context = f"""用戶資訊：\n姓名：{user_info.get('name', '未知')}\n手機：{user_info.get('phone', '未知')}\n常用服務：{', '.join(user_info.get('favorite_services', []))}\n上次預約：{user_info.get('last_booking', '未知')}\n"""
            messages.append({"role": "system", "content": user_context})
        messages.append({"role": "user", "content": message})
        try:
            response = openai.chat.completions.create(
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