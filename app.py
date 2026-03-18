import streamlit as st
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, NotFound, PermissionDenied
import PyPDF2
import os
import random
import pandas as pd
import re
from datetime import datetime, timedelta

# --- 1. КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    div[data-testid="stButton"] button {
        width: 100% !important; height: 55px !important; margin-top: 10px !important;
        font-size: 18px !important; font-weight: bold !important; border-radius: 12px !important;
    }
    div[data-testid="stButton"] button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stButton"] button[kind="secondary"] { background-color: #6c757d !important; color: white !important; }
    .main-title { text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 2. ФУНКЦІЇ ---
@st.cache_data(show_spinner="Зчитую інструкцію...")
def get_pdf_text(file_path):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            # Для надійності обмежимо зчитування 150 сторінками, якщо модель буде старішою
            for i, page in enumerate(reader.pages):
                if i > 150: break 
                t = page.extract_text()
                if t: text += t + " "
        return re.sub(r'\s+', ' ', text).strip()[:100000] # Тимчасово зменшимо для тесту
    except Exception as e: return f"Помилка: {e}"

if "user_query" not in st.session_state: st.session_state.user_query = ""
def clear_text(): st.session_state.user_query = ""

# --- 3. ІНТЕРФЕЙС ---
files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not files:
    st.error("Додайте PDF файли!")
    st.stop()

selected_file = st.selectbox("Оберіть інструкцію:", files)
answer_mode = st.radio("Тип відповіді:", ["Стисла", "Розгорнута"], horizontal=True)
final_context = get_pdf_text(selected_file)

user_query = st.text_input("Пошук", placeholder="Ваше питання...", key="user_query", label_visibility="collapsed")
search_btn = st.button("🔍 Пошук", type="primary", use_container_width=True)
st.button("🗑️ Очистити поле", type="secondary", on_click=clear_text, use_container_width=True)

# --- 4. ЛОГІКА ШІ (УНІВЕРСАЛЬНА) ---
if search_btn and user_query:
    success = False
    # Пріоритет: 1.5 Flash -> 1.5 Flash-latest -> 1.0 Pro (найбільш сумісна)
    model_variants = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-1.0-pro']
    
    with st.spinner('Зв'язoк з сервером Google...'):
        available_keys = [k for k in ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"] if k in st.secrets]
        random.shuffle(available_keys)

        for key_id in available_keys:
            if success: break
            genai.configure(api_key=st.secrets[key_id])
            
            for mv in model_variants:
                try:
                    # Для 1.0 Pro не використовуємо system_instruction (вона її не підтримує)
                    if mv == 'gemini-1.0-pro':
                        model = genai.GenerativeModel(model_name=mv)
                        full_prompt = f"Ти технічний експерт. Використовуй цей текст: {final_context}\n\nПитання: {user_query}. Відповідай українською."
                    else:
                        model = genai.GenerativeModel(
                            model_name=mv,
                            system_instruction="Ти експерт ПЧУ-5. Відповідай суворо за текстом."
                        )
                        full_prompt = f"Контекст: {final_context}\n\nПитання: {user_query}"
                    
                    response = model.generate_content(full_prompt)
                    st.subheader("Результат:")
                    st.success(response.text)
                    success = True
                    break 
                except (PermissionDenied, NotFound):
                    continue # Пробуємо іншу модель або ключ
                except Exception as e:
                    last_error = str(e)
                    continue

        if not success:
            st.error(f"⚠️ Помилка доступу. Можлива причина: ваш регіон заблоковано Google для API. Спробуйте створити новий ключ з іншим обліковим записом Google.")
            st.info(f"Технічні деталі останньої спроби: {last_error}")

st.markdown(f"<hr><center>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</center>", unsafe_allow_html=True)
