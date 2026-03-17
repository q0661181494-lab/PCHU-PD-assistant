import streamlit as st
import google.generativeai as genai
import PyPDF2
import os
import random
import pandas as pd
import requests
import time
from datetime import datetime

# --- 0. ГЛОБАЛЬНА СТАТИСТИКА (СПІЛЬНА ДЛЯ ВСІХ ПРИСТРОЇВ) ---
@st.cache_resource
def get_global_stats():
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
                model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models
                return genai.GenerativeModel(model_name)
            except: continue 
    return None

model = get_working_model()

# --- 2. ІНТЕРФЕЙС ТА СЕКРЕТНИЙ SIDEBAR ---
st.set_page_config(page_title="Технічна бібліотека ст. Ворожба", layout="centered")

with st.sidebar:
    st.title("📂 Керування")
    st.markdown("<p style='color: gray; font-size: 0.8rem; margin-bottom: -15px;'>тільки для адміністратора</p>", unsafe_allow_html=True)
    admin_password = st.text_input("Додати файл інструкції (PDF):", type="password", placeholder="Виберіть файл...")
    
    if admin_password == "30033003": 
        st.success("Доступ до повної аналітики відкрито")
        if global_stats:
            df = pd.DataFrame(global_stats)
            st.subheader("📊 Детальна статистика")
            st.table(df[::-1]) # Останні запити зверху
            
            # Кнопка для завантаження повної бази в Excel-форматі
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Скачати повний звіт (Excel)",
                data=csv,
                file_name=f"pchu5_full_analytics_{datetime.now().strftime('%d_%m_%H%M')}.csv",
                mime="text/csv",
            )
            if st.button("🗑️ Очистити всю історію"):
                global_stats.clear()
                st.rerun()
        else:
            st.info("Запитів поки не зафіксовано.")

st.subheader("📚 РОЗУМНА ТЕХНІЧНА БІБЛІОТЕКА ПЧУ-5")

# --- 3. ЧИТАННЯ PDF ---
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

# --- 5. МЕНЮ ---
st.write("---")
selected_option = st.selectbox("Оберіть інструкцію:", available_files)
answer_mode = st.radio("Оберіть тип відповіді:", ["Стисла (головні тези)", "Розгорнута (детально)"], index=0, horizontal=True)

# --- 6. ПІДГОТОВКА ТЕКСТУ ---
final_context = extract_text_from_pdf(selected_option, max_pages=500)
final_context = final_context[:250000]

# --- 7. ПОШУК ---
st.write("---")
col1, col2 = st.columns([0.85, 0.15])
with col1:
    user_query = st.text_input("Пошук", placeholder="Напишіть ваше питання або Білет N...", label_visibility="collapsed")
with col2:
    search_button = st.button("🔍 Пошук")

# --- 8. ЛОГІКА ВІДПОВІДІ ТА МАКСИМАЛЬНА АНАЛІТИКА ---
if (user_query or search_button) and final_context:
    if not user_query.strip():
        st.warning("Введіть питання.")
    else:
        # 1. Збір гео-даних та провайдера
        city, region, provider = "Unknown", "Unknown", "Unknown"
        try:
            geo = requests.get('http://ip-api.com', timeout=1.5).json()
            city = geo.get('city', 'Unknown')
            region = geo.get('regionName', 'Unknown')
            provider = geo.get('isp', 'Unknown')
        except: pass

        # 2. Збір даних пристрою
        headers = st.context.headers
        ua = headers.get("User-Agent", "Unknown Device")
        
        # Спроба визначити ОС (спрощено)
        os_info = "Other"
        if "Android" in ua: os_info = "Android"
        elif "iPhone" in ua or "iPad" in ua: os_info = "iOS"
        elif "Windows" in ua: os_info = "Windows"
        
        current_time = datetime.now().strftime("%d.%m %H:%M:%S")
        start_process = time.time() # Засікаємо час обробки
        
        with st.spinner('ШІ аналізує документацію...'):
            try:
                style = "тези" if answer_mode == "Стисла (головні тези)" else "детально з пунктами правил"
                prompt = f"Контекст: {final_context}\n\nПитання: {user_query}\n\nІнструкція: {style}. Відповідай українською."
                
                response = model.generate_content(prompt)
                process_time = round(time.time() - start_process, 2) # Час у секундах
                
                st.subheader("Відповідь:")
                st.success(response.text)
                
                # Запис МАКСИМАЛЬНОЇ статистики
                global_stats.append({
                    "Дата/Час": current_time,
                    "Місто": city,
                    "Область": region,
                    "Провайдер": provider,
                    "ОС": os_info,
                    "Запит": user_query,
                    "Файл": selected_option[:20],
                    "Режим": answer_mode[:10],
                    "Час (сек)": process_time,
                    "Статус": "Успішно ✅"
                })
                
            except Exception as e:
                process_time = round(time.time() - start_process, 2)
                st.error(f"Помилка ШІ. Спробуйте ще раз.")
                global_stats.append({
                    "Дата/Час": current_time,
                    "Місто": city,
                    "Область": region,
                    "Провайдер": provider,
                    "ОС": os_info,
                    "Запит": user_query,
                    "Файл": selected_option[:20],
                    "Час (сек)": process_time,
                    "Статус": f"Помилка: {str(e)[:40]}"
                })
            
            # Обмеження історії (останні 500 запитів для стабільності пам'яті)
            if len(global_stats) > 500: global_stats.pop(0)

# --- 9. ПІДПИС ---
st.markdown("<br><hr><center><p style='color: gray;'>© 2026 Розробка: ПЧУ-5 Сергій ШИНКАРЕНКО</p></center>", unsafe_allow_html=True)
