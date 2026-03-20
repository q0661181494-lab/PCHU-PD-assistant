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

# --- 2. КОНФІГУРАЦІЯ СТОРІНКИ ТА ПРИМУСОВИЙ CSS ---
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
    
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        width: 100% !important;
    }

    .stButton {
        width: 100% !important;
    }

    div[data-testid="stButton"] button {
        width: 100% !important;
        display: block !important;
        height: 55px !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 18px !important;
        margin-top: 8px !important;
        margin-bottom: 8px !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
    }
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #6c757d !important;
        color: white !important;
    }

    div[data-testid="stButton"] button:active {
        transform: scale(0.98) !important;
    }

    .answer-card {
        background-color: #ffffff;
        padding: 22px;
        border-radius: 15px;
        border-left: 6px solid #28a745;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: #1E1E1E;
        line-height: 1.6;
        margin-top: 20px;
        font-size: 16px;
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
    chunks = [full_text[i:i+3000] for i in range(0, len(full_text), 2500)]
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
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return response.text, model_name, name
            except Exception:
                continue 
    return None, None, None

# --- 5. БОКОВА ПАНЕЛЬ (ОНОВЛЕНО ЗГІДНО ЗАПИТУ) ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    access_code = st.text_input("Введіть код доступу:", type="password")
    
    if access_code == "3003": 
        st.subheader("📊 Постійна статистика")
        
        stats_file = "stats.csv"
        
        if os.path.exists(stats_file):
            df_stats = pd.read_csv(stats_file)
            
            # Налаштування відображення таблиці
            # Використовуємо column_config для скорочення тексту в "Запиті"
            st.dataframe(
                df_stats[::-1], 
                use_container_width=True,
                column_config={
                    "Запит": st.column_config.TextColumn(
                        "Запит (натисніть щоб розгорнути)",
                        width="medium",
                        help="Клацніть на клітинку, щоб побачити повний текст питання"
                    ),
                    "Інструкція": st.column_config.TextColumn("Обрана інструкція"),
                    "Тип": st.column_config.TextColumn("Тип відповіді")
                }
            )
            
            # Додаткова можливість розгорнутого перегляду останнього запиту
            with st.expander("🔍 Детальний перегляд останнього питання"):
                last_q = df_stats.iloc[-1]["Запит"] if not df_stats.empty else "Немає даних"
                st.write(last_q)
            
            col1, col2 = st.columns(2)
            with col1:
                csv_download = df_stats.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Скачати CSV",
                    data=csv_download,
                    file_name=f"stats_pchu5_{datetime.now().strftime('%d_%m_%Y')}.csv",
                    mime="text/csv"
                )
            with col2:
                if st.button("🗑️ Очистити", type="secondary"):
                    os.remove(stats_file)
                    st.rerun()
        else:
            st.info("Історія запитів порожня")

# --- 6. ОСНОВНИЙ ІНТЕРФЕЙС ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.error("Файли не знайдені!")
    st.stop()

selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (детально)"], horizontal=True)

full_document_text = extract_text_from_pdf(selected_option)

user_query = st.text_input("Пошук", placeholder="Введіть ваше запитання...", key="query_field", label_visibility="collapsed")

search_button = st.button("🔍 Пошук", type="primary")
clear_button = st.button("🗑️ Очистити поле", type="secondary", on_click=clear_search_field)

# --- 7. ЛОГІКА ВІДПОВІДІ (ДОДАНО НОВІ КОЛОНКИ ПРИ ЗАПИСУ) ---
if search_button:
    if not user_query:
        st.warning("Будь ласка, введіть запитання.")
    elif not full_document_text:
        st.error("Помилка зчитування файлу.")
    else:
        with st.status("Обробка запиту...", expanded=True) as status:
            st.write("📖 Зчитую інструкцію...")
            st.write("🔍 Шукаю потрібний розділ у документації...")
            context = get_relevant_context(user_query, full_document_text)
            
            st.write("🤖 Формую відповідь...")
            style = "тези" if answer_mode == "Стисла (тези)" else "детально з пунктами правил"
            prompt = f"Контекст: {context}\n\nПитання: {user_query}\n\nСтиль: {style}. Українською."
            
            answer, used_model, used_key = get_ai_response(prompt)
            
            if answer:
                status.update(label="✅ Аналіз завершено!", state="complete", expanded=False)
                
                # --- ЗАПИС РОЗШИРЕНОЇ СТАТИСТИКИ ---
                now = datetime.now() + timedelta(hours=2)
                new_data = {
                    "Дата": now.strftime("%d.%m.%Y"),
                    "Час": now.strftime("%H:%M:%S"),
                    "Інструкція": selected_option,  # Нова колонка
                    "Тип": answer_mode,             # Нова колонка
                    "Запит": user_query,
                    "ШІ": used_model.replace("models/", ""),
                    "Ключ": used_key
                }
                
                df_entry = pd.DataFrame([new_data])
                stats_file = "stats.csv"
                if not os.path.isfile(stats_file):
                    df_entry.to_csv(stats_file, index=False, encoding='utf-8-sig')
                else:
                    df_entry.to_csv(stats_file, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                status.update(label="❌ Виникла помилка", state="error", expanded=True)

        if answer:
            st.subheader("Результат:")
            st.markdown(f'<div class="answer-card">{answer}</div>', unsafe_allow_html=True)

# --- 8. ПІДПИС ---
st.markdown(f"<div style='text-align: center; color: gray; font-size: 10px; margin-top: 40px;'>© {datetime.now().year} ПЧУ-5 Сергій ШИНКАРЕНКО</div>", unsafe_allow_html=True)
