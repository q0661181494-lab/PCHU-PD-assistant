import streamlit as st
import google.generativeai as genai
import PyPDF2
from gtts import gTTS
import io
import os

# --- 1. НАЛАШТУВАННЯ ШІ ---
try:
    # Беремо ключ із налаштувань Secrets (безпечний метод)
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    # Автоматичний вибір робочої моделі
    all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_models else all_models
    model = genai.GenerativeModel(model_name)
except Exception as e:
    st.error(f"Помилка конфігурації: {e}")
    st.stop()

st.set_page_config(page_title="Технічна бібліотека ПЧУ-5", layout="centered")
st.title("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

# --- 2. ФУНКЦІЯ ЧИТАННЯ PDF ---
def extract_text_from_pdf(file_path, max_pages=100):
    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except:
        return ""

# --- 3. ЗБІР ФАЙЛІВ З ГІТХАБУ ---
available_files = [f for f in os.listdir(".") if f.endswith(".pdf")]

if not available_files:
    st.warning("⚠️ Завантажте PDF-файли на GitHub (Add file -> Upload), щоб вони з'явилися тут.")
    st.stop()

# --- 4. ІНТЕРФЕЙС НАЛАШТУВАНЬ ---
st.subheader("⚙️ Налаштування пошуку")

# Вибір файлу
selected_option = st.selectbox(
    "Оберіть інструкцію або пошук по всій базі:",
    ["🔍 Шукати в усіх документах одночасно"] + available_files
)

# Вибір типу відповіді (ЗА ЗАМОВЧУВАННЯМ - СТИСЛА)
answer_mode = st.radio(
    "Якою має бути відповідь?",
    ["Стисла (головні тези)", "Розгорнута (детально з пунктами)"],
    index=0,  # index=0 ставить вибір на перший варіант за замовчуванням
    horizontal=True
)

# --- 5. ПІДГОТОВКА ТЕКСТУ ДОКУМЕНТІВ ---
final_context = ""
if selected_option == "🔍 Шукати в усіх документах одночасно":
    for file in available_files:
        # Для "всіх" читаємо потроху, щоб не перевантажити ШІ
        final_context += f"\n--- ФАЙЛ: {file} ---\n" + extract_text_from_pdf(file, max_pages=15)
else:
    final_context = extract_text_from_pdf(selected_option, max_pages=100)

final_context = final_context[:100000] # Ліміт символів для стабільності

# --- 6. ПОШУК З ЛУПОЮ ---
st.write("---")
# Створюємо дві колонки для поля та кнопки
col1, col2 = st.columns([0.85, 0.15])

with col1:
    user_query = st.text_input("Ваше питання (натисніть Enter або на лупу):", placeholder="Наприклад: Яка норма ширини колії?")

with col2:
    st.write("##") # Відступ для вирівнювання кнопки
    search_button = st.button("🔍")

# Умова запуску: натиснуто Enter АБО натиснуто кнопку з лупою
if (user_query or search_button) and final_context:
    if not user_query:
        st.warning("Спочатку впишіть питання у поле.")
    else:
        with st.spinner('ШІ аналізує документацію...'):
            try:
                # Налаштування стилю відповіді
                if answer_mode == "Стисла (головні тези)":
                    style_instr = "Надай дуже коротку відповідь українською, тільки факти та цифри."
                else:
                    style_instr = "Надай максимально повну відповідь українською, з цитатами, пунктами правил та деталями."

                prompt = f"""
                Ти технічний експерт. Використовуй цей текст:
                {final_context}
                
                ПИТАННЯ: {user_query}
                ІНСТРУКЦІЯ: {style_instr}
                """
                
                response = model.generate_content(prompt)
                st.subheader("Відповідь:")
                st.success(response.text)
                
                # Кнопка озвучки
                if st.button("🔊 Озвучити відповідь"):
                    with st.spinner('Генерую голос...'):
                        tts = gTTS(text=response.text, lang='uk')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.audio(fp, format="audio/mp3")
                        
            except Exception as e:
                st.error(f"Помилка ШІ: {e}")
