import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
from datetime import datetime

# --- 0. СПІЛЬНА ПАМ'ЯТЬ ДЛЯ ВСІХ КОРИСТУВАЧІВ (ГЛОБАЛЬНА СТАТИСТИКА) ---
@st.cache_resource
def get_global_stats():
    # Цей список зберігається на сервері та доступний всім пристроям одночасно
    return []

global_stats = get_global_stats()

# --- 1. ПІДКЛЮЧЕННЯ ШІ (РОТАЦІЯ КЛЮЧІВ) ---
def get_working_model():
    key_names = ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]
    random.shuffle(key_names)
    for name in key_names:
        if name in st.secrets:
            try:
                api_key = st.secrets[name]
                genai.configure(api_key=api_key)
                
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                
                return genai.GenerativeModel(model_name)
            except Exception:
                continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ТА СЕКРЕТНИЙ SIDEBAR ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")

with st.sidebar:
    st.title("📂 Керування")
    
    # Сіра помітка над полем пароля
    st.markdown("<p style='color: gray; font-size: 0.8rem; margin-bottom: -15px;'>тільки для адміністратора</p>", unsafe_allow_html=True)
    
    # Поле пароля, замасковане під завантаження файлу
    admin_password = st.text_input("Додати файл інструкції (PDF):", type="password", placeholder="Виберіть файл...")
    
    # ПЕРЕВІРКА ПАРОЛЯ (30033003)
    if admin_password == "30033003": 
        st.success("Доступ до спільної статистики відкрито")
        st.subheader("📊 Запити з усіх пристроїв")
        if global_stats:
            # Вивід таблиці (свіжі запити зверху)
            st.table(global_stats[::-1])
            if st.button("🗑️ Очистити історію для всіх"):
                global_stats.clear()
                st.rerun()
        else:
            st.info("Запитів поки не зафіксовано.")

st.subheader("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

if not model:
    st.error("❌ Не вдалося підключитися до ШІ. Перевірте ключі в Secrets.")
    st.stop()

# --- 3. ФУНКЦІЯ ЧИТАННЯ PDF ---
def extract_text_from_pdf(file_path, max_pages=500):
    text = ""
    try:
        if not os.path.exists(file_path): return ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages[:max_pages]:
                t = page.extract_text()
                if t: text += t + "\n"
        return text
    except: return ""

# --- 4. ЗБІР ФАЙЛІВ ---
available_files = sorted([f for f in os.listdir(".") if f.endswith(".pdf")])
if not available_files:
    st.warning("⚠️ Файли .pdf не знайдені.")
    st.stop()

# --- 5. НАЛАШТУВАННЯ ПОШУКУ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла (головні тези)", "Розгорнута (детально)"], index=0, horizontal=True)

# --- 6. ПІДГОТОВКА ТЕКСТУ (ОПТИМІЗОВАНО) ---
final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000]

# --- 7. ПОШУК З ЛУПОЮ ---
st.write("---")
col1, col2 = st.columns([0.85, 0.15])
with col1:
    user_query = st.text_input("Пошук", placeholder="Напишіть ваше питання або Білет N...", label_visibility="collapsed")
with col2:
    search_button = st.button("🔍 Пошук")

# --- 8. ЛОГІКА ВІДПОВІДІ ТА ЗАПИС СТАТИСТИКИ ---
if (user_query or search_button) and final_context:
    if not user_query.strip():
        st.warning("Введіть питання.")
    else:
        # Збір технічних даних
        headers = st.context.headers
        user_agent = headers.get("User-Agent", "Unknown Device")
        current_time = datetime.now().strftime("%d.%m %H:%M")
        
        with st.spinner('ШІ аналізує документацію...'):
            try:
                style = "тези" if answer_mode == "Стисла (головні тези)" else "детально з пунктами правил"
                prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
                
                response = model.generate_content(prompt)
                st.subheader("Відповідь:")
                st.success(response.text)
                
                # ЗАПИС У СПІЛЬНУ ТАБЛИЦЮ (Sidebar)
                global_stats.append({
                    "Час": current_time,
                    "Пристрій": user_agent[:25],
                    "Файл": selected_option[:15],
                    "Запит": user_query
                })
                
                # Обмеження списку (останні 100 запитів), щоб не перевантажувати сервер
                if len(global_stats) > 100:
                    global_stats.pop(0)
                
                # Також дублюємо в стандартні Logs для надійності
                print(f"GLOBAL LOG | {current_time} | {user_query}")
                
            except Exception as e:
                st.error(f"Вибачте, виникла помилка. Спробуйте ще раз за хвилину.")
                print(f"ERROR | {current_time} | {str(e)}")

# --- 9. ПІДПИС РОЗРОБНИКА ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
