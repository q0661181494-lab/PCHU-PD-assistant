import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. ПІДКЛЮЧЕННЯ (Беремо ключ із Secrets)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    # Автоматичний пошук робочої моделі (виправляє помилку 404)
    # Намагаємося знайти gemini-1.5-flash або будь-яку доступну
    all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model_to_use = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_models else all_models[0]
    model = genai.GenerativeModel(model_to_use)
except Exception as e:
    st.error(f"Помилка ініціалізації: {e}")
    st.stop()

st.set_page_config(page_title="Тех-Помічник", layout="centered")
st.title("🤖 Технічний Помічник")

# 2. НОВА ФУНКЦІЯ: ВИБІР РЕЖИМУ ВІДПОВІДІ
answer_type = st.radio(
    "Оберіть тип відповіді:",
    ["Стисла (головні тези)", "Розгорнута (детально з пунктами правил)"],
    index=0,
    horizontal=True
)

st.write("---")
uploaded_file = st.file_uploader("Завантажте PDF або TXT", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages[:100]:
                t = page.extract_text()
                if t: full_text += t + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        full_text = full_text[:100000] # Обмежуємо обсяг для стабільності
    except Exception as e:
        st.error(f"Помилка файлу: {e}")

    user_query = st.text_input("Ваше питання (натисніть Enter):")

    if user_query and full_text:
        with st.spinner('ШІ готує відповідь...'):
            try:
                # НАЛАШТУВАННЯ ІНСТРУКЦІЇ ЗАЛЕЖНО ВІД ВИБОРУ
                if answer_type == "Стисла (головні тези)":
                    instruction = "Надай дуже коротку відповідь, тільки головні тези та цифри."
                else:
                    instruction = "Надай максимально повну, розгорнуту відповідь з цитуванням пунктів правил та таблиць."

                prompt = f"""
                Контекст документа: {full_text}
                Питання: {user_query}
                Інструкція: {instruction} Відповідай українською мовою.
                """
                
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.subheader("Відповідь:")
                    st.success(response.text)

                    if st.button("🔊 Озвучити"):
                        tts = gTTS(text=response.text, lang='uk')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.audio(fp, format="audio/mp3")
            except Exception as e:
                st.error(f"Помилка запиту: {str(e)}")
