import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io

st.set_page_config(page_title="Тех-Помічник", layout="centered")

# 1. Розумне підключення до моделі
@st.cache_resource
def get_ai_model():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # Пробуємо список моделей, від найновішої до найстабільнішої
        models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                # Тестовий короткий запит для перевірки працездатності
                model.generate_content("test", generation_config={"max_output_tokens": 1})
                return model
            except:
                continue
        return None
    except Exception as e:
        st.error(f"Помилка конфігурації: {e}")
        return None

model = get_ai_model()

if not model:
    st.error("ШІ не зміг підключитися. Перевірте ваш API Key в Secrets (можливо, там є зайві пробіли).")
    st.stop()

st.title("🤖 Технічний Помічник")
st.write("Завантажте файл та натисніть Enter після введення питання.")

uploaded_file = st.file_uploader("Оберіть PDF або TXT", type=['pdf', 'txt'])

if uploaded_file:
    full_text = ""
    try:
        if uploaded_file.type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            # Читаємо лише перші 30 сторінок для швидкості
            for i, page in enumerate(pdf_reader.pages[:30]):
                t = page.extract_text()
                if t: full_text += t + "\n"
        else:
            full_text = uploaded_file.read().decode("utf-8")
        
        full_text = full_text[:30000] # Обмеження обсягу
        
    except Exception as e:
        st.error(f"Не вдалося прочитати файл: {e}")

    user_query = st.text_input("Ваше питання:")

    if user_query and full_text:
        with st.spinner('ШІ аналізує документ...'):
            try:
                prompt = f"Контекст: {full_text} \n\n Питання: {user_query} \n\n Дай коротку відповідь українською мовою."
                response = model.generate_content(prompt)
                
                if response and response.text:
                    st.subheader("Відповідь:")
                    st.success(response.text)

                    if st.button("🔊 Озвучити відповідь"):
                        tts = gTTS(text=response.text, lang='uk')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.audio(fp, format="audio/mp3")
                else:
                    st.warning("ШІ повернув порожню відповідь. Спробуйте інше питання.")
            except Exception as e:
                st.error(f"Помилка запиту: {str(e)}")
