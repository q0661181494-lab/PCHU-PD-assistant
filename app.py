import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io
import os
import random

# --- 1. ПІДКЛЮЧЕННЯ (МАКСИМАЛЬНО ПРОСТЕ ТА НАДІЙНЕ) ---
def get_working_model():
    # Додайте ключі KEY1, KEY2, KEY3... у Secrets вашого Streamlit
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                # Використовуємо базову назву моделі без зайвих тестів
                model = genai.GenerativeModel('gemini-1.5-flash')
                return model
            except:
                continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")
st.title("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

# Якщо модель не підключилася, виводимо конкретну пораду
if not model:
    st.error("❌ Помилка підключення до Google AI. Перевірте, чи правильно вказано KEY1 у Secrets (Налаштування -> Secrets).")
    st.info("Переконайтеся, що запис у Secrets виглядає так: KEY1 = \"ваш_ключ\"")
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
    except:
        return ""

# --- 4. ЗБІР ФАЙЛІВ ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ Будь ласка, завантажте PDF-файли в репозиторій GitHub.")
    st.stop()

# --- 5. НАЛАШТУВАННЯ ПОШУКУ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", ["🔍 Шукати в усіх документах одночасно"] + available_files)

answer_mode = st.radio(
    "Оберіть тип відповіді:", 
    ["Стисла (головні тези)", "Розгорнута (детально)"], 
    index=0, horizontal=True
)

# --- 6. ПІДГОТОВКА ТЕКСТУ (ЗМЕНШЕНО ДЛЯ СТАБІЛЬНОСТІ) ---
final_context = ""
if selected_option == "🔍 Шукати в усіх документах одночасно":
    for file in available_files:
        final_context += f"\n--- ФАЙЛ: {file} ---\n" + extract_text_from_pdf(file, max_pages=5)
else:
    final_context = extract_text_from_pdf(selected_option, max_pages=50)

# Обмеження до 20к символів, щоб гарантовано проходити по лімітах безкоштовної версії
final_context = final_context[:20000]

# --- 7. ПОШУК З ЛУПОЮ ---
st.write("---")
col1, col2 = st.columns([0.85, 0.15])
with col1:
    user_query = st.text_input("", placeholder="Напишіть ваше питання тут...", label_visibility="collapsed")
with col2:
    search_button = st.button("🔍 Пошук")

# --- 8. ВІДПОВІДЬ ---
if (user_query or search_button) and final_context:
    if not user_query:
        st.warning("Введіть питання.")
    else:
        with st.spinner('Аналізую документацію...'):
            try:
                style = "тези" if answer_mode == "Стисла (головні тези)" else "детально з пунктами правил"
                prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Мова: українська."
                
                response = model.generate_content(prompt)
                
                st.subheader("Відповідь:")
                st.success(response.text)
                
                if st.button("🔊 Озвучити"):
                    tts = gTTS(text=response.text, lang='uk')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp, format="audio/mp3")
            except Exception as e:
                st.error(f"Помилка: {e}")
