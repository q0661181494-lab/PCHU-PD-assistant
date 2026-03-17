import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
from datetime import datetime

# --- 0. СПІЛЬНА ПАМ'ЯТЬ ДЛЯ ВСІХ КОРИСТУВАЧІВ ---
@st.cache_resource
def get_global_stats():
    # Цей список буде один на весь сервер для всіх пристроїв
    return []

global_stats = get_global_stats()

# --- 1. ПІДКЛЮЧЕННЯ ШІ ---
def get_working_model():
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                return genai.GenerativeModel(model_name)
            except: continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ТА СЕКРЕТНИЙ SIDEBAR ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")

with st.sidebar:
    st.title("📂 Керування")
    admin_password = st.text_input("Додати файл інструкції (PDF):", type="password", placeholder="Виберіть файл...")
    
    if admin_password == "30033003": 
        st.success("Доступ до спільної статистики відкрито")
        st.subheader("📊 Запити з усіх пристроїв")
        if global_stats:
            # Вивід таблиці (останні запити зверху)
            st.table(global_stats[::-1])
            if st.button("🗑️ Очистити для всіх"):
                global_stats.clear()
                st.rerun()
        else:
            st.info("Запитів ще не було.")

st.subheader("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

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
    st.warning("⚠️ Файли .pdf не знайдені.")
    st.stop()

# --- 5. МЕНЮ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла (головні тези)", "Розгорнута (детально)"], index=0, horizontal=True)

# --- 6. ПІДГОТОВКА ТЕКСТУ ---
final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000]

# --- 7. ПОШУК ---
st.write("---")
col1, col2 = st.columns([0.85, 0.15])
with col1:
    user_query = st.text_input("Пошук", placeholder="Напишіть ваше питання або Білет N...", label_visibility="collapsed")
with col2:
    search_button = st.button("🔍 Пошук")

# --- 8. ЛОГІКА ВІДПОВІДІ ТА ЗАПИС У СПІЛЬНУ БАЗУ ---
if (user_query or search_button) and final_context:
    if not user_query.strip():
        st.warning("Введіть питання.")
    else:
        headers = st.context.headers
        user_agent = headers.get("User-Agent", "Unknown Device")
        current_time = datetime.now().strftime("%d.%m %H:%M")
        
        with st.spinner('ШІ аналізує документацію...'):
            try:
                style = "тези" if answer_mode == "Стисла (головні тези)" else "детально з пунктами правил"
                prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
                
                response = model.generate_content(prompt)
                st.subheader("Відповідь:")
                st.success(response.text)
                
                # ЗАПИС У СПІЛЬНИЙ СПИСОК (бачать всі адміни)
                global_stats.append({
                    "Час": current_time,
                    "Пристрій": user_agent[:25],
                    "Файл": selected_option[:15],
                    "Запит": user_query
                })
                
                # Обмежуємо список, щоб не перевантажувати пам'ять (останні 100 запитів)
                if len(global_stats) > 100:
                    global_stats.pop(0)
                
            except Exception as e:
                st.error(f"Помилка: {e}")

# --- 9. ПІДПИС ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
