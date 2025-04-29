# Beauty Bot - Line 預約機器人

這是一個整合了 Line Bot、ChatGPT 和 Google Calendar 的美容預約系統。

## 功能特點

- Line Bot 自動回覆與預約服務
- 整合 ChatGPT 4.0-mini 進行自然對話
- Google Calendar 整合，自動管理預約時段
- Firebase 資料庫儲存用戶資訊
- 個人化用戶體驗，記住用戶偏好

## 環境需求

- Python 3.8+
- Line Bot API 金鑰
- OpenAI API 金鑰
- Google Calendar API 憑證
- Firebase 專案設定

## 安裝步驟

1. 克隆專案
```bash
git clone [repository-url]
cd beauty_bot
```

2. 安裝依賴
```bash
pip install -r requirements.txt
```

3. 設定環境變數
創建 `.env` 文件並填入以下資訊：
```
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
OPENAI_API_KEY=your_openai_api_key
GOOGLE_CALENDAR_CREDENTIALS=credentials/google_calendar_credentials.json
FIREBASE_CREDENTIALS=credentials/firebase_credentials.json
```

4. 運行應用
```bash
python app.py
```

## 部署說明

### Render 平台部署設定

1. 在 Render 平台創建一個新的 Web Service
2. 設置以下環境變數:

```
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
OPENAI_API_KEY=your_openai_api_key
RENDER=true
```

3. 對於 Google Calendar 和 Firebase 憑證，需要將 JSON 檔案內容作為環境變數:

```
GOOGLE_CALENDAR_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project-id",...} 
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project-id",...}
```

注意：這兩個環境變數必須包含完整的 JSON 憑證內容。可使用以下步驟:
1. 開啟憑證 JSON 檔案
2. 複製所有內容（包括大括號）
3. 粘貼到 Render 的環境變數設定中

4. 設置 Start Command:
```
python app.py
```

5. 其他可選環境變數:
```
GOOGLE_CALENDAR_ID=your_calendar_id  # 如需使用特定日曆
PORT=10000  # 如需更改默認端口
```

## 憑證文件說明

1. Google Calendar 憑證:
   - 需要從 Google Cloud Console 創建服務帳號並下載 JSON 憑證
   - 本地開發：將檔案放在 `credentials/google_calendar_credentials.json`
   - Render 部署：將檔案內容設置為環境變數 `GOOGLE_CALENDAR_CREDENTIALS_JSON`

2. Firebase 憑證:
   - 需要從 Firebase 控制台創建服務帳號並下載 JSON 憑證
   - 本地開發：將檔案放在 `credentials/firebase_credentials.json`
   - Render 部署：將檔案內容設置為環境變數 `FIREBASE_CREDENTIALS_JSON`

## 注意事項

- 請確保所有 API 金鑰和憑證的安全性
- 定期備份 Firebase 資料庫
- 監控 API 使用量以避免超額費用
- 確保 Google Calendar 和 Firebase 服務帳號有足夠的權限
- 在 Render 部署時，請確認環境變數設置正確，特別是包含完整 JSON 的憑證內容 