import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io
import os
import random

# --- 1. РОЗУМНЕ ПІДКЛЮЧЕННЯ (ПОКРАЩЕНА РОТАЦІЯ) ---
def get_working_model():
    # Додайте ключі KEY1, KEY2, KEY3, KEY4, KEY5 у Secrets
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                # Використовуємо стабільну модель flash
                model = genai.GenerativeModel('gemini-1.5-flash')
                # Легка перевірка без великого запиту
                return model
            except:
                continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")
st.title("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

if not model:
    st.error("❌ Жоден API-ключ не працює або вони не додані в Secrets. Додайте KEY1, KEY2 тощо.")
    st.stop()

# --- 3. ФУНКЦІЯ ЧИТАННЯ PDF ---
def extract_text_from_pdf(file_path, max_pages=50):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            # Обмежуємо кількість сторінок для економії лімітів
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except:
        return ""

# --- 4. ЗБІР ФАЙЛІВ ---
available_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
if not available_files:
    st.warning("⚠️ PDF-файли не знайдені в репозиторії.")
    st.stop()

# --- 5. НАЛАШТУВАННЯ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", ["🔍 Шукати в усіх документах одночасно"] + available_files)

answer_mode = st.radio(
    "Оберіть тип відповіді:", 
    ["Стисла (головні тези)", "Розгорнута (детально)"], 
    index=0, horizontal=True
)

# --- 6. ПІДГОТОВКА ТЕКСТУ (ОПТИМІЗОВАНО) ---
final_context = ""
if selected_option == "🔍 Шукати в усіх документах одночасно":
    for file in available_files:
        # Беремо по 10 сторінок з кожного файлу для загального пошуку
        final_context += f"\n--- ФАЙЛ: {file} ---\n" + extract_text_from_pdf(file, max_pages=10)
else:
    final_context = extract_text_from_pdf(selected_option, max_pages=80)

# ОБМЕЖЕННЯ: 30 000 символів — ідеально для безкоштовного Gemini
final_context = final_context[:30000]

# --- 7. ПОШУК ---
st.write("---")
user_query = st.text_input("Ваше питання:", placeholder="Наприклад: норми виправлення просадок...")

if user_query and final_context:
    with st.spinner('ШІ аналізує базу даних...'):
        try:
            style = "Коротко, тези" if answer_mode == "Стисла (головні тези)" else "Детально, з пунктами правил"
            prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Мова: українська."
            
            response = model.generate_content(prompt)
            st.subheader("Відповідь:")
            st.success(response.text)
            
            # Озвучка
            if st.button("🔊 Озвучити"):
                tts = gTTS(text=response.text, lang='uk')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, format="audio/mp3")
        except Exception as e:
            if "429" in str(e):
                st.error("Помилка: Занадто багато запитів. Зачекайте 30 секунд.")
            else:
                st.error(f"Помилка: {e}")
