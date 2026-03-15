import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random

# --- 1. ПІДКЛЮЧЕННЯ (ПРОФЕСІЙНЕ ВИРІШЕННЯ ПОМИЛКИ 404) ---
def get_working_model():
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                
                # Автоматично шукаємо правильну назву моделі, щоб уникнути 404
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                # Пріоритет на flash, якщо ні — беремо першу доступну
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                
                return genai.GenerativeModel(model_name)
            except Exception:
                continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")
st.title("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

if not model:
    st.error("❌ Не вдалося підключитися до ШІ. Перевірте ключі в Secrets.")
    st.stop()

# --- 3. ФУНКЦІЯ ЧИТАННЯ PDF ---
def extract_text_from_pdf(file_path, max_pages=30):
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

# --- 5. НАЛАШТУВАННЯ ПОШУКУ ---
st.write("---")
# ВИДАЛЕНО: пункт "Шукати в усіх документах одночасно"
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла (головні тези)", "Розгорнута (детально)"], index=0, horizontal=True)

# --- 6. ПІДГОТОВКА ТЕКСТУ (ОПТИМІЗОВАНО) ---
# ВИДАЛЕНО: логіку перевірки selected_option на загальний пошук
final_context = extract_text_from_pdf(selected_option, max_pages=60)
final_context = final_context[:25000]

# --- 7. ПОШУК З ЛУПОЮ ---
st.write("---")
col1, col2 = st.columns([0.85, 0.15])
with col1:
    user_query = st.text_input("", placeholder="Напишіть ваше питання або "Білет №..."...", label_visibility="collapsed")
with col2:
    search_button = st.button("🔍 Пошук")

# --- 8. ЛОГІКА ВІДПОВІДІ ---
if (user_query or search_button) and final_context:
    if not user_query:
        st.warning("Введіть питання.")
    else:
        with st.spinner('ШІ аналізує документацію...'):
            try:
                style = "тези" if answer_mode == "Стисла (головні тези)" else "детально з пунктами правил"
                prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
                
                response = model.generate_content(prompt)
                st.subheader("Відповідь:")
                st.success(response.text)
                
                
            except Exception as e:
                st.error(f"Помилка: {e}")
