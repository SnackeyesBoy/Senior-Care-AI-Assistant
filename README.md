# 👵 Senior Care AI Assistant (高齡照護雙語 AI 助手)

這是一款專為高齡者設計的 AI 照護系統，具備多模態互動與長照輔助功能。

## ✨ 核心功能
* **溫柔語音陪聊**：結合 Whisper STT 與 OpenAI TTS，提供雙語長者情緒陪伴。
* **藥袋 OCR 智慧解析**：使用 GPT-4o 視覺模型，自動擷取藥袋資訊並生成語音叮嚀。
* **無縫用藥提醒**：自動生成專屬用藥清單，並支援一鍵加入 Google Calendar。
* **家屬健康報告**：分析近期對話與用藥紀錄，自動彙整結構化報告給家屬。

## 🛠️ 如何在本地端執行
1. Clone 專案：`git clone https://github.com/你的帳號/你的專案.git`
2. 安裝依賴：`pip install -r requirements.txt`
3. 環境變數：建立 `.env` 檔案，並填入 `OPENAI_API_KEY=你的金鑰`
4. 啟動系統：`streamlit run app.py`

一個專為長者與其家屬設計的無障礙、多模態（語音、視覺、文字）智慧照護系統。本專案採用 **Streamlit** 構建前端，整合 **OpenAI API (GPT-4o, Whisper, TTS)**，並結合本地端資料持久化技術，實作具備主動關懷、風險預警、藥單解析與家屬端自動化報告的商用原型。

---

## 🚀 核心功能亮點 (Key Features)

### 1. 💬 AI 溫柔陪聊系統 (多模態動態對話)
* **無障礙語音輸入 (STT)**：整合 `streamlit-mic_recorder` 與 **Whisper-1** 模型，長者只需一鍵即可透過麥克風聊天，免除打字困擾。
* **逼真擬真語音 (TTS)**：採用 **OpenAI TTS-1** 技術，提供多款溫柔音色（Nova, Shimmer, Alloy, Onyx）即時朗讀回覆。
* **時間與天氣感知**：系統自動連結即時天氣 API (`wttr.in`) 與系統時間，將環境狀態無縫融入對話中（例如：提醒多喝水或保暖）。
* **語言自動匹配 (Dynamic Language Switching)**：採用 *Late Prompting (最終指令覆蓋)* 技巧，系統會精準偵測長者最新輸入的語言（中文/英文），做到「中文輸入、中文回覆；英文輸入、英文回覆」。

### 2. 🚨 危險症狀即時警示 (Safety Check System)
* **底層關鍵字攔截**：當長者在對話中提及特定的高風險關鍵字（如：*胸痛、跌倒、喘不過氣、chest pain* 等），系統會立刻中斷常規對話。
* **緊急應變機制**：畫面上跳出紅色高亮警告，並強制透過音訊播放緊急語音指南，叮嚀長者立即休息並聯絡 119 或家屬。

### 3. 📷 藥袋 OCR 智慧視覺解析與行事曆連動
* **旗艦級視覺推理**：將藥袋影像透過 Base64 編碼，調用 **GPT-4o** 進行密集的文字結構化抽取，自動提煉出藥名、用法、劑量與推測外觀。
* **Google 行事曆輕量級整合**：利用 `urllib.parse` 進行安全網址編碼，生成一鍵加入 Google 行事曆的邀請網址。長者或家屬點擊按鈕，即可跨裝置同步用藥行程，達成原生系統的主動推播提醒。

### 4. 📊 家屬端健康與互動報告 (Family Report System)
* **長者記憶系統**：系統具備長期記憶能力，會將長者的身體習慣與重要病史注入對話上下文，提供個人化照護。
* **自動化摘要**：扮演專業長照個管師角色，統整長者近期的「聊天紀錄日誌」與「用藥狀況」，一鍵產出結構化的家屬健康報告。

---

## ⚙️ 技術棧統籌 (Tech Stack)

* **Web UI Framework**: Streamlit (自訂高齡友善放大 CSS 樣式)
* **AI Models**: 
  * `gpt-4o` (藥袋影像解析)
  * `gpt-4o-mini` (智慧陪聊、上下文推理)
  * `whisper-1` (語音轉文字 STT)
  * `tts-1` (文字轉語音 TTS)
* **Database**: 本地輕量化 JSON 資料持久化儲存 (`user_data.json`)
* **Third-party APIs**: Wttr.in (即時氣象資料)、Google Calendar API Template (行事曆連動)

---

## 📂 專案架構說明 (Architecture)

```text
.
├── app.py               # Streamlit 主程式（包含 UI 渲染、API 呼叫與四大模式邏輯）
├── user_data.json       # 本地端輕量資料庫（自動生成，儲存用藥紀錄、對話日誌與長者記憶）
├── .env                 # 環境變數設定檔（存放 OpenAI API 金鑰，嚴禁上傳 GitHub）
├── .gitignore           # Git 忽略清單（已預設排除機密金鑰、本地測試資料與音訊暫存檔）
├── requirements.txt     # 套件依賴版本清單
└── README.md            # 專案說明文件
