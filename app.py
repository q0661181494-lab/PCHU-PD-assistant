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
        st.error(f"Помилка запису: {e}")

# --- 2. СТИЛІ (Кнопки на всю ширину) ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 26px; font-weight: bold; margin-bottom: 25px; color: #1E1E1E; }
    
    /* Кнопки на всю ширину */
    div.stButton > button {
        width: 100% !important;
        display: block;
        height: 60px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        border: none !important;
    }
    
    /* Кольори */
    button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    button[kind="secondary"] { background-color: #6c757d !important; color: white !important; }
    
    .answer-card { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border-left: 8px solid #28a745; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 3. БІЧНА ПАНЕЛЬ З ПАРОЛЕМ ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    admin_password = st.text_input("Введіть пароль", type="password")
    
    # Пароль за замовчуванням "pchu5admin" (можете змінити в Secrets пізніше)
    correct_password = st.secrets.get("ADMIN_PASSWORD", "1234") 
    
    if admin_password == correct_password:
        st.success("Доступ дозволено")
        st.write("### Статистика запитів")
        try:
            data = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="0")
            st.dataframe(data, use_container_width=True)
        except:
            st.warning("Не вдалося завантажити таблицю")
    elif admin_password:
        st.error("Невірний пароль")

# --- 4. ОСНОВНА ЛОГІКА ---
def get_ai_response(prompt):
    keys = ["KEY1", "KEY2", "KEY3"]
    random.shuffle(keys)
    for k in keys:
        if k in st.secrets:
            try:
                genai.configure(api_key=st.secrets[k])
                model = genai.GenerativeModel('gemini-1.5-flash')
                return model.generate_content(prompt).text, "Gemini 1.5", k
            except: continue
    return None, None, None

@st.cache_data
def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
selected_file = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Формат відповіді:", ["Стисла", "Розгорнута"], horizontal=True)

if "query_field" not in st.session_state: st.session_state.query_field = ""
user_query = st.text_input("Пошук", value=st.session_state.query_field, placeholder="Введіть запитання...", label_visibility="collapsed")

col1, col2 = st.columns(1) # Для гарантії ширини кнопок у стовпці

with col1:
    if st.button("🔍 Знайди відповідь", type="primary"):
        if not user_query:
            st.warning("Введіть запитання!")
        else:
            with st.status("Шукаю в документах...") as status:
                full_text = extract_text_from_pdf(selected_file)
                style = "тезисно" if answer_mode == "Стисла" else "детально"
                prompt = f"Текст: {full_text[:10000]}\n\nПитання: {user_query}\n\nСтиль: {style}. Мова: українська."
                
                answer, model_name, key_used = get_ai_response(prompt)
                
                if answer:
                    status.update(label="✅ Готово!", state="complete")
                    st.markdown(f'<div class="answer-card">{answer}</div>', unsafe_allow_html=True)
                    save_to_google_sheets([
                        (datetime.now() + timedelta(hours=2)).strftime("%d.%m.%Y %H:%M:%S"),
                        "User", user_query, "---", model_name, key_used, "Device"
                    ])
                else:
                    status.update(label="❌ Помилка ключа ШІ", state="error")
                    st.error("Додайте KEY1 у Secrets!")

if st.button("🗑️ Очистити пошук", type="secondary"):
    st.session_state.query_field = ""
    st.rerun()

st.markdown(f"<div style='text-align: center; color: gray; font-size: 11px; margin-top: 50px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
