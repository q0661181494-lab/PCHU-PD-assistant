import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 0. СПІЛЬНА ПАМ'ЯТЬ ДЛЯ СТАТИСТИКИ ---
@st.cache_resource
def get_global_stats():
    return []

global_stats = get_global_stats()

if "user_query" not in st.session_state:
    st.session_state.user_query = ""

def clear_text():
    st.session_state.user_query = ""

# --- 1. ПІДКЛЮЧЕННЯ ШІ (З ПЕРЕВІРКОЮ КЛЮЧА ТА МОДЕЛІ) ---
def get_working_model_info():
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                
                # Шукаємо доступні моделі
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_id = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                
                model_obj = genai.GenerativeModel(model_id)
                # Повертаємо об'єкт моделі, назву ключа та коротку назву моделі
                return model_obj, name, model_id.replace('models/', '')
            except Exception:
                continue 
    return None, None, None

# Отримуємо дані про підключення при старті
model, active_key_name, active_model_name = get_working_model_info()

# --- 2. ІНТЕРФЕЙС ТА ПРИХОВУВАННЯ ПАНЕЛІ ---
st.set_page_config(
    page_title="Технічна бібліотека ст. Ворожба", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS для великих кнопок
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
            st.subheader("📊 Детальна статистика")
            # Виводимо таблицю (нові колонки з'являться автоматично)
            st.table(df[::-1]) 
            
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

# --- 5. МЕНЮ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла", "Розгорнута"], index=0, horizontal=True)

final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000]

# --- 6. ПОШУК ТА КНОПКИ ---
st.write("---")
query_text = st.text_input("Пошук", placeholder="Введіть ваше питання тут...", key="user_query", label_visibility="collapsed")

search_button = st.button("Пошук", type="primary", use_container_width=True)
clear_button = st.button("Очистити", type="secondary", on_click=clear_text, use_container_width=True)

# --- 7. ЛОГІКА ВІДПОВІДІ (З АВТОМАТИЧНИМ ПЕРЕБОРОМ КЛЮЧІВ ПРИ ПОМИЛЦІ) ---
if (search_button) and final_context:
    if not user_query.strip():
        st.warning("Введіть питання.")
    else:
        # Час
        now_utc = datetime.utcnow()
        ukraine_offset = 3 if (4 <= now_utc.month <= 10) else 2
        current_time = (now_utc + timedelta(hours=ukraine_offset)).strftime("%d.%m %H:%M:%S")
        
        start_process = time.time()
        success = False
        
        with st.spinner('ШІ аналізує документацію...'):
            # Складаємо список всіх доступних ключів у випадковому порядку
            keys_to_try = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
            random.shuffle(keys_to_try)
            
            for key_name in keys_to_try:
                if key_name in st.secrets:
                    try:
                        # Спроба підключити конкретний ключ
                        genai.configure(api_key=st.secrets[key_name])
                        temp_model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        style = "тези" if answer_mode == "Стисла" else "детально з пунктами правил"
                        prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
                        
                        response = temp_model.generate_content(prompt)
                        process_time = int(time.time() - start_process)
                        
                        st.subheader("Відповідь:")
                        st.success(response.text)
                        
                        # Запис у статистику
                        global_stats.append({
                            "Дата/Час": current_time,
                            "Запит": user_query,
                            "Файл": selected_option[:25],
                            "Ключ": key_name,
                            "Статус": "Успішно ✅",
                            "Час (сек)": process_time
                        })
                        success = True
                        break # ВИХОДИМО З ЦИКЛУ, БО ВІДПОВІДЬ ОТРИМАНО
                        
                    except Exception as e:
                        # Якщо ключ не спрацював, просто йдемо до наступного в списку
                        continue 
            
            if not success:
                st.error("⚠️ Всі безкоштовні ключі наразі перевантажені. Будь ласка, зачекайте 1 хвилину.")
                global_stats.append({
                    "Дата/Час": current_time, "Запит": user_query, "Статус": "ВСІ ЛІМІТИ ❌"
                })

# --- 8. ПІДПИС РОЗРОБНИКА ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
