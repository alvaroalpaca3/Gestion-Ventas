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
        client = gspread.authorize(creds)
        return client.open("GestionDiaria")
    except Exception as e:
        st.error("⚠️ Error de enlace: Revisa que el Excel esté compartido con el correo del JSON.")
        return None

@st.cache_data(ttl=60)
def cargar_datos():
    doc = conectar_google()
    if not doc: return pd.DataFrame(), pd.DataFrame()
    
    # Cargar Vendedores
    try:
        ws_est = doc.worksheet("Estructura")
        lista_est = ws_est.get_all_values()
        df_est = pd.DataFrame(lista_est[1:], columns=lista_est[0])
        df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(8)
    except: df_est = pd.DataFrame()

    # Cargar Histórico
    try:
        ws_reg = doc.sheet1
        df_reg = pd.DataFrame(ws_reg.get_all_records())
        df_reg.columns = [str(c).strip().upper() for c in df_reg.columns]
    except: df_reg = pd.DataFrame()
        
    return df_est, df_reg

# --- INICIALIZACIÓN ---
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
    st.sidebar.success(f"Bienvenido: {nom_v}")
else:
    nom_v = sup_v = zon_v = "N/A"

# --- INTERFAZ ---
st.header("📊SISTEMA DE GESTIÓN DIARIA")

tab1, tab2 = st.tabs(["📝 REGISTRO", "📊 DASHBOARD"])

with tab1:
    st.subheader("📊 REGISTRO DE VENTAS")
    
    detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
    
    with st.form(key=f"f_{st.session_state.form_key}"):
        # 22 Columnas inicializadas
        t_op = n_cl = d_cl = dir_ins = mail = c1 = c2 = prod = c_fe = n_ped = pil = m_nv = n_ref = c_ref = "N/A"

        if detalle == "NO-VENTA":
            m_nv = st.selectbox("MOTIVO DE NO VENTA *", ["SELECCIONA", "COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "YA TIENE SERVICIO"])
            st.info("💡 Solo llena el motivo. DNI y Zonal se guardan automáticamente.")
        
        elif detalle == "REFERIDO":
            n_ref = st.text_input("Nombre del Referido *").upper()
            c_ref = st.text_input("Contacto Referido (9 dígitos) *", max_chars=9)
            
        elif detalle != "SELECCIONA":
            ca, cb = st.columns(2)
            with ca:
                n_cl = st.text_input("Nombre Cliente *").upper()
                d_cl = st.text_input("DNI/RUC Cliente *")
                t_op = st.selectbox("Operación *", ["CAPTACIÓN", "MIGRACIÓN", "ALTA"])
                prod = st.selectbox("Producto *", ["BA", "DUO", "TRIO"])
                pil = st.radio("Piloto?", ["NO", "SI"], horizontal=True)
            with cb:
                dir_ins = st.text_input("Dirección *").upper()
                c1 = st.text_input("Celular 1 (9 dígitos) *", max_chars=9)
                c2 = st.text_input("Celular 2")
                n_ped = st.text_input("N° Pedido")
                mail = st.text_input("Email")
                c_fe = st.text_input("Código FE")
               

        if st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True):
            error = False
            if nom_v == "N/A":
                st.error("❌ DNI no reconocido en Estructura.")
                error = True
            elif detalle == "REFERIDO" and (len(c_ref) != 9 or not c_ref.isdigit()):
                st.error("❌ El contacto del referido debe tener 9 dígitos numéricos.")
                error = True
            elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"] and (len(c1) != 9 or not c1.isdigit()):
                st.error("❌ El celular 1 debe tener 9 dígitos numéricos.")
                error = True
            elif detalle == "SELECCIONA":
                st.error("❌ Seleccione un tipo de gestión.")
                error = True

            if not error:
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
                    st.success("✅ ¡Registro exitoso!")
                    time.sleep(1)
                    st.session_state.form_key += 1
                    st.rerun()
                except Exception as e: st.error(f"Error al guardar: {e}")


with tab2:
    st.subheader("📊 DASHBOARD OPERATIVO")
    
    if df_registros.empty:
        st.info("Aún no hay datos registrados para mostrar el análisis.")
    else:
        # --- SECCIÓN DE FILTROS ---
        st.markdown("Filtros de Búsqueda")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            zonales = ["TODOS"] + sorted(df_registros["ZONAL"].unique().tolist())
            zonal_sel = st.selectbox("Filtrar por Zonal", zonales)
            
        with col_f2:
            df_temp = df_registros if zonal_sel == "TODOS" else df_registros[df_registros["ZONAL"] == zonal_sel]
            supervisores = ["TODOS"] + sorted(df_temp["SUPERVISOR"].unique().tolist())
            sup_sel = st.selectbox("Filtrar por Supervisor", supervisores)

        df_filtered = df_registros.copy()
        if zonal_sel != "TODOS":
            df_filtered = df_filtered[df_filtered["ZONAL"] == zonal_sel]
        if sup_sel != "TODOS":
            df_filtered = df_filtered[df_filtered["SUPERVISOR"] == sup_sel]

        # --- MÉTRICAS RÁPIDAS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Registros Filtrados", len(df_filtered))
        ventas_f = len(df_filtered[df_filtered["DETALLE"] == "VENTA FIJA"])
        m2.metric("Ventas Fijas", ventas_f)
        m3.metric("% Efectividad", f"{(ventas_f/len(df_filtered)*100):.1f}%" if len(df_filtered)>0 else "0%")

        st.divider()

        # --- RANKING CON SEMÁFORO (40 REGISTROS = VERDE) ---
        st.markdown("🏆 Ranking de Productividad Diaria")
        
        if "FECHA" in df_filtered.columns and "NOMBRE VENDEDOR" in df_filtered.columns:
            # Crear tabla pivote
            ranking_df = df_filtered.pivot_table(
                index="NOMBRE VENDEDOR", 
                columns="FECHA", 
                values="DETALLE", 
                aggfunc="count", 
                fill_value=0
            )
            
            # Añadir columna de Total
            ranking_df["TOTAL MES"] = ranking_df.sum(axis=1)
            ranking_df = ranking_df.sort_values(by="TOTAL MES", ascending=False)
            
            # Función para aplicar el color verde si es >= 40
            def resaltar_metas(val):
                color = 'background-color: #90EE90' if val >= 40 else ''
                return color

            # Aplicar el estilo a la tabla
            st.dataframe(ranking_df.style.applymap(resaltar_metas), use_container_width=True)
            st.caption("🟢 Las celdas en verde indican que el vendedor alcanzó la meta de 40 registros o más.")

        st.divider()

        # --- GRÁFICOS INFERIORES ---
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("📅 Tendencia Diaria")
            df_counts = df_filtered.groupby("FECHA").size().reset_index(name="Cantidad")
            fig_linea = px.bar(df_counts, x="FECHA", y="Cantidad", text_auto=True, color_discrete_sequence=["#1E90FF"])
            st.plotly_chart(fig_linea, use_container_width=True)
            
        with col_g2:
            st.markdown("🎯 Mix de Gestión")
            fig_pie = px.pie(df_filtered, names="DETALLE", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)






