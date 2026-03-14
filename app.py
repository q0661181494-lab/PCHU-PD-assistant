import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. Налаштування сторінки
st.set_page_config(page_title="Тех-Помічник", layout="centered")

# 2. Підключення ключа з налаштувань (Secrets)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except:
    st.error("Помилка: API Key не налаштовано в Secrets! Будь ласка, додайте його в налаштуваннях Streamlit.")
    st.stop()

st.title("🤖 Технічний Помічник")
st.write("Завантажте документ (PDF або TXT) і ставте питання.")

# 3. Поле для завантаження файлу
uploaded_file = st.file_uploader("Оберіть файл", type=['pdf', 'txt'])

if uploaded_file:
    # Читання тексту з файлу
    full_text = ""
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                full_text += text
    else:
        full_text = uploaded_file.read().decode("utf-8")

    # 4. Поле для введення питання
    user_query = st.text_input("Ваше питання (можна продиктувати через мікрофон):")

    if user_query:
        with st.spinner('Шукаю відповідь у документі...'):
            # Формуємо запит до ШІ
            prompt = f"Ти технічний експерт. Відповідай коротко і по суті. Використовуй цей текст: {full_text}. Питання: {user_query}"
            response = model.generate_content(prompt)
            answer_text = response.text
            
            # Виводимо текстову відповідь
            st.subheader("Відповідь:")
            st.info(answer_text)

            # 5. Кнопка для озвучки
            if st.button("🔊 Озвучити відповідь"):
                with st.spinner('Генерую голос...'):
                    tts = gTTS(text=answer_text, lang='uk')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp, format="audio/mp3")
