import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. ПІДКЛЮЧЕННЯ (КЛЮЧ БЕРЕТЬСЯ ІЗ SECRETS)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Помилка конфігурації: {e}")
    st.stop()

st.set_page_config(page_title="Тех-Помічник", layout="centered")
st.title("🤖 Технічний Помічник")
st.write("Завантажте файл та обов'язково натисніть Enter після питання.")

uploaded_file = st.file_uploader("Оберіть PDF або TXT", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            # Збільшуємо кількість сторінок, які читає ШІ
            for page in pdf_reader.pages[:100]:
                text = page.extract_text()
                if text: full_text += text + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        # Збільшуємо ліміт символів до 100 000 (це близько 50 сторінок)
        full_text = full_text[:100000]
    except Exception as e:
        st.error(f"Помилка файлу: {e}")

    user_query = st.text_input("Ваше питання:")

    if user_query and full_text:
        with st.spinner('ШІ шукає повну відповідь...'):
            try:
                # ОСЬ ТУТ ТЕПЕР ПРАВИЛЬНІ ФІГУРНІ ДУЖКИ { }
                prompt = f"""
                Ти — професійний технічний експерт. Надай максимально повну, розгорнуту та аргументовану відповідь на основі наданого тексту. 
                Якщо в тексті є таблиці, цифри або конкретні пункти правил — обов'язково включи їх у відповідь. 
                Якщо питання стосується норм або стандартів, процитуй відповідні частини документа.

                Контекст документа:
                {full_text}

                Питання від користувача:
                {user_query}

                Надай детальну відповідь українською мовою:
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
                st.error(f"Помилка ШІ: {str(e)}")
