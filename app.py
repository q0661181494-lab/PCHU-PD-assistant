import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. Налаштування інтерфейсу
st.set_page_config(page_title="Тех-Помічник", layout="centered")

# 2. Ініціалізація ШІ
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    # Використовуємо базову назву моделі, яку Google підтримує найдовше
    model = genai.GenerativeModel('gemini-1.5-flash')
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
            for i, page in enumerate(pdf_reader.pages):
                if i > 50: break # Обмеження для стабільності
                t = page.extract_text()
                if t: full_text += t + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        full_text = full_text[:30000] # Залишаємо початок документа
        
    except Exception as e:
        st.error(f"Помилка при читанні файлу: {e}")

    # 4. Введення питання
    user_query = st.text_input("Ваше питання (натисніть Enter після введення):")

    if user_query and full_text:
        with st.spinner('ШІ аналізує документ...'):
            try:
                # Обов'язково вказуємо мову в інструкції
                prompt = f"Контекст: {full_text}\n\nПитання: {user_query}\n\nДай коротку відповідь українською мовою."
                
                # Запит до ШІ
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.subheader("Відповідь:")
                    st.info(response.text)

                    # 5. Озвучка
                    if st.button("🔊 Озвучити відповідь"):
                        tts = gTTS(text=response.text, lang='uk')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.audio(fp, format="audio/mp3")
                else:
                    st.warning("Не вдалося отримати відповідь. Спробуйте інше питання.")
            except Exception as e:
                st.error(f"Сталася помилка запиту. Спробуйте ще раз через хвилину.")
