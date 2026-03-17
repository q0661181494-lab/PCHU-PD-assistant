import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime

# --- 0. ГЛОБАЛЬНА СТАТИСТИКА ТА СТАН ПОЛЯ ---
@st.cache_resource
def get_global_stats():
    return []

global_stats = get_global_stats()

# Ініціалізація стану текстового поля
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
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models
                return genai.GenerativeModel(model_name)
            except: continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ---
st.set_page_config(
    page_title="Технічна бібліотека ст. Ворожба", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

with st.sidebar:
    st.title("⚙️ Налаштування")
    st.markdown("<p style='color: gray; font-size: 0.8rem; margin-bottom: -15px;'>тільки для адміністратора</p>", unsafe_allow_html=True)
    admin_password = st.text_input("Додати файл інструкції (PDF):", type="password", placeholder="Виберіть файл...")
    
    if admin_password == "30033003": 
        st.success("Доступ до аналітики відкрито")
        if global_stats:
            df = pd.DataFrame(global_stats)
            st.subheader("📊 Статистика запитів")
            st.table(df[::-1])
            csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(label="📥 Скачати звіт (Excel)", data=csv, file_name=f"pchu5_stats_{datetime.now().strftime('%d_%m_%H%M')}.csv", mime="text/csv")
            if st.button("🗑️ Очистити історію"):
                global_stats.clear()
                st.rerun()
        else:
            st.info("Запитів поки не зафіксовано.")

st.subheader("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

# --- 3. ФУНКЦІЯ ЧИТАННЯ PDF ---
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

# --- 4. ЗБІР ФАЙЛІВ ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ Файли .pdf не знайдені.")
    st.stop()

# --- 5. МЕНЮ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла (головні тези)", "Розгорнута (детально)"], index=0, horizontal=True)

# --- 6. ПІДГОТОВКА ТЕКСТУ ---
final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000]

# --- 7. ПОШУК ТА ОЧИЩЕННЯ ---
st.write("---")
# Поле введення, прив'язане до session_state
query_text = st.text_input("Пошук", placeholder="Напишіть ваше питання або Білет N...", key="user_query", label_visibility="collapsed")

col1, col2, _ = st.columns([0.2, 0.2, 0.6])
with col1:
    search_button = st.button("🔍 Пошук", type="primary")
with col2:
    st.button("🗑️ Очистити", on_click=clear_text)

# --- 8. ЛОГІКА ВІДПОВІДІ ---
if (search_button) and final_context:
    if not query_text.strip():
        st.warning("Введіть питання.")
    else:
        headers = st.context.headers
        ua = headers.get("User-Agent", "Unknown Device")
        os_info = "Комп'ютер"
        if "Android" in ua: os_info = "Android"
        elif "iPhone" in ua or "iPad" in ua: os_info = "iPhone/iPad"
        
        current_time = datetime.now().strftime("%d.%m %H:%M:%S")
        start_process = time.time()
        
        with st.spinner('ШІ аналізує документацію...'):
            try:
                style = "тези" if answer_mode == "Стисла (головні тези)" else "детально з пунктами правил"
                prompt = f"Контекст: {final_context}\n\nПитання: {query_text}\n\nІнструкція: {style}. Відповідай українською."
                
                response = model.generate_content(prompt)
                process_time = round(time.time() - start_process, 2)
                
                st.subheader("Відповідь:")
                st.success(response.text)
                
                global_stats.append({
                    "Дата/Час": current_time,
                    "Пристрій": os_info,
                    "Запит": query_text,
                    "Файл": selected_option[:25],
                    "Режим": "Стисла" if answer_mode == "Стисла (головні тези)" else "Розгорнута",
                    "Час (сек)": process_time,
                    "Статус": "Успішно ✅"
                })
                
            except Exception as e:
                st.error(f"Помилка ШІ. Спробуйте ще раз.")
                global_stats.append({
                    "Дата/Час": current_time, "Пристрій": os_info, "Запит": query_text, 
                    "Файл": selected_option[:25], "Час (сек)": 0, "Статус": f"Помилка: {str(e)[:40]}"
                })
            
            if len(global_stats) > 500: global_stats.pop(0)

# --- 9. ПІДПИС РОЗРОБНИКА ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
