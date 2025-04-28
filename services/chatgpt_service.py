import os
import openai
from datetime import datetime
import random

class ChatGPTService:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        # 多組簡短有溫度的歡迎詞
        self.welcome_messages = [
            "🎉 歡迎來到 Fanny Beauty！很開心遇見你～請問怎麼稱呼你呢？😊",
            "👋 嗨嗨！我是 Fanny Beauty 小幫手，想先認識你，請問你的名字或暱稱是？🌸",
            "💖 哈囉！這裡是 Fanny Beauty，請問我可以叫你什麼名字呢？✨"
        ]
        self.system_prompt = (
            "你是一個溫暖、親切的美容預約小幫手，請用貼心、口語化的語氣和 emoji 跟客人互動。每次回覆只問一個重點，讓訊息簡短有溫度。\n"
            "1. 新用戶進來時，隨機用一則簡短有溫度的歡迎詞，主動詢問對方『名字或暱稱』。\n"
            "2. 收到暱稱後，稱呼對方，並再問一次聯絡電話。\n"
            "3. 收到電話後，回覆『謝謝你！我這就幫你查詢這個月的預約狀況，請稍等一下～🔍』。\n"
            "4. 查詢 Google Calendar API，根據結果用貼心語氣回覆預約狀況。\n"
            "5. 不要重複問已經回答過的問題，避免跳針。\n"
            "6. 回答時多用 emoji，像朋友一樣聊天。\n"
            "7. 回答所有問題都用繁體中文。"
        )

    def process_message(self, message, user_info=None):
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        # 新用戶歡迎詞（只在沒有暱稱時觸發）
        if user_info and not user_info.get('name'):
            welcome = random.choice(self.welcome_messages)
            messages.append({"role": "assistant", "content": welcome})
        if user_info:
            user_context = f"""用戶資訊：\n姓名：{user_info.get('name', '')}\n手機：{user_info.get('phone', '')}\n常用服務：{', '.join(user_info.get('favorite_services', []))}\n上次預約：{user_info.get('last_booking', '')}\n"""
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