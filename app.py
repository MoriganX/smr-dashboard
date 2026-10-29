# app.py
import io
from datetime import date
import pandas as pd
import streamlit as st

from logic import build_report

st.set_page_config(page_title="Готовность объектов к СМР", page_icon="🏗️", layout="wide")

# --- ТЕМНАЯ ТЕМА (CSS) ---
st.markdown("""
    <style>
    .card-green { background-color: #1a2e1f; border-left: 5px solid #2ecc71; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #e8f5e9; }
    .card-red { background-color: #2e1a1a; border-left: 5px solid #e74c3c; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #ffebee; }
    .tag { background-color: #2c2c2c; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-right: 5px; border: 1px solid #444; color: #ddd; display: inline-block; margin-top: 5px; }
    .tag-red { background-color: #3a1f1f; color: #ff8a80; border-color: #5a2a2a; }
    .tag-green { background-color: #1f3a24; color: #81c784; border-color: #2e5c38; }
    [data-testid="stMetricValue"] { color: #FAFAFA; }
    [data-testid="stMetricLabel"] { color: #b0b0b0; }
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

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    regions = ["Все"] + list(report["Регион"].dropna().unique()) if "Регион" in report else ["Все"]
    managers = ["Все"] + list(report["Менеджер"].dropna().unique()) if "Менеджер" in report else ["Все"]
    
    sel_region = c1.selectbox("Регион", regions)
    sel_manager = c2.selectbox("Менеджер по развитию", managers)
    sel_status = c3.selectbox("Статус", ["Все", "Готовы к СМР", "Не готовы"])

filtered = report.copy()
if sel_region != "Все" and "Регион" in filtered:
    filtered = filtered[filtered["Регион"] == sel_region]
if sel_manager != "Все" and "Менеджер" in filtered:
    filtered = filtered[filtered["Менеджер"] == sel_manager]

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

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 🟢 Готовы к СМР")
    ready_df = filtered[filtered["Готов к СМР"] == "ДА"]
    if ready_df.empty: st.write("Нет объектов")
    for _, row in ready_df.iterrows():
        code = row.get('Код', '')
        address = row.get('Адрес', '')
        manager = row.get('Менеджер', '')
        plan = row.get('План СМР', '')
        
        st.markdown(f"""
        <div class="card-green">
            <strong>{code} | {address}</strong><br>
            <span style="color:#a5d6a7; font-size:0.9em;">Менеджер: {manager}</span><br>
            <span style="font-size:0.8em; color:#81c784;">План СМР: {plan}</span><br>
            <span class="tag tag-green">Объект в работе — полностью готов</span>
        </div>
        """, unsafe_allow_html=True)

with col_right:
    st.markdown("### 🔴 Не готовы")
    not_ready_df = filtered[filtered["Готов к СМР"] == "НЕТ"]
    if not_ready_df.empty: st.write("Нет объектов")
    for _, row in not_ready_df.iterrows():
        code = row.get('Код', '')
        address = row.get('Адрес', '')
        manager = row.get('Менеджер', '')
        plan = row.get('План СМР', '')
        missing = row.get('Отсутствует', '')
        
        tags_html = ""
        if missing and missing != "—":
            for tag in missing.split(", "):
                tags_html += f'<span class="tag tag-red">{tag}</span>'
        
        overdue_html = ""
        if row.get('Просрочка', 0) > 0:
            overdue_html = f'<span class="tag tag-red" style="font-weight:bold;">Просрочка: {row["Просрочка"]} дн.</span>'

        st.markdown(f"""
        <div class="card-red">
            <strong>{code} | {address}</strong><br>
            <span style="color:#ef9a9a; font-size:0.9em;">Менеджер: {manager}</span><br>
            <span style="font-size:0.8em; color:#e57373;">План СМР: {plan}</span><br>
            <div style="margin-top:10px;">{tags_html} {overdue_html}</div>
        </div>
        """, unsafe_allow_html=True)

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