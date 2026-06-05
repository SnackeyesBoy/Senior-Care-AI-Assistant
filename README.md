# 👵 Senior Care AI Assistant (高齡照護 AI 助手)

這是一款專為高齡者設計的 AI 照護系統，具備多模態互動與長照輔助功能。

## ✨ 核心功能

* **溫柔語音陪聊**：結合 Whisper STT 與 OpenAI TTS，提供雙語長者情緒陪伴。
* **藥袋 OCR 智慧解析**：使用 GPT-4o 視覺模型，自動擷取藥袋資訊並生成語音叮嚀。
* **無縫用藥提醒**：自動生成專屬用藥清單，並支援一鍵加入 Google Calendar。
* **家屬健康報告**：分析近期對話與用藥紀錄，自動彙整結構化報告給家屬。

## 🛠️ 如何在本地端執行

1. Clone 專案：`git clone https://github.com/SnackeyesBoy/Senior-Care-AI-Assistant.git`
2. 安裝依賴：`pip install -r requirements.txt`
3. 環境變數：建立 `.env` 檔案，並填入 `OPENAI_API_KEY=你的金鑰`
4. 啟動系統：`streamlit run app.py`
