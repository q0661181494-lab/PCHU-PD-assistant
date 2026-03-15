import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io
import os
import random

# --- 1. РОЗУМНЕ ПІДКЛЮЧЕННЯ (ПОКРАЩЕНА РОТАЦІЯ) ---
def get_working_model():
    # Додайте ключі KEY1, KEY2, KEY3, KEY4, KEY5 у Secrets вашого Streamlit
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                # ВИПРАВЛЕНО: додано повну назву моделі для усунення помилки 404
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                return model
            except:
                continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")
st.title("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

if not model:
    st.error("❌ Жоден API-ключ не працює. Перевірте Secrets у налаштуваннях Streamlit.")
    st.stop()

# --- 3. ФУНКЦІЯ ЧИТАННЯ PDF ---
def extract_text_from_pdf(file_path, max_pages=50):
    text = ""
    try:
        if not os.path.exists(file_path): return ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except:
        return ""

# --- 4. ЗБІР ФАЙЛІВ З РЕПОЗИТОРІЮ ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ Завантажте PDF-файли в корінь репозиторію на GitHub.")
    st.stop()

# --- 5. НАЛАШТУВАННЯ ПОШУКУ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію або пошук по всій базі:", ["🔍 Шукати в усіх документах одночасно"] + available_files)

answer_mode = st.radio(
    "Оберіть тип відповіді:", 
    ["Стисла (головні тези)", "Розгорнута (детально з пунктами правил)"], 
    index=0, 
    horizontal=True
)

# --- 6. ПІДГОТОВКА ТЕКСТУ (ОПТИМІЗОВАНО ПІД ЛІМІТИ) ---
final_context = ""
if selected_option == "🔍 Шукати в усіх документах одночасно":
    for file in available_files:
        # Беремо по 10 сторінок з кожного файлу для загального пошуку, щоб не «забити» ліміт
        final_context += f"\n--- ФАЙЛ: {file} ---\n" + extract_text_from_pdf(file, max_pages=10)
else:
    final_context = extract_text_from_pdf(selected_option, max_pages=80)

# Обмежуємо загальний обсяг до 35 000 символів (безпечно для безкоштовного Gemini)
final_context = final_context[:35000]

# --- 7. ПОШУК З ЛУПОЮ (ОДИН РЯДОК) ---
st.write("---")
col1, col2 = st.columns([0.85, 0.15])
with col1:
    user_query = st.text_input("", placeholder="Напишіть ваше питання тут...", label_visibility="collapsed")
with col2:
    search_button = st.button("🔍 Пошук")

# --- 8. ЛОГІКА ВІДПОВІДІ ---
if (user_query or search_button) and final_context:
    if not user_query:
        st.warning("Будь ласка, введіть питання.")
    else:
        with st.spinner('ШІ аналізує документацію...'):
            try:
                style_instr = "Надай дуже коротку відповідь, тільки тези." if answer_mode == "Стисла (головні тези)" else "Надай повну відповідь з пунктами правил."
                prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style_instr} Відповідай українською мовою."
                
                response = model.generate_content(prompt)
                
                st.subheader("Відповідь:")
                st.success(response.text)
                
                # Кнопка озвучки з'являється тільки після відповіді
                if st.button("🔊 Озвучити відповідь"):
                    tts = gTTS(text=response.text, lang='uk')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp, format="audio/mp3")
                    
            except Exception as e:
                if "429" in str(e):
                    st.error("⚠️ Ліміт запитів вичерпано. Спробуйте через 30 секунд або додайте ще один KEY у Secrets.")
                else:
                    st.error(f"Сталася помилка: {e}")
