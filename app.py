import streamlit as st
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import PyPDF2
import os
import random
import pandas as pd
import time
import re
from datetime import datetime, timedelta

# --- 1. КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(
    page_title="Технічна бібліотека ст. Ворожба", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ПОСИЛЕНИЙ CSS
st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; }
    div[data-testid="stButton"] button {
        width: 100% !important; 
        height: 55px !important; 
        margin-top: 10px !important;
        font-size: 18px !important; 
        font-weight: bold !important; 
        border-radius: 10px !important;
    }
    div[data-testid="stButton"] button[kind="primary"] { background-color: #28a745 !important; color: white !important; }
    div[data-testid="stButton"] button[kind="secondary"] { background-color: #6c757d !important; color: white !important; }
    .main-title {
        text-align: center;
        font-size: 26px;
        font-weight: bold;
        color: #1E1E1E;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 2. ГЛОБАЛЬНА СТАТИСТИКА ТА КЕШУВАННЯ ---
@st.cache_resource
def get_global_stats():
    return []

global_stats = get_global_stats()

@st.cache_data(show_spinner="Обробка інструкції... Це займе трохи часу для великих файлів.")
def get_cleaned_pdf_context(file_path):
    """Зчитує весь текст, очищує його від зайвих пробілів та кешує."""
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + " "
        
        # Оптимізація: видаляємо подвійні пробіли та зайві переноси рядків (економія токенів)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ліміт 750,000 символів (~300 сторінок), щоб ШІ точно все прочитав
        return text[:750000]
    except Exception as e:
        return f"Помилка читання PDF: {e}"

# --- 3. АДМІН-ПАНЕЛЬ (SIDEBAR) ---
if "user_query" not in st.session_state:
    st.session_state.user_query = ""

def clear_text():
    st.session_state.user_query = ""

with st.sidebar:
    st.markdown("### ⚙️ Адмін-панель")
    admin_password = st.text_input("Пароль:", type="password")
    if admin_password == "30033003":
        if global_stats:
            st.dataframe(pd.DataFrame(global_stats)[::-1], use_container_width=True)
            if st.button("🗑️ Очистити історію"):
                global_stats.clear()
                st.rerun()
        else:
            st.info("Історія порожня.")

# --- 4. ВИБІР ФАЙЛІВ ТА ПІДГОТОВКА КОНТЕКСТУ ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ Покладіть PDF файли в папку з додатком.")
    st.stop()

st.write("---")
selected_file = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (пункти правил)"], horizontal=True)

# Отримуємо текст (кешовано)
final_context = get_cleaned_pdf_context(selected_file)

# --- 5. ПОШУК ---
st.write("---")
user_query = st.text_input("Пошук", placeholder="Наприклад: Які терміни огляду колії?", key="user_query", label_visibility="collapsed")

col1, col2 = st.columns(2)
with col1:
    search_button = st.button("🔍 Пошук", type="primary")
with col2:
    st.button("🗑️ Очистити", type="secondary", on_click=clear_text)

# --- 6. ЛОГІКА Gemini ---
if search_button:
    if not user_query.strip():
        st.warning("Введіть запитання.")
    elif "Помилка читання" in final_context:
        st.error(final_context)
    else:
        now = datetime.utcnow() + timedelta(hours=(3 if (4 <= datetime.utcnow().month <= 10) else 2))
        current_time = now.strftime("%d.%m %H:%M:%S")
        
        success = False
        with st.spinner('Аналізую всю інструкцію... зачекайте...'):
            keys = [k for k in ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"] if k in st.secrets]
            random.shuffle(keys)
            
            for key_id in keys:
                try:
                    genai.configure(api_key=st.secrets[key_id])
                    # Використовуємо системну інструкцію для кращої точності
                    model = genai.GenerativeModel(
                        model_name='gemini-1.5-flash',
                        system_instruction="Ти — технічний експерт ПЧУ-5. Відповідай суворо за наданим текстом інструкції. Якщо інформації немає в тексті, так і скажи."
                    )
                    
                    prompt = f"Контекст (Інструкція): {final_context}\n\nПитання: {user_query}\n\nФормат відповіді: {answer_mode}. Мова: українська."
                    
                    response = model.generate_content(prompt)
                    
                    st.subheader("Результат пошуку:")
                    st.success(response.text)
                    
                    global_stats.append({
                        "Час": current_time,
                        "Файл": selected_file,
                        "Запит": user_query,
                        "Ключ": key_id
                    })
                    success = True
                    break
                
                except ResourceExhausted:
                    continue # Пробуємо наступний ключ
                except Exception as e:
                    st.error(f"Помилка: {e}")
                    break
            
            if not success:
                st.error("⚠️ Ліміти запитів вичерпані. Спробуйте через хвилину.")

# --- 7. ПІДПИС ---
st.markdown(f"<br><hr><center><p style='color: gray;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
