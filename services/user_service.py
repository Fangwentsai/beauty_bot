from datetime import datetime

class UserService:
    def __init__(self, firebase_service):
        self.firebase_service = firebase_service

    def get_user_info(self, user_id):
        """獲取用戶資訊，如果不存在則創建新用戶"""
        user_info = self.firebase_service.get_user(user_id)
        
        if not user_info:
            # 創建新用戶
            self.firebase_service.create_user(user_id, {
                'name': '',
                'phone': '',
                'favorite_services': [],
                'state': '',
                'booking_date': '',
                'booking_time': ''
            })
            user_info = self.firebase_service.get_user(user_id)
        
        return user_info

    def update_user_info(self, user_id, user_data):
        """更新用戶資訊"""
        self.firebase_service.update_user(user_id, user_data)

    def set_state(self, user_id, state, booking_date='', booking_time='', selected_service=None):
        """設定用戶狀態與暫存預約資訊"""
        update = {'state': state}
        if booking_date is not None:
            update['booking_date'] = booking_date
        if booking_time is not None:
            update['booking_time'] = booking_time
        if selected_service is not None:
            update['selected_service'] = selected_service
        self.update_user_info(user_id, update)

    def add_booking(self, user_id, booking_data):
        """添加預約記錄"""
        self.firebase_service.add_booking_history(user_id, booking_data)

    def get_booking_history(self, user_id):
        """獲取用戶預約歷史"""
        return self.firebase_service.get_booking_history(user_id)

    def update_favorite_services(self, user_id, service):
        """更新用戶常用服務"""
        user_info = self.get_user_info(user_id)
        favorite_services = user_info.get('favorite_services', [])
        
        if service not in favorite_services:
            favorite_services.append(service)
            self.update_user_info(user_id, {
                'favorite_services': favorite_services
            }) 