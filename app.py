import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io
import os
import random

# --- 1. РОЗУМНЕ ПІДКЛЮЧЕННЯ (РОТАЦІЯ КЛЮЧІВ) ---
def get_working_model():
    # Додайте сюди назви ключів, які ви прописали в Secrets (наприклад, KEY1, KEY2)
    key_names = ["KEY1", "KEY2", "KEY3"] 
    random.shuffle(key_names)
    
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_models else all_models
                model = genai.GenerativeModel(model_name)
                # Тестова перевірка ключа
                model.generate_content("test", generation_config={"max_output_tokens": 1})
                return model
            except:
                continue 
    return None

model = get_working_model()

if not model:
    st.error("❌ Всі ліміти вичерпано. Зачекайте 1 хвилину або додайте нові ключі з інших акаунтів.")
    st.stop()

# --- 2. ІНТЕРФЕЙС (ОНОВЛЕНО ЗГІДНО З ВАШИМ МАЛЮНКОМ) ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")
st.title("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

# --- 3. ФУНКЦІЯ ЧИТАННЯ PDF ---
def extract_text_from_pdf(file_path, max_pages=100):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except:
        return ""

# --- 4. ЗБІР ФАЙЛІВ З ГІТХАБУ ---
available_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
if not available_files:
    st.warning("⚠️ Завантажте PDF-файли на GitHub.")
    st.stop()

# --- 5. НАЛАШТУВАННЯ ПОШУКУ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію або пошук по всій базі:", ["🔍 Шукати в усіх документах одночасно"] + available_files)

# За замовчуванням — стисла (index=0)
answer_mode = st.radio(
    "Оберіть тип відповіді:", 
    ["Стисла (головні тези)", "Розгорнута (детально з пунктами правил)"], 
    index=0, 
    horizontal=True
)

# --- 6. ПІДГОТОВКА ТЕКСТУ ---
final_context = ""
if selected_option == "🔍 Шукати в усіх документах одночасно":
    for file in available_files:
        final_context += f"\n--- ФАЙЛ: {file} ---\n" + extract_text_from_pdf(file, max_pages=15)
else:
    final_context = extract_text_from_pdf(selected_option, max_pages=100)
final_context = final_context[:100000]

# --- 7. ПОШУК З ЛУПОЮ В ОДИН РЯДОК ---
st.write("---")
col1, col2 = st.columns([0.9, 0.1])
with col1:
    user_query = st.text_input("", placeholder="Напишіть ваше питання тут...", label_visibility="collapsed")
with col2:
    search_button = st.button("🔍")

if (user_query or search_button) and final_context:
    if not user_query:
        st.warning("Будь ласка, введіть питання.")
    else:
        with st.spinner('ШІ аналізує документацію...'):
            try:
                if answer_mode == "Стисла (головні тези)":
                    style_instr = "Надай дуже коротку відповідь українською, тільки головні тези та цифри."
                else:
                    style_instr = "Надай максимально повну, розгорнуту та аргументовану відповідь українською мовою з цитатами та пунктами правил."

                prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style_instr}"
                
                response = model.generate_content(prompt)
                st.subheader("Відповідь:")
                st.success(response.text)
                
                if st.button("🔊 Озвучити відповідь"):
                    tts = gTTS(text=response.text, lang='uk')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp, format="audio/mp3")
            except Exception as e:
                st.error(f"Сталася помилка при запиті: {e}")

