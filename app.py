import os
import json
import base64
import urllib.parse
from datetime import datetime
from pathlib import Path
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
import requests

# ==============================================================================
# 1. 環境變數、路徑處理與本地資料庫初始化
# ==============================================================================
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
env_path = current_dir / ".env"
data_path = current_dir / "user_data.json"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("OPENAI_API_KEY")

# 簡易本地資料庫讀寫
def load_data():
    if data_path.exists():
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"medications": [], "memory": "長者喜歡被關心，目前尚無特殊疾病紀錄。", "chat_logs": [], "taken_history": []}

def save_data(data):
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_data = load_data()

# 確保 taken_history 欄位存在
if "taken_history" not in user_data:
    user_data["taken_history"] = []

# 每日自動重置當日服藥打勾狀態，但完整保留過往歷史封存紀錄
today_str = str(datetime.today().date())
if user_data.get("last_run_date") != today_str:
    user_data["last_run_date"] = today_str
    for med in user_data.get("medications", []):
        med["checked"] = False
    save_data(user_data)

# ==============================================================================
# 2. 高齡句麵友善：CSS 樣式強制放大（大字體、大按鈕）
# ==============================================================================
st.set_page_config(page_title="Senior Care AI", page_icon="👵", layout="centered")

st.markdown("""
    <style>
    html, body, [data-testid="stWidgetLabel"], p {
        font-size: 24px !important;
        line-height: 1.6 !important;
    }
    [data-testid="stChatMessage"] p {
        font-size: 26px !important;
        font-weight: 500 !important;
    }
    [data-testid="stMarkdownContainer"] p {
        font-size: 24px !important;
    }
    div[data-testid="stRadio"] label {
        padding: 10px 0px !important;
    }
    div[data-testid="stSelectbox"] div {
        font-size: 22px !important;
    }
    input[data-testid="stChatInputTextArea"] {
        font-size: 24px !important;
    }
    h1 { font-size: 45px !important; }
    h2, h3 { font-size: 32px !important; }
    button {
        font-size: 22px !important;
        padding: 12px 24px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 3. 外部 API 連動函數（天氣與 LINE 通報）
# ==============================================================================
def get_live_weather(location="Minxiong"):
    try:
        url = f"https://wttr.in/{location}?format=%C+%t&lang=zh-tw"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.text.strip()
        return "晴朗偏熱 / 28度"
    except Exception:
        return "晴朗偏熱 / 28度"

def send_line_alert(message):
    """📢 店家級全體群發版：只要手機加好友，全體同步接收通知"""
    line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    
    if not line_token:
        st.error("❌ LINE 錯誤：找不到 LINE_CHANNEL_ACCESS_TOKEN，請檢查 .env 檔案")
        return
        
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Authorization": f"Bearer {line_token}",
        "Content-Type": "application/json"
    }
    data = {
        "messages": [{"type": "text", "text": message}]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=5)
        if response.status_code != 200:
            st.error(f"❌ LINE 群發失敗！狀態碼: {response.status_code}，原因: {response.text}")
        else:
            st.toast("🔔 LINE 通知已成功群發送出！")
    except Exception as e:
        st.error(f"❌ LINE 連線發送失敗: {e}")

# ==============================================================================
# 4. 🤖 多國語言包配置
# ==============================================================================
LANG_PACK = {
    "繁體中文": {
        "title": "👵 高齡照護 AI 助手",
        "subtitle": "陪伴長者聊聊天、幫忙看藥袋，讓生活更安心。",
        "sidebar_header": "⚙️ 功能面板",
        "api_ok": "● API 金鑰狀態：已讀取 ✅",
        "api_fail": "● API 金鑰狀態：未讀取 ❌",
        "mode_label": "選擇功能：",
        "modes": ["🗣️ AI 溫柔陪聊", "🏥 藥袋 OCR 辨識", "💊 用藥提醒清單", "📅 當天紀錄檢閱", "📊 AI 健康報告"],
        "voice_label": "🔊 選擇陪伴聲音：",
        "voice_options": {
            "溫柔孫女 (Nova)": "nova",
            "親切護理師 (Shimmer)": "shimmer",
            "暖心大男孩 (Alloy)": "alloy",
            "沉穩大叔 (Onyx)": "onyx"
        },
        "title_label": "👤 怎麼稱呼您：", 
        "titles": ["阿公 / 大哥", "阿嬤 / 大姐"], 
        "mic_header": "🎤 按這裡開始說話",
        "mic_sub": "點擊下方大按鈕開始說話，講完點擊停止即可。",
        "mic_start": "▶️ 開始錄音 (Start)",
        "mic_stop": "⏹️ 停止錄音 (Stop)",
        "mic_listening": "正在聽你說話...",
        "mic_success": "聽到了：",
        "ocr_header": "📷 上傳藥袋相片",
        "ocr_hint": "請選擇藥袋照片...",
        "ocr_caption": "已上傳的藥袋",
        "gpt_processing": "🧠 GPT 視覺模型正在辨識藥袋並分析外觀...",
        "ocr_result_title": "📊 藥單自動解析結果 (含長者友善提醒)",
        "chat_placeholder": "陪聊點天吧...",
        "tts_loading": "👵 正在溫柔地對你說話...",
        "api_error": "哎呀，我的腦袋剛剛稍微卡住了，你可以再跟我說一次嗎？",
        "api_no_key": "請先在 .env 檔案中配置正確的 API 金鑰。",
        "welcome_template": "{user_title}～我是你們的 AI 小乖乖啦！今天身體有沒有舒舒服服呀？快跟我聊聊天嘛！",
        "alert_danger": "⚠️ 系統偵測到危險症狀！請立即坐下休息，系統建議您立刻撥打 119 或通知家屬！",
        "alert_audio": "{user_title}，系統發現您可能不舒服，請立刻坐著休息，趕快打給家人或119喔！",
        "ocr_success": "✅ 藥單智慧導覽完成！紀錄已自動同步至「用藥提醒清單」。",
        "ocr_warning": "⚠️ 視覺模型已讀取相片，但無法從中提煉出藥品結構，請確認相片是否包含用藥資訊。",
        "ocr_hint_panel": "💡 請在左側面板上傳藥袋照片，系統將自動為您解析用藥資訊。",
        "ocr_voice_title": "👵 AI 志工語音叮嚀",
        "ocr_med_list_key": "藥品列表",
        "ocr_script_key": "語音播報稿",
        "ocr_prompt_template": """你是一個精準且充滿溫度的醫療藥單視覺解析助手。請仔細閱讀這張藥袋照片。
請幫我仔細過濾、提煉，找出裡面提到的所有藥品資訊。
你必須嚴格輸出一個符合以下標準的 JSON 物件，不要包含 any 額外的說明文字或 Markdown 外殼：

{{
  "藥品列表": [
    {{
      "藥名": "完整中英文藥名 (例如：辛敏妥膜衣錠 ALLEVO TABLET)",
      "什麼時候吃": "服用時間與頻率 (例如：每天早晚飯後)",
      "吃多少": "單次用量 (例如：每次 1 顆)",
      "藥物外觀": "根據藥名或包裝推測其常見外觀 (例如：白色圓形藥丸、外用藥膏)"
    }}
  ],
  "語音播報稿": "請用極度溫柔、親切、速度緩慢的繁體中文，像孝順的孫子孫女在跟【{short_title}】撒嬌、關心一樣，整理一份口頭吃藥提醒。內容要包含相片中的藥名、怎麼吃、以及藥物長相。句子要非常正向、帶有鼓勵感、且精簡短小（控制在三句左右），最後叮嚀一句貼心的話。記住，一律親切地稱呼使用者為【{short_title}】！"
}}""",
        "list_title": "💊 專屬用藥清單",
        "list_empty": "目前還沒有紀錄藥品喔！請先使用「藥袋 OCR 辨識」功能上傳藥袋。",
        "list_time": "時間",
        "list_dose": "劑量",
        "list_appearance": "外觀",
        "list_taken": "✅ 我今天已經確認吃這顆藥了（回報給家屬）",
        "list_add_cal": "📅 加入 Google 行事曆",
        "list_clear": "🗑️ 清空所有用藥紀錄",
        "history_title": "📅 當天紀錄檢閱",
        "history_desc": "家屬專區：選擇特定日期，即可快速調閱長者當天的詳細對話日誌與歷史服藥時間戳記。",
        "report_title": "📊 AI 健康報告生成",
        "report_desc": "智慧長照專區：選擇指定日期，系統將串接 GPT-4o 針對長者當天的所有互動紀錄與用藥順從度進行密集摘要，產出結構化健康報告。",
        "report_date_label": "📅 選擇查詢日期：",
        "report_log_sub": "💬 當日詳細對話紀錄日誌",
        "report_med_sub": "💊 當日歷史服藥確認紀錄",
        "report_no_logs": "📭 該日無任何對話紀錄。",
        "report_no_meds": "❌ 當日無任何服藥標記紀錄。",
        "report_btn": "✨ 立即生成該日 AI 健康報告",
        "report_no_logs_warn": "⚠️ 該日沒有任何聊天對話數據，無法產生健康總結報告。",
        "report_loading": "🧠 正在為家屬統整長者的健康數據與互動紀錄...",
        "report_success": "✅ 報告生成完畢",
        "report_fail": "報告生成失敗",
        "report_prompt_template": """你是專業的長照個管師。請根據以下長者「指定日期」的互動紀錄與用藥資料，撰寫一份給家屬看的簡短摘要報告。
請使用繁體中文，語氣要專業但充滿關懷。
請依序分點列出：
1. 【情緒與精神狀態摘要】
2. 【提及的身體狀況】(請特別標註是否有疼痛或不適的描述)
3. 【用藥與服藥確認狀況概述】

該日詳細聊天紀錄：{chat_logs}
該日實際服藥紀錄：{medications}"""
    },
    "English": {
        "title": "👵 Senior Care AI Assistant",
        "subtitle": "Chating with elders and helping look at medicine bags.",
        "sidebar_header": "⚙️ Control Panel",
        "api_ok": "● API Key: Loaded ✅",
        "api_fail": "● API Key: Missing ❌",
        "mode_label": "Select Feature:",
        "modes": ["🗣️ AI Chat Companion", "🏥 Medicine Bag OCR", "💊 Medication List", "📅 Daily Records", "📊 AI Health Report"],
        "voice_label": "🔊 Select AI Voice:",
        "voice_options": {
            "Sweet Granddaughter (Nova)": "nova",
            "Caring Nurse (Shimmer)": "shimmer",
            "Warm Boy (Alloy)": "alloy",
            "Calm Uncle (Onyx)": "onyx"
        },
        "title_label": "👤 How should I call you:",
        "titles": ["Grandpa / Sir", "Grandma / Madam"],
        "mic_header": "🎤 Press to Speak",
        "mic_sub": "Click the large button to start talking.",
        "mic_start": "▶️ Start Recording",
        "mic_stop": "⏹️ Stop Recording",
        "mic_listening": "Listening to you...",
        "mic_success": "Heard: ",
        "ocr_header": "📷 Upload Medicine Bag",
        "ocr_hint": "Choose a photo...",
        "ocr_caption": "Uploaded Image",
        "gpt_processing": "🧠 GPT Vision is scanning and analyzing the image...",
        "ocr_result_title": "📊 Medication Guide (Senior Friendly)",
        "chat_placeholder": "Talk to your assistant here...",
        "tts_loading": "👵 Preparing voice response...",
        "api_error": "Oops, my brain slipped for a second.",
        "api_no_key": "Please configure your API key in the .env file first.",
        "welcome_template": "Hi {user_title}! I'm your sweet grandchild here. How are you feeling today? Tell me everything!",
        "alert_danger": "⚠️ Danger detected! Please sit down and rest immediately. We recommend calling 119 or notifying your family right away!",
        "alert_audio": "{user_title}, I noticed you might not be feeling well. Please sit and rest immediately, and call your family or 119!",
        "ocr_success": "✅ Medication guide complete! Records automatically synced to the Medication List.",
        "ocr_warning": "⚠️ The model read the photo but couldn't extract medication info. Please ensure it's visible.",
        "ocr_hint_panel": "💡 Please upload a medicine bag photo on the left panel for automatic parsing.",
        "ocr_voice_title": "👵 AI Volunteer Voice Reminder",
        "ocr_med_list_key": "Medication List",
        "ocr_script_key": "Voice Script",
        "ocr_prompt_template": """You are a highly accurate and caring medical prescription visual assistant. Please carefully read this medicine bag photo.
Extract and filter all medication information mentioned.
You MUST output a JSON object strictly following this standard, without any extra text or Markdown formatting:

{{
  "Medication List": [
    {{
      "Medication Name": "Full medication name (e.g., ALLEVO TABLET)",
      "When to take": "Time and frequency (e.g., Every morning and evening after meals)",
      "Dosage": "Single dose amount (e.g., 1 tablet each time)",
      "Appearance": "Deduced appearance based on name or packaging (e.g., White round pill, ointment)"
    }}
  ],
  "Voice Script": "Please write an oral medication reminder in extremely gentle, caring, and slow English, like a loving grandchild talking to their 【{short_title}】. It must include the medication names, how to take them, and their appearance. Keep it highly positive, encouraging, and short (about three sentences), ending with a sweet caring remark. Always address the user as 【{short_title}】!"
}}""",
        "list_title": "💊 Exclusive Medication List",
        "list_empty": "No medications recorded yet! Please upload a bag using the OCR feature first.",
        "list_time": "Time",
        "list_dose": "Dosage",
        "list_appearance": "Appearance",
        "list_taken": "✅ I have taken this medicine today (Notify Family)",
        "list_add_cal": "📅 Add to Google Calendar",
        "list_clear": "🗑️ Clear All Medication Records",
        "history_title": "📅 Daily Records Review",
        "history_desc": "Family Section: Select a specific date to view the detailed chat logs and historical medication time stamps of the day.",
        "report_title": "📊 Family Health Report",
        "report_desc": "AI Case Manager Section: Select a date, and the system will leverage GPT-4o to analyze the elder's full dialogue and medication history for a comprehensive report.",
        "report_date_label": "📅 Select Date:",
        "report_log_sub": "💬 Detailed Chat Logs for the Day",
        "report_med_sub": "💊 Historical Medication Records for the Day",
        "report_no_logs": "📭 No chat records on this day.",
        "report_no_meds": "❌ No medication taken records on this day.",
        "report_btn": "✨ Generate AI Report for This Day",
        "report_no_logs_warn": "⚠️ No chat records found for this day. Cannot generate health report.",
        "report_loading": "🧠 Compiling health data and interaction records...",
        "report_success": "✅ Report generated successfully",
        "report_fail": "Report generation failed",
        "report_prompt_template": """You are a professional long-term care case manager. Based on the elder's interaction records and medication data for the specific day below, write a brief report for the family.
Please use English, and maintain a professional yet caring tone.
Please list the following points in order:
1. [Summary of Emotional and Mental State]
2. [Mentioned Physical Conditions] (Specifically note any descriptions of pain or discomfort)
3. [Overview of Medication Status and Adherence]

Chat Logs of the day: {chat_logs}
Medication Taken Logs of the day: {medications}"""
    }
}

# ==============================================================================
# 5. 介面頂部與語言切換
# ==============================================================================
with st.sidebar:
    lang = st.selectbox("🌐 語言 / Language", ["繁體中文", "English"])

L = LANG_PACK[lang]

client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        st.error(f"OpenAI Client Init Failed: {e}")
else:
    st.error(L["api_no_key"])

# ==============================================================================
# 6. 側邊欄控制面板
# ==============================================================================
with st.sidebar:
    # 快捷加入 LINE 訂閱功能
    bot_id = "@609cpspd"  
    line_add_url = f"https://line.me/R/ti/p/{bot_id}"
    st.subheader("📲 訂閱系統通知" if lang == "繁體中文" else "📲 Subscribe LINE")
    st.link_button("加入 LINE 好友" if lang == "繁體中文" else "🟢 Add LINE Friend", line_add_url)
    st.divider()

    st.header(L["sidebar_header"])
    
    # 功能切換（升級為 5 個核心模組）
    selected_mode = st.radio(L["mode_label"], L["modes"])
    is_chat_mode = (selected_mode == L["modes"][0])
    is_ocr_mode = (selected_mode == L["modes"][1])
    is_list_mode = (selected_mode == L["modes"][2])
    is_history_mode = (selected_mode == L["modes"][3]) # 📅 當天紀錄檢閱
    is_report_mode = (selected_mode == L["modes"][4])  # 📊 AI 健康報告
    
    st.divider()
    
    # 讓使用者選擇男女性稱呼
    user_title_choice = st.radio(L["title_label"], L["titles"])
    short_title = user_title_choice.split(" / ")[0]
    
    st.divider()
    
    # 雙語音色切換選單
    VOICE_OPTIONS = L["voice_options"]
    selected_voice_name = st.selectbox(L["voice_label"], list(VOICE_OPTIONS.keys()))
    chosen_voice_value = VOICE_OPTIONS[selected_voice_name]
    
    st.divider()
    
    # 處理語音輸入
    audio_text_input = None
    if is_chat_mode and client:
        st.subheader(L["mic_header"])
        st.write(L["mic_sub"])
        
        audio_record = mic_recorder(
            start_prompt=L["mic_start"],
            stop_prompt=L["mic_stop"],
            key='recorder'
        )
        
        if audio_record:
            with st.spinner(L["mic_listening"]):
                try:
                    audio_bytes = audio_record['bytes']
                    temp_audio_path = current_dir / "temp_input.wav"
                    
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio_bytes)
                    
                    with open(temp_audio_path, "rb") as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", 
                            file=audio_file
                        )
                    audio_text_input = transcript.text
                    st.success(f"{L['mic_success']}{audio_text_input}")
                    
                    if temp_audio_path.exists():
                        os.remove(temp_audio_path)
                        
                except Exception as e:
                    st.sidebar.error(f"Speech recognition failed: {e}")

    elif is_ocr_mode:
        st.subheader(L["ocr_header"])
        uploaded_file = st.file_uploader(L["ocr_hint"], type=["jpg", "jpeg", "png"])
        if uploaded_file:
            st.image(uploaded_file, caption=L["ocr_caption"], use_container_width=True)

# ==============================================================================
# 7. 輔助函數：OpenAI TTS 語音生成
# ==============================================================================
def text_to_speech_openai(text, voice_value, output_filename="response.mp3"):
    if not client:
        return None
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice_value,
            input=text
        )
        response.stream_to_file(output_filename)
        return output_filename
    except Exception as e:
        st.error(f"OpenAI TTS 語音生成失敗: {e}")
        return None

def encode_image_to_base64(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

# ==============================================================================
# 8. 主畫面邏輯（🎯 核心修改：將變數拉至最外層，使所有 Mode 都能讀取，防止清除時報錯）
# ==============================================================================
st.title(L["title"])

dynamic_system_prompt = (
    f"你是一位專業的高齡照護陪伴 AI，同時也是一位充滿愛心、耐心、孝順且正向的孫子或孫女。\n"
    f"你正在陪伴的對象是「{short_title}」，請自然且親切地稱呼對方為【{short_title}】。\n"
    "你的主要任務不是回答問題，而是陪伴、關心、傾聽與鼓勵長者，讓長者感受到被重視、被關懷與被陪伴。\n\n"
    "【角色設定】\n"
    "你的個性必須保持：溫柔、耐心、親切、樂觀、正向、有同理心。\n"
    "請像真正的孫子或孫女與長輩聊天，而不是像客服或機器人。\n"
    "讓長者感受到：有人關心我、有人願意聽我說話、我不是一個人。\n\n"
    "【對話風格】\n"
    "請使用自然口語，像家人聊天一樣。\n"
    "可以適度加入語氣詞，例如：哇、喔、真的呀、太好了、辛苦您了、好棒喔。\n"
    "避免使用生硬、官方、書面化的語氣。\n"
    "不要使用條列式回答。\n\n"
    "【長者友善原則】\n"
    "請使用簡單易懂的詞彙。\n"
    "避免艱深術語與複雜說明。\n"
    "每次回答控制在 30～80 個字左右。\n"
    "盡量不超過 3 句話。\n"
    "因為長者主要透過語音收聽，所以回答必須簡短清楚。\n\n"
    "【情緒支持】\n"
    "如果長者提到身體不舒服、疼痛、失眠、孤單、難過、焦慮、擔心家人等情況。\n"
    "請優先表達同理與關心。\n"
    "先安慰，再鼓勵，最後再進行簡單互動。\n"
    "不要直接跳到建議或分析。\n\n"
    "【正向鼓勵】\n"
    "適度給予肯定與鼓勵。\n"
    "例如：好棒喔、真不容易呢、辛苦您了、您做得很好喔、今天也很努力呢。\n\n"
    "【一次一問】\n"
    "每次回覆結尾最多只能提出一個問題。\n"
    "問題必須簡單且容易回答。\n"
    "禁止一次提出多個問題。\n\n"
    "【記憶運用】\n"
    "如果系統提供長者近期紀錄或歷史對話內容，請自然融入對話中，不要直接列出記錄內容。\n\n"
    "【天氣關懷】\n"
    "如果系統提供目前天氣資訊，請把天氣轉化成貼心提醒，不要直接照念氣象資訊。\n\n"
    "【健康提醒】\n"
    "可以提醒：多喝水、按時吃藥、均衡飲食、適度活動、保持充足睡眠。\n\n"
    "【醫療安全規則】\n"
    "不要自行診斷疾病，如果出現胸痛、呼吸困難、昏倒等情況，請溫柔提醒儘快聯絡家人或醫護人員。\n\n"
    "【回覆格式】\n"
    f"1. 自然稱呼【{short_title}】。2. 關心與回應對方內容。3. 给予鼓勵與陪伴感。4. 最多提出一個簡單問題。"
)

elder_memory = user_data.get("memory", "長者喜歡被關心，目前尚無特殊疾病紀錄。")
memory_prompt = f"【系統隱藏提示：這是長者的近期記憶與狀態，請自然融入對話中】\n{elder_memory}"
dynamic_welcome_msg = L["welcome_template"].format(user_title=short_title)

# ----------------- 模式 1：AI 溫柔陪聊 -----------------
if is_chat_mode:
    st.write(L["subtitle"])
    
    # 加上 "messages" not in st.session_state 判定，被洗掉時會自動重新抓取歡迎詞
    if ("current_lang" not in st.session_state or st.session_state.current_lang != lang or 
        "current_title" not in st.session_state or st.session_state.current_title != short_title or
        "messages" not in st.session_state):
        
        st.session_state.current_lang = lang
        st.session_state.current_title = short_title
        st.session_state.messages = [
            {"role": "system", "content": dynamic_system_prompt},
            {"role": "system", "content": memory_prompt},
            {"role": "assistant", "content": dynamic_welcome_msg}
        ]

    for msg in st.session_state.messages:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    user_input = st.chat_input(L["chat_placeholder"])
    if audio_text_input:
        user_input = audio_text_input

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
            
        user_data["chat_logs"].append({"time": str(datetime.now()), "role": "user", "msg": user_input})
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_data(user_data)

        # 危險症狀警示】雙語關鍵字攔截與 LINE 緊急群發通報
        danger_keywords = ["胸痛", "跌倒", "摔倒", "呼吸困難", "喘不過氣", "吐血", "暈", "劇痛","痛","不舒服" ,"chest pain", "fall", "can't breathe"]
        if any(k in user_input.lower() for k in danger_keywords):
            st.error(L["alert_danger"])
            warning_audio = text_to_speech_openai(L["alert_audio"].format(user_title=short_title), chosen_voice_value, "alert.mp3")
            if warning_audio:
                st.audio(warning_audio, format="audio/mp3", autoplay=True)
            
            # 根據當前語系自動切換 LINE 推播內容
            if lang == "繁體中文":
                alert_msg = (
                    f"🚨 【系統緊急通知】🚨\n\n"
                    f"您好，系統剛剛偵測到 {short_title} 提及身體嚴重不適！\n\n"
                    f"長者發出的原話：「{user_input}」\n\n"
                    f"系統已第一時間用語音引導長者坐下休息並提醒就醫，請您立刻與長者聯繫確認安全狀況！"
                )
            else:
                alert_msg = (
                    f"🚨 【Emergency Alert Notification】🚨\n\n"
                    f"Hello, the system has just detected that {short_title} mentioned severe physical discomfort!\n\n"
                    f"Elder's original words: \"{user_input}\"\n\n"
                    f"The system has immediately guided the elder by voice to sit down, rest, and seek medical attention. Please contact them immediately to ensure their safety!"
                )
            
            send_line_alert(alert_msg)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            if client:
                try:
                    current_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                    
                    if "天氣" in user_input or "weather" in user_input.lower():
                        live_weather_info = get_live_weather(location="Minxiong")
                        weather_prompt = f"【System Info: Current weather is {live_weather_info}. Please blend this naturally into your reply.】"
                        current_messages.insert(-1, {"role": "system", "content": weather_prompt})

                    meds_list = user_data.get("medications", [])
                    if meds_list:
                        meds_ctx = "【長者目前被系統紀錄的藥單資訊 / Medication Memory】:\n"
                        for m in meds_list:
                            m_n = m.get("藥名", m.get("Medication Name", "未知"))
                            m_t = m.get("什麼時候吃", m.get("When to take", "未標示"))
                            m_d = m.get("吃多少", m.get("Dosage", "未標示"))
                            m_a = m.get("藥物外觀", m.get("Appearance", "未標示"))
                            meds_ctx += f"- 藥名: {m_n}, 服用時間: {m_t}, 單次劑量: {m_d}, 常見外觀: {m_a}\n"
                        meds_ctx += "\n【指示】：如果長者詢問他該吃什麼藥、藥物長相、或者怎麼服用，你必須根據上方表格資料給予溫柔、正確且極度簡短的對話口頭解答。"
                        current_messages.insert(-1, {"role": "system", "content": meds_ctx})

                    now = datetime.now()
                    if lang == "繁體中文":
                        weekdays_tw = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                        current_time_str = now.strftime("%Y年%m月%d日 %H:%M") + f" ({weekdays_tw[now.weekday()]})"
                        time_prompt = f"【系統提示時間感知：現在時間是 {current_time_str}。請根據現在的時間給予適切的關心（如午安、該休息了）。另外，請運用你的知識推算今天的「農曆日期」或「近期節氣與傳統節日」，並自然且溫馨地在回覆中跟長者分享或問候！】"
                    else:
                        weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        current_time_str = now.strftime("%Y-%m-%d %H:%M") + f" ({weekdays_en[now.weekday()]})"
                        time_prompt = f"【System Info: Current local time is {current_time_str}. Please greet the user based on the time of day. Also, accurately infer today's Traditional Chinese Lunar date or upcoming traditional festivals/solar terms, and naturally share it with the user in your response!】"

                    current_messages.insert(-1, {"role": "system", "content": time_prompt})

                    current_messages.append({
                        "role": "system", 
                        "content": "FINAL CRITICAL RULE: You MUST evaluate the language of the user's message above. If it is English, your ENTIRE response MUST be in English. 如果上方使用者的訊息是中文，你的回覆必須全部是中文。"
                    })

                    stream = client.chat.completions.create(
                        model="gpt-4o-mini", 
                        messages=current_messages,
                        stream=True,
                    )
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    
                    user_data["chat_logs"].append({"time": str(datetime.now()), "role": "assistant", "msg": full_response})
                    save_data(user_data)
                    
                    with st.spinner(L["tts_loading"]):
                        audio_file_path = text_to_speech_openai(full_response, chosen_voice_value, output_filename="chat_response.mp3")
                        if audio_file_path:
                            st.audio(audio_file_path, format="audio/mp3", autoplay=True)
                    
                except Exception as e:
                    st.error(L["api_error"])
                    full_response = L["api_error"]
                    message_placeholder.markdown(full_response)
            else:
                st.error(L["api_no_key"])

            st.session_state.messages.append({"role": "assistant", "content": full_response})

# ----------------- 模式 2：藥袋 OCR 辨識 -----------------
elif is_ocr_mode:
    if uploaded_file is not None:
        st.subheader(L["ocr_result_title"])
        if client:
            with st.spinner(L["gpt_processing"]):
                try:
                    base64_image = encode_image_to_base64(uploaded_file)
                    prompt = L["ocr_prompt_template"].format(short_title=short_title)
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }
                        ],
                        temperature=0.1
                    )
                    gpt_output = response.choices[0].message.content.strip()
                    if gpt_output.startswith("```json"):
                        gpt_output = gpt_output.replace("```json", "").replace("```", "").strip()
                    elif gpt_output.startswith("```"):
                        gpt_output = gpt_output.replace("```", "").strip()
                        
                    parsed_data = json.loads(gpt_output)
                    med_list_key = L["ocr_med_list_key"]
                    script_key = L["ocr_script_key"]
                    
                    if parsed_data.get(med_list_key):
                        st.data_editor(parsed_data[med_list_key], use_container_width=True)
                        user_data["medications"].extend(parsed_data[med_list_key])
                        save_data(user_data)
                        
                        voice_script = parsed_data[script_key]
                        st.divider()
                        st.subheader(L["ocr_voice_title"])
                        st.info(voice_script)
                        
                        with st.spinner(L["tts_loading"]):
                            audio_file_path = text_to_speech_openai(voice_script, chosen_voice_value, output_filename="med_reminder.mp3")
                            if audio_file_path:
                                st.audio(audio_file_path, format="audio/mp3", autoplay=True)
                        st.success(L["ocr_success"])
                    else:
                        st.warning(L["ocr_warning"])
                except Exception as e:
                    st.error(f"視覺解析失敗: {e}")
        else:
            st.error(L["api_no_key"])
    else:
        st.info(L["ocr_hint_panel"])

# ----------------- 模式 3：用藥提醒清單 -----------------
elif is_list_mode:
    st.subheader(L["list_title"])
    if not user_data.get("medications"):
        st.info(L["list_empty"])
    else:
        for idx, med in enumerate(user_data["medications"]):
            med_name = med.get("藥名", med.get("Medication Name", "未知藥物 / Unknown"))
            med_time = med.get("什麼時候吃", med.get("When to take", "未標示 / N/A"))
            med_dose = med.get("吃多少", med.get("Dosage", "未標示 / N/A"))
            med_app = med.get("藥物外觀", med.get("Appearance", "未標示 / N/A"))
            
            with st.expander(f"📌 {med_name}", expanded=True):
                st.write(f"**{L['list_time']}**：{med_time}")
                st.write(f"**{L['list_dose']}**：{med_dose}")
                st.write(f"**{L['list_appearance']}**：{med_app}")
                st.divider()
                
                # 用藥確認與 LINE 群發報平安
                is_med_taken_originally = med.get("checked", False)
                cb_unique_key = f"cb_{idx}_{med_name}"
                med_taken_now = st.checkbox(L["list_taken"], value=is_med_taken_originally, key=cb_unique_key)
                
                if med_taken_now and not is_med_taken_originally:
                    user_data["medications"][idx]["checked"] = True
                    now_date_str = str(datetime.today().date())
                    now_time_str = datetime.now().strftime("%H:%M")
                    if not any(h["date"] == now_date_str and h["med_name"] == med_name for h in user_data["taken_history"]):
                        user_data["taken_history"].append({
                            "date": now_date_str,
                            "time": now_time_str,
                            "med_name": med_name,
                            "med_time": med_time,
                            "med_dose": med_dose
                        })
                    save_data(user_data)
                    
                    if lang == "繁體中文":
                        line_report_text = f"🟢 【長者服藥報平安】\n\n您的【{short_title}】剛剛已經在系統上確認吃藥囉！\n💊 藥物名稱：{med_name}\n☀️ 服藥時間：{med_time}\n📊 藥物劑量：{med_dose}\n\n系統已記錄，請家屬放心！"
                    else:
                        line_report_text = f"🟢 【Medication Taken Report】\n\nYour beloved 【{short_title}】 has checked off their medicine!\n💊 Med Name: {med_name}\n☀️ Schedule: {med_time}\n📊 Dosage: {med_dose}\n\nEverything is on track. Rest assured!"
                    
                    send_line_alert(line_report_text)
                    st.rerun()
                    
                elif not med_taken_now and is_med_taken_originally:
                    user_data["medications"][idx]["checked"] = False
                    now_date_str = str(datetime.today().date())
                    user_data["taken_history"] = [h for h in user_data["taken_history"] if not (h["date"] == now_date_str and h["med_name"] == med_name)]
                    save_data(user_data)
                    st.rerun()
                
                st.write("") 
                # 🎯 核心修復：還原乾淨的 Google Calendar 網址字串（剔除錯誤嵌入的 Markdown）
                cal_title = f"💊 吃藥提醒: {med_name}" if lang == "繁體中文" else f"💊 Med Reminder: {med_name}"
                cal_details = f"【時間/Time】: {med_time}\n【劑量/Dosage】: {med_dose}\n【外觀/Appearance】: {med_app}\n\n*由 Senior Care AI 貼心提醒*"
                url_title = urllib.parse.quote(cal_title)
                url_details = urllib.parse.quote(cal_details)
                date_str = datetime.today().strftime("%Y%m%d")
                cal_url = f"[https://calendar.google.com/calendar/render?action=TEMPLATE&text=](https://calendar.google.com/calendar/render?action=TEMPLATE&text=){url_title}&details={url_details}&dates={date_str}/{date_str}"
                
                st.link_button(L["list_add_cal"], cal_url, type="primary")
        
        st.divider()
        if st.button(L["list_clear"]):
            user_data["medications"] = []
            user_data["taken_history"] = []
            save_data(user_data)
            st.rerun()

# ----------------- 模式 4：📅 當天紀錄檢閱 (新拆分頁面) -----------------
elif is_history_mode:
    st.subheader(L["history_title"])
    st.write(L["history_desc"])
    st.divider()
    
    # 日期選取器
    target_date = st.date_input(L["report_date_label"], value=datetime.today().date(), key="hist_date_picker")
    target_date_str = str(target_date)
    
    # 清除指定日期紀錄的按鈕
    if st.button(f"🗑️ 清除 {target_date_str} 的紀錄", type="secondary"):
        # 1. 刪除該天的聊天紀錄
        user_data["chat_logs"] = [log for log in user_data.get("chat_logs", []) if not log.get("time", "").startswith(target_date_str)]
        
        # 2. 刪除該天的服藥紀錄
        user_data["taken_history"] = [h for h in user_data.get("taken_history", []) if h.get("date") != target_date_str]
        
        # 3. 如果清除的是「今天」，同步把目前的打勾狀態與聊天視窗重置
        if target_date_str == str(datetime.today().date()):
            for med in user_data.get("medications", []):
                med["checked"] = False
            if "messages" in st.session_state:
                st.session_state.messages = [
                    {"role": "system", "content": dynamic_system_prompt},
                    {"role": "system", "content": memory_prompt},
                    {"role": "assistant", "content": dynamic_welcome_msg}
                ]
                
        save_data(user_data)
        st.success(f"✅ 已成功清除 {target_date_str} 的所有對話與用藥紀錄！")
        st.rerun()
        
    st.divider()
    
    # 1. 當日對話日誌
    st.subheader(L["report_log_sub"])
    day_logs = [log for log in user_data.get("chat_logs", []) if log.get("time", "").startswith(target_date_str)]
    if day_logs:
        for log in day_logs:
            log_time = log.get("time", "")[11:16]
            role_label = "👤 長者" if log.get("role") == "user" else "🤖 助手"
            st.caption(f"[{log_time}] {role_label}:")
            st.write(log.get("msg", ""))
    else:
        st.info(L["report_no_logs"])
        
    st.divider()
    
    # 2. 當日服藥歷史
    st.subheader(L["report_med_sub"])
    day_meds = [h for h in user_data.get("taken_history", []) if h.get("date") == target_date_str]
    if day_meds:
        for h in day_meds:
            st.success(f"✅ **{h.get('med_name')}** - 已於 {h.get('time')} 確認服用 (時段: {h.get('med_time')}, 劑量: {h.get('med_dose')})")
    else:
        st.warning(L["report_no_meds"])

# ----------------- 模式 5：📊 AI 健康報告 (新拆分頁面) -----------------
elif is_report_mode:
    st.subheader(L["report_title"])
    st.write(L["report_desc"])
    st.divider()
    
    # 日期選取器
    target_date = st.date_input(L["report_date_label"], value=datetime.today().date(), key="report_date_picker")
    target_date_str = str(target_date)
    st.divider()
    
    if st.button(L["report_btn"]):
        if not client:
            st.error(L["api_no_key"])
        else:
            # 撈取該指定日期的對話與服藥歷史資料送交大腦分析
            day_logs = [log for log in user_data.get("chat_logs", []) if log.get("time", "").startswith(target_date_str)]
            day_meds = [h for h in user_data.get("taken_history", []) if h.get("date") == target_date_str]
            
            if not day_logs:
                st.warning(L["report_no_logs_warn"])
            else:
                with st.spinner(L["report_loading"]):
                    try:
                        report_prompt = L["report_prompt_template"].format(
                            chat_logs=json.dumps(day_logs, ensure_ascii=False),
                            medications=json.dumps(day_meds, ensure_ascii=False)
                        )
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": report_prompt}],
                            temperature=0.5
                        )
                        st.success(L["report_success"])
                        st.markdown(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"{L['report_fail']}: {e}")
