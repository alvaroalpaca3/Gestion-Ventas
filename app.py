import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import time
import plotly.express as px

# --- 1. CONEXIÓN SEGURA ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        return gspread.authorize(creds).open("GestionDiaria")
    except: return None

@st.cache_data(ttl=30) # Cache corto para pruebas
def cargar_datos():
    doc = conectar_google()
    if not doc: return pd.DataFrame(), pd.DataFrame()
    
    # Carga Estructura
    try:
        ws_est = doc.worksheet("Estructura")
        df_est = pd.DataFrame(ws_est.get_all_values()[1:], columns=ws_est.get_all_values()[0])
        df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(8)
    except: df_est = pd.DataFrame()

    # Carga Registros
    try:
        ws_reg = doc.sheet1
        df_reg = pd.DataFrame(ws_reg.get_all_records())
        df_reg.columns = [c.strip().upper() for c in df_reg.columns]
    except: df_reg = pd.DataFrame()
        
    return df_est, df_reg

st.set_page_config(page_title="Gestión de Ventas v2", layout="wide")
df_maestro, df_registros = cargar_datos()

# --- SIDEBAR ---
st.sidebar.title("👤 Identificación")
dni_input = st.sidebar.text_input("DNI VENDEDOR", max_chars=8)
dni_clean = "".join(filter(str.isdigit, dni_input)).zfill(8)

vendedor = df_maestro[df_maestro['DNI'] == dni_clean] if not df_maestro.empty else pd.DataFrame()

if not vendedor.empty and len(dni_input) == 8:
    sup_fijo = vendedor.iloc[0]['SUPERVISOR']
    nom_v = vendedor.iloc[0]['NOMBRE VENDEDOR']
    st.sidebar.success(f"✅ {nom_v}")
else:
    sup_fijo = "N/A"; nom_v = "N/A"

# --- TABS ---
t1, t2 = st.tabs(["📝 REGISTRO", "📊 DASHBOARD"])

with t1:
    # (Aquí va tu formulario que ya funciona perfectamente)
    st.info("Complete los datos de la gestión diaria.")
    # ... código del formulario ...

with t2:
    st.title("Dashboard de Resultados")
    if df_registros.empty:
        st.warning("No hay datos en Sheet1 para mostrar gráficos.")
    else:
        # PROTECCIÓN LÍNEA 110: Verificamos si existe la columna
        col_busqueda = "SUPERVISOR"
        if col_busqueda in df_registros.columns:
            f_sup = st.multiselect("Filtrar por Supervisor", options=df_registros[col_busqueda].unique())
            
            df_f = df_registros.copy()
            if f_sup: df_f = df_f[df_f[col_busqueda].isin(f_sup)]
            
            # Gráfico Seguro
            fig = px.pie(df_f, names=df_f.columns[5], title="Mix de Gestiones") # Columna 5 suele ser DETALLE
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"No se encontró la columna '{col_busqueda}' en el Excel.")
