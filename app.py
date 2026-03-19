import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. ПІДКЛЮЧЕННЯ ТАБЛИЦІ ---
SPREADSHEET_ID = "1OINic0CgdHAXhegjbHgQdflbTL0DnpHJDj7EwA1N1Tw"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. СТИЛІ (Кнопки на всю ширину та дизайн) ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")
st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 26px; font-weight: bold; margin-bottom: 25px; color: #1E1E1E; }
    /* Фікс кнопок: на всю ширину */
    .stButton > button {
        width: 100% !important;
        height: 60px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        display: block !important;
        margin-bottom: 10px !important;
    }
    button[kind="primary"] { background-color: #28a745 !important; color: white !important; border: none !important; }
    button[kind="secondary"] { background-color: #6c757d !important; color: white !important; border: none !important; }
    .answer-card { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border-left: 8px solid #28a745; box-shadow: 0 4px 10px rgba(0,0,0,0.1); color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. БІЧНА ПАНЕЛЬ (АДМІНКА) ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    admin_pwd = st.text_input("Введіть пароль", type="password")
    
    # Пароль береться із Secrets (поле ADMIN_PASSWORD) або "1234"
    correct_pwd = str(st.secrets.get("ADMIN_PASSWORD", "1234"))
    
    if admin_pwd == correct_pwd:
        st.success("Доступ дозволено")
        try:
            # Читаємо саме "Аркуш1", як на вашому скріншоті
            stats_df = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="Аркуш1")
            st.write("### Статистика:")
            st.dataframe(stats_df)
        except Exception as e:
            st.warning(f"Не вдалося завантажити 'Аркуш1'. Перевірте назву вкладки в таблиці.")
    elif admin_pwd:
        st.error("Невірний пароль")

# --- 4. ФУНКЦІЇ ШІ ТА PDF ---
def get_ai_response(prompt):
    # Складаємо список ключів, які ви реально ввели в Secrets
    keys_to_test = [f"KEY{i}" for i in range(1, 6)]
    available_keys = [k for k in keys_to_test if k in st.secrets]
    
    if not available_keys:
        return "ERROR_NO_KEYS"

    random.shuffle(available_keys) # Рандом для обходу лімітів
    
    for key_name in available_keys:
        try:
            genai.configure(api_key=st.secrets[key_name])
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception:
            continue # Якщо ключ не спрацював, беремо наступний
    return None

@st.cache_data
def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, "rb") as f:
            pdf = PyPDF2.PdfReader(f)
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    except:
        return ""

# --- 5. ГОЛОВНИЙ ІНТЕРФЕЙС ---
st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

available_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
if not available_files:
    st.error("Завантажте хоча б один PDF файл у GitHub!")
    st.stop()

selected_file = st.selectbox("Оберіть інструкцію:", available_files)
ans_mode = st.radio("Формат:", ["Стисла", "Розгорнута"], horizontal=True)

if "q_input" not in st.session_state: st.session_state.q_input = ""
u_query = st.text_input("Пошук", value=st.session_state.q_input, placeholder="Введіть запитання...", label_visibility="collapsed")

if st.button("🔍 Знайди відповідь", type="primary"):
    if not u_query:
        st.warning("Введіть запитання!")
    else:
        with st.status("Обробка запиту...") as status:
            pdf_content = extract_text_from_pdf(selected_file)
            if not pdf_content:
                status.update(label="❌ Помилка читання PDF", state="error")
            else:
                style_instr = "тезисно" if ans_mode == "Стисла" else "детально"
                full_prompt = f"Ти технічний експерт залізниці. Використовуй цей текст: {pdf_content[:15000]}\n\nПитання: {u_query}\n\nВідповідай українською в стилі: {style_instr}."
                
                ai_answer = get_ai_response(full_prompt)
                
                if ai_answer == "ERROR_NO_KEYS":
                    status.update(label="❌ Ключі не знайдено в Secrets", state="error")
                elif ai_answer:
                    status.update(label="✅ Готово!", state="complete")
                    st.markdown(f'<div class="answer-card">{ai_answer}</div>', unsafe_allow_html=True)
                    
                    # Логування в таблицю
                    try:
                        log_row = [(datetime.now() + timedelta(hours=2)).strftime("%d.%m.%Y %H:%M:%S"), "Користувач", u_query]
                        # Тут можна додати функцію запису conn.update, якщо колонки співпадають
                    except: pass
                else:
                    status.update(label="❌ ШІ тимчасово недоступний (ліміти)", state="error")

if st.button("🗑️ Очистити", type="secondary"):
    st.session_state.q_input = ""
    st.rerun()

st.markdown(f"<div style='text-align: center; color: gray; font-size: 11px; margin-top: 50px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
