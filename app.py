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

# --- LOGO EN SIDEBAR ---
import os

# Buscamos cualquier archivo que se llame logo (sin importar si es png, jpg o minúsculas)
archivos_en_carpeta = os.listdir('.')
logo_encontrado = [f for f in archivos_en_carpeta if f.lower().startswith('logo.')]

if logo_encontrado:
    st.sidebar.image(logo_encontrado[0], use_container_width=True)
else:
    st.sidebar.info("⌛ Esperando archivo logo.png en GitHub...")

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
    st.markdown("#### 📝 REGISTRO DE VENTAS")
    
    detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
    
    # Usamos el form_key para resetear el formulario tras guardar
    with st.form(key=f"registro_form_{st.session_state.form_key}"):
        # 1. Inicialización de variables para las 22 columnas
        t_op = n_cl = d_cl = dir_ins = mail = c1 = c2 = prod = c_fe = n_ped = pil = m_nv = n_ref = c_ref = "N/A"

        if detalle == "NO-VENTA":
            m_nv = st.selectbox("MOTIVO DE NO VENTA *", ["SELECCIONA", "COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "YA TIENE SERVICIO"])
            st.info("💡 No es necesario reescribir DNI ni Zonal.")
        
        elif detalle == "REFERIDO":
            n_ref = st.text_input("Nombre del Referido *").upper()
            c_ref = st.text_input("Contacto Referido (9 dígitos) *", max_chars=9)
            
        elif detalle != "SELECCIONA":
            ca, cb = st.columns(2)
            with ca:
                n_cl = st.text_input("Nombre Cliente *").upper()
                d_cl = st.text_input("DNI/RUC Cliente (8 dígitos) *", max_chars=8)
                t_op = st.selectbox("Operación *", ["SELECCIONA", "CAPTACIÓN", "MIGRACIÓN", "COMPLETA TV","COMPLETA BA", "COMPLETA MT"])
                prod = st.selectbox("Producto *", ["SELECCIONA", "NAKED","DUO INT + TV", "DUO BA", "DUO TV", "TRIO"])
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
            # Validaciones de Seguridad y Acceso
            if nom_v == "N/A":
                st.error("❌ Acceso denegado: Ingrese su DNI en la barra lateral.")
                error = True
            elif detalle == "SELECCIONA":
                st.error("❌ Debe seleccionar un tipo de gestión.")
                error = True
            
            # Validación específica para VENTA FIJA / AGENDADO
            elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"]:
                if not n_cl.strip() or not dir_ins.strip() or not mail.strip():
                    st.error("❌ Los campos Nombre, Dirección y Email no pueden estar vacíos.")
                    error = True
                elif len(d_cl) != 8 or not d_cl.isdigit():
                    st.error("❌ El DNI debe ser de 8 dígitos numéricos.")
                    error = True
                elif len(c1) != 9 or not c1.isdigit():
                    st.error("❌ El Celular debe ser de 9 dígitos numéricos (sin letras).")
                    error = True
                elif len(n_ped) != 10 or not n_ped.isdigit():
                    st.error("❌ El N° de Pedido debe tener 10 dígitos numéricos.")
                    error = True
                elif len(c_fe) != 13:
                    st.error("❌ El código FE debe tener exactamente 13 caracteres.")
                    error = True
                elif t_op == "SELECCIONA" or prod == "SELECCIONA":
                    st.error("❌ Seleccione Operación y Producto.")
                    error = True

            # 3. Validación NO-VENTA
            elif detalle == "NO-VENTA" and m_nv == "SELECCIONA":
                st.error("❌ Debe seleccionar un motivo de No-Venta.")
                error = True

            if not error:
                try:
                    tz = pytz.timezone('America/Lima')
                    ahora = datetime.now(tz)
                    f_actual = ahora.strftime("%d/%m/%Y")
                    h_actual = ahora.strftime("%H")
                    
                    fila = [
                        ahora.strftime("%d/%m/%Y %H:%M:%S"), zon_v, f"'{dni_clean}", nom_v, sup_v,
                        detalle, t_op, n_cl, f"'{d_cl}", dir_ins, mail, f"'{c1}", "N/A",
                        prod, c_fe, f"'{n_ped}", pil, m_nv, n_ref, f"'{c_ref}",
                        f_actual, h_actual
                    ]
                    conectar_google().sheet1.append_row(fila, value_input_option='USER_ENTERED')
                    st.success(f"✅ ¡Guardado! (Hora: {h_actual})")
                    time.sleep(1)
                    st.session_state.form_key += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

with tab2:
    st.markdown("##### 📊 DASHBOARD OPERATIVO")
    
    if df_registros.empty:
        st.info("Aún no hay datos registrados.")
    else:
        # --- FILTROS INDEPENDIENTES ---
        st.markdown("🔍 **Configuración de Vista**")
        c_f1, c_f2, c_f3 = st.columns(3)
        
        with c_f1:
            # Este filtro SOLO afecta al monitor de horas de hoy
            dias_unicos = sorted(df_registros["FECHA"].unique().tolist(), reverse=True)
            dia_sel = st.selectbox("📅 Día para Control Horario", dias_unicos)
        
        with c_f2:
            # Filtro para el Ranking Acumulado/Histórico
            zonales = ["TODOS"] + sorted(df_registros["ZONAL"].unique().tolist())
            zonal_sel = st.selectbox("Zonal (Histórico)", zonales)
            
        with c_f3:
            # Filtro para el Ranking Acumulado/Histórico
            df_t = df_registros if zonal_sel == "TODOS" else df_registros[df_registros["ZONAL"] == zonal_sel]
            supervisores = ["TODOS"] + sorted(df_t["SUPERVISOR"].unique().tolist())
            sup_sel = st.selectbox("Supervisor (Histórico)", supervisores)

        # --- SECCIÓN 1: MONITOR HORARIO (FILTRADO POR DÍA) ---
        st.divider()
        st.markdown(f"⏰ **Actividad por Horas - Día Seleccionado: {dia_sel}**")
        
        df_hoy = df_registros[df_registros["FECHA"] == dia_sel]
        
        if not df_hoy.empty:
            ranking_h = df_hoy.pivot_table(
                index="NOMBRE VENDEDOR", columns="HORA", values="DETALLE", 
                aggfunc="count", fill_value=0
            )
            ranking_h = ranking_h.reindex(sorted(ranking_h.columns), axis=1)
            ranking_h["TOTAL"] = ranking_h.sum(axis=1)
            ranking_h = ranking_h.sort_values(by="TOTAL", ascending=False)

            def style_horas(val):
                if val == 0: return 'background-color: #F0F2F6; color: #A0A0A0;' # Gris para inactividad
                return 'background-color: #E1F5FE; color: #01579B; font-weight: bold;' # Azul para actividad
            
            st.dataframe(ranking_h.style.applymap(style_horas), use_container_width=True)
        else:
            st.warning("No hay registros para este día.")

        # --- SECCIÓN 2: PRODUCTIVIDAD ACUMULADA (HISTÓRICO CON META 40) ---
        st.divider()
        st.markdown("🏆 **Ranking de Metas Diarias (Meta: 40 Registros)**")
        
        # Filtramos el acumulado por Zonal y Supervisor (afecta a todos los días)
        df_acc = df_registros.copy()
        if zonal_sel != "TODOS": df_acc = df_acc[df_acc["ZONAL"] == zonal_sel]
        if sup_sel != "TODOS": df_acc = df_acc[df_acc["SUPERVISOR"] == sup_sel]

        if not df_acc.empty:
            ranking_d = df_acc.pivot_table(
                index="NOMBRE VENDEDOR", columns="FECHA", values="DETALLE", 
                aggfunc="count", fill_value=0
            )
            # Ordenamos: Fechas más recientes primero
            ranking_d = ranking_d.reindex(sorted(ranking_d.columns, reverse=True), axis=1)
            ranking_d["TOTAL PERIODO"] = ranking_d.sum(axis=1)
            ranking_d = ranking_d.sort_values(by="TOTAL PERIODO", ascending=False)

            def style_meta(val):
                try:
                    # Aplicamos el color verde si llega a la meta de 40
                    if float(val) >= 40: return 'background-color: #90EE90; font-weight: bold;'
                except: pass
                return ''

            # Aplicamos estilo a toda la tabla para resaltar los días ganadores
            st.dataframe(ranking_d.style.applymap(style_meta), use_container_width=True)
            st.caption("🟢 Los días donde se alcanzó la meta de 40 gestiones aparecen en verde.")
        else:
            st.info("No hay datos históricos para los filtros seleccionados.")


# --- BOTÓN DE DESCARGA A EXCEL ---
            import io
            
            # Convertimos el ranking a un archivo Excel en memoria
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                ranking_d.to_excel(writer, sheet_name='Ranking_Metas')
            
            st.download_button(
                label="📥 Descargar Ranking Acumulado (Excel)",
                data=buffer.getvalue(),
                file_name=f"Ranking_Dimiare_{dia_sel.replace('/','-')}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )



