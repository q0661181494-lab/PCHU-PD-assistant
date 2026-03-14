import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. ВСТАВЛЕНИЙ ВАШ КЛЮЧ (ПРАЦЮЄ НАПРЯМУ)
MY_API_KEY = "AIzaSyBNK5emKQAUBGY0G8do89HxQgNO8-EIllY"

# Налаштування ШІ
try:
    genai.configure(api_key=MY_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Помилка підключення до ШІ: {e}")

# Інтерфейс додатка
st.set_page_config(page_title="Тех-Помічник", layout="centered")
st.title("🤖 Технічний Помічник")
st.write("Завантажте документ і ставте питання (натисніть Enter після введення).")

# Завантаження файлу
uploaded_file = st.file_uploader("Оберіть файл (PDF або TXT)", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            # Читаємо перші 50 сторінок для стабільності
            for i, page in enumerate(pdf_reader.pages[:50]):
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        # Обмеження обсягу тексту (перші 30к символів)
        full_text = full_text[:30000]
        
    except Exception as e:
        st.error(f"Помилка при читанні файлу: {e}")

    # Поле для питання
    user_query = st.text_input("Ваше питання:")

    if user_query and full_text:
        with st.spinner('ШІ аналізує документ...'):
            try:
                # Запит до ШІ
                prompt = f"Контекст: {full_text}\n\nПитання: {user_query}\n\nВідповідай коротко українською мовою."
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.subheader("Відповідь:")
                    st.success(response.text)

                    # Озвучка відповіді
                    if st.button("🔊 Озвучити відповідь"):
                        with st.spinner('Генерую аудіо...'):
                            tts = gTTS(text=response.text, lang='uk')
                            fp = io.BytesIO()
                            tts.write_to_fp(fp)
                            st.audio(fp, format="audio/mp3")
                else:
                    st.warning("ШІ не зміг знайти відповідь. Спробуйте інше питання.")
            except Exception as e:
                st.error(f"Помилка запиту: {e}")
