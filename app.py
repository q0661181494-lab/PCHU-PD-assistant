import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime

# --- 0. ГЛОБАЛЬНА СТАТИСТИКА (СПІЛЬНА) ---
@st.cache_resource
def get_global_stats():
    # Повертає порожній список для збору ТІЛЬКИ потрібних даних
    return []

global_stats = get_global_stats()

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
            except: continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ТА СТИЛІЗАЦІЯ ---
st.set_page_config(
    page_title="Технічна бібліотека ст. Ворожба", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS для кольорових кнопок та фіксації ряду на мобільних
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #dc3545 !important;
        color: white !important;
        border: none !important;
    }
    [data-testid="column"] {
        width: 49% !important;
        flex: 1 1 45% !important;
        min-width: 45% !important;
    }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ Налаштування")
    st.markdown("<p style='color: gray; font-size: 0.8rem; margin-bottom: -15px;'>тільки для адміністратора</p>", unsafe_allow_html=True)
    admin_password = st.text_input("Додати файл інструкції (PDF):", type="password", placeholder="Виберіть файл...")
    
    if admin_password == "30033003": 
        st.success("Доступ відкритий")
        if global_stats:
            # Створюємо таблицю ТІЛЬКИ з потрібними колонками
            df = pd.DataFrame(global_stats)
            # Переконуємося, що старі колонки (місто/область) видалені, якщо вони раптом потрапили в кеш
            cols_to_keep = ["Дата/Час", "Пристрій", "Запит", "Файл", "Режим", "Час (сек)", "Статус"]
            df = df[[c for c in cols_to_keep if c in df.columns]]
            
            st.subheader("📊 Статистика")
            st.table(df[::-1])
            
            csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(label="📥 Скачати звіт (Excel)", data=csv, file_name=f"pchu5_stats_{datetime.now().strftime('%d_%m')}.csv", mime="text/csv")
            
            if st.button("🗑️ Очистити історію"):
                global_stats.clear()
                st.rerun()
        else:
            st.info("Запитів немає.")

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

# --- 4. ФАЙЛИ ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ PDF не знайдені.")
    st.stop()

# --- 5. МЕНЮ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла", "Розгорнута"], index=0, horizontal=True)

# --- 6. ПІДГОТОВКА ТЕКСТУ ---
final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000]

# --- 7. ПОШУК ТА КНОПКИ ---
st.write("---")
query_text = st.text_input("Пошук", placeholder="Введіть питання...", key="user_query", label_visibility="collapsed")

col1, col2 = st.columns(2)
with col1:
    search_button = st.button("🔍 Пошук", type="primary", use_container_width=True)
with col2:
    st.button("🗑️ Очистити", type="secondary", on_click=clear_text, use_container_width=True)

# --- 8. ЛОГІКА ВІДПОВІДІ ---
if (search_button) and final_context:
    if not query_text.strip():
        st.warning("Введіть питання.")
    else:
        headers = st.context.headers
        ua = headers.get("User-Agent", "")
        os_info = "Комп'ютер"
        if "Android" in ua: os_info = "Android"
        elif "iPhone" in ua or "iPad" in ua: os_info = "iPhone/iPad"
        
        current_time = datetime.now().strftime("%d.%m %H:%M:%S")
        start_process = time.time()
        
        with st.spinner('ШІ аналізує...'):
            try:
                style = "тези" if answer_mode == "Стисла" else "детально"
                prompt = f"Контекст: {final_context}\n\nПитання: {query_text}\n\nІнструкція: {style}. Відповідай українською."
                
                response = model.generate_content(prompt)
                process_time = round(time.time() - start_process, 2)
                
                st.subheader("Відповідь:")
                st.success(response.text)
                
                # ЗАПИС БЕЗ МІСТА ТА ОБЛАСТІ
                global_stats.append({
                    "Дата/Час": current_time,
                    "Пристрій": os_info,
                    "Запит": query_text,
                    "Файл": selected_option[:25],
                    "Режим": answer_mode,
                    "Час (сек)": process_time,
                    "Статус": "Успішно ✅"
                })
                
            except Exception as e:
                st.error("Помилка ШІ.")
                global_stats.append({
                    "Дата/Час": current_time, "Пристрій": os_info, "Запит": query_text, 
                    "Файл": selected_option[:25], "Час (сек)": 0, "Статус": f"Помилка"
                })
            
            if len(global_stats) > 500: global_stats.pop(0)

# --- 9. ПІДПИС ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
