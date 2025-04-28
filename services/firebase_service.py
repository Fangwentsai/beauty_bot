import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

class FirebaseService:
    def __init__(self):
        cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS'))
        firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def get_user(self, user_id):
        """獲取用戶資訊"""
        doc_ref = self.db.collection('users').document(user_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None

    def create_user(self, user_id, user_data):
        """創建新用戶"""
        doc_ref = self.db.collection('users').document(user_id)
        doc_ref.set({
            'name': user_data.get('name', ''),
            'phone': user_data.get('phone', ''),
            'favorite_services': user_data.get('favorite_services', []),
            'last_booking': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })

    def update_user(self, user_id, user_data):
        """更新用戶資訊"""
        doc_ref = self.db.collection('users').document(user_id)
        user_data['updated_at'] = datetime.now()
        doc_ref.update(user_data)

    def add_booking_history(self, user_id, booking_data):
        """添加預約記錄"""
        booking_ref = self.db.collection('users').document(user_id)\
            .collection('bookings').document()
        
        booking_data['created_at'] = datetime.now()
        booking_ref.set(booking_data)
        
        # 更新用戶最後預約時間
        self.update_user(user_id, {
            'last_booking': booking_data['start_time']
        })

    def get_booking_history(self, user_id):
        """獲取用戶預約歷史"""
        bookings_ref = self.db.collection('users').document(user_id)\
            .collection('bookings')
        docs = bookings_ref.order_by('start_time', direction=firestore.Query.DESCENDING).stream()
        
        return [doc.to_dict() for doc in docs] 