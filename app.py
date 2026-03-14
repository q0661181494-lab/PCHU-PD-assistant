import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. ВАШ КЛЮЧ API
MY_API_KEY = "AIzaSyBNK5emKQAUBGY0G8do89HxQgNO8-EIllY"

# Налаштування AI
try:
    genai.configure(api_key=MY_API_KEY)
    # Використовуємо найпростішу назву моделі
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Помилка підключення: {e}")

st.set_page_config(page_title="Технічний Помічник", layout="centered")
st.title("🤖 Технічний Помічник")
st.write("Завантажте документ та поставте питання (натисніть Enter).")

uploaded_file = st.file_uploader("Оберіть файл (PDF або TXT)", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages[:50]: # Читаємо перші 50 сторінок
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        full_text = full_text[:30000] # Обмежуємо обсяг тексту
        
    except Exception as e:
        st.error(f"Помилка при читанні файлу: {e}")

    user_query = st.text_input("Ваше питання:")

    if user_query and full_text:
        with st.spinner('AI аналізує документ...'):
            try:
                # Чітка інструкція для AI
                prompt = f"Ти технічний експерт. На основі тексту нижче дай коротку відповідь українською мовою. \n\n ТЕКСТ: {full_text} \n\n ПИТАННЯ: {user_query}"
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.subheader("Відповідь:")
                    st.success(response.text)

                    if st.button("🔊 Озвучити відповідь"):
                        tts = gTTS(text=response.text, lang='uk')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.audio(fp, format="audio/mp3")
            except Exception as e:
                st.error(f"Сталася помилка запиту (404 або інша): {e}")
