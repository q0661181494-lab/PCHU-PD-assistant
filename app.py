import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
from datetime import datetime, timedelta

# --- 1. ІНІЦІАЛІЗАЦІЯ СТАТИСТИКИ ТА ФАЙЛУ ---
STATS_FILE = "stats_history.csv"

if "stats_history" not in st.session_state:
    if os.path.exists(STATS_FILE):
        try:
            # Автоматичне завантаження всієї історії з диска при старті
            df_existing = pd.read_csv(STATS_FILE)
            st.session_state.stats_history = df_existing.to_dict('records')
        except:
            st.session_state.stats_history = []
    else:
        st.session_state.stats_history = []

# --- 2. КОНФІГУРАЦІЯ СТОРІНКИ ТА СТИЛІЗАЦІЯ ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    .main-title {
        text-align: center; font-size: 24px; font-weight: bold;
        margin-top: -40px; margin-bottom: 25px; line-height: 1.2;
        color: #1E1E1E; display: block;
    }
    [data-testid="stVerticalBlock"] > div:has(div.stButton) { width: 100% !important; }
    .stButton { width: 100% !important; }
    div[data-testid="stButton"] button {
        width: 100% !important; display: block !important; height: 55px !important;
        border-radius: 12px !important; font-weight: bold !important;
        font-size: 18px !important; margin-top: 8px !important;
        margin-bottom: 8px !important; border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-testid="stButton"] button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stButton"] button[kind="secondary"] { background-color: #6c757d !important; color: white !important; }
    
    .answer-card {
        background-color: #ffffff; padding: 22px; border-radius: 15px;
        border-left: 6px solid #28a745; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: #1E1E1E; line-height: 1.6; margin-top: 20px; font-size: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ ВЕЛИКИХ ТЕКСТІВ ---
def clear_search_field():
    st.session_state["query_field"] = ""

@st.cache_data(show_spinner="Аналіз документа... Це може зайняти до 1 хвилини для великих файлів")
def extract_text_from_pdf(file_path):
    text_parts = []
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t: text_parts.append(t)
        return "\n".join(text_parts)
    except Exception as e:
        return f"Помилка зчитування: {e}"

def get_relevant_context(query, full_text, top_k=25):
    # Налаштування для великих документів (250+ сторінок)
    chunk_size = 2000 
    overlap = 500  # Перекриття, щоб не розривати речення
    
    chunks = []
    for i in range(0, len(full_text), chunk_size - overlap):
        chunks.append(full_text[i:i + chunk_size])

    if not query: return "\n".join(chunks[:10])
    
    query_words = query.lower().split()
    scored_chunks = []
    for chunk in chunks:
        # Рахуємо входження слів запиту в кожному шматку
        score = sum(chunk.lower().count(word) for word in query_words)
        scored_chunks.append((score, chunk))
    
    # Сортування за релевантністю
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Повертаємо топ-25 найбільш відповідних уривків (це приблизно 40-50 тис. символів)
    return "\n\n--- ФРАГМЕНТ ІНСТРУКЦІЇ ---\n\n".join
