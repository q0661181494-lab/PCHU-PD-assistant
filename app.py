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

# --- 2. КОНФІГУРАЦІЯ СТОРІНКИ ТА CSS ---
st.set_page_config(page_title="Технічна бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    /* 1. Напис та іконка підняті вгору */
    .main-title {
        text-align: center;
        font-size: 22px;
        font-weight: bold;
        margin-top: -70px; 
        margin-bottom: 15px;
        line-height: 1.2;
        color: #1E1E1E;
    }
    
    /* 2. Кнопки на ВСЮ ширину */
    div[data-testid="stButton"] {
        width: 100%;
    }
    div[data-testid="stButton"] button {
        width: 100% !important;
        display: block;
        height: 50px !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        font-size: 16px !important;
        margin-bottom: 10px !important;
        border: none !important;
    }
    
    /* Кольори кнопок */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
    }
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #6c757d !important;
        color: white !important;
    }
    
    .block-container {
        padding-top: 4.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Заголовок
st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. ФУНКЦІЯ ОЧИЩЕННЯ ПОЛЯ (БЕЗ REBOOT) ---
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

# --- 5. ПЕРЕБОР КЛЮЧІВ ТА МОДЕЛЕЙ ---
def get_ai_response(prompt):
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    
    for name in key_names:
        if name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[name])
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
    st.warning("⚠️ Файли .pdf не знайдені.")
    st.stop()

selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (детально)"], horizontal=True)

final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000] 

# ПОЛЕ ВВОДУ з прив'язаним ключем (Key)
user_query = st.text_input("Пошук", placeholder="Напишіть ваше питання...", key="query_field", label_visibility="collapsed")

# Кнопки одна під одною
search_button = st.button("🔍 Пошук", type="primary") # Зелена

# Кнопка Очистити з функцією clear_search_field (БЕЗ перезавантаження)
st.button("🗑️ Очистити поле", type="secondary", on_click=clear_search_field)

# --- 8. ЛОГІКА ВІДПОВІДІ ---
if search_button:
    if not user_query:
        st.warning("Введіть запитання.")
    elif not final_context:
        st.error("Документ порожній або не знайдений.")
    else:
        with st.spinner('ШІ аналізує документацію...'):
            style = "тези" if answer_mode == "Стисла (тези)" else "детально з пунктами правил"
            prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
            
            answer, used_model, used_key = get_ai_response(prompt)
            
            if answer:
                st.subheader("Відповідь:")
                st.success(answer)
                
                # Статистика
                now = datetime.now() + timedelta(hours=2) 
                st.session_state.stats_history.append({
                    "Час": now.strftime("%H:%M:%S"),
                    "Запит": user_query,
                    "Версія ШІ": used_model.replace("models/", ""),
                    "Ключ": used_key
                })
            else:
                st.error("❌ Помилка API. Спробуйте пізніше.")

# --- 9. ПІДПИС ---
st.markdown(f"<div style='text-align: center; color: gray; font-size: 10px; margin-top: 30px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
