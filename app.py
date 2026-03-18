import streamlit as st
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, NotFound
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

# CSS для кнопок на всю ширину
st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; }
    div[data-testid="stButton"] button {
        width: 100% !important; 
        height: 55px !important; 
        margin-top: 12px !important;
        margin-bottom: 5px !important;
        font-size: 18px !important; 
        font-weight: bold !important; 
        border-radius: 12px !important;
        border: none !important;
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
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t: text += t + " "
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:750000] # Ліміт ~300 сторінок
    except Exception as e:
        return f"Помилка читання PDF: {e}"

# --- 3. СЕСІЯ ТА АДМІНКА ---
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

# --- 4. ПІДГОТОВКА ФАЙЛІВ ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ Покладіть PDF файли в папку з додатком.")
    st.stop()

st.write("---")
selected_file = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (пункти правил)"], horizontal=True)

final_context = get_cleaned_pdf_context(selected_file)

# --- 5. ПОШУК ---
st.write("---")
user_query = st.text_input("Пошук", placeholder="Введіть ваше питання...", key="user_query", label_visibility="collapsed")

search_button = st.button("🔍 Пошук", type="primary", use_container_width=True)
st.button("🗑️ Очистити поле", type="secondary", on_click=clear_text, use_container_width=True)

# --- 6. ЛОГІКА Gemini (ВИПРАВЛЕНО 404) ---
if search_button:
    if not user_query.strip():
        st.warning("Введіть запитання.")
    elif "Помилка читання" in final_context:
        st.error(final_context)
    else:
        now = datetime.utcnow() + timedelta(hours=(3 if (4 <= datetime.utcnow().month <= 10) else 2))
        current_time = now.strftime("%d.%m %H:%M:%S")
        
        success = False
        with st.spinner('ШІ аналізує інструкцію...'):
            keys = [k for k in ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"] if k in st.secrets]
            random.shuffle(keys)
            
            for key_id in keys:
                try:
                    genai.configure(api_key=st.secrets[key_id])
                    
                    # КЛЮЧОВЕ ВИПРАВЛЕННЯ: додано models/ перед назвою
                    model = genai.GenerativeModel(
                        model_name='models/gemini-1.5-flash',
                        system_instruction="Ти — технічний експерт залізниці. Відповідай суворо за текстом наданої інструкції українською мовою."
                    )
                    
                    prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nФормат відповіді: {answer_mode}."
                    
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
                
                except NotFound:
                    st.error(f"⚠️ Помилка 404: Модель не знайдена на ключі {key_id}. Перевірте налаштування API.")
                    break
                except ResourceExhausted:
                    continue # Пробуємо наступний ключ, якщо закінчились ліміти
                except Exception as e:
                    st.error(f"Помилка при використанні {key_id}: {str(e)}")
                    continue
            
            if not success and not any(st.session_state.get('error_shown', False) for k in keys):
                st.error("⚠️ На жаль, зараз ліміти запитів вичерпані для всіх ключів. Спробуйте через 1-2 хвилини.")

# --- 7. ПІДПИС ---
st.markdown(f"<br><hr><center><p style='color: gray;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
