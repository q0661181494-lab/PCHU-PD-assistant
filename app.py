import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. ПІДКЛЮЧЕННЯ ---
SPREADSHEET_ID = "1OINic0CgdHAXhegjbHgQdflbTL0DnpHJDj7EwA1N1Tw"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. СТИЛІ (Кнопки на всю ширину) ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")
st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 26px; font-weight: bold; margin-bottom: 25px; }
    /* Потужний стиль для кнопок на всю ширину */
    .stButton > button {
        width: 100% !important;
        height: 60px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        display: block !important;
    }
    button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    button[kind="secondary"] { background-color: #6c757d !important; color: white !important; }
    .answer-card { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border-left: 8px solid #28a745; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. АДМІНКА ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    pwd = st.text_input("Пароль", type="password")
    if pwd == st.secrets.get("ADMIN_PASSWORD", "1234"):
        st.success("Доступ дозволено")
        try:
            # Читаємо Аркуш1 (використовуємо саме назву, як на вашому скріншоті)
            df_logs = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="Аркуш1")
            st.dataframe(df_logs)
        except:
            st.warning("Таблиця порожня або не знайдено 'Аркуш1'")
    elif pwd:
        st.error("Невірний пароль")

# --- 4. ЛОГІКА ---
def get_ai_response(prompt):
    # Беремо всі ключі KEY1-KEY5, які ми бачимо у ваших Secrets
    keys = [f"KEY{i}" for i in range(1, 6)]
    valid_keys = [k for k in keys if k in st.secrets]
    if not valid_keys: return None
    
    random.shuffle(valid_keys)
    for k in valid_keys:
        try:
            genai.configure(api_key=st.secrets[k])
            model = genai.GenerativeModel('gemini-1.5-flash')
            return model.generate_content(prompt).text
        except: continue
    return None

@st.cache_data
def load_pdf(file):
    text = ""
    with open(file, "rb") as f:
        pdf = PyPDF2.PdfReader(f)
        for p in pdf.pages:
            text += p.extract_text() + "\n"
    return text

# --- 5. ІНТЕРФЕЙС ---
st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

files = [f for f in os.listdir(".") if f.endswith(".pdf")]
selected_file = st.selectbox("Оберіть інструкцію:", files)
mode = st.radio("Формат:", ["Стисла", "Розгорнута"], horizontal=True)

if "q" not in st.session_state: st.session_state.q = ""
query = st.text_input("Пошук", value=st.session_state.q, placeholder="Запитання...", label_visibility="collapsed")

if st.button("🔍 Знайди відповідь", type="primary"):
    if query:
        with st.status("Шукаю в ПТЕ...") as s:
            txt = load_pdf(selected_file)
            # Беремо більше тексту для кращої відповіді
            prompt = f"Ти асистент ПЧУ-5. Використовуй текст: {txt[:15000]}\n\nПитання: {query}\n\nВідповідай українською."
            ans = get_ai_response(prompt)
            if ans:
                s.update(label="✅ Готово", state="complete")
                st.markdown(f'<div class="answer-card">{ans}</div>', unsafe_allow_html=True)
            else:
                s.update(label="❌ Помилка ключів", state="error")
    else: st.warning("Введіть запитання")

if st.button("🗑️ Очистити", type="secondary"):
    st.session_state.q = ""
    st.rerun()
