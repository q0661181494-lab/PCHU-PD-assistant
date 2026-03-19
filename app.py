import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. ПІДКЛЮЧЕННЯ ДО ТАБЛИЦЬ (БЕЗПЕЧНЕ) ---
SPREADSHEET_ID = "1OINic0CgdHAXhegjbHgQdflbTL0DnpHJDj7EwA1N1Tw"

# Налаштування сторінки (як у "золотому коді")
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

# --- 2. ВАШ ЗОЛОТИЙ CSS ---
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        margin-top: -40px; 
        margin-bottom: 25px;
        line-height: 1.2;
        color: #1E1E1E;
        display: block;
    }
    
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        width: 100% !important;
    }

    .stButton {
        width: 100% !important;
    }

    div[data-testid="stButton"] button {
        width: 100% !important;
        display: block !important;
        height: 55px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        margin-top: 8px !important;
        margin-bottom: 8px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
    }
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #6c757d !important;
        color: white !important;
    }

    .answer-card {
        background-color: #ffffff;
        padding: 22px;
        border-radius: 15px;
        border-left: 6px solid #28a745;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: #1E1E1E;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. ФУНКЦІЇ ---
def clear_search_field():
    st.session_state["query_field"] = ""

def get_ai_response(prompt):
    # Ротація ключів з ваших Secrets
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    for name in key_names:
        if name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[name])
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text, name
            except:
                continue 
    return None, None

# --- 4. АДМІН-ПАНЕЛЬ ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    access_code = st.text_input("Код доступу:", type="password")
    if access_code == "3003":
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="Аркуш1")
            st.write("Статистика запитів:")
            st.dataframe(df.dropna(how="all").tail(15))
        except:
            st.info("Таблиця недоступна")

# --- 5. ІНТЕРФЕЙС ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (детально)"], horizontal=True)

user_query = st.text_input("Введіть запитання:", key="query_field")

if st.button("🔍 Пошук", type="primary"):
    if user_query:
        with st.status("Обробка...", expanded=True) as status:
            # Видобуваємо текст (спрощено як у золотому коді)
            pdf_text = ""
            with open(selected_option, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages[:15]: 
                    pdf_text += page.extract_text() + " "
            
            prompt = f"Контекст: {pdf_text[:10000]}\n\nПитання: {user_query}\nСтиль: {answer_mode}. Українською."
            answer, used_key = get_ai_response(prompt)
            
            if answer:
                status.update(label="✅ Готово!", state="complete")
                st.markdown(f'<div class="answer-card">{answer}</div>', unsafe_allow_html=True)
                
                # ТИХИЙ ЗАПИС У ТАБЛИЦЮ
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    timestamp = (datetime.now() + timedelta(hours=2)).strftime("%d.%m.%Y %H:%M")
                    new_entry = pd.DataFrame([{"Час": timestamp, "Запит": user_query, "Ключ": used_key}])
                    old_df = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="Аркуш1")
                    updated_df = pd.concat([old_df.dropna(how="all"), new_entry], ignore_index=True)
                    conn.update(spreadsheet=SPREADSHEET_ID, worksheet="Аркуш1", data=updated_df)
                except:
                    pass 
            else:
                status.update(label="❌ Помилка API", state="error")

st.button("🗑️ Очистити поле", type="secondary", on_click=clear_search_field)

st.markdown(f"<div style='text-align: center; color: gray; font-size: 10px; margin-top: 40px;'>© {datetime.now().year} ПЧУ-5</div>", unsafe_allow_html=True)
