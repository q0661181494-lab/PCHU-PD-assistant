import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random

# --- 1. ФУНКЦІЯ ЗАПИТУ З АВТОМАТИЧНОЮ РОТАЦІЄЮ КЛЮЧІВ ---
def ask_gemini(prompt):
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
                return response.text
            except Exception as e:
                if "429" in str(e):
                    continue
                else:
                    return f"Помилка API: {e}"
    
    return "❌ Всі доступні ключі вичерпали свої ліміти. Спробуйте через 1 хвилину."

# --- 2. ЛОГІКА ОЧИЩЕННЯ ТЕКСТУ ---
if "user_query" not in st.session_state:
    st.session_state.user_query = ""

def clear_text():
    st.session_state.user_query = ""

# --- 3. ІНТЕРФЕЙС ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")
st.title("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

# --- 4. ЧИТАННЯ PDF ---
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

# --- 5. ФАЙЛИ ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ Файли .pdf не знайдені.")
    st.stop()

# --- 6. МЕНЮ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", ["🔍 Шукати в усіх документах одночасно"] + available_files)
answer_mode = st.radio("Тип відповіді:", ["Стисла", "Розгорнута"], index=0, horizontal=True)

# --- 7. КОНТЕКСТ ---
final_context = ""
if selected_option == "🔍 Шукати в усіх документах одночасно":
    for file in available_files:
        final_context += f"\n--- ФАЙЛ: {file} ---\n" + extract_text_from_pdf(file, max_pages=5)
else:
    final_context = extract_text_from_pdf(selected_option, max_pages=60)

final_context = final_context[:25000]

# --- 8. ПОШУК ТА КНОПКИ ---
st.write("---")
# Додаємо поле з прив'язкою до session_state
user_query = st.text_input("", placeholder="Напишіть ваше питання тут...", key="user_query", label_visibility="collapsed")

# Створюємо три колонки: для пошуку, очищення та відступу
col1, col2, _ = st.columns([0.2, 0.2, 0.6])

with col1:
    search_button = st.button("🔍 Пошук", type="primary")

with col2:
    st.button("🗑️ Очистити", on_click=clear_text)

# --- 9. ЛОГІКА ВІДПОВІДІ ---
if (search_button) and final_context:
    if not user_query.strip():
        st.warning("Введіть питання.")
    else:
        with st.spinner('ШІ аналізує документацію...'):
            style = "тези" if answer_mode == "Стисла" else "детально з пунктами правил"
            prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
            
            answer = ask_gemini(prompt)
            
            st.subheader("Відповідь:")
            if "❌" in answer:
                st.error(answer)
            else:
                st.success("Аналіз завершено!")
                st.write(answer)
