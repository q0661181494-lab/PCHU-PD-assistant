import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 0. ГЛОБАЛЬНА СТАТИСТИКА (СПІЛЬНА ПАМ'ЯТЬ) ---
@st.cache_resource
def get_global_stats():
    return []

global_stats = get_global_stats()

# Стан поля пошуку
if "user_query" not in st.session_state:
    st.session_state.user_query = ""

def clear_text():
    st.session_state.user_query = ""

# --- 1. ПІДКЛЮЧЕННЯ ШІ (РОТАЦІЯ КЛЮЧІВ) ---
def get_working_model():
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                return genai.GenerativeModel(model_name)
            except:
                continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ТА СТИЛІЗАЦІЯ ---
st.set_page_config(
    page_title="Технічна бібліотека ст. Ворожба", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS для великих кнопок, хрестика та мобільної версії
st.markdown("""
    <style>
    input::-webkit-search-cancel-button { -webkit-appearance: searchfield-cancel-button !important; cursor: pointer; }
    div[data-testid="stButton"] button {
        width: 100% !important; height: 50px !important; margin-bottom: 10px !important;
        font-size: 18px !important; font-weight: bold !important; border: none !important;
    }
    div[data-testid="stButton"] button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stButton"] button[kind="secondary"] { background-color: #dc3545 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<h3 style='margin-bottom: 0px;'>⚙️ Налаштування</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: gray; font-size: 0.8rem; margin-bottom: -15px;'>тільки для адміністратора</p>", unsafe_allow_html=True)
    admin_password = st.text_input("Додати файл інструкції (PDF):", type="password", placeholder="Виберіть файл...")
    
    if admin_password == "30033003": 
        st.success("Доступ відкрито")
        if global_stats:
            df = pd.DataFrame(global_stats)
            valid_cols = ["Дата/Час", "Запит", "Файл", "Режим", "Час (сек)", "Статус"]
            df_display = df[[c for c in valid_cols if c in df.columns]]
            st.table(df_display[::-1])
            csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(label="📥 Скачати звіт (Excel)", data=csv, file_name="stats_pchu5.csv", mime="text/csv")
            if st.button("🗑️ Очистити історію"):
                global_stats.clear()
                st.rerun()

st.subheader("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

# --- 3. ЧИТАННЯ PDF ---
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

available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ PDF не знайдені.")
    st.stop()

# --- 4. МЕНЮ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла", "Розгорнута"], index=0, horizontal=True)

final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000]

# --- 5. ПОШУК ТА КНОПКИ ---
st.write("---")
query_text = st.text_input("Пошук", placeholder="Введіть ваше питання тут...", key="user_query", label_visibility="collapsed")

search_button = st.button("Пошук", type="primary", use_container_width=True)
clear_button = st.button("Очистити", type="secondary", on_click=clear_text, use_container_width=True)

# --- 6. ЛОГІКА ВІДПОВІДІ ---
if search_button and final_context:
    if not query_text.strip():
        st.warning("Введіть питання.")
    else:
        # Автоматичний розрахунок київського часу (UTC+2/UTC+3)
        now_utc = datetime.utcnow()
        # Спрощена логіка літнього часу (березень-жовтень)
        ukraine_offset = 3 if (3 <= now_utc.month <= 10) else 2
        current_time = (now_utc + timedelta(hours=ukraine_offset)).strftime("%d.%m %H:%M:%S")
        
        start_process = time.time()
        
        with st.spinner('ШІ аналізує документацію...'):
            try:
                style = "тези" if answer_mode == "Стисла" else "детально з пунктами правил"
                prompt = f"Контекст: {final_context}\n\nПитання: {query_text}\n\nІнструкція: {style}. Відповідай українською."
                
                if model:
                    response = model.generate_content(prompt)
                    process_time = int(time.time() - start_process)
                    
                    st.subheader("Відповідь:")
                    st.success(response.text)
                    
                    global_stats.append({
                        "Дата/Час": current_time,
                        "Запит": query_text,
                        "Файл": selected_option[:25],
                        "Режим": answer_mode,
                        "Час (сек)": process_time,
                        "Статус": "Успішно ✅"
                    })
                else:
                    st.error("Помилка підключення до ШІ. Перевірте ключі API.")
            except Exception as e:
                st.error(f"Помилка запиту. Спробуйте ще раз за хвилину.")
                global_stats.append({"Дата/Час": current_time, "Запит": query_text, "Статус": "Помилка", "Час (сек)": 0})
            
            if len(global_stats) > 500: global_stats.pop(0)

# --- 7. ПІДПИС РОЗРОБНИКА ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
