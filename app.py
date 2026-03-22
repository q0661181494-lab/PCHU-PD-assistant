import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
from datetime import datetime, timedelta

# --- 1. ІНІЦІАЛІЗАЦІЯ СТАТИСТИКИ ---
if "stats_history" not in st.session_state:
    st.session_state.stats_history = []
if "last_processed_query" not in st.session_state:
    st.session_state.last_processed_query = ""

# --- 2. КОНФІГУРАЦІЯ СТОРІНКИ ТА CSS (ДОДАНО ЕКСПЕРТНИЙ СТИЛЬ) ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    .main-title {
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        margin-top: -40px; 
        margin-bottom: 25px;
        line-height: 1.2;
        color: #1E1E1E;
        display: block;
    }
    
    .stButton > button {
        width: 100% !important;
        height: 55px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }
    
    /* Стандартна картка (Зелена) */
    .answer-card {
        background-color: #ffffff;
        padding: 22px;
        border-radius: 15px;
        border-left: 6px solid #28a745;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: #1E1E1E;
        line-height: 1.6;
        margin-top: 20px;
    }

    /* Експертна картка (Синя) */
    .expert-card {
        background-color: #f0f7ff;
        padding: 22px;
        border-radius: 15px;
        border-left: 6px solid #007bff;
        box-shadow: 0 4px 20px rgba(0,123,255,0.15);
        color: #1E1E1E;
        line-height: 1.6;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. ДОПОМІЖНІ ФУНКЦІЇ ---
def clear_search_field():
    st.session_state["query_field"] = ""
    st.session_state["last_processed_query"] = ""

@st.cache_data
def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except: return ""

def get_relevant_context(query, full_text, top_k=35):
    chunks = [full_text[i:i+6000] for i in range(0, len(full_text), 5000)]
    if not query: return "\n".join(chunks[:5])
    query_words = query.lower().split()
    scored_chunks = []
    for chunk in chunks:
        score = sum(chunk.lower().count(word) for word in query_words)
        scored_chunks.append((score, chunk))
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return "\n---\n".join([c[1] for c in scored_chunks[:top_k]])

# --- 4. РОБОТА З ШІ (API) ---
def get_ai_response(prompt):
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    for name in key_names:
        if name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[name])
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text, 'gemini-1.5-flash', name
            except: continue 
    return None, None, None

# --- 5. БОКОВА ПАНЕЛЬ ---
with st.sidebar:
    st.header("🔐 Додати інструкцію (формат pdf, txt)")
    access_code = st.text_input("Введіть код доступу:", type="password")
    if access_code == "3003": 
        stats_file = "stats.csv"
        if os.path.exists(stats_file):
            df_stats = pd.read_csv(stats_file)
            st.dataframe(df_stats[::-1], use_container_width=True)
            if st.button("🗑️ Очистити статистику"):
                os.remove(stats_file)
                st.rerun()

# --- 6. ОСНОВНИЙ ІНТЕРФЕЙС (ОНОВЛЕНО: ДОДАНО ЕКСПЕРТ) ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.error("Файли не знайдені!")
    st.stop()

selected_option = st.selectbox("Оберіть інструкцію:", available_files)

# Додано третій варіант "Експерт"
answer_mode = st.radio("Тип відповіді:", ["Стисла", "Розгорнута", "Експерт"], horizontal=True)

full_document_text = extract_text_from_pdf(selected_option)

user_query = st.text_input("Пошук", placeholder="Введіть запитання...", key="query_field", label_visibility="collapsed")

col_left, col_right = st.columns(2)
with col_left:
    search_button = st.button("🔍 Пошук", type="primary")
with col_right:
    st.button("🗑️ Очистити", type="secondary", on_click=clear_search_field)

# --- 7. ЛОГІКА ВІДПОВІДІ (ОНОВЛЕНО: ГІБРИДНИЙ ПОШУК ТА КОЛЬОРИ) ---
enter_pressed = user_query != "" and st.session_state.last_processed_query != user_query

if search_button or enter_pressed:
    if not user_query:
        st.warning("Будь ласка, введіть запитання.")
    elif not full_document_text:
        st.error("Помилка файлу.")
    else:
        st.session_state.last_processed_query = user_query
        
        with st.status("Процес аналізу...", expanded=True) as status:
            st.write("📖 Пошук у документах...")
            context = get_relevant_context(user_query, full_document_text, top_k=40)
            
            st.write("🤖 Генерація відповіді...")
            
            # Логіка формування промпту залежно від режиму
            if answer_mode == "Експерт":
                # РЕЖИМ ЕКСПЕРТ: PDF + ЗОВНІШНІ ЗНАННЯ
                prompt = (
                    f"Ти — провідний технічний експерт ПЧУ-5. Твоє завдання: надати максимально глибоку відповідь.\n\n"
                    f"ВИКОРИСТОВУЙ:\n"
                    f"1. Дані з Контексту (як базу).\n"
                    f"2. Свої внутрішні знання, технічні стандарти та інформацію з інтернету для розширення відповіді.\n\n"
                    f"Контекст: {context}\n\n"
                    f"Питання: {user_query}\n\n"
                    f"Стиль: Максимально детальний експертний аналіз. Мова: українська."
                )
            else:
                # ЗВИЧАЙНІ РЕЖИМИ: СУВОРО PDF
                prompt = (
                    f"Ти — асистент ПЧУ-5. Відповідай ВИКЛЮЧНО за наданим Контекстом.\n\n"
                    f"ПРАВИЛА:\n"
                    f"1. Якщо в Контексті немає відповіді на '{user_query}', відповідай: 'На жаль, у вибраній інструкції інформація за вашим запитом відсутня'.\n"
                    f"2. Не використовуй зовнішні знання.\n\n"
                    f"Контекст: {context}\n\n"
                    f"Питання: {user_query}\n\n"
                    f"Стиль: {answer_mode}. Мова: українська."
                )
            
            answer, used_model, used_key = get_ai_response(prompt)
            
            if answer:
                status.update(label="✅ Готово!", state="complete", expanded=False)
                
                # Запис статистики
                now = datetime.now() + timedelta(hours=2)
                new_data = {"Дата": now.strftime("%d.%m.%Y"), "Час": now.strftime("%H:%M:%S"), 
                            "Інструкція": selected_option, "Тип": answer_mode, "Запит": user_query, 
                            "ШІ": used_model, "Ключ": used_key}
                pd.DataFrame([new_data]).to_csv("stats.csv", mode='a', header=not os.path.exists("stats.csv"), index=False, encoding='utf-8-sig')

        if answer:
            st.subheader("Результат:")
            # Вибір класу рамки: синій для Експерта, зелений для інших
            card_style = "expert-card" if answer_mode == "Експерт" else "answer-card"
            st.markdown(f'<div class="{card_style}">{answer}</div>', unsafe_allow_html=True)

# --- 8. ПІДПИС ---
st.markdown(f"<div style='text-align: center; color: gray; font-size: 10px; margin-top: 40px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
