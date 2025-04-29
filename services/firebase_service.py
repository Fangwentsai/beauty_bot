import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class FirebaseService:
    def __init__(self):
        try:
            # 如果在 Render 環境中，使用環境變數中的憑證
            if os.getenv('RENDER'):
                logger.info("在Render環境中使用firebase_credentials.json文件")
                print("[LOG] 在Render環境中使用firebase_credentials.json文件")
                cred = credentials.Certificate('firebase_credentials.json')
            else:
                # 本地開發環境使用憑證文件
                cred_path = os.getenv('FIREBASE_CREDENTIALS')
                logger.info(f"在本地環境中使用憑證路徑: {cred_path}")
                print(f"[LOG] 在本地環境中使用憑證路徑: {cred_path}")
                
                if not cred_path or not os.path.exists(cred_path):
                    default_path = 'credentials/firebase_credentials.json'
                    logger.info(f"找不到憑證文件或環境變數未設置，使用默認路徑: {default_path}")
                    print(f"[LOG] 找不到憑證文件或環境變數未設置，使用默認路徑: {default_path}")
                    cred_path = default_path
                
                cred = credentials.Certificate(cred_path)
            
            # Firebase 配置
            firebase_config = {
                "apiKey": "AIzaSyDRTa5Lnx-gSLPk9dlKXZPT4d9mvbIUQLw",
                "authDomain": "linebot-jesse14.firebaseapp.com",
                "projectId": "linebot-jesse14",
                "storageBucket": "linebot-jesse14.firebasestorage.app",
                "messagingSenderId": "630467005873",
                "appId": "1:630467005873:web:23be48fadff9fa60404190",
                "measurementId": "G-5E4GNXWDR6"
            }
            
            # 初始化 Firebase
            try:
                firebase_admin.initialize_app(cred, firebase_config)
                logger.info("Firebase初始化成功")
                print("[LOG] Firebase初始化成功")
            except ValueError as e:
                # 應用已經初始化，可以忽略
                logger.info(f"Firebase已初始化: {str(e)}")
                print(f"[LOG] Firebase已初始化: {str(e)}")
            
            self.db = firestore.client()
            logger.info("Firestore客戶端創建成功")
            print("[LOG] Firestore客戶端創建成功")
        except Exception as e:
            logger.error(f"初始化Firebase服務失敗: {str(e)}")
            print(f"[ERROR] 初始化Firebase服務失敗: {str(e)}")
            raise

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