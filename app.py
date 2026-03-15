import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. ВАШ КЛЮЧ (ПЕРЕВІРЕНО)
MY_API_KEY = st.secrets["GOOGLE_API_KEY"]

# 2. НАЙБІЛЬШ НАДІЙНИЙ СПОСІБ ПІДКЛЮЧЕННЯ
try:
    genai.configure(api_key=MY_API_KEY)
    
    # Шукаємо першу доступну модель, яка вміє генерувати текст
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # Вибираємо gemini-1.5-flash або будь-яку іншу доступну
    model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
    model = genai.GenerativeModel(model_name)
except Exception as e:
    st.error(f"Помилка ініціалізації: {e}")

st.set_page_config(page_title="Екзамен ЦП-0269", layout="centered")
st.title("🤖 Технічний Помічник")
st.write("Завантажте файл та обов'язково натисніть Enter після питання.")

uploaded_file = st.file_uploader("Оберіть PDF або TXT", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages[:30]: # Читаємо перші 30 сторінок
                text = page.extract_text()
                if text: full_text += text + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        full_text = full_text[:25000] # Обмеження для стабільності
    except Exception as e:
        st.error(f"Помилка файлу: {e}")

    user_query = st.text_input("Ваше питання:")

    if user_query and full_text:
        with st.spinner('ШІ шукає відповідь...'):
            try:
                # Прямий запит без складних налаштувань
                response = model.generate_content(f"Контекст: {full_text}\n\nПитання: {user_query}\n\nВідповідай коротко українською.")
                
                if response and response.text:
                    st.subheader("Відповідь:")
                    st.success(response.text)

                    # Озвучка
                    if st.button("🔊 Озвучити"):
                        tts = gTTS(text=response.text, lang='uk')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.audio(fp, format="audio/mp3")
                else:
                    st.warning("Спробуйте змінити питання.")
            except Exception as e:
                st.error(f"Помилка ШІ: {str(e)}")
