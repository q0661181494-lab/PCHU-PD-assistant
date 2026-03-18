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

# --- 2. КОНФІГУРАЦІЯ СТОРІНКИ ТА ПОСИЛЕНИЙ CSS ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
    <style>
    /* Головний заголовок */
    .main-title {
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        margin-top: -40px; 
        margin-bottom: 25px;
        line-height: 1.2;
        color: #1E1E1E;
    }
    
    /* Кнопки на всю ширину */
    div.stButton {
        width: 100% !important;
    }
    div.stButton > button {
        width: 100% !important;
        display: block !important;
        height: 55px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        margin-top: 8px !important;
        border: none !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Кольори кнопок */
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
    }
    div.stButton > button[kind="secondary"] {
        background-color: #6c757d !important;
        color: white !important;
    }

    /* Картка відповіді */
    .answer-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        border-left: 6px solid #28a745;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
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

def get_relevant_context(query, full_text, top_k=15):
    # Розбиття на частини (RAG)
    chunks = [full_text[i:i+3000] for i in range(0, len(full_text), 2500)]
    if not query: return "\n".join(chunks[:5])
    
    query_words = query.lower().split()
    scored_chunks = []
    for chunk in chunks:
        score = sum(chunk.lower().count(word) for word in query_words)
        scored_chunks.append((score, chunk))
    
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return "\n---\n".join([c[1] for c in scored_chunks[:top_k]])

# --- 4. РОБОТА З ШІ ---
def get_ai_response(prompt):
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    for name in key_names:
        if name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[name])
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text, model_name, name
            except Exception:
                continue 
    return None, None, None

# --- 5. БОКОВА ПАНЕЛЬ ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    access_code = st.text_input("Введіть код доступу:", type="password")
    if access_code == "3003": 
        st.subheader("Історія поточної сесії")
        if st.session_state.stats_history:
            df = pd.DataFrame(st.session_state.stats_history)
            st.dataframe(df[::-1], use_container_width=True)
        else:
            st.info("Запитів ще не було")

# --- 6. ОСНОВНИЙ ІНТЕРФЕЙС ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.error("Файли не знайдені!")
    st.stop()

selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (детально)"], horizontal=True)

# Зчитування (завдяки кешу працює миттєво при повторі)
full_document_text = extract_text_from_pdf(selected_option)

user_query = st.text_input("Пошук", placeholder="Введіть питання або номер білета...", key="query_field", label_visibility="collapsed")

search_button = st.button("🔍 Пошук", type="primary")
st.button("🗑️ Очистити поле", type="secondary", on_click=clear_search_field)

# --- 7. ЛОГІКА ВІДПОВІДІ (З НОВИМ STATUS) ---
if search_button:
    if not user_query:
        st.warning("Будь ласка, введіть запитання.")
    elif not full_document_text:
        st.error("Помилка: не вдалося отримати текст із файлу.")
    else:
        # ВИКОРИСТАННЯ ST.STATUS (Як ти просив)
        with st.status("Опрацювання запиту...", expanded=True) as status:
            st.write("📖 Зчитую інструкцію...")
            # Текст уже в пам'яті завдяки кешу
            
            st.write("🔍 Шукаю потрібний розділ у документації...")
            context = get_relevant_context(user_query, full_document_text)
            
            st.write("🤖 Формую тези та відповідь...")
            style = "тези" if answer_mode == "Стисла (тези)" else "детально з пунктами правил"
            prompt = f"Контекст: {context}\n\nПитання: {user_query}\n\nСтиль: {style}. Українською."
            
            answer, used_model, used_key = get_ai_response(prompt)
            
            if answer:
                status.update(label="✅ Відповідь сформована!", state="complete", expanded=False)
            else:
                status.update(label="❌ Помилка аналізу", state="error", expanded=True)

        if answer:
            st.subheader("Результат пошуку:")
            # Візуальна картка для відповіді
            st.markdown(f"""
                <div class="answer-card">
                    {answer}
                </div>
            """, unsafe_allow_html=True)
            
            # Статистика
            now = (datetime.now() + timedelta(hours=2)).strftime("%H:%M:%S")
            st.session_state.stats_history.append({
                "Час": now, 
                "Запит": user_query, 
                "ШІ": used_model.replace("models/", ""), 
                "Ключ": used_key
            })
        else:
            st.error("Не вдалося отримати відповідь від сервера. Спробуйте ще раз.")

# --- 8. ПІДПИС ---
st.markdown(f"<div style='text-align: center; color: gray; font-size: 10px; margin-top: 40px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
