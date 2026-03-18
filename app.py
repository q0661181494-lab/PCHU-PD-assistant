import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 0. СПІЛЬНА ПАМ'ЯТЬ ДЛЯ СТАТИСТИКИ (ГЛОБАЛЬНА) ---
@st.cache_resource
def get_global_stats():
    return []

global_stats = get_global_stats()

# Стан поля пошуку для функції очищення
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
            except Exception:
                continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ТА СТИЛІЗАЦІЯ ---
st.set_page_config(
    page_title="Технічна бібліотека ст. Ворожба", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Посилений CSS для кнопок на всю ширину та оформлення
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
        st.success("Доступ до аналітики відкрито")
        if global_stats:
            df = pd.DataFrame(global_stats)
            st.subheader("📊 Останні запити")
            valid_cols = ["Дата/Час", "Запит", "Файл", "Режим", "Час (сек)", "Статус"]
            df_display = df[[c for c in valid_cols if c in df.columns]]
            st.table(df_display[::-1]) 
            
            csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(label="📥 Скачати звіт (Excel)", data=csv, file_name=f"pchu5_stats_{datetime.now().strftime('%d_%m')}.csv", mime="text/csv")
            
            if st.button("🗑️ Очистити історію"):
                global_stats.clear()
                st.rerun()
        else:
            st.info("Запитів поки немає.")

st.subheader("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

if not model:
    st.error("❌ Не вдалося підключитися до ШІ. Перевірте ключі в Secrets.")
    st.stop()

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
    st.warning("⚠️ PDF не знайдені.")
    st.stop()

# --- 5. НАЛАШТУВАННЯ ПОШУКУ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла", "Розгорнута"], index=0, horizontal=True)

# --- 6. ПІДГОТОВКА ТЕКСТУ ---
final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000]

# --- 7. ПОШУК ТА КНОПКИ ---
st.write("---")
user_query = st.text_input("Пошук", placeholder="Введіть ваше питання тут...", key="user_query", label_visibility="collapsed")

search_button = st.button("Пошук", type="primary", use_container_width=True)
clear_button = st.button("Очистити", type="secondary", on_click=clear_text, use_container_width=True)

# --- 8. ЛОГІКА ВІДПОВІДІ ТА ЗБІР СТАТИСТИКИ ---
if (search_button) and final_context:
    if not user_query.strip():
        st.warning("Введіть питання.")
    else:
        # ВИПРАВЛЕНО: Корекція часу для України
        now_utc = datetime.utcnow()
        # Квітень - Жовтень = +3 (літо), Березень та інше = +2 (зима)
        ukraine_offset = 3 if (4 <= now_utc.month <= 10) else 2
        current_time = (now_utc + timedelta(hours=ukraine_offset)).strftime("%d.%m %H:%M:%S")
        
        start_process = time.time()
        
        with st.spinner('ШІ аналізує документацію...'):
            try:
                style = "тези" if answer_mode == "Стисла" else "детально з пунктами правил"
                prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
                
                response = model.generate_content(prompt)
                process_time = int(time.time() - start_process)
                
                st.subheader("Відповідь:")
                st.success(response.text)
                
                global_stats.append({
                    "Дата/Час": current_time,
                    "Запит": user_query,
                    "Файл": selected_option[:25],
                    "Режим": answer_mode,
                    "Час (сек)": process_time,
                    "Статус": "Успішно ✅"
                })
                
                if len(global_stats) > 500: global_stats.pop(0)
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    st.error("⚠️ Досягнуто ліміт безкоштовних запитів до ШІ. Будь ласка, зачекайте 1 хвилину та спробуйте ще раз.")
                    status_log = "ЛІМІТ ВИЧЕРПАНО ❌"
                else:
                    st.error("Виникла технічна помилка. Спробуйте ще раз пізніше.")
                    status_log = f"ПОМИЛКА: {error_msg[:30]}"
                
                global_stats.append({
                    "Дата/Час": current_time, 
                    "Запит": user_query, 
                    "Файл": selected_option[:25],
                    "Режим": answer_mode,
                    "Статус": status_log,
                    "Час (сек)": 0
                })

# --- 9. ПІДПИС РОЗРОБНИКА ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
