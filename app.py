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

# --- 2. КОНФІГУРАЦІЯ СТОРІНКИ ТА ПРИМУСОВИЙ CSS ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    /* 1. Головний заголовок */
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
    
    /* 2. ПРИМУСОВЕ РОЗТЯГУВАННЯ КНОПОК НА ВЕСЬ ЕКРАН */
    /* Знімаємо обмеження ширини внутрішніх блоків Streamlit */
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        width: 100% !important;
    }

    /* Стилізація контейнера кнопки */
    .stButton {
        width: 100% !important;
    }

    /* Стилізація самої кнопки (максимальний пріоритет) */
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
        transition: all 0.2s ease-in-out !important;
    }
    
    /* Кольори кнопок */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #28a745 !important; /* Зелений */
        color: white !important;
    }
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #6c757d !important; /* Сірий */
        color: white !important;
    }

    /* Ефект при натисканні */
    div[data-testid="stButton"] button:active {
        transform: scale(0.98) !important;
    }

    /* Картка відповіді */
    .answer-card {
        background-color: #ffffff;
        padding: 22px;
        border-radius: 15px;
        border-left: 6px solid #28a745;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: #1E1E1E;
        line-height: 1.6;
        margin-top: 20px;
        font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. ДОПОМІЖНІ ФУНКЦІЇ ---
def clear_search_field():
    st.session_state["query_field"] = ""

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
    # RAG: Розбиття на частини для точності
    chunks = [full_text[i:i+3000] for i in range(0, len(full_text), 2500)]
    if not query: return "\n".join(chunks[:5])
    
    query_words = query.lower().split()
    scored_chunks = []
    for chunk in chunks:
        score = sum(chunk.lower().count(word) for word in query_words)
        scored_chunks.append((score, chunk))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return "\n---\n".join([c[1] for c in scored_chunks[:top_k]])

# --- 4. РОБОТА З ШІ (API) ---
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

# --- 5. БОКОВА ПАНЕЛЬ ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    access_code = st.text_input("Введіть код доступу:", type="password")
    if access_code == "3003": 
        st.subheader("Історія поточної сесії")
        if st.session_state.stats_history:
            df = pd.DataFrame(st.session_state.stats_history)
            st.dataframe(df[::-1], use_container_width=True)
        else:
            st.info("Запитів ще не було")

# --- 6. ОСНОВНИЙ ІНТЕРФЕЙС ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.error("Файли не знайдені!")
    st.stop()

selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (детально)"], horizontal=True)

# Зчитування тексту з кешуванням
full_document_text = extract_text_from_pdf(selected_option)

# Поле вводу
user_query = st.text_input("Пошук", placeholder="Введіть ваше запитання...", key="query_field", label_visibility="collapsed")

# Кнопки (одна під одною)
search_button = st.button("🔍 Пошук", type="primary")
clear_button = st.button("🗑️ Очистити поле", type="secondary", on_click=clear_search_field)

# --- 7. ЛОГІКА ВІД
