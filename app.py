import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. Налаштування сторінки
st.set_page_config(page_title="Тех-Помічник", layout="centered")

# 2. Підключення ключа
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Помилка конфігурації API.")
    st.stop()

st.title("🤖 Технічний Помічник")
st.write("Завантажте документ і ставте питання.")

uploaded_file = st.file_uploader("Оберіть файл (PDF або TXT)", type=['pdf', 'txt'])

if uploaded_file:
    # 3. Витягуємо текст
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        # Обмежуємо обсяг тексту, щоб не було помилки InvalidArgument (залишаємо перші 30к символів)
        full_text = full_text[:30000] 
        
    except Exception as e:
        st.error(f"Помилка при читанні файлу: {e}")

    # 4. Поле для питання
    user_query = st.text_input("Ваше питання:")

    if user_query and full_text:
        with st.spinner('Шукаю відповідь...'):
            try:
                # Чіткий промпт для ШІ
                prompt = f"Ти технічний експерт. На основі наданого тексту дай коротку і точну відповідь українською мовою. Якщо в тексті немає відповіді, так і скажи. \n\n ТЕКСТ ДОКУМЕНТА: {full_text} \n\n ПИТАННЯ: {user_query}"
                
                response = model.generate_content(prompt)
                
                if response:
                    st.subheader("Відповідь:")
                    st.info(response.text)

                    # 5. Кнопка для озвучки
                    if st.button("🔊 Озвучити відповідь"):
                        tts = gTTS(text=response.text, lang='uk')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.audio(fp, format="audio/mp3")
            except Exception as e:
                st.error(f"ШІ не зміг обробити запит. Спробуйте поставити питання інакше. Деталі: {e}")
