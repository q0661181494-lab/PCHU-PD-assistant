import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- КОНФІГУРАЦІЯ ТАБЛИЦІ ---
SPREADSHEET_ID = "1OINic0CgdHAXhegjbHgQdflbTL0DnpHJDj7EwA1N1Tw"

# Налаштування сторінки
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

# Спроба підключення до Google Sheets (якщо не вдасться, додаток не впаде)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    conn = None

# --- СТИЛІЗАЦІЯ ІНТЕРФЕЙСУ ---
st.markdown("""
    <style>
    .main-title { text-align: center; font-size: 26px; font-weight: bold; margin-top: -30px; margin-bottom: 30px; color: #1E1E1E; }
    
    /* Стиль для кнопок */
    .stButton > button { 
        width: 100% !important; 
        height: 50px !important; 
        border-radius: 12px !important; 
        font-weight: bold !important; 
        font-size: 18px !important; 
        margin-top: 10px !important;
    }
    
    /* Колір кнопки Пошук */
    button[kind="primary"] { background-color: #28a745 !important; color: white !important; border: none !important; }
    button[kind="primary"]:hover { background-color: #218838 !important; }
    
    /* Колір кнопки Очистити */
    button[kind="secondary"] { background-color: #6c757d !important; color: white !important; border: none !important; }
    button[kind="secondary"]:hover { background-color: #5a6268 !important; }

    /* Картка з відповіддю */
    .answer-card { 
        background-color: #f8f9fa; 
        padding: 20px; 
        border-radius: 15px; 
        border-left: 6px solid #28a745; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
        margin-top: 20px;
        color: #333;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- ДОПОМІЖНІ ФУНКЦІЇ ---
def reset_query():
    st.session_state["query_input"] = ""

def get_ai_answer(context_text, question, mode):
    # Список ключів для ротації
    available_keys = [k for k in ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"] if k in st.secrets]
    random.shuffle(available_keys)
    
    for key_name in available_keys:
        try:
            genai.configure(api_key=st.secrets[key_name])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            full_prompt = f"""
            Ти — технічний асистент ПЧУ-5. Використовуй наданий текст інструкції для відповіді.
            Формат відповіді: {mode}.
            Мова: Українська.
            
            Текст інструкції:
            {context_text[:12000]}
            
            Запитання: {question}
            """
            
            response = model.generate_content(full_prompt)
            return response.text, "gemini-1.5-flash", key_name
        except Exception:
            continue
    return None, None, None

# --- БІЧНА ПАНЕЛЬ (АДМІН) ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    admin_code = st.text_input("Введіть код доступу:", type="password")
    if admin_code == "3003":
        st.success("Доступ дозволено")
        if conn:
            try:
                st.write("Остання статистика:")
                data = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="Аркуш1")
                st.dataframe(data.dropna(how="all").tail(10))
            except:
                st.info("Таблиця ще порожня або недоступна")

# --- ОСНОВНИЙ ІНТЕРФЕЙС ---
pdf_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
selected_pdf = st.selectbox("Оберіть інструкцію:", pdf_files)

response_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (детально)"], horizontal=True)

user_input = st.text_input("Введіть запитання:", key="query_input", placeholder="Наприклад: Основні типи рейок")

# Кнопки дій
if st.button("🔍 Пошук", type="primary"):
    if user_input:
        with st.status("🔍 Шукаю відповідь в інструкції...", expanded=True) as status:
            try:
                # Зчитування PDF
                raw_text = ""
                with open(selected_pdf, "rb") as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    # Зчитуємо перші 20 сторінок для балансу швидкості та якості
                    pages_to_read = min(len(pdf_reader.pages), 20)
                    for i in range(pages_to_read):
                        raw_text += pdf_reader.pages[i].extract_text() + " "
                
                # Запит до ШІ
                ans, model_name, used_key = get_ai_answer(raw_text, user_input, response_mode)
                
                if ans:
                    status.update(label="✅ Відповідь сформована!", state="complete")
                    st.markdown(f'<div class="answer-card">{ans}</div>', unsafe_allow_html=True)
                    
                    # Запис у Google Таблицю (тихий режим)
                    if conn:
                        try:
                            # Час за Києвом (UTC+2)
                            timestamp = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
                            new_data = pd.DataFrame([{
                                "Час": timestamp, 
                                "Запит": user_input, 
                                "ШІ": model_name, 
                                "Ключ": used_key
                            }])
                            
                            existing_data = conn.read(spreadsheet=SPREADSHEET_ID, worksheet="Аркуш1")
                            updated_df = pd.concat([existing_data.dropna(how="all"), new_data], ignore_index=True)
                            conn.update(spreadsheet=SPREADSHEET_ID, worksheet="Аркуш1", data=updated_df)
                        except:
                            pass # Ігноруємо помилки запису, щоб не псувати досвід користувача
                else:
                    status.update(label="❌ Помилка: Ключі ШІ не працюють", state="error")
            except Exception as e:
                status.update(label=f"❌ Сталася помилка: {str(e)}", state="error")
    else:
        st.warning("Будь ласка, введіть запитання.")

st.button("🗑️ Очистити поле", type="secondary", on_click=reset_query)

# Футер
st.markdown("---")
st.caption("© 2026 ПЧУ-5 | Сергій ШИНКАРЕНКО")
