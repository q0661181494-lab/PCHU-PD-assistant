import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

# 1. ПІДКЛЮЧЕННЯ (КЛЮЧ БЕРЕТЬСЯ ІЗ SECRETS)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    # АВТОМАТИЧНИЙ ПОШУК РОБОЧОЇ МОДЕЛІ (вирішує помилку 404)
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # Пріоритет на gemini-1.5-flash, якщо ні — беремо першу доступну
    selected_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
    model = genai.GenerativeModel(selected_model)
except Exception as e:
    st.error(f"Помилка ініціалізації ШІ: {e}")
    st.stop()

st.set_page_config(page_title="Тех-Помічник", layout="centered")
st.title("🤖 Технічний Помічник")
st.write("Завантажте файл та обов'язково натисніть Enter після питання.")

# Завантаження файлу
uploaded_file = st.file_uploader("Оберіть PDF або TXT", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            # Читаємо до 100 сторінок
            for page in pdf_reader.pages[:100]:
                text = page.extract_text()
                if text: full_text += text + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        # Ліміт символів для стабільності (близько 50-60 сторінок)
        full_text = full_text[:100000]
    except Exception as e:
        st.error(f"Помилка при читанні файлу: {e}")

    user_query = st.text_input("Ваше питання:")

    if user_query and full_text:
        with st.spinner('ШІ шукає повну відповідь...'):
            try:
                # Промпт для розгорнутої відповіді з правильними дужками {}
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
                else:
                    st.warning("ШІ не зміг сформувати відповідь. Спробуйте інше питання.")
            except Exception as e:
                st.error(f"Сталася помилка при запиті: {str(e)}")
