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
    
    # Cargar Vendedores (Hoja: Estructura)
    try:
        ws_est = doc.worksheet("Estructura")
        lista_est = ws_est.get_all_values()
        df_est = pd.DataFrame(lista_est[1:], columns=lista_est[0])
        df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.zfill(8)
    except: df_est = pd.DataFrame()

    # Cargar Histórico (Sheet1)
    try:
        ws_reg = doc.sheet1
        df_reg = pd.DataFrame(ws_reg.get_all_records())
        df_reg.columns = [str(c).strip().upper() for c in df_reg.columns]
    except: df_reg = pd.DataFrame()
        
    return df_est, df_reg

# --- 3. INICIALIZACIÓN ---
df_maestro, df_registros = cargar_datos()
if "form_key" not in st.session_state: st.session_state.form_key = 0

# --- 4. BARRA LATERAL (LOGIN Y ACCESO) ---
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
else:
    st.sidebar.write("🖼️ **DIMIARE**")

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

# --- 5. INTERFAZ PRINCIPAL ---
st.header("📊 REGISTRO DE GESTIÓN DIARIA")
tab1, tab2 = st.tabs(["📝 REGISTRO", "📊 DASHBOARD"])

# --- PESTAÑA 1: REGISTRO (CON TODAS LAS VALIDACIONES) ---
with tab1:
    st.markdown("#### 📝 INGRESO DE DATOS")
    detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
    
    with st.form(key=f"registro_form_{st.session_state.form_key}"):
        # Inicialización de campos
        t_op = n_cl = d_cl = dir_ins = mail = c1 = prod = c_fe = n_ped = pil = m_nv = n_ref = c_ref = "N/A"

        if detalle == "NO-VENTA":
            m_nv = st.selectbox("MOTIVO DE NO VENTA *", ["SELECCIONA", "COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "YA TIENE SERVICIO"])
            st.info("💡 Instrucción: Solo debe llenar el motivo. Su DNI y Zonal se guardan automáticamente.")
        
        elif detalle == "REFERIDO":
            n_ref = st.text_input("Nombre del Referido *").upper()
            c_ref = st.text_input("Contacto Referido (9 dígitos) *", max_chars=9)
            
        elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"]:
            ca, cb = st.columns(2)
            with ca:
                n_cl = st.text_input("Nombre Cliente *").upper()
                d_cl = st.text_input("DNI/RUC Cliente (8-11 dígitos) *", max_chars=11)
                t_op = st.selectbox("Operación *", ["SELECCIONA", "CAPTACIÓN", "MIGRACIÓN", "COMPLETA TV", "COMPLETA BA", "COMPLETA MT"])
                prod = st.selectbox("Producto *", ["SELECCIONA", "NAKED", "DUO INT + TV", "DUO BA", "DUO TV", "TRIO"])
                pil = st.radio("Piloto?", ["NO", "SI"], horizontal=True)
            with cb:
                dir_ins = st.text_input("Dirección *").upper()
                c1 = st.text_input("Celular 1 (9 dígitos) *", max_chars=9)
                n_ped = st.text_input("N° Pedido (10 dígitos) *", max_chars=10)
                mail = st.text_input("Email *")
                c_fe = st.text_input("Código FE (13 caracteres) *", max_chars=13)

        submit = st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True)

        if submit:
            error = False
            # Validaciones de Seguridad
            if nom_v == "N/A":
                st.error("❌ Error: Debe ingresar un DNI válido en la barra lateral.")
                error = True
            elif detalle == "SELECCIONA":
                st.error("❌ Error: Seleccione un tipo de gestión.")
                error = True
            
            # Validación VENTA FIJA / AGENDADO
            elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"]:
                if any(x == "SELECCIONA" or not str(x).strip() for x in [n_cl, d_cl, dir_ins, c1, n_ped, mail, c_fe, t_op, prod]):
                    st.error("❌ Error: Todos los campos con (*) son obligatorios.")
                    error = True
                elif len(d_cl) < 8:
                    st.error("❌ Error: El DNI/RUC debe tener al menos 8 dígitos.")
                    error = True
                elif len(c1) != 9:
                    st.error("❌ Error: El celular debe tener 9 dígitos.")
                    error = True
                elif len(n_ped) != 10:
                    st.error("❌ Error: El número de pedido debe tener 10 dígitos.")
                    error = True
                elif len(c_fe) != 13:
                    st.error("❌ Error: El código FE debe tener 13 caracteres.")
                    error = True

            # Validación REFERIDO
            elif detalle == "REFERIDO":
                if not n_ref.strip() or len(c_ref) != 9:
                    st.error("❌ Error: Ingrese Nombre y Celular (9 dígitos) del referido.")
                    error = True

            # Validación NO-VENTA
            elif detalle == "NO-VENTA" and m_nv == "SELECCIONA":
                st.error("❌ Error: Seleccione el motivo de la no-venta.")
                error = True

            if not error:
                try:
                    tz = pytz.timezone('America/Lima')
                    ahora = datetime.now(tz)
                    fila = [
                        ahora.strftime("%d/%m/%Y %H:%M:%S"), zon_v, f"'{dni_clean}", nom_v, sup_v,
                        detalle, t_op, n_cl, f"'{d_cl}", dir_ins, mail, f"'{c1}", "N/A",
                        prod, c_fe, f"'{n_ped}", pil, m_nv, n_ref, f"'{c_ref}",
                        ahora.strftime("%d/%m/%Y"), ahora.strftime("%H")
                    ]
                    conectar_google().sheet1.append_row(fila, value_input_option='USER_ENTERED')
                    
                    # --- REFRESCO INSTANTÁNEO ---
                    st.cache_data.clear()
                    st.success("✅ Gestión guardada exitosamente.")
                    time.sleep(1)
                    st.session_state.form_key += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar en base de datos: {e}")

# --- PESTAÑA 2: DASHBOARD (TODO EN UNO) ---
with tab2:
    if df_registros.empty:
        st.info("No hay datos registrados aún.")
    else:
        # Limpieza de datos
        df_registros['DETALLE'] = df_registros['DETALLE'].astype(str).str.strip().str.upper()

        # Filtros Superiores
        f1, f2, f3 = st.columns(3)
        with f1:
            dia_sel = st.selectbox("📅 Día Control Horario", sorted(df_registros["FECHA"].unique(), reverse=True))
        with f2:
            z_list = ["TODOS"] + sorted(df_registros["ZONAL"].unique().astype(str).tolist())
            z_sel = st.selectbox("Zonal (Histórico)", z_list)
        with f3:
            df_temp = df_registros[df_registros["ZONAL"] == z_sel] if z_sel != "TODOS" else df_registros.copy()
            s_list = ["TODOS"] + sorted(df_temp["SUPERVISOR"].unique().astype(str).tolist())
            s_sel = st.selectbox("Supervisor (Histórico)", s_list)

        df_final = df_temp[df_temp["SUPERVISOR"] == s_sel] if s_sel != "TODOS" else df_temp.copy()

        # --- SECCIÓN 1: MONITOR HORARIO ---
        st.divider()
        st.markdown(f"⏰ **Actividad por Horas ({dia_sel})**")
        df_hoy = df_final[df_final["FECHA"] == dia_sel]
        if not df_hoy.empty:
            rh = df_hoy.pivot_table(index="NOMBRE VENDEDOR", columns="HORA", values="DETALLE", aggfunc="count", fill_value=0)
            rh["TOTAL"] = rh.sum(axis=1)
            st.dataframe(rh.sort_values(by="TOTAL", ascending=False), use_container_width=True)

        # --- SECCIÓN 2: RANKING DE METAS DIARIAS ---
        st.divider()
        st.markdown("🏆 **Ranking de Metas Diarias (Meta: ≥ 40)**")
        if not df_final.empty:
            rd = df_final.pivot_table(index="NOMBRE VENDEDOR", columns="FECHA", values="DETALLE", aggfunc="count", fill_value=0)
            rd = rd.reindex(sorted(rd.columns, reverse=True), axis=1)
            cols_fechas = rd.columns.tolist()
            rd["TOTAL ACUM"] = rd.sum(axis=1)
            
            def color_metas(val):
                try:
                    if int(val) >= 40: return 'background-color: #90EE90; color: #004D00; font-weight: bold; text-align: center;'
                except: pass
                return 'text-align: center;'

            st.dataframe(rd.sort_values(by="TOTAL ACUM", ascending=False).style.applymap(color_metas, subset=cols_fechas)
                         .set_properties(subset=['TOTAL ACUM'], **{'background-color': '#CCE5FF', 'font-weight': 'bold', 'text-align': 'center'}), 
                         use_container_width=True)

        # --- SECCIÓN 3: MATRIZ DE PRODUCTIVIDAD (IZQ-CENTRO) ---
        st.divider()
        st.markdown(f"📋 **Matriz de Productividad ({z_sel} - {s_sel})**")
        if not df_final.empty:
            tp = df_final.pivot_table(index="NOMBRE VENDEDOR", columns="DETALLE", values="FECHA", aggfunc="count", fill_value=0)
            tp["TOTAL GESTIONES"] = tp.sum(axis=1)
            tp = tp.sort_values(by="TOTAL GESTIONES", ascending=False)

            # Estilo: Vendedor a la IZQUIERDA, Datos CENTRADOS
            st.dataframe(
                tp.style.set_properties(**{'text-align': 'center'})
                .set_properties(subset=['TOTAL GESTIONES'], **{'background-color': '#CCE5FF', 'color': '#004085', 'font-weight': 'bold'}),
                use_container_width=True
            )

            # MÉTRICAS COMPACTAS
            st.write("")
            m1, m2, m3 = st.columns(3)
            tg = int(tp["TOTAL GESTIONES"].sum())
            top_v = tp.index[0]
            with m1: st.markdown(f"<div style='text-align:center'><small>Total Global</small><br><strong style='font-size:24px;color:#004085'>{tg}</strong></div>", unsafe_allow_html=True)
            with m2: st.markdown(f"<div style='text-align:center'><small>Vendedor Top</small><br><strong style='font-size:16px;color:#2E7D32'>{top_v}</strong></div>", unsafe_allow_html=True)
            with m3: st.markdown(f"<div style='text-align:center'><small>Promedio</small><br><strong style='font-size:24px;color:#004085'>{round(tg/len(tp),1)}</strong></div>", unsafe_allow_html=True)

            # GRÁFICA DE DONA VISUAL
            st.write("")
            df_pie = tp.drop(columns=['TOTAL GESTIONES']).sum().reset_index()
            df_pie.columns = ['GESTIÓN', 'CANTIDAD']
            fig = px.pie(df_pie, values='CANTIDAD', names='GESTIÓN', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_traces(textinfo='value+percent', texttemplate='<b>%{label}</b><br>%{value} uds.')
            fig.update_layout(height=420, margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

            # BOTÓN EXCEL
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                tp.to_excel(writer, sheet_name='Productividad')
            st.download_button("📥 Descargar Matriz a Excel", data=buf.getvalue(), file_name="Productividad_Dimiare.xlsx", use_container_width=True)
