import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import pickle
from datetime import datetime, timedelta
from filelock import FileLock

# --- 1. ІНІЦІАЛІЗАЦІЯ СТАТИСТИКИ ---
if "stats_history" not in st.session_state:
    st.session_state.stats_history = []
if "last_processed_query" not in st.session_state:
    st.session_state.last_processed_query = ""

# --- 2. КОНФІГУРАЦІЯ СТОРІНКИ ТА CSS ---
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
}

.stButton button {
    width: 100% !important;
    height: 55px !important;
    border-radius: 12px !important;
    font-weight: bold !important;
    font-size: 18px !important;
}

.answer-card {
    background-color: #ffffff;
    padding: 22px;
    border-radius: 15px;
    border-left: 6px solid #28a745;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. PDF З КЕШЕМ ---
@st.cache_data(show_spinner=False)
def extract_text_from_pdf(file_path):
    cache_file = file_path + ".pkl"

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except:
            pass

    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"

        with open(cache_file, "wb") as f:
            pickle.dump(text, f)

        return text

    except Exception as e:
        print("PDF ERROR:", e)
        return ""

# --- 4. CHUNKING З КЕШЕМ ---
def load_or_create_chunks(full_text, file_name):
    cache_file = file_name + "_chunks.pkl"

    if os.path.exists(cache_file):
        try:
            return pickle.load(open(cache_file, "rb"))
        except:
            pass

    paragraphs = full_text.split("\n\n")

    chunks = []
    current = ""

    for p in paragraphs:
        if len(current) + len(p) < 5000:
            current += p + "\n"
        else:
            chunks.append(current)
            current = p

    if current:
        chunks.append(current)

    pickle.dump(chunks, open(cache_file, "wb"))
    return chunks

def get_relevant_context(query, full_text, file_name, top_k=7):
    chunks = load_or_create_chunks(full_text, file_name)

    if not query:
        return "\n---\n".join(chunks[:5])

    query_words = query.lower().split()
    scored_chunks = []

    for chunk in chunks:
        score = sum(chunk.lower().count(word) for word in query_words)
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    return "\n---\n".join([c[1] for c in scored_chunks[:top_k]])

# --- 5. AI ---
@st.cache_resource
def get_available_models():
    try:
        return [
            m.name for m in genai.list_models()
            if 'generateContent' in m.supported_generation_methods
        ]
    except Exception as e:
        print("MODEL ERROR:", e)
        return []

def get_ai_response(prompt):
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)

    available_models = get_available_models()

    for name in key_names:
        if name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[name])

                model_name = (
                    'models/gemini-1.5-flash'
                    if 'models/gemini-1.5-flash' in available_models
                    else available_models[0] if available_models else None
                )

                if not model_name:
                    continue

                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)

                if response and hasattr(response, "text"):
                    return response.text, model_name, name

            except Exception as e:
                print(f"AI ERROR ({name}):", e)
                continue

    return None, None, None

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    access_code = st.text_input("Введіть код доступу:", type="password")

    if access_code == "3003":
        stats_file = "stats.csv"

        if os.path.exists(stats_file):
            df_stats = pd.read_csv(stats_file)

            st.dataframe(df_stats[::-1], use_container_width=True)

            if st.button("🗑️ Очистити"):
                os.remove(stats_file)
                st.rerun()
        else:
            st.info("Історія порожня")

# --- 7. UI ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])

if not available_files:
    st.error("Файли не знайдені!")
    st.stop()

selected_option = st.selectbox("Оберіть інструкцію:", available_files)

answer_mode = st.radio(
    "Тип відповіді:",
    ["Стисла (тези)", "Розгорнута (детально)"],
    horizontal=True
)

full_document_text = extract_text_from_pdf(selected_option)

user_query = st.text_input(
    "Пошук",
    key="query_field",
    placeholder="Введіть запит..."
)

search_button = st.button("🔍 Пошук")

# --- 8. ЛОГІКА ---
enter_pressed = user_query != "" and st.session_state.last_processed_query != user_query

if search_button or enter_pressed:
    if not user_query:
        st.warning("Введіть запит")
    elif not full_document_text:
        st.error("Помилка PDF")
    else:
        st.session_state.last_processed_query = user_query

        with st.status("Обробка..."):

            context = get_relevant_context(
                user_query,
                full_document_text,
                selected_option,
                top_k=7
            )

            style = "тези" if "Стисла" in answer_mode else "детально"

            prompt = f"""
Ти технічний експерт.
Використовуй тільки контекст.
Якщо немає інформації — скажи "Немає інформації в документі".

Контекст:
{context}

Питання:
{user_query}

Стиль: {style}
Мова: українська
"""

            answer, used_model, used_key = get_ai_response(prompt)

            if answer:
                st.success("Готово")

                now = datetime.now() + timedelta(hours=2)

                df_entry = pd.DataFrame([{
                    "Дата": now.strftime("%d.%m.%Y"),
                    "Час": now.strftime("%H:%M:%S"),
                    "Інструкція": selected_option,
                    "Тип": answer_mode,
                    "Запит": user_query,
                    "ШІ": used_model,
                    "Ключ": used_key
                }])

                lock = FileLock("stats.lock")

                with lock:
                    if not os.path.isfile("stats.csv"):
                        df_entry.to_csv("stats.csv", index=False, encoding='utf-8-sig')
                    else:
                        df_entry.to_csv("stats.csv", mode='a', header=False, index=False, encoding='utf-8-sig')

            else:
                st.error("Помилка ШІ")

        if answer:
            st.markdown(f"<div class='answer-card'>{answer}</div>", unsafe_allow_html=True)

# --- 9. FOOTER ---
st.markdown(f"<div style='text-align:center;font-size:10px;'>© {datetime.now().year}</div>", unsafe_allow_html=True)
