import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import time
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Dimiare v2", layout="wide")

# --- CONEXIÓN MEJORADA ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("GestionDiaria")
    except Exception as e:
        # Si sale <Response [200]>, imprimimos un mensaje más claro
        st.error(f"Error de acceso: Verifica que el archivo se llame 'GestionDiaria' y que el email de la cuenta de servicio sea Editor.")
        return None

@st.cache_data(ttl=60)
def cargar_datos():
    doc = conectar_google()
    if not doc: 
        return pd.DataFrame(), pd.DataFrame()
    
    # Cargar Estructura
    try:
        ws_est = doc.worksheet("Estructura")
        lista_est = ws_est.get_all_values()
        if len(lista_est) > 1:
            df_est = pd.DataFrame(lista_est[1:], columns=lista_est[0])
            df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(8)
        else:
            df_est = pd.DataFrame()
    except:
        df_est = pd.DataFrame()

    # Cargar Registros (Sheet1)
    try:
        ws_reg = doc.sheet1
        data = ws_reg.get_all_records()
        df_reg = pd.DataFrame(data)
        df_reg.columns = [str(c).strip().upper() for c in df_reg.columns]
    except:
        df_reg = pd.DataFrame()
        
    return df_est, df_reg

# --- INICIO DE LÓGICA ---
df_maestro, df_registros = cargar_datos()
if "form_key" not in st.session_state: 
    st.session_state.form_key = 0

# --- SIDEBAR: IDENTIFICACIÓN ---
st.sidebar.title("👤 Acceso Vendedor")
dni_input = st.sidebar.text_input("INGRESE SU DNI", max_chars=8)
dni_clean = "".join(filter(str.isdigit, dni_input)).zfill(8)

vendedor = df_maestro[df_maestro['DNI'] == dni_clean] if not df_maestro.empty else pd.DataFrame()

if not vendedor.empty and len(dni_input) == 8:
    nom_v = vendedor.iloc[0]['NOMBRE VENDEDOR']
    sup_v = vendedor.iloc[0]['SUPERVISOR']
    zon_v = vendedor.iloc[0]['ZONAL']
    st.sidebar.success(f"Bienvenido: {nom_v}")
else:
    nom_v = sup_v = zon_v = "N/A"

# --- CUERPO PRINCIPAL ---
tab1, tab2 = st.tabs(["📝 REGISTRO", "📊 DASHBOARD"])

with tab1:
    detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
    
    with st.form(key=f"f_{st.session_state.form_key}"):
        # Inicializamos las 22 columnas
        t_op = n_cl = d_cl = dir_ins = mail = c1 = c2 = prod = c_fe = n_ped = pil = m_nv = n_ref = c_ref = "N/A"

        if detalle == "NO-VENTA":
            m_nv = st.selectbox("MOTIVO DE NO VENTA *", ["SELECCIONA", "COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "YA TIENE SERVICIO"])
            st.info("💡 Solo llena el motivo. DNI y Zonal se guardan automáticamente.")
        
        elif detalle == "REFERIDO":
            n_ref = st.text_input("Nombre del Referido *").upper()
            c_ref = st.text_input("Contacto Referido (9 dígitos) *", max_chars=9)
            
        elif detalle != "SELECCIONA":
            c_a, c_b = st.columns(2)
            with c_a:
                n_cl = st.text_input("Nombre Cliente *").upper()
                d_cl = st.text_input("DNI/RUC Cliente *")
                t_op = st.selectbox("Operación *", ["CAPTACIÓN", "MIGRACIÓN", "ALTA"])
                prod = st.selectbox("Producto *", ["BA", "DUO", "TRIO"])
            with c_b:
                dir_ins = st.text_input("Dirección *").upper()
                c1 = st.text_input("Celular 1 (9 dígitos) *", max_chars=9)
                c2 = st.text_input("Celular 2")
                n_ped = st.text_input("N° Pedido")
                mail = st.text_input("Email")
                c_fe = st.text_input("Código FE")
                pil = st.radio("Piloto?", ["NO", "SI"], horizontal=True)

        if st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True):
            # Validaciones de seguridad
            if nom_v == "N/A":
                st.error("❌ DNI no reconocido.")
            elif detalle == "REFERIDO" and (len(c_ref) != 9 or not c_ref.isdigit()):
                st.error("❌ El contacto del referido debe tener 9 dígitos.")
            elif detalle == "VENTA FIJA" and (len(c1) != 9 or not c1.isdigit()):
                st.error("❌ El celular 1 debe tener 9 dígitos.")
            elif detalle == "SELECCIONA":
                st.error("❌ Seleccione un tipo de gestión.")
            else:
                try:
                    tz = pytz.timezone('America/Lima')
                    ahora = datetime.now(tz)
                    fila = [
                        ahora.strftime("%d/%m/%Y %H:%M:%S"), zon_v, f"'{dni_clean}", nom_v, sup_v,
                        detalle, t_op, n_cl, f"'{d_cl}", dir_ins, mail, f"'{c1}", f"'{c2}",
                        prod, c_fe, f"'{n_ped}", pil, m_nv, n_ref, f"'{c_ref}",
                        ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S")
                    ]
                    conectar_google().sheet1.append_row(fila, value_input_option='USER_ENTERED')
                    st.success("✅ Guardado correctamente.")
                    time.sleep(1)
                    st.session_state.form_key += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

with tab2:
    st.header("Dashboard de Gestión")
    if df_registros.empty:
        st.info("No hay datos para mostrar gráficos aún.")
    else:
        # Gráfico simple de torta
        col_busqueda = "DETALLE" if "DETALLE" in df_registros.columns else df_registros.columns[5]
        fig = px.pie(df_registros, names=col_busqueda, title="Resumen de Gestiones")
        st.plotly_chart(fig, use_container_width=True)

