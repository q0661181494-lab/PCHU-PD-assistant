import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
from datetime import datetime, timedelta

# --- 1. ІНІЦІАЛІЗАЦІЯ СТАТИСТИКИ ---
if "stats_history" not in st.session_state:
    st.session_state.stats_history = []

# --- 2. КОНФІГУРАЦІЯ СТОРІНКИ ТА ПОСИЛЕНИЙ CSS ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    /* 1. Повернення та корекція заголовка */
    .main-title {
        text-align: center;
        font-size: 22px;
        font-weight: bold;
        margin-top: -40px; 
        margin-bottom: 20px;
        line-height: 1.3;
        color: #1E1E1E;
        display: block;
    }
    
    /* 2. РОЗТЯГУВАННЯ КНОПОК НА ВСЮ ШИРИНУ */
    /* Стиль для контейнера кнопки */
    div.stButton {
        width: 100% !important;
    }
    
    /* Стиль для самої кнопки всередині контейнера */
    div.stButton > button {
        width: 100% !important;
        display: block !important;
        height: 55px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        margin-top: 5px !important;
        border: none !important;
        transition: 0.3s;
    }
    
    /* Кольори кнопок */
    /* Зелена кнопка (Пошук) */
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #218838 !important;
    }
    
    /* Сіра кнопка (Очистити) */
    div.stButton > button[kind="secondary"] {
        background-color: #6c757d !important;
        color: white !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: #5a6268 !important;
    }
    
    /* Прибираємо стандартні обмеження ширини елементів Streamlit */
    .element-container, .stMarkdown, .stTextInput {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Відображення заголовка
st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. ФУНКЦІЯ ОЧИЩЕННЯ ПОЛЯ (БЕЗ ПЕРЕЗАВАНТАЖЕННЯ) ---
def clear_search_field():
    st.session_state["query_field"] = ""

# --- 4. БОКОВА ПАНЕЛЬ АДМІНІСТРАТОРА ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    access_code = st.text_input("Введіть код доступу:", type="password")
    if access_code == "3003": 
        st.subheader("Історія запитів")
        if st.session_state.stats_history:
            df = pd.DataFrame(st.session_state.stats_history)
            st.dataframe(df[::-1], use_container_width=True)
            if st.button("🗑️ Очистити історію"):
                st.session_state.stats_history = []
                st.rerun()
        else:
            st.info("Запитів ще не було")
    elif access_code:
        st.error("Невірний код")

# --- 5. ФУНКЦІЯ ШІ (ПЕРЕБОР КЛЮЧІВ) ---
def get_ai_response(prompt):
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    for name in key_names:
        if name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[name])
                # Автоматичний підбір моделі для уникнення 404
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text, model_name, name
            except Exception:
                continue 
    return None, None, None

# --- 6. ФУНКЦІЯ ЧИТАННЯ PDF ---
@st.cache_data
def extract_text_from_pdf(file_path, max_pages=500):
    text = ""
    try:
        if not os.path.exists(file_path): return ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except: return ""

# --- 7. ОСНОВНИЙ ІНТЕРФЕЙС ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.error("Файли .pdf не знайдені!")
    st.stop()

selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (детально)"], horizontal=True)

# Отримання контенту
final_context = extract_text_from_pdf(selected_option)
final_context = final_context[:250000] 

# Поле вводу з ключем для очищення
user_query = st.text_input("Пошук", placeholder="Напишіть ваше питання...", key="query_field", label_visibility="collapsed")

# Кнопки одна під одною на всю ширину
search_button = st.button("🔍 Пошук", type="primary")
clear_button = st.button("🗑️ Очистити поле", type="secondary", on_click=clear_search_field)

# --- 8. ЛОГІКА ВІДПОВІДІ ---
if search_button:
    if not user_query:
        st.warning("Будь ласка, введіть запитання.")
    else:
        with st.spinner('ШІ аналізує документацію...'):
            style = "тези" if answer_mode == "Стисла (тези)" else "детально з пунктами правил"
            prompt = f"Ти технічний експерт. Контекст: {final_context}\n\nПитання: {user_query}\n\nВідповідь має бути: {style}. Відповідай українською."
            
            answer, used_model, used_key = get_ai_response(prompt)
            
            if answer:
                st.subheader("Відповідь:")
                st.success(answer)
                
                # Запис у статистику для адмінки
                now = datetime.now() + timedelta(hours=2) 
                st.session_state.stats_history.append({
                    "Час": now.strftime("%H:%M:%S"),
                    "Запит": user_query,
                    "Модель": used_model.replace("models/", ""),
                    "Ключ": used_key
                })
            else:
                st.error("На жаль, не вдалося отримати відповідь. Перевірте ключі API.")

# --- 9. ПІДПИС ---
st.markdown(f"<div style='text-align: center; color: gray; font-size: 10px; margin-top: 30px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
