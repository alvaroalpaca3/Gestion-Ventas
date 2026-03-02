import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import time
import plotly.express as px
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Comercial Dimiare", layout="wide")

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("GestionDiaria")
    except Exception as e:
        st.error("⚠️ Error de enlace: Revisa las credenciales en st.secrets y permisos del Excel.")
        return None

@st.cache_data(ttl=60)
def cargar_datos():
    doc = conectar_google()
    if not doc: return pd.DataFrame(), pd.DataFrame()
    
    # Cargar Maestro (Estructura de Vendedores)
    try:
        ws_est = doc.worksheet("Estructura")
        lista_est = ws_est.get_all_values()
        df_est = pd.DataFrame(lista_est[1:], columns=lista_est[0])
        # Tratamos el DNI del Excel como texto puro
        df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
    except: df_est = pd.DataFrame()

    # Cargar Registros (Base de Datos)
    try:
        ws_reg = doc.sheet1
        df_reg = pd.DataFrame(ws_reg.get_all_records())
        df_reg.columns = [str(c).strip().upper() for c in df_reg.columns]
    except: df_reg = pd.DataFrame()
        
    return df_est, df_reg

# --- 3. INICIALIZACIÓN DE VARIABLES DE SESIÓN ---
if 'nom_v' not in st.session_state: st.session_state.nom_v = "N/A"
if 'zon_v' not in st.session_state: st.session_state.zon_v = "N/A"
if 'sup_v' not in st.session_state: st.session_state.sup_v = "N/A"
if 'dni_clean' not in st.session_state: st.session_state.dni_clean = ""
if 'form_key' not in st.session_state: st.session_state.form_key = 0

# Carga inicial de datos
df_maestro, df_registros = cargar_datos()

# --- 4. BARRA LATERAL (ACCESO) ---
st.sidebar.markdown("<h2 style='text-align: center; color: #1E3A8A;'>DIAMIRE</h2>", unsafe_allow_html=True)
st.sidebar.title("👤 Acceso Vendedor")

dni_input = st.sidebar.text_input("DNI / CE VENDEDOR", max_chars=9)
dni_digits = "".join(filter(str.isdigit, dni_input))

if len(dni_digits) >= 7:
    # Quitamos ceros a la izquierda para comparar con el Maestro
    dni_busqueda = dni_digits.lstrip('0')
    
    if not df_maestro.empty:
        # Normalizamos columna DNI del Maestro para match
        df_maestro['DNI_MATCH'] = df_maestro['DNI'].astype(str).str.lstrip('0')
        vendedor_data = df_maestro[df_maestro['DNI_MATCH'] == dni_busqueda]
        
        if not vendedor_data.empty:
            st.session_state.nom_v = vendedor_data.iloc[0]['NOMBRE VENDEDOR']
            st.session_state.zon_v = vendedor_data.iloc[0]['ZONAL']
            st.session_state.sup_v = vendedor_data.iloc[0]['SUPERVISOR']
            st.session_state.dni_clean = dni_input # Guardamos el original con sus ceros
            st.sidebar.success(f"✅ Bienvenido: {st.session_state.nom_v}")
        else:
            st.session_state.nom_v = "N/A"
            st.sidebar.error("❌ Documento no encontrado")
else:
    st.session_state.nom_v = "N/A"

# Asignación local para evitar NameError en todo el script
nom_v = st.session_state.nom_v
zon_v = st.session_state.zon_v
sup_v = st.session_state.sup_v
dni_clean = st.session_state.dni_clean

st.sidebar.caption("©2026 by Dubby System SA")

# --- 5. CUERPO PRINCIPAL ---
st.header("📊 GESTIÓN COMERCIAL")
tab1, tab_personal, tab2 = st.tabs(["📝 REGISTRO", "📈 MI PROGRESO", "🔐 ADMIN"])

