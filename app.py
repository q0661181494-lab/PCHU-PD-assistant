import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

st.set_page_config(page_title="Тех-Помічник", layout="centered")

# 1. Спроба підключення до ШІ
try:
    if "GOOGLE_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        # ЗМІНЕНО: Використовуємо іншу назву моделі, яка працює з v1beta
        model = genai.GenerativeModel('models/gemini-1.5-flash')
    else:
        st.error("Ключ API не знайдено!")
        st.stop()
except Exception as e:
    st.error(f"Помилка ініціалізації: {e}")
    st.stop()

st.title("🤖 Технічний Помічник")
st.write("Завантажте файл та натисніть Enter після введення питання.")

uploaded_file = st.file_uploader("Оберіть PDF або TXT", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for i, page in enumerate(pdf_reader.pages[:20]):
                t = page.extract_text()
                if t: full_text += t + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        full_text = full_text[:20000]
        
    except Exception as e:
        st.error(f"Не вдалося прочитати файл: {e}")

    user_query = st.text_input("Ваше питання:")

    if user_query and full_text:
        with st.spinner('Зачекайте, ШІ формує відповідь...'):
            try:
                # Надсилаємо запит
                prompt = f"Контекст: {full_text} \n\n Питання: {user_query} \n\n Відповідай українською мовою."
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
                st.error(f"Помилка від Google: {str(e)}")
