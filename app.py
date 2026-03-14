import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. Налаштування інтерфейсу
st.set_page_config(page_title="Тех-Помічник", layout="centered")

# 2. Ініціалізація ШІ
try:
    # Беремо ключ із налаштувань Secrets
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # Використовуємо стабільну назву моделі
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"Помилка конфігурації: {e}")
    st.stop()

st.title("🤖 Технічний Помічник")
st.write("Завантажте документ і ставте питання.")

# 3. Завантаження файлу
uploaded_file = st.file_uploader("Оберіть файл (PDF або TXT)", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            # Читаємо перші 100 сторінок (цього вистачить для більшості інструкцій)
            for i, page in enumerate(pdf_reader.pages):
                if i > 100: break
                t = page.extract_text()
                if t: full_text += t + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        # Обмежуємо обсяг тексту для стабільної роботи (приблизно 50к символів)
        full_text = full_text[:50000] 
        
    except Exception as e:
        st.error(f"Помилка при читанні файлу: {e}")

    # 4. Введення питання
    user_query = st.text_input("Ваше питання (натисніть Enter після введення):")

    if user_query and full_text:
        with st.spinner('ШІ аналізує документ...'):
            try:
                # Формуємо запит
                prompt = f"Контекст: {full_text}\n\nПитання: {user_query}\n\nВідповідай українською мовою, коротко і чітко на основі тексту."
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.subheader("Відповідь:")
                    st.info(response.text)

                    # 5. Озвучка відповіді
                    if st.button("🔊 Озвучити відповідь голосом"):
                        with st.spinner('Генерую аудіо...'):
                            tts = gTTS(text=response.text, lang='uk')
                            fp = io.BytesIO()
                            tts.write_to_fp(fp)
                            st.audio(fp, format="audio/mp3")
                else:
                    st.warning("ШІ не зміг знайти відповідь у цьому документі.")
            except Exception as e:
                st.error(f"Помилка запиту до ШІ: {e}")
