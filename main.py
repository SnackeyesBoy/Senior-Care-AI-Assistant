import os
import json
import base64
from pathlib import Path
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from streamlit_mic_recorder import mic_recorder
import requests

# ==============================================================================
# 0. 基礎設定
# ==============================================================================
current_dir = Path(__file__).parent if "__file__" in locals() else Path.cwd()
load_dotenv(current_dir / ".env")

st.set_page_config(page_title="Senior Care AI", page_icon="👵", layout="centered")

# ==============================================================================
# 1. API Client
# ==============================================================================
def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

client = get_client()

# ==============================================================================
# 2. UI 美化
# ==============================================================================
st.markdown("""
<style>
html, body, p { font-size: 22px !important; line-height: 1.6 !important; }
button { font-size: 20px !important; padding: 10px 20px !important; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. 天氣
# ==============================================================================
def get_weather(location="Chiayi"):
    try:
        r = requests.get(f"https://wttr.in/{location}?format=%C+%t&lang=zh-tw", timeout=5)
        return r.text.strip() if r.status_code == 200 else "晴朗 28°C"
    except:
        return "晴朗 28°C"

# ==============================================================================
# 4. 多語系
# ==============================================================================
LANG = {
    "繁體中文": {
        "title": "👵 高齡照護 AI",
        "chat": "聊天",
        "ocr": "藥袋辨識",
        "input": "說點什麼...",
        "upload": "上傳藥袋",
        "voice": "語音輸出中..."
    },
    "English": {
        "title": "👵 Senior AI",
        "chat": "Chat",
        "ocr": "OCR",
        "input": "Say something...",
        "upload": "Upload image",
        "voice": "Speaking..."
    }
}

lang = st.sidebar.selectbox("Language", list(LANG.keys()))
L = LANG[lang]

# ==============================================================================
# 5. session state 初始化
# ==============================================================================
def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

init_state()

# ==============================================================================
# 6. system prompt（簡化但保留核心）
# ==============================================================================
SYSTEM_PROMPT = """
你是溫柔的高齡陪伴AI。
請簡短回答（2~4句），溫暖、口語化，不要專業術語。
一次最多一個問題。
"""

# ==============================================================================
# 7. 工具：TTS
# ==============================================================================
def tts(text, voice="nova"):
    try:
        res = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        path = "speech.mp3"
        res.stream_to_file(path)
        return path
    except Exception as e:
        st.error(f"TTS error: {e}")
        return None

# ==============================================================================
# 8. OCR prompt
# ==============================================================================
OCR_PROMPT = """
請解析藥袋內容，輸出 JSON：
{
  "meds":[{"name":"","time":"","dose":"","appearance":""}],
  "script":"溫柔口語提醒長者吃藥"
}
不要輸出多餘文字。
"""

def parse_json_safe(text):
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return None

def encode_img(file):
    return base64.b64encode(file.getvalue()).decode()

# ==============================================================================
# 9. UI
# ==============================================================================
st.title(L["title"])

mode = st.sidebar.radio("Mode", [L["chat"], L["ocr"]])

# ==============================================================================
# 10. CHAT MODE
# ==============================================================================
if mode == L["chat"]:
    for m in st.session_state.messages:
        st.chat_message(m["role"]).write(m["content"])

    user = st.chat_input(L["input"])

    if user and client:
        st.session_state.messages.append({"role": "user", "content": user})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages

        with st.chat_message("assistant"):
            msg_box = st.empty()
            reply = ""

            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    reply += chunk.choices[0].delta.content
                    msg_box.markdown(reply + "▌")

            msg_box.markdown(reply)

            audio = tts(reply)
            if audio:
                st.audio(audio, autoplay=True)

            st.session_state.messages.append({"role": "assistant", "content": reply})

# ==============================================================================
# 11. OCR MODE
# ==============================================================================
elif mode == L["ocr"]:
    file = st.file_uploader(L["upload"], type=["png", "jpg", "jpeg"])

    if file and client:
        st.image(file, use_container_width=True)

        with st.spinner("OCR processing..."):
            img64 = encode_img(file)

            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": OCR_PROMPT},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{img64}"
                        }}
                    ]
                }],
                temperature=0.2
            )

            data = parse_json_safe(res.choices[0].message.content)

            if not data:
                st.error("解析失敗")
            else:
                st.subheader("藥物資訊")
                st.write(data.get("meds", []))

                script = data.get("script", "")
                st.info(script)

                audio = tts(script)
                if audio:
                    st.audio(audio, autoplay=True)