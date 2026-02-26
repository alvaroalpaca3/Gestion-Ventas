import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import time
import plotly.express as px
import os
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
        st.error("⚠️ Error de enlace: Revisa las credenciales en st.secrets.")
        return None

@st.cache_data(ttl=60)
def cargar_datos():
    doc = conectar_google()
    if not doc: return pd.DataFrame(), pd.DataFrame()
    
    try:
        ws_est = doc.worksheet("Estructura")
        lista_est = ws_est.get_all_values()
        df_est = pd.DataFrame(lista_est[1:], columns=lista_est[0])
        df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(8)
    except: df_est = pd.DataFrame()

    try:
        ws_reg = doc.sheet1
        df_reg = pd.DataFrame(ws_reg.get_all_records())
        # Normalizamos encabezados a mayúsculas y sin espacios
        df_reg.columns = [str(c).strip().upper() for c in df_reg.columns]
    except: df_reg = pd.DataFrame()
        
    return df_est, df_reg

# --- 3. INICIALIZACIÓN ---
df_maestro, df_registros = cargar_datos()
if "form_key" not in st.session_state: st.session_state.form_key = 0

# --- 4. BARRA LATERAL ---
st.sidebar.markdown("<h2 style='text-align: center; color: #1E3A8A;'>DIAMIRE</h2>", unsafe_allow_html=True)

st.sidebar.title("👤 Acceso Vendedor")
dni_input = st.sidebar.text_input("DNI VENDEDOR", max_chars=8)
dni_clean = "".join(filter(str.isdigit, dni_input)).zfill(8)

vendedor = df_maestro[df_maestro['DNI'] == dni_clean] if not df_maestro.empty else pd.DataFrame()

if not vendedor.empty and len(dni_input) == 8:
    nom_v = vendedor.iloc[0]['NOMBRE VENDEDOR']
    sup_v = vendedor.iloc[0]['SUPERVISOR']
    zon_v = vendedor.iloc[0]['ZONAL']
    st.sidebar.success(f"Bienvenido: {nom_v}")
else:
    nom_v = sup_v = zon_v = "N/A"

st.sidebar.write("")
st.sidebar.caption("©2026 Todos los derechos reservados")
st.sidebar.caption("by Dubby System SAC")

# --- 5. CUERPO PRINCIPAL ---
st.header("📊 SISTEMA DE GESTIÓN COMERCIAL")
tab1, tab_personal, tab2 = st.tabs(["📝 REGISTRO", "📈 MI PROGRESO", "📊 DASHBOARD ADMIN"])

# --- PESTAÑA 1: REGISTRO (CON TODAS TUS VALIDACIONES) ---
with tab1:
    st.markdown("#### 📝 INGRESO DE GESTIÓN")
    detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
    
    with st.form(key=f"registro_form_{st.session_state.form_key}"):
        t_op = n_cl = d_cl = dir_ins = mail = c1 = prod = c_fe = n_ped = pil = m_nv = n_ref = c_ref = "N/A"

        if detalle == "NO-VENTA":
            m_nv = st.selectbox("MOTIVO DE NO VENTA *", ["SELECCIONA", "COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "YA TIENE SERVICIO"])
            st.info("💡 Solo debe llenar el motivo. DNI y Zonal se guardan automáticamente.")
        
        elif detalle == "REFERIDO":
            n_ref = st.text_input("Nombre del Referido *").upper()
            c_ref = st.text_input("Contacto Referido (9 dígitos) *", max_chars=9)
            
        elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"]:
            ca, cb = st.columns(2)
            with ca:
                n_cl = st.text_input("Nombre Cliente *").upper()
                d_cl = st.text_input("DNI Cliente *", max_chars=8)
                t_op = st.selectbox("Operación *", ["SELECCIONA", "CAPTACIÓN", "MIGRACIÓN", "COMPLETA TV", "COMPLETA BA", "COMPLETA MT"])
                prod = st.selectbox("Producto *", ["SELECCIONA", "NAKED", "DUO INT + TV", "DUO BA", "DUO TV", "TRIO"])
                pil = st.radio("Piloto?", ["NO", "SI"], horizontal=True)
            with cb:
                dir_ins = st.text_input("Dirección *").upper()
                c1 = st.text_input("Celular 1 *", max_chars=9)
                n_ped = st.text_input("N° Pedido *", max_chars=10)
                mail = st.text_input("Email *")
                c_fe = st.text_input("Código FE *", max_chars=13)

        submit = st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True)

        if submit:
            error = False
            if nom_v == "N/A":
                st.error("❌ Acceso denegado: Ingrese su DNI en la barra lateral.")
                error = True
            elif detalle == "SELECCIONA":
                st.error("❌ Seleccione un tipo de gestión.")
                error = True
            elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"]:
                if any(x == "SELECCIONA" or not str(x).strip() for x in [n_cl, d_cl, dir_ins, c1, n_ped, mail, c_fe, t_op, prod]):
                    st.error("❌ Error: Todos los campos marcados con (*) son obligatorios.")
                    error = True
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
            elif detalle == "REFERIDO" and (not n_ref.strip() or len(c_ref) != 9):
                st.error("❌ Error: Nombre y Celular del Referido (9 dígitos) son obligatorios.")
                error = True
            elif detalle == "NO-VENTA" and m_nv == "SELECCIONA":
                st.error("❌ Error: Seleccione el motivo de No-Venta.")
                error = True

            if not error:
                try:
                    tz = pytz.timezone('America/Lima')
                    ahora = datetime.now(tz)
                    fila = [ahora.strftime("%d/%m/%Y %H:%M:%S"), zon_v, f"'{dni_clean}", nom_v, sup_v, detalle, t_op, n_cl, f"'{d_cl}", dir_ins, mail, f"'{c1}", "N/A", prod, c_fe, f"'{n_ped}", pil, m_nv, n_ref, f"'{c_ref}", ahora.strftime("%d/%m/%Y"), ahora.strftime("%H")]
                    conectar_google().sheet1.append_row(fila, value_input_option='USER_ENTERED')
                    st.cache_data.clear()
                    st.success("✅ ¡Guardado!")
                    time.sleep(1)
                    st.session_state.form_key += 1
                    st.rerun()
                except Exception as e: st.error(f"Error al guardar: {e}")

# --- PESTAÑA 2: MI PROGRESO (CON CORRECCIÓN DE KEYERROR) ---
with tab_personal:
    if nom_v == "N/A":
        st.warning("👈 Ingrese su DNI en la barra lateral para ver su actividad personal.")
    else:
        st.subheader(f"📈 Resumen: {nom_v}")
        
        if not df_registros.empty:
            # Corrección del Error: Buscamos la columna de DNI de forma segura
            col_dni_busqueda = [c for c in df_registros.columns if 'DNI' in c and 'CLIENTE' not in c]
            if col_dni_busqueda:
                col_real = col_dni_busqueda[0]
                df_registros[col_real] = df_registros[col_real].astype(str).str.replace("'", "").str.zfill(8)
                df_mio = df_registros[df_registros[col_real] == dni_clean].copy()
                
                if df_mio.empty:
                    st.info("No se encontraron registros previos con este DNI.")
                else:
                    c_p1, c_p2 = st.columns([2, 1])
                    with c1:
                        st.markdown("🏆 **Gestiones por Fecha (Meta ≥ 40)**")
                        resumen_dias = df_mio.groupby("FECHA").size().to_frame("TOTAL")
                        st.dataframe(resumen_dias.T.style.applymap(lambda v: 'background-color: #90EE90;' if v >= 40 else ''), use_container_width=True)
                        
                        st.markdown("📊 **Mix de Gestión Personal**")
                        fig_mio = px.pie(df_mio, names='DETALLE', hole=0.4)
                        st.plotly_chart(fig_mio, use_container_width=True)
            else:
                st.error("No se encontró la columna de DNI en la base de datos.")

# --- PESTAÑA 3: DASHBOARD ADMIN (PROTEGIDA) ---
with tab2:
    st.subheader("🔐 Acceso Administrador")
    c_u, c_p = st.columns(2)
    with c_u: a_user = st.text_input("Usuario", key="ad_u")
    with c_p: a_pass = st.text_input("Contraseña", type="password", key="ad_p")

    if a_user == "admin" and a_pass == "Diamire2026*":
        st.success("🔓 Acceso Concedido")
        if not df_registros.empty:
            # Filtros y tablas que ya tenías funcionando perfectamente...
            f1, f2 = st.columns(2)
            with f1: dia_sel = st.selectbox("📅 Día Control", sorted(df_registros["FECHA"].unique(), reverse=True))
            with f2: zon_sel = st.selectbox("Zonal", ["TODOS"] + sorted(df_registros["ZONAL"].unique().tolist()))
            
            df_dash = df_registros[df_registros["FECHA"] == dia_sel]
            if zon_sel != "TODOS": df_dash = df_dash[df_dash["ZONAL"] == zon_sel]
            
            st.markdown(f"📋 **Resultados del día {dia_sel}**")
            st.dataframe(df_dash, use_container_width=True)
            
            # Botón de descarga
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                df_registros.to_excel(writer, index=False, sheet_name='Data')
            st.download_button("📥 Descargar Base Completa", data=buf.getvalue(), file_name="Gestion_Dimiare.xlsx", use_container_width=True)
    elif a_user != "" or a_pass != "":
        st.error("❌ Credenciales incorrectas.")



