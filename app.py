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

# --- 1. КОНФІГУР ПАНЕЛІ ТА СТИЛІВ ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 26px; font-weight: bold; margin-bottom: 25px; color: #1E1E1E; }
    
    /* Кнопки на всю ширину БЕЗ КОЛОНОК */
    div.stButton > button {
        width: 100% !important;
        display: block !important;
        height: 60px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        margin-bottom: 10px !important;
    }
    
    button[kind="primary"] { background-color: #28a745 !important; color: white !important; border: none !important; }
    button[kind="secondary"] { background-color: #6c757d !important; color: white !important; border: none !important; }
    
    .answer-card { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border-left: 8px solid #28a745; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ПІДКЛЮЧЕННЯ ТАБЛИЦІ ---
SPREADSHEET_ID = "1OINic0CgdHAXhegjbHgQdflbTL0DnpHJDj7EwA1N1Tw"
conn = st.connection("gsheets", type=GSheetsConnection)

def save_to_google_sheets(row_data):
    try:
        # Читаємо існуючі дані
        df = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="0")
        df = df.dropna(how="all")
        # Додаємо новий рядок
        new_row = pd.DataFrame([row_data], columns=df.columns)
        updated_df = pd.concat([df, new_row], ignore_index=True)
        # Оновлюємо
        conn.update(spreadsheet=SPREADSHEET_ID, data=updated_df)
    except Exception as e:
        st.sidebar.error(f"Помилка запису: {e}")

# --- 3. АДМІН-ПАНЕЛЬ З ПАРОЛЕМ ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    admin_password = st.text_input("Введіть пароль", type="password")
    
    # Використовуємо пароль із Secrets або "1234" за замовчуванням
    correct_password = st.secrets.get("ADMIN_PASSWORD", "1234")
    
    if admin_password == str(correct_password):
        st.success("Доступ дозволено")
        st.write("### Статистика запитів")
        try:
            # Читаємо таблицю для відображення в адмінці
            stats_df = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="0")
            st.dataframe(stats_df)
        except:
            st.warning("Таблиця порожня або недоступна")
    elif admin_password:
        st.error("Невірний пароль")

# --- 4. ЛОГІКА ШІ ТА PDF ---
def get_ai_response(prompt):
    keys = ["KEY1", "KEY2", "KEY3"]
    valid_keys = [k for k in keys if k in st.secrets]
    if not valid_keys: return None, None, None
    
    random.shuffle(valid_keys)
    for k in valid_keys:
        try:
            genai.configure(api_key=st.secrets[k])
            model = genai.GenerativeModel('gemini-1.5-flash')
            return model.generate_content(prompt).text, "Gemini 1.5", k
        except: continue
    return None, None, None

@st.cache_data
def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except: return "Помилка читання PDF"

# --- 5. ГОЛОВНИЙ ЕКРАН ---
st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not files:
    st.error("Файли PDF не знайдені!")
    st.stop()

selected_file = st.selectbox("Оберіть інструкцію:", files)
answer_mode = st.radio("Формат відповіді:", ["Стисла", "Розгорнута"], horizontal=True)

if "query" not in st.session_state: st.session_state.query = ""
user_query = st.text_input("Пошук", value=st.session_state.query, placeholder="Введіть ваше запитання...", label_visibility="collapsed")

# Кнопка пошуку (тепер точно на всю ширину)
if st.button("🔍 Знайди відповідь", type="primary"):
    if not user_query:
        st.warning("Введіть запитання!")
    else:
        with st.status("Шукаю відповідь...") as status:
            pdf_text = extract_text_from_pdf(selected_file)
            style = "тезисно" if answer_mode == "Стисла" else "детально"
            prompt = f"Ти технічний асистент залізниці. Контекст: {pdf_text[:12000]}\n\nПитання: {user_query}\n\nВідповідай українською, стиль: {style}."
            
            answer, model_name, key_used = get_ai_response(prompt)
            
            if answer:
                status.update(label="✅ Відповідь знайдено!", state="complete")
                st.markdown(f'<div class="answer-card">{answer}</div>', unsafe_allow_html=True)
                
                # Дані для таблиці
                save_to_google_sheets([
                    (datetime.now() + timedelta(hours=2)).strftime("%d.%m.%Y %H:%M:%S"),
                    "User", user_query, "5сек", model_name, key_used, "PC/Mobile"
                ])
            else:
                status.update(label="❌ Помилка ключа ШІ", state="error")
                st.error("Перевірте KEY1 у налаштуваннях Secrets!")

# Кнопка очистки
if st.button("🗑️ Очистити пошук", type="secondary"):
    st.session_state.query = ""
    st.rerun()

st.markdown(f"<div style='text-align: center; color: gray; font-size: 11px; margin-top: 50px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