# --- PESTAÑA 1: FORMULARIO ---
with tab1:
    if nom_v == "N/A":
        st.info("👈 Por favor, ingresa tu DNI en la barra lateral para habilitar el formulario.")
    else:
        st.markdown(f"#### 📝 Registro para: **{nom_v}** ({zon_v})")
        detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
        
        with st.form(key=f"registro_form_{st.session_state.form_key}"):
            # Inicializamos todos los campos en N/A
            t_op = n_cl = d_cl = dir_ins = mail = c1 = prod = c_fe = n_ped = pil = m_nv = n_ref = c_ref = "N/A"

            if detalle == "NO-VENTA":
                opciones_nv = ["COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "YA TIENE SERVICIO"]
                m_nv = st.selectbox("MOTIVO DE NO-VENTA *", options=opciones_nv, index=None, placeholder="Elija un motivo...")
                st.info("💡 Solo debe llenar el motivo. Sus datos se guardarán automáticamente.")
            
            elif detalle == "REFERIDO":
                n_ref = st.text_input("Nombre del Referido *").upper()
                c_ref = st.text_input("Contacto Referido (9 dígitos) *", max_chars=9)
            
            elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"]:
                ca, cb = st.columns(2)
                with ca:
                    n_cl = st.text_input("Nombre Cliente *").upper()
                    d_cl = st.text_input("DNI Cliente *", max_chars=8)
                    t_op = st.selectbox("Operación *", ["CAPTACIÓN", "MIGRACIÓN", "COMPLETA TV", "COMPLETA BA", "COMPLETA MT"])
                    prod = st.selectbox("Producto *", ["NAKED", "DUO INT + TV", "DUO BA", "DUO TV", "TRIO"])
                    pil = st.radio("Piloto?", ["NO", "SI"], horizontal=True)
                with cb:
                    dir_ins = st.text_input("Dirección *").upper()
                    c1 = st.text_input("Celular 1 *", max_chars=9)
                    n_ped = st.text_input("N° Orden *", max_chars=10)
                    mail = st.text_input("Email *")
                    c_fe = st.text_input("Código FE *", max_chars=13)

            submit = st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True)

            if submit:
                error = False
                # Validaciones
                if detalle == "SELECCIONA":
                    st.error("❌ Elija un tipo de gestión.")
                    error = True
                elif detalle == "NO-VENTA" and m_nv is None:
                    st.error("❌ Debe elegir un motivo.")
                    error = True
                elif detalle == "REFERIDO" and (not n_ref or len(c_ref) < 9):
                    st.error("❌ Complete los datos del referido.")
                    error = True
                elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"] and (not n_cl or len(d_cl) < 8 or not n_ped):
                    st.error("❌ Complete todos los campos marcados con (*).")
                elif len(d_cl) < 8:
                    st.error("❌ Error: El DNI debe tener 8 dígitos.")
                    error = True
                elif len(c1) != 9 or not c1.isdigit():
                    st.error("❌ Error: El celular debe tener 9 dígitos numéricos.")
                    error = True
                elif len(n_ped) != 10 or not n_ped.isdigit():
                    st.error("❌ Error: El N° de Pedido debe tener 10 dígitos.")
                    error = True
                elif len(c_fe) != 13:
                    st.error("❌ Error: El código FE debe tener exactamente 13 caracteres.")
                    error = True
                elif detalle == "REFERIDO" and (not n_ref.strip() or len(c_ref) != 9 or not c_ref.isdigit()):
                    st.error("❌ Error: El Celular del Referido debe tener exactamente 9 DÍGITOS NUMÉRICOS.")
                    error = True
                elif detalle == "NO-VENTA" and m_nv is None:
                    st.error("❌ Error: Seleccione el motivo de No-Venta.")
                    error = True    
                    
                if not error:
                    try:
                        tz = pytz.timezone('America/Lima')
                        ahora = datetime.now(tz)
                        # Armado de fila para Google Sheets
                        fila = [
                            ahora.strftime("%d/%m/%Y %H:%M:%S"), 
                            zon_v, 
                            f"'{dni_clean}", # Forzamos texto con apóstrofe
                            nom_v, 
                            sup_v, 
                            detalle, 
                            t_op, n_cl, f"'{d_cl}", dir_ins, mail, f"'{c1}", "N/A", 
                            prod, c_fe, f"'{n_ped}", pil, m_nv, n_ref, f"'{c_ref}", 
                            ahora.strftime("%d/%m/%Y"), ahora.strftime("%H")
                        ]
                        
                        conectar_google().sheet1.append_row(fila, value_input_option='USER_ENTERED')
                        st.cache_data.clear()
                        st.success("✅ ¡Registro guardado exitosamente!")
                        time.sleep(1)
                        st.session_state.form_key += 1
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al conectar con la base: {e}")

# --- PESTAÑA 2: MI PROGRESO ---
with tab_personal:
    if nom_v != "N/A" and not df_registros.empty:
        df_mio = df_registros[df_registros["NOMBRE VENDEDOR"].astype(str).str.strip() == nom_v].copy()
        if not df_mio.empty:
            st.subheader(f"Resumen de: {nom_v}")
            st.dataframe(df_mio.tail(10), use_container_width=True, hide_index=True)
        else:
            st.info("No tienes registros aún.")
    else:
        st.warning("Ingrese su DNI para ver su progreso.")

# --- PESTAÑA 3: ADMIN ---
with tab2:
    st.markdown("##### 🔐 Acceso Administrador")
    user = st.text_input("Usuario", key="adm_u")
    pws = st.text_input("Contraseña", type="password", key="adm_p")
    
    if user == "admin" and pws == "Diamire2026*":
        st.success("Acceso concedido")
        if not df_registros.empty:
            st.dataframe(df_registros, use_container_width=True)
