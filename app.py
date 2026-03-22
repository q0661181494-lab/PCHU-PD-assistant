import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import pickle
from datetime import datetime, timedelta

# --- 1. SESSION ---
if "last_processed_query" not in st.session_state:
    st.session_state.last_processed_query = ""

# --- 2. UI ---
st.set_page_config(page_title="Бібліотека ПЧУ-5", layout="centered")

st.markdown("""
<style>
.main-title {
    text-align: center;
    font-size: 24px;
    font-weight: bold;
    margin-top: -40px;
    margin-bottom: 25px;
}

.stButton button {
    width: 100% !important;
    height: 55px !important;
    border-radius: 12px !important;
    font-weight: bold !important;
}

.answer-card {
    background-color: #fff;
    padding: 20px;
    border-left: 6px solid #28a745;
    border-radius: 10px;
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>📚 РОЗУМНА ТЕХНІЧНА<br>БІБЛІОТЕКА ПЧУ-5</div>", unsafe_allow_html=True)

# --- 3. PDF CACHE ---
@st.cache_data(show_spinner=False)
def extract_text_from_pdf(file_path):
    cache_file = file_path + ".pkl"

    if os.path.exists(cache_file):
        try:
            return pickle.load(open(cache_file, "rb"))
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

        pickle.dump(text, open(cache_file, "wb"))
        return text

    except Exception as e:
        st.error(f"PDF ERROR: {e}")
        return ""

# --- 4. CHUNKS ---
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

# --- 5. AI (СТАБІЛЬНИЙ) ---
def get_ai_response(prompt):
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]

    for name in key_names:
        if name in st.secrets:
            try:
                genai.configure(api_key=st.secrets[name])

                model = genai.GenerativeModel("models/gemini-1.5-flash")
                response = model.generate_content(prompt)

                if response and hasattr(response, "text"):
                    return response.text, "gemini-1.5-flash", name

            except Exception as e:
                st.error(f"❌ {name}: {e}")
                continue

    st.error("❌ Жоден API ключ не працює")
    return None, None, None

# --- 6. SIDEBAR ---
with st.sidebar:
    st.header("🔐 Адмін-панель")
    access_code = st.text_input("Код:", type="password")

    if access_code == "3003":
        if os.path.exists("stats.csv"):
            df = pd.read_csv("stats.csv")
            st.dataframe(df[::-1])
        else:
            st.info("Немає даних")

# --- 7. FILES ---
files = [f for f in os.listdir(".") if f.endswith(".pdf")]

if not files:
    st.error("PDF не знайдені")
    st.stop()

selected = st.selectbox("Оберіть інструкцію:", sorted(files))

mode = st.radio("Тип відповіді:", ["Стисла (тези)", "Розгорнута (детально)"], horizontal=True)

text = extract_text_from_pdf(selected)

query = st.text_input("Пошук", key="query_field")

btn = st.button("🔍 Пошук")

enter = query != "" and st.session_state.last_processed_query != query

# --- 8. LOGIC ---
if btn or enter:
    if not query:
        st.warning("Введіть запит")
    elif not text:
        st.error("PDF порожній")
    else:
        st.session_state.last_processed_query = query

        with st.status("Обробка..."):

            context = get_relevant_context(query, text, selected, top_k=7)

            style = "тези" if "Стисла" in mode else "детально"

            prompt = f"""
Ти технічний експерт.
Використовуй тільки контекст.
Якщо немає інформації — скажи "Немає інформації в документі".

Контекст:
{context}

Питання:
{query}

Стиль: {style}
Мова: українська
"""

            answer, model, key = get_ai_response(prompt)

            if answer:
                st.success("Готово")

                now = datetime.now() + timedelta(hours=2)

                df = pd.DataFrame([{
                    "Дата": now.strftime("%d.%m.%Y"),
                    "Час": now.strftime("%H:%M:%S"),
                    "Файл": selected,
                    "Тип": mode,
                    "Запит": query,
                    "Модель": model,
                    "Ключ": key
                }])

                if not os.path.exists("stats.csv"):
                    df.to_csv("stats.csv", index=False, encoding='utf-8-sig')
                else:
                    df.to_csv("stats.csv", mode='a', header=False, index=False, encoding='utf-8-sig')

                st.markdown(f"<div class='answer-card'>{answer}</div>", unsafe_allow_html=True)

            else:
                st.error("Помилка ШІ")

# --- 9. FOOTER ---
st.markdown(f"<div style='text-align:center;font-size:10px;'>© {datetime.now().year}</div>", unsafe_allow_html=True)
