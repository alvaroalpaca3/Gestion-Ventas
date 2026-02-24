import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import time
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Comercial Dimiare", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds).open("GestionDiaria")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

@st.cache_data(ttl=60)
def cargar_datos():
    doc = conectar_google()
    if not doc: return pd.DataFrame(), pd.DataFrame()
    
    # Cargar Estructura (Vendedores)
    try:
        ws_est = doc.worksheet("Estructura")
        df_est = pd.DataFrame(ws_est.get_all_values()[1:], columns=ws_est.get_all_values()[0])
        df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(8)
    except: df_est = pd.DataFrame()

    # Cargar Registros (Sheet1)
    try:
        ws_reg = doc.sheet1
        df_reg = pd.DataFrame(ws_reg.get_all_records())
        df_reg.columns = [str(c).strip().upper() for c in df_reg.columns]
    except: df_reg = pd.DataFrame()
        
    return df_est, df_reg

# --- INICIO ---
df_maestro, df_registros = cargar_datos()
if "form_key" not in st.session_state: st.session_state.form_key = 0

# --- SIDEBAR: ACCESO ---
st.sidebar.title("👤 Acceso Vendedor")
dni_input = st.sidebar.text_input("DNI VENDEDOR", max_chars=8)
dni_clean = "".join(filter(str.isdigit, dni_input)).zfill(8)

vendedor = df_maestro[df_maestro['DNI'] == dni_clean] if not df_maestro.empty else pd.DataFrame()

if not vendedor.empty and len(dni_input) == 8:
    nom_v = vendedor.iloc[0]['NOMBRE VENDEDOR']
    sup_v = vendedor.iloc[0]['SUPERVISOR']
    zon_v = vendedor.iloc[0]['ZONAL']
    st.sidebar.success(f"✅ {nom_v}")
    st.sidebar.info(f"Zonal: {zon_v}")
else:
    nom_v = sup_v = zon_v = "N/A"

# --- TABS ---
tab1, tab2 = st.tabs(["📝 REGISTRO", "📊 DASHBOARD"])

with tab1:
    detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
    
    with st.form(key=f"f_{st.session_state.form_key}"):
        # Variables iniciales (22 columnas alineadas con tu Excel)
        t_op = n_cl = d_cl = dir_ins = mail = c1 = c2 = prod = c_fe = n_ped = pil = m_nv = n_ref = c_ref = "N/A"

        if detalle == "NO-VENTA":
            m_nv = st.selectbox("MOTIVO DE NO VENTA *", ["SELECCIONA", "COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "YA TIENE SERVICIO"])
            st.info("💡 Solo llena el motivo. DNI y Zonal se vinculan automáticamente.")
        
        elif detalle == "REFERIDO":
            n_ref = st.text_input("Nombre y Apellido del Referido *").upper()
            c_ref = st.text_input("N° de Contacto Referido (9 dígitos) *", max_chars=9)
            if c_ref and (not c_ref.isdigit() or len(c_ref) != 9):
                st.warning("⚠️ El número debe tener 9 dígitos numéricos.")
            
        elif detalle != "SELECCIONA":
            col_a, col_b = st.columns(2)
            with col_a:
                n_cl = st.text_input("Nombre de Cliente *").upper()
                d_cl = st.text_input("DNI/RUC Cliente *")
                t_op = st.selectbox("Tipo de Operación *", ["CAPTACIÓN", "MIGRACIÓN", "ALTA"])
                prod = st.selectbox("Producto *", ["BA", "DUO", "TRIO"])
            with col_b:
                dir_ins = st.text_input("Dirección de Instalación *").upper()
                c1 = st.text_input("N° Contacto 1 (9 dígitos) *", max_chars=9)
                c2 = st.text_input("N° Contacto 2")
                n_ped = st.text_input("N° de Pedido")
                mail = st.text_input("Email Cliente")
                c_fe = st.text_input("Código FE")
                pil = st.radio("¿Venta Piloto?", ["NO", "SI"], horizontal=True)

        if st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True):
            # VALIDACIONES
            error = False
            if nom_v == "N/A":
                st.error("❌ Identifícate con tu DNI en el panel izquierdo.")
                error = True
            elif detalle == "SELECCIONA":
                st.error("❌ Selecciona un Detalle de Gestión.")
                error = True
            elif detalle == "NO-VENTA" and m_nv == "SELECCIONA":
                st.error("❌ Selecciona el motivo de la no venta.")
                error = True
            elif detalle == "REFERIDO" and (not n_ref or len(c_ref) != 9 or not c_ref.isdigit()):
                st.error("❌ Nombre de referido y número de 9 dígitos son obligatorios.")
                error = True
            elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"] and (not n_cl or not d_cl or len(c1) != 9):
                st.error("❌ Datos de cliente y celular de 9 dígitos son obligatorios.")
                error = True

            if not error:
                try:
                    tz = pytz.timezone('America/Lima')
                    ahora = datetime.now(tz)
                    fila = [
                        ahora.strftime("%d/%m/%Y %H:%M:%S"), # Marca temporal
                        zon_v, f"'{dni_clean}", nom_v, sup_v, # Datos Vendedor
                        detalle, t_op, n_cl, f"'{d_cl}", # Gestión y Cliente
                        dir_ins, mail, f"'{c1}", f"'{c2}", # Contactos
                        prod, c_fe, f"'{n_ped}", pil, # Producto y Pedido
                        m_nv, n_ref, f"'{c_ref}", # No Venta y Referidos
                        ahora.strftime("%d/%m/%Y"), ahora.strftime("%H:%M:%S") # Fecha y Hora
                    ]
                    conectar_google().sheet1.append_row(fila, value_input_option='USER_ENTERED')
                    st.success("✅ ¡Registrado con éxito!")
                    time.sleep(1)
                    st.session_state.form_key += 1
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

with tab2:
    st.header("Análisis de Ventas")
    if df_registros.empty:
        st.info("Sin datos para mostrar.")
    else:
        c_det = "DETALLE" if "DETALLE" in df_registros.columns else df_registros.columns[5]
        col1, col2 = st.columns(2)
        col1.metric("Total Gestiones", len(df_registros))
        col2.metric("Ventas Fijas", len(df_registros[df_registros[c_det] == "VENTA FIJA"]))
        st.plotly_chart(px.pie(df_registros, names=c_det, title="Distribución de Gestiones", hole=0.4), use_container_width=True)
