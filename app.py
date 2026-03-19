import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. НАЛАШТУВАННЯ ТАБЛИЦІ ---
SPREADSHEET_ID = "1OINic0CgdHAXhegjbHgQdflbTL0DnpHJDj7EwA1N1Tw"
conn = st.connection("gsheets", type=GSheetsConnection)

def save_to_google_sheets(row_data):
    try:
        df = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="0")
        df = df.dropna(how="all")
        new_row = pd.DataFrame([row_data], columns=df.columns)
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(spreadsheet=SPREADSHEET_ID, data=updated_df)
    except Exception as e:
        st.sidebar.error(f"Помилка таблиці: {e}")

# --- 2. ДОПОМІЖНІ ФУНКЦІЇ ---
def get_user_ip():
    try: return requests.get('https://ifconfig.me', timeout=2).text
    except: return "Невідомо"

@st.cache_data
def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except: return ""

def get_relevant_context(query, full_text, top_k=15):
    if not query: return ""
    chunks = [full_text[i:i+3000] for i in range(0, len(full_text), 2500)]
    query_words = query.lower().split()
    scored_chunks = []
    for chunk in chunks:
        score = sum(chunk.lower().count(word) for word in query_words)
        scored_chunks.append((score, chunk))
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return "\n---\n".join([c[1] for c in scored_chunks[:top_k]])

def get_ai_response(prompt):
    # Перевіряємо ключі KEY1, KEY2... які ви маєте додати в Secrets
    keys = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(keys)
    for k_name in keys:
        if k_name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[k_name])
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text, "Gemini 1.5 Flash", k_name
            except Exception as e:
                continue
    return None, None, None

# --- 3. ІНТЕРФЕЙС ТА СТИЛІ ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

# ПОКРАЩЕНІ СТИЛІ ДЛЯ КНОПОК
st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 26px; font-weight: bold; margin-bottom: 25px; color: #1E1E1E; }
    /* Кнопки на всю ширину */
    div.stButton > button {
        width: 100% !important;
        height: 60px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 20px !important;
        text-transform: uppercase;
    }
    /* Колір кнопки пошуку */
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
    }
    /* Колір кнопки очистки */
    div.stButton > button[kind="secondary"] {
        background-color: #6c757d !important;
        color: white !important;
        border: none !important;
    }
    .answer-card { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border-left: 8px solid #28a745; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# БІЧНА ПАНЕЛЬ (SIDEBAR)
with st.sidebar:
    st.header("⚙️ Адмін-панель")
    st.info(f"Статус підключення: ✅ OK")
    st.write(f"Ваш IP: `{get_user_ip()}`")
    if st.button("🔄 Оновити дані"):
        st.rerun()

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# Основна логіка
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.error("Завантажте PDF-інструкції в репозиторій GitHub!")
    st.stop()

selected_file = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Формат відповіді:", ["Стисла", "Розгорнута"], horizontal=True)

if "query_field" not in st.session_state: st.session_state.query_field = ""

user_query = st.text_input("Пошук", value=st.session_state.query_field, placeholder="Введіть ваше запитання...", label_visibility="collapsed")

if st.button("🔍 Знайди відповідь", type="primary"):
    if not user_query:
        st.warning("Введіть запитання!")
    else:
        start_time = time.time()
        with st.status("Шукаю інформацію в інструкції...", expanded=False) as status:
            full_text = extract_text_from_pdf(selected_file)
            context = get_relevant_context(user_query, full_text)
            
            style = "тезисно" if answer_mode == "Стисла" else "детально з пунктами"
            prompt = f"Контекст із залізничної інструкції: {context}\n\nПитання: {user_query}\n\nВідповідай українською, стиль: {style}."
            
            answer, model_name, key_used = get_ai_response(prompt)
            
            if answer:
                proc_time = round(time.time() - start_time, 2)
                status.update(label=f"✅ Готово! ({proc_time} сек)", state="complete")
                st.markdown(f'<div class="answer-card">{answer}</div>', unsafe_allow_html=True)
                
                save_to_google_sheets([
                    (datetime.now() + timedelta(hours=2)).strftime("%d.%m.%Y %H:%M:%S"),
                    get_user_ip(),
                    user_query,
                    proc_time,
                    model_name,
                    key_used,
                    "Комп'ютер/Моб"
                ])
            else:
                status.update(label="❌ Помилка: Ключі ШІ не знайдено або вони не працюють", state="error")
                st.error("Будь ласка, додайте KEY1 у налаштування Secrets (Streamlit Cloud).")

if st.button("🗑️ Очистити пошук", type="secondary"):
    st.session_state.query_field = ""
    st.rerun()

st.markdown(f"<div style='text-align: center; color: gray; font-size: 11px; margin-top: 50px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
