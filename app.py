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
# ID вашої таблиці зі скріншота
SPREADSHEET_ID = "1OINic0CgdHAXhegjbHgQdflbTL0DnpHJDj7EwA1N1Tw"

# Створення підключення до Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def save_to_google_sheets(row_data):
    """Записує дані у наступний вільний рядок таблиці"""
    try:
        # Зчитуємо поточні дані (перші 7 стовпців)
        # Використовуємо worksheet="Аркуш1" або індекс "0"
        df = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="0")
        df = df.dropna(how="all") # прибираємо порожні рядки
        
        # Створюємо новий рядок як DataFrame з тими ж назвами колонок, що в таблиці
        new_row = pd.DataFrame([row_data], columns=df.columns)
        
        # Додаємо новий рядок до існуючих
        updated_df = pd.concat([df, new_row], ignore_index=True)
        
        # Оновлюємо таблицю в хмарі
        conn.update(spreadsheet=SPREADSHEET_ID, data=updated_df)
    except Exception as e:
        st.error(f"Помилка запису в Google Таблицю: {e}")

# --- 2. ДОПОМІЖНІ ФУНКЦІЇ ---
def get_user_ip():
    try: return requests.get('https://ifconfig.me', timeout=2).text
    except: return "Невідомо"

def get_user_device():
    ua = st.context.headers.get("User-Agent", "").lower()
    if any(m in ua for m in ["iphone", "android", "mobile"]): return "Мобільний"
    return "Комп'ютер"

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
    """Шукає найбільш релевантні шматки тексту (RAG)"""
    if not query: return ""
    chunks = [full_text[i:i+3000] for i in range(0, len(full_text), 2500)]
    query_words = query.lower().split()
    scored_chunks = []
    for chunk in chunks:
        score = sum(chunk.lower().count(word) for word in query_words)
        scored_chunks.append((score, chunk))
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return "\n---\n".join([c[1] for c in scored_chunks[:top_k]])

def get_ai_response(prompt):
    """Отримує відповідь від ШІ, перебираючи ваші ключі"""
    keys = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(keys)
    for k_name in keys:
        if k_name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[k_name])
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text, "Gemini 1.5 Flash", k_name
            except: continue
    return None, None, None

# --- 3. ІНТЕРФЕЙС ТА СТИЛІ ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 24px; font-weight: bold; margin-top: -40px; margin-bottom: 25px; color: #1E1E1E; }
    div[data-testid="stButton"] button { width: 100% !important; height: 55px !important; border-radius: 12px !important; font-weight: bold !important; font-size: 18px !important; margin-top: 8px !important; border: none !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; }
    div[data-testid="stButton"] button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stButton"] button[kind="secondary"] { background-color: #6c757d !important; color: white !important; }
    .answer-card { background-color: #f8f9fa; padding: 22px; border-radius: 15px; border-left: 6px solid #28a745; color: #1E1E1E; box-shadow: 0 4px 12px rgba(0,0,0,0.05); line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

if "query_field" not in st.session_state: st.session_state.query_field = ""

# Вибір файлу
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.error("Завантажте PDF-інструкції!")
    st.stop()

selected_file = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Формат відповіді:", ["Стисла", "Розгорнута"], horizontal=True)

# Пошуковий запит
user_query = st.text_input("Пошук", placeholder="Введіть запитання...", key="query_field", label_visibility="collapsed")

# Кнопка пошуку
if st.button("🔍 Знайди відповідь", type="primary"):
    if not user_query:
        st.warning("Будь ласка, введіть запитання.")
    else:
        start_time = time.time()
        with st.status("Обробка...", expanded=True) as status:
            full_text = extract_text_from_pdf(selected_file)
            context = get_relevant_context(user_query, full_text)
            
            style = "тезисно" if answer_mode == "Стисла" else "детально з пунктами"
            prompt = f"Контекст: {context}\n\nПитання: {user_query}\n\nВідповідай українською, стиль: {style}."
            
            answer, model_name, key_used = get_ai_response(prompt)
            proc_time = round(time.time() - start_time, 2)
            
            if answer:
                status.update(label=f"✅ Готово! ({proc_time} сек)", state="complete")
                st.markdown(f'<div class="answer-card">{answer}</div>', unsafe_allow_html=True)
                
                # Запис у Google Таблицю за вашим списком колонок
                save_to_google_sheets([
                    (datetime.now() + timedelta(hours=2)).strftime("%d.%m.%Y %H:%M:%S"),
                    get_user_ip(),
                    user_query,
                    proc_time,
                    model_name,
                    key_used,
                    get_user_device()
                ])
            else:
                status.update(label="❌ Помилка ШІ", state="error")

if st.button("🗑️ Очистити пошук", type="secondary"):
    st.session_state.query_field = ""
    st.rerun()

st.markdown(f"<div style='text-align: center; color: gray; font-size: 11px; margin-top: 50px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
