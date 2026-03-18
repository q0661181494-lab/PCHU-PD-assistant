import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 1. КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(
    page_title="Технічна бібліотека ст. Ворожба", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ПОСИЛЕНИЙ CSS: Відступи, Кольори кнопок та Заголовок
st.markdown("""
    <style>
    /* Налаштування відступів контейнера */
    .block-container {
        padding-top: 2rem !important; /* Трохи більше місця зверху для видимості меню */
        padding-bottom: 0rem !important;
    }
    
    /* Кнопки на всю ширину та висоту */
    div[data-testid="stButton"] button {
        width: 100% !important; 
        height: 55px !important; 
        margin-top: 10px !important;
        margin-bottom: 5px !important;
        font-size: 18px !important; 
        font-weight: bold !important; 
        border-radius: 10px !important;
        border: none !important;
    }
    
    /* Зелена кнопка (Пошук) */
    div[data-testid="stButton"] button[kind="primary"] { 
        background-color: #28a745 !important; 
        color: white !important; 
    }
    
    /* СІРА кнопка (Очистити) */
    div[data-testid="stButton"] button[kind="secondary"] { 
        background-color: #6c757d !important; 
        color: white !important; 
    }

    /* Стиль заголовка - тепер з невеликим відступом зверху */
    .main-title {
        margin-top: 10px !important;
        padding-bottom: 15px;
        text-align: center;
        font-size: 26px;
        font-weight: bold;
        color: #1E1E1E;
    }
    </style>
    """, unsafe_allow_html=True)

# Заголовок
st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 0. ГЛОБАЛЬНА СТАТИСТИКА ---
@st.cache_resource
def get_global_stats():
    return []

global_stats = get_global_stats()

if "user_query" not in st.session_state:
    st.session_state.user_query = ""

def clear_text():
    st.session_state.user_query = ""

# --- БІЧНА ПАНЕЛЬ (SIDEBAR) ---
with st.sidebar:
    st.markdown("### ⚙️ Адмін-панель")
    admin_password = st.text_input("Введіть пароль для статистики:", type="password")
    
    if admin_password == "30033003": 
        st.success("Доступ до аналітики відкрито")
        if global_stats:
            df = pd.DataFrame(global_stats)
            st.write("Останні запити:")
            st.dataframe(df[::-1], use_container_width=True)
            if st.button("🗑️ Очистити історію", type="secondary"):
                global_stats.clear()
                st.rerun()
        else:
            st.info("Історія запитів порожня.")

# --- 2. ФУНКЦІЇ ТА ЗБІР ФАЙЛІВ ---
def extract_text_from_pdf(file_path, max_pages=500):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except: return ""

available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ Покладіть PDF файли в папку з додатком.")
    st.stop()

# --- 4. МЕНЮ ВИБОРУ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла", "Розгорнута"], horizontal=True)

# Кешування контексту для швидкості (опціонально)
final_context = extract_text_from_pdf(selected_option)[:200000]

# --- 5. ПОШУК ТА КНОПКИ ---
st.write("---")
user_query = st.text_input("Пошук", placeholder="Введіть ваше питання тут...", key="user_query", label_visibility="collapsed")

# Кнопки вертикально одна під одною
search_button = st.button("🔍 Пошук", type="primary", use_container_width=True)
st.button("🗑️ Очистити поле", type="secondary", on_click=clear_text, use_container_width=True)

# --- 6. ЛОГІКА ВІДПОВІДІ ---
if search_button and final_context:
    if not user_query.strip():
        st.warning("Будь ласка, напишіть запитання.")
    else:
        now_utc = datetime.utcnow()
        ukraine_offset = 3 if (4 <= now_utc.month <= 10) else 2
        current_date_time = (now_utc + timedelta(hours=ukraine_offset)).strftime("%d.%m %H:%M:%S")
        
        start_process = time.time()
        success = False
        tried_keys = [] 
        
        with st.spinner('ШІ шукає відповідь...'):
            key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
            random.shuffle(key_names) 
            
            for key_id in key_names:
                if key_id in st.secrets:
                    tried_keys.append(key_id)
                    try:
                        genai.configure(api_key=st.secrets[key_id])
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        style = "тези" if answer_mode == "Стисла" else "детально з пунктами правил"
                        prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
                        
                        response = model.generate_content(prompt)
                        st.subheader("Результат пошуку:")
                        st.success(response.text)
                        
                        global_stats.append({
                            "Дата/Час": current_date_time,
                            "Запит": user_query,
                            "Статус": "Успішно",
                            "Ключ": key_id
                        })
                        success = True
                        break 
                    except: continue 
            
            if not success:
                st.error("⚠️ На жаль, зараз ліміти безкоштовних запитів вичерпані. Спробуйте пізніше.")

# --- 7. ПІДПИС ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
