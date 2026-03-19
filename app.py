import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import csv
from datetime import datetime, timedelta
import io

# Назва файлу для спільної статистики
LOG_FILE = "global_usage_stats.csv"

# --- 1. ФУНКЦІЇ ДЛЯ РОБОТИ ЗІ СТАТИСТИКОЮ ---
def save_to_log(user_query, model_name, file_name, key_name):
    """Записує дані про запит у CSV файл на сервері"""
    now = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile(LOG_FILE)
    
    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Час", "Інструкція", "Запит", "Модель", "Ключ"])
        writer.writerow([now, file_name, user_query[:50], model_name, key_name])

def load_log():
    """Зчитує історію запитів"""
    if os.path.exists(LOG_FILE):
        try:
            return pd.read_csv(LOG_FILE)
        except:
            return pd.DataFrame(columns=["Час", "Інструкція", "Запит", "Модель", "Ключ"])
    return pd.DataFrame(columns=["Час", "Інструкція", "Запит", "Модель", "Ключ"])

# --- 2. КОНФІГУРАЦІЯ ІНТЕРФЕЙСУ ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 26px; font-weight: bold; margin-top: -40px; margin-bottom: 25px; color: #1E1E1E; }
    [data-testid="stVerticalBlock"] > div:has(div.stButton) { width: 100% !important; }
    .stButton { width: 100% !important; }
    div[data-testid="stButton"] button { width: 100% !important; height: 55px !important; border-radius: 12px !important; font-weight: bold !important; font-size: 18px !important; }
    div[data-testid="stButton"] button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stButton"] button[kind="secondary"] { background-color: #6c757d !important; color: white !important; }
    .answer-card { background-color: #ffffff; padding: 22px; border-radius: 15px; border-left: 6px solid #28a745; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-top: 20px; font-size: 16px; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. ЛОГІКА РОБОТИ З ШІ ---
def get_ai_response(prompt):
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    active_keys = [k for k in key_names if k in st.secrets]
    
    if not active_keys:
        return None, "Помилка: Ключі API не знайдено.", "N/A", "N/A"

    last_error = ""
    for name in active_keys:
        try:
            genai.configure(api_key=st.secrets[name])
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            target = 'models/gemini-1.5-flash'
            chosen_model_name = target if target in available_models else available_models[0]
            
            model = genai.GenerativeModel(chosen_model_name)
            response = model.generate_content(prompt)
            return response.text, None, chosen_model_name.replace("models/", ""), name
        except Exception as e:
            last_error = str(e)
            continue
            
    return None, f"Помилка: {last_error}", "Error", "None"

# --- 4. БОКОВА ПАНЕЛЬ (АДМІНІСТРУВАННЯ ТА СКАЧУВАННЯ) ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    admin_code = st.text_input("Код доступу:", type="password")
    
    if admin_code == "3003":
        st.subheader("📊 Глобальна статистика")
        df_log = load_log()
        if not df_log.empty:
            st.dataframe(df_log[::-1], use_container_width=True, hide_index=True)
            
            # --- ФУНКЦІЯ СКАЧУВАННЯ ---
            csv_data = df_log.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Скачати історію (CSV)",
                data=csv_data,
                file_name=f"stats_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
            
            if st.button("🗑️ Видалити історію"):
                if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
                st.rerun()
        else:
            st.info("Історія порожня.")

# --- 5. ОСНОВНИЙ ФУНКЦІОНАЛ ---
files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not files:
    st.error("Завантажте PDF-файли.")
    st.stop()

selected_pdf = st.selectbox("Оберіть інструкцію:", files)
mode = st.radio("Формат відповіді:", ["Стисло (тези)", "Розгорнуто"], horizontal=True)

@st.cache_data
def load_pdf_text(path):
    try:
        reader = PyPDF2.PdfReader(path)
        return " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except: return ""

pdf_text = load_pdf_text(selected_pdf)
user_input = st.text_input("Запитання:", placeholder="Наприклад: Вимоги безпеки...")

btn_search = st.button("🔍 Пошук", type="primary")

# --- 6. ОБРОБКА ЗАПИТУ ---
if btn_search:
    if not user_input:
        st.warning("Введіть запитання!")
    elif not pdf_text:
        st.error("PDF не зчитано.")
    else:
        with st.status("ШІ працює...") as status:
            context = pdf_text[:15000] 
            style = "тезисно" if mode == "Стисло (тези)" else "детально"
            full_prompt = f"Контекст: {context}\n\nПитання: {user_input}\nМова: Українська. Стиль: {style}."
            
            answer, error, model_used, key_used = get_ai_response(full_prompt)
            
            if answer:
                save_to_log(user_input, model_used, selected_pdf, key_used)
                status.update(label="Готово!", state="complete")
                st.markdown(f'<div class="answer-card">{answer}</div>', unsafe_allow_html=True)
            else:
                st.error(error)

st.markdown(f"<div style='text-align: center; color: gray; font-size: 10px; margin-top: 50px;'>© {datetime.now().year} ПЧУ-5</div>", unsafe_allow_html=True)
