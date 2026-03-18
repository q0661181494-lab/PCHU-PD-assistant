import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import time
from datetime import datetime, timedelta

# --- 0. ГЛОБАЛЬНА СТАТИСТИКА (СПІЛЬНА ДЛЯ ВСІХ ПРИСТРОЇВ) ---
@st.cache_resource
def get_global_stats():
    return []

global_stats = get_global_stats()

# Стан поля пошуку для функції очищення
if "user_query" not in st.session_state:
    st.session_state.user_query = ""

def clear_text():
    st.session_state.user_query = ""

# --- 1. ІНТЕРФЕЙС ТА ПРИМУСОВЕ ПРИХОВУВАННЯ ПАНЕЛІ ---
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
    
    /* Фіксація кнопок в один ряд на мобільних пристроях */
    [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 10px !important;
    }
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
            valid_cols = ["Дата/Час", "Запит", "Файл", "Ключ", "Час (сек)", "Статус"]
            df_display = df[[c for c in valid_cols if c in df.columns]]
            st.table(df_display[::-1]) 
            
            csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(label="📥 Скачати звіт (Excel)", data=csv, file_name=f"pchu5_stats_{datetime.now().strftime('%d_%m')}.csv", mime="text/csv")
            
            if st.button("🗑️ Очистити історію"):
                global_stats.clear()
                st.rerun()

st.subheader("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

# --- 2. ФУНКЦІЯ ЧИТАННЯ PDF ---
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

# --- 3. ЗБІР ФАЙЛІВ ---
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
user_query = st.text_input("Пошук", placeholder="Введіть ваше питання тут...", key="user_query", label_visibility="collapsed")

col1, col2 = st.columns(2)
with col1:
    search_button = st.button("🔍 Пошук", type="primary", use_container_width=True)
with col2:
    st.button("🗑️ Очистити", type="secondary", on_click=clear_text, use_container_width=True)

# --- 6. ЛОГІКА ВІДПОВІДІ (З ЛАНЦЮЖКОМ ПЕРЕБОРУ КЛЮЧІВ) ---
if (search_button) and final_context:
    if not user_query.strip():
        st.warning("Введіть питання.")
    else:
        # Корекція часу для України (Березень = +2, Квітень-Жовтень = +3)
        now_utc = datetime.utcnow()
        ukraine_offset = 3 if (4 <= now_utc.month <= 10) else 2
        current_date_time = (now_utc + timedelta(hours=ukraine_offset)).strftime("%d.%m %H:%M:%S")
        
        start_process = time.time()
        success = False
        tried_keys = [] # Список для збору назв спробованих ключів
        
        with st.spinner('ШІ аналізує документацію...'):
            # Список ключів для перебору
            key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
            random.shuffle(key_names) # Мішаємо для рівномірного навантаження
            
            for key_id in key_names:
                if key_id in st.secrets:
                    tried_keys.append(key_id) # Додаємо ключ до списку спроб
                    try:
                        # Конфігурація поточного ключа
                        genai.configure(api_key=st.secrets[key_id])
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        style = "тези" if answer_mode == "Стисла" else "детально з пунктами правил"
                        prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
                        
                        response = model.generate_content(prompt)
                        process_time = int(time.time() - start_process)
                        
                        # Успіх!
                        st.subheader("Відповідь:")
                        st.success(response.text)
                        
                        # Створюємо рядок-ланцюжок (наприклад: "KEY3, KEY1 ✅")
                        keys_chain = ", ".join(tried_keys) + " ✅"
                        
                        global_stats.append({
                            "Дата/Час": current_date_time,
                            "Запит": user_query,
                            "Файл": selected_option[:20],
                            "Ключ": keys_chain,
                            "Режим": answer_mode,
                            "Час (сек)": process_time,
                            "Статус": "Успішно"
                        })
                        success = True
                        break # Зупиняємо перебір
                        
                    except Exception:
                        # Якщо ключ не спрацював, просто йдемо до наступного
                        continue 
            
            if not success:
                st.error("⚠️ На жаль, всі безкоштовні ліміти запитів наразі вичерпані. Спробуйте через 1-2 хвилини.")
                # Фіксуємо повний ланцюжок невдач (наприклад: "KEY2, KEY4, KEY1, KEY5, KEY3 ❌")
                keys_chain = ", ".join(tried_keys) + " ❌"
                global_stats.append({
                    "Дата/Час": current_date_time, 
                    "Запит": user_query, 
                    "Ключ": keys_chain, 
                    "Статус": "ВСІ ЛІМІТИ ВИЧЕРПАНО",
                    "Час (сек)": 0
                })

# --- 7. ПІДПИС РОЗРОБНИКА ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
