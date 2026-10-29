# app.py
import io
from datetime import date
import pandas as pd
import streamlit as st

from logic import build_report

# Настройка страницы (широкий формат)
st.set_page_config(page_title="Готовность объектов к СМР", page_icon="🏗️", layout="wide")

# Стилизация под скриншот (немного CSS)
st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }
    .card-green { background-color: #e6f4ea; border-left: 5px solid #1e8e3e; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .card-red { background-color: #fce8e6; border-left: 5px solid #d93025; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .tag { background-color: #f1f3f4; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 5px; border: 1px solid #dadce0; }
    .tag-red { background-color: #fce8e6; color: #d93025; border-color: #fad2cf; }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ Готовность объектов к стройке")
st.caption(f"Ежедневный отчет | Дата: {date.today().strftime('%d.%m.%Y')}")

uploaded = st.file_uploader("Загрузите Excel-файл реестра (.xlsx)", type=["xlsx"])

if not uploaded:
    st.info("⬆️ Загрузите файл, чтобы построить отчет.")
    st.stop()

try:
    df_raw = pd.read_excel(uploaded)
    report = build_report(df_raw)
except Exception as e:
    st.error(f"Ошибка чтения файла: {e}")
    st.stop()

# --- Фильтры (верхняя панель) ---
with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    
    regions = ["Все"] + list(report["Регион"].dropna().unique()) if "Регион" in report else ["Все"]
    managers = ["Все"] + list(report["Менеджер"].dropna().unique()) if "Менеджер" in report else ["Все"]
    
    sel_region = c1.selectbox("Регион", regions)
    sel_manager = c2.selectbox("Менеджер по развитию", managers)
    sel_status = c3.selectbox("Статус", ["Все", "Готовы к СМР", "Не готовы"])

# Применяем фильтры
filtered = report.copy()
if sel_region != "Все" and "Регион" in filtered:
    filtered = filtered[filtered["Регион"] == sel_region]
if sel_manager != "Все" and "Менеджер" in filtered:
    filtered = filtered[filtered["Менеджер"] == sel_manager]

# --- Сводка (Метрики) ---
total = len(filtered)
ready = len(filtered[filtered["Готов к СМР"] == "ДА"])
not_ready = total - ready
overdue = len(filtered[filtered["Просрочка"] > 0]) if "Просрочка" in filtered else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Активные объекты", total)
m2.metric("Готовы к СМР", ready)
m3.metric("Не готовы", not_ready)
m4.metric("Просрочен план СМР", overdue)

st.divider()

# --- Карточки ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 🟢 Готовы к СМР")
    ready_df = filtered[filtered["Готов к СМР"] == "ДА"]
    if ready_df.empty:
        st.write("Нет объектов")
    for _, row in ready_df.iterrows():
        code = row.get('Код', '')
        address = row.get('Адрес', '')
        manager = row.get('Менеджер', '')
        plan = row.get('План СМР', '')
        
        st.markdown(f"""
        <div class="card-green">
            <strong>{code} | {address}</strong><br>
            <span style="color:#5f6368; font-size:0.9em;">Менеджер: {manager}</span><br>
            <span style="font-size:0.8em; color:#5f6368;">План СМР: {plan}</span><br>
            <span class="tag" style="margin-top:10px; display:inline-block; background-color:#ceead6; color:#1e8e3e; border-color:#a8dab5;">Объект в работе — полностью готов</span>
        </div>
        """, unsafe_allow_html=True)

with col_right:
    st.markdown("### 🔴 Не готовы")
    not_ready_df = filtered[filtered["Готов к СМР"] == "НЕТ"]
    if not_ready_df.empty:
        st.write("Нет объектов")
    for _, row in not_ready_df.iterrows():
        code = row.get('Код', '')
        address = row.get('Адрес', '')
        manager = row.get('Менеджер', '')
        plan = row.get('План СМР', '')
        missing = row.get('Отсутствует', '')
        
        # Формируем красные теги для отсутствующих критериев
        tags_html = ""
        if missing and missing != "—":
            for tag in missing.split(", "):
                tags_html += f'<span class="tag tag-red">{tag}</span>'
        
        # Если есть просрочка, добавляем пометку
        overdue_html = ""
        if row.get('Просрочка', 0) > 0:
            overdue_html = f'<span class="tag" style="background-color:#fce8e6; color:#d93025; font-weight:bold;">Просрочка: {row["Просрочка"]} дн.</span>'

        st.markdown(f"""
        <div class="card-red">
            <strong>{code} | {address}</strong><br>
            <span style="color:#5f6368; font-size:0.9em;">Менеджер: {manager}</span><br>
            <span style="font-size:0.8em; color:#5f6368;">План СМР: {plan}</span><br>
            <div style="margin-top:10px;">{tags_html} {overdue_html}</div>
        </div>
        """, unsafe_allow_html=True)

# --- Экспорт ---
st.sidebar.header("📥 Экспорт данных")
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    filtered.to_excel(writer, sheet_name="Отчет", index=False)
buf.seek(0)

st.sidebar.download_button(
    "Скачать текущий отчет (.xlsx)",
    data=buf,
    file_name=f"Отчет_СМР_{date.today().isoformat()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)