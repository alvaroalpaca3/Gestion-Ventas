import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import time
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Comercial Dimiare", layout="wide", initial_sidebar_state="expanded")

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Se cargan las credenciales desde los Secrets de Streamlit
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("GestionDiaria")
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

@st.cache_data(ttl=60)
def cargar_datos():
    doc = conectar_google()
    if not doc:
        return pd.DataFrame(), pd.DataFrame()
    
    # Cargar hoja de Estructura (Vendedores)
    try:
        ws_est = doc.worksheet("Estructura")
        df_est = pd.DataFrame(ws_est.get_all_values()[1:], columns=ws_est.get_all_values()[0])
        df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(8)
    except:
        df_est = pd.DataFrame()

    # Cargar hoja de Registros (Sheet1)
    try:
        ws_reg = doc.sheet1
        data = ws_reg.get_all_records()
        df_reg = pd.DataFrame(data)
        df_reg.columns = [str(c).strip().upper() for c in df_reg.columns]
    except:
        df_reg = pd.DataFrame()
        
    return df_est, df_reg

# --- LÓGICA DE INICIO ---
df_maestro, df_registros = cargar_datos()

if "form_key" not in st.session_state:
    st.session_state.form_key = 0

# --- SIDEBAR: IDENTIFICACIÓN ---
st.sidebar.title("👤 Acceso Vendedor")
dni_input = st.sidebar.text_input("INGRESE SU DNI", max_chars=8, key="dni_user")
dni_clean = "".join(filter(str.isdigit, dni_input)).zfill(8)

vendedor_data = df_maestro[df_maestro['DNI'] == dni_clean] if not df_maestro.empty else pd.DataFrame()

if not vendedor_data.empty and len(dni_input) == 8:
    nom_v = vendedor_data.iloc[0]['NOMBRE VENDEDOR']
    sup_v = vendedor_data.iloc[0]['SUPERVISOR']
    zon_v = vendedor_data.iloc[0]['ZONAL']
    st.sidebar.success(f"Bienvenido: {nom_v}")
    st.sidebar.info(f"Zonal: {zon_v} | Sup: {sup_v}")
else:
    nom_v = "N/A"; sup_v = "N/A"; zon_v = "N/A"
    if len(dni_input) == 8: st.sidebar.error("DNI no encontrado en Estructura")

# --- CUERPO PRINCIPAL ---
tab1, tab2 = st.tabs(["📝 REGISTRO DE GESTIÓN", "📊 DASHBOARD"])

with tab1:
    st.title("Formulario de Productividad")
    
    # Selección de Motivo Principal
    tipo_gestion = st.selectbox("DETALLE DE GESTIÓN *", 
                                ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])

    with st.form(key=f"form_{st.session_state.form_key}"):
        # Variables por defecto
        motivo_nv = cliente = dni_ruc = operacion = producto = direccion = cel1 = cel2 = "N/A"
        pedido = "0"; piloto = "NO"; n_ref = "N/A"; c_ref = "N/A"

        # Lógica dinámica según el tipo de gestión
        if tipo_gestion == "NO-VENTA":
            st.subheader("Datos de No Venta")
            motivo_nv = st.selectbox("INDICAR MOTIVO *", ["SELECCIONA", "COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "NO INTERESADO"])
            st.info("Nota: DNI y Zonal se guardarán automáticamente.")
            
        elif tipo_gestion == "REFERIDO":
            st.subheader("Datos del Referido")
            n_ref = st.text_input("Nombre del Referido").upper()
            c_ref = st.text_input("Teléfono del Referido", max_chars=9)

        elif tipo_gestion != "SELECCIONA":
            col_a, col_b = st.columns(2)
            with col_a:
                cliente = st.text_input("Nombre del Cliente *").upper()
                dni_ruc = st.text_input("DNI/RUC Cliente *", max_chars=11)
                operacion = st.selectbox("Operación *", ["SELECCIONA", "CAPTACIÓN", "MIGRACIÓN", "ALTA"])
            with col_b:
                producto = st.selectbox("Producto *", ["SELECCIONA", "BA", "DUO", "TRIO"])
                direccion = st.text_input("Dirección de Instalación *").upper()
                pedido = st.text_input("N° de Pedido (10 dígitos)", max_chars=10)
                cel1 = st.text_input("Celular 1 *", max_chars=9)

        # Botón de envío
        enviar = st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True)

    if enviar:
        if nom_v == "N/A":
            st.error("Error: Debe identificarse con un DNI válido en la barra lateral.")
        elif tipo_gestion == "SELECCIONA" or (tipo_gestion == "NO-VENTA" and motivo_nv == "SELECCIONA"):
            st.error("Error: Complete todos los campos obligatorios (*).")
        else:
            try:
                # Configurar tiempo y fila
                tz = pytz.timezone('America/Lima')
                now = datetime.now(tz)
                
                # Fila alineada con los 22 encabezados del Excel
                nueva_fila = [
                    now.strftime("%d/%m/%Y %H:%M:%S"), # Marca temporal
                    zon_v, f"'{dni_clean}", nom_v, sup_v, # Datos vendedor
                    tipo_gestion, operacion, cliente, f"'{dni_ruc}", # Datos gestion
                    direccion, "N/A", f"'{cel1}", "N/A", # Contactos
                    producto, "N/A", f"'{pedido}", piloto, # Venta
                    motivo_nv, n_ref, f"'{c_ref}", # No venta / Referidos
                    now.strftime("%d/%m/%Y"), now.strftime("%H:%M:%S") # Fecha y Hora separadas
                ]
                
                conectar_google().sheet1.append_row(nueva_fila, value_input_option='USER_ENTERED')
                st.success(f"✅ Gestión de {tipo_gestion} guardada con éxito.")
                time.sleep(2)
                st.session_state.form_key += 1
                st.rerun()
            except Exception as error:
                st.error(f"Error al guardar: {error}")

with tab2:
    st.title("Panel de Control")
    if df_registros.empty:
        st.warning("No hay datos registrados aún.")
    else:
        # Gráficos Dinámicos
        c_det = "DETALLE" if "DETALLE" in df_registros.columns else df_registros.columns[5]
        
        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.pie(df_registros, names=c_det, title="Distribución de Gestiones", hole=0.3)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            # Ventas por Supervisor
            df_ventas = df_registros[df_registros[c_det].astype(str).str.contains("VENTA", na=False)]
            if not df_ventas.empty:
                c_sup = "SUPERVISOR" if "SUPERVISOR" in df_ventas.columns else df_ventas.columns[4]
                fig2 = px.bar(df_ventas.groupby(c_sup).size().reset_index(name='Cant'), 
                             x=c_sup, y='Cant', title="Ventas por Supervisor", color=c_sup)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sin ventas registradas para el gráfico de barras.")
