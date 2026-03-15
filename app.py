import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io
import os

# --- 1. НАЛАШТУВАННЯ ШІ ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # Автопошук робочої моделі
    all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_models else all_models[0]
    model = genai.GenerativeModel(model_name)
except Exception as e:
    st.error(f"Помилка конфігурації: {e}")
    st.stop()

st.set_page_config(page_title="Технічна бібліотека ПЧУ-5", layout="centered")
st.title("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА КОЛІЙНИКА")

# --- 2. ФУНКЦІЯ ЧИТАННЯ PDF ---
def extract_text_from_pdf(file_path, max_pages=50):
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

# --- 3. ЗБІР ФАЙЛІВ З ГІТХАБУ ---
available_files = [f for f in os.listdir(".") if f.endswith(".pdf")]

if not available_files:
    st.warning("⚠️ Завантажте PDF-файли на GitHub (Add file -> Upload).")
    st.stop()

# --- 4. ІНТЕРФЕЙС НАЛАШТУВАНЬ ---
st.subheader("⚙️ Налаштування пошуку")

# Вибір файлу
selected_option = st.selectbox(
    "Оберіть інструкцію або пошук по всій базі:",
    ["🔍 Шукати в усіх документах одночасно"] + available_files
)

# Вибір типу відповіді (додано назад)
answer_mode = st.radio(
    "Якою має бути відповідь?",
    ["Стисла (головні тези)", "Розгорнута (детально з пунктами)"],
    index=1,
    horizontal=True
)

# --- 5. ФОРМУВАННЯ КОНТЕКСТУ ---
final_context = ""
if selected_option == "🔍 Шукати в усіх документах одночасно":
    for file in available_files:
        final_context += f"\n--- ФАЙЛ: {file} ---\n" + extract_text_from_pdf(file, max_pages=15)
else:
    final_context = extract_text_from_pdf(selected_option, max_pages=100)

final_context = final_context[:100000] # Обмеження для стабільності

# --- 6. ЗАПИТАННЯ ТА ВІДПОВІДЬ ---
user_query = st.text_input("Ваше питання (натисніть Enter):")

if user_query and final_context:
    with st.spinner('ШІ аналізує документацію...'):
        try:
            # Налаштування інструкції для ШІ
            if answer_mode == "Стисла (головні тези)":
                style_instr = "Надай дуже коротку відповідь українською, тільки факти та цифри."
            else:
                style_instr = "Надай максимально повну відповідь українською, з цитатами, пунктами правил та деталями."

            prompt = f"""
            Ти технічний експерт. Використовуй цей текст:
            {final_context}
            
            ПИТАННЯ: {user_query}
            ІНСТРУКЦІЯ: {style_instr}
            """
            
            response = model.generate_content(prompt)
            st.subheader("Відповідь:")
            st.success(response.text)
            
            # Кнопка озвучки (окрема)
            if st.button("🔊 Озвучити відповідь"):
                tts = gTTS(text=response.text, lang='uk')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp, format="audio/mp3")
                
        except Exception as e:
            st.error(f"Помилка ШІ: {e}")
