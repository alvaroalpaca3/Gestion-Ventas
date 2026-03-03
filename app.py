import streamlit as st
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from datetime import datetime
import pytz
import time
import plotly.express as px
import io

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Comercial Dimiare", layout="wide")

# --- 2. BLOQUE DE SEGURIDAD (MANTENIMIENTO) ---
if st.secrets.get("mantenimiento", False):
    if st.query_params.get("admin") != "true":
        st.error("⚠️ SISTEMA EN MANTENIMIENTO")
        st.info("Estamos optimizando la base de datos. Regresamos en breve.")
        st.stop()
    else:
        st.sidebar.success("🛠️ MODO PRUEBA ACTIVO")

# --- 3. CONEXIÓN Y CARGA DE DATOS ---
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("GestionDiaria")
    except Exception as e:
        st.error(f"⚠️ Error de Conexión: {e}")
        return None

@st.cache_data(ttl=3600)
def cargar_datos():
    doc = conectar_google()
    df_est, df_reg = pd.DataFrame(), pd.DataFrame()
    if doc:
        try:
            ws_est = doc.worksheet("Estructura")
            lista_est = ws_est.get_all_values()
            df_est = pd.DataFrame(lista_est[1:], columns=lista_est[0])
            df_est['DNI'] = df_est['DNI'].astype(str).str.replace(r'[^0-9]', '', regex=True).str.strip()
            
            ws_reg = doc.sheet1
            df_reg = pd.DataFrame(ws_reg.get_all_records())
            df_reg.columns = [str(c).strip().upper() for c in df_reg.columns]
        except: pass
    return df_est, df_reg

# --- 4. INICIALIZACIÓN DE SESIÓN ---
if 'nom_v' not in st.session_state: st.session_state.nom_v = "N/A"
if 'zon_v' not in st.session_state: st.session_state.zon_v = "N/A"
if 'sup_v' not in st.session_state: st.session_state.sup_v = "N/A"
if 'dni_clean' not in st.session_state: st.session_state.dni_clean = ""
if 'form_key' not in st.session_state: st.session_state.form_key = 0

df_maestro, df_registros = cargar_datos()

# --- 5. BARRA LATERAL (ACCESO) ---
st.sidebar.markdown("<h2 style='text-align: center; color: #1E3A8A;'>DIAMIRE</h2>", unsafe_allow_html=True)
st.sidebar.title("👤 Acceso Vendedor")
dni_input = st.sidebar.text_input("DNI / CE VENDEDOR", max_chars=9)
# Normalizamos para búsqueda
dni_busqueda = "".join(filter(str.isdigit, dni_input)).lstrip('0')

if len(dni_busqueda) >= 6 and not df_maestro.empty:
    df_maestro['DNI_MATCH'] = df_maestro['DNI'].astype(str).str.replace(r'\.0$', '', regex=True).str.lstrip('0')
    vendedor_data = df_maestro[df_maestro['DNI_MATCH'] == dni_busqueda]
    if not vendedor_data.empty:
        st.session_state.nom_v = vendedor_data.iloc[0]['NOMBRE VENDEDOR']
        st.session_state.zon_v = vendedor_data.iloc[0]['ZONAL']
        st.session_state.sup_v = vendedor_data.iloc[0]['SUPERVISOR']
        st.session_state.dni_clean = dni_input # Mantiene ceros
        st.sidebar.success(f"✅ Bienvenido: {st.session_state.nom_v}")
    else: st.session_state.nom_v = "N/A"
else: st.session_state.nom_v = "N/A"

# Variables locales para usar en el cuerpo
nom_v, zon_v, sup_v, dni_clean = st.session_state.nom_v, st.session_state.zon_v, st.session_state.sup_v, st.session_state.dni_clean

st.sidebar.caption("©2026 by Dubby System SA")

# --- 6. CUERPO PRINCIPAL ---
st.header("📊 GESTIÓN COMERCIAL")
tab1, tab_personal, tab2 = st.tabs(["📝 REGISTRO", "📈 MI PROGRESO", "🔐 ADMIN"])

with tab1:
    if nom_v == "N/A":
        st.info("👈 Ingresa tu DNI en la barra lateral para habilitar el formulario.")
    else:
        st.markdown(f"#### 📝 Registro para: **{nom_v}** ({zon_v})")
        detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
        
        with st.form(key=f"registro_form_{st.session_state.form_key}"):
            t_op = n_cl = d_cl = dir_ins = mail = c1 = prod = c_fe = n_ped = pil = m_nv = n_ref = c_ref = "N/A"

            if detalle == "NO-VENTA":
                opciones_nv = ["COMPETENCIA", "MALA EXPERIENCIA", "CARGO ALTO", "SIN COBERTURA", "YA TIENE SERVICIO"]
                m_nv = st.selectbox("MOTIVO DE NO-VENTA *", options=opciones_nv, index=None, placeholder="Elija un motivo...")
                st.info(f"💡 DNI ({dni_clean}) y Zonal ({zon_v}) automáticos.")
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
                    n_ped = st.text_input("N° Orden *", max_chars=10)
                    mail = st.text_input("Email *")
                    c_fe = st.text_input("Código FE *", max_chars=13)

            submit = st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True)

            if submit:
                error = False
                if detalle == "SELECCIONA":
                    st.error("❌ Elija un tipo de gestión."); error = True
                elif detalle == "NO-VENTA" and m_nv is None:
                    st.error("❌ Seleccione el motivo de No-Venta."); error = True
                elif detalle == "REFERIDO" and (not n_ref.strip() or len(c_ref) != 9 or not c_ref.isdigit()):
                    st.error("❌ Verifique nombre y celular (9 dígitos)."); error = True
                elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"]:
                    if any(x == "SELECCIONA" or not str(x).strip() for x in [n_cl, d_cl, dir_ins, c1, n_ped, mail, c_fe, t_op, prod]):
                        st.error("❌ Complete todos los campos (*)."); error = True
                    elif len(d_cl) < 8 or len(c1) != 9 or len(n_ped) != 10 or len(c_fe) != 13:
                        st.error("❌ Error en longitud de DNI (8), Celular (9), Pedido (10) o FE (13)."); error = True

                # --- BLOQUE DE GUARDADO CON PROTECCIÓN (REEMPLAZA DESDE AQUÍ) ---
                if not error:
                    intentos = 0
                    exito = False
                    while intentos < 3 and not exito:
                        try:
                            tz = pytz.timezone('America/Lima')
                            ahora = datetime.now(tz)
                            fila = [
                                ahora.strftime("%d/%m/%Y %H:%M:%S"), zon_v, f"'{dni_clean}", nom_v, sup_v, 
                                detalle, t_op, n_cl, f"'{d_cl}", dir_ins, mail, f"'{c1}", "N/A", 
                                prod, c_fe, f"'{n_ped}", pil, m_nv, n_ref, f"'{c_ref}", 
                                ahora.strftime("%d/%m/%Y"), ahora.strftime("%H")
                            ]
                            # Intentamos el envío
                            conectar_google().sheet1.append_row(fila, value_input_option='USER_ENTERED')
                            
                            st.success("✅ ¡Registro guardado!")
                            exito = True # Rompe el ciclo while
                            time.sleep(1)
                            st.session_state.form_key += 1
                            st.rerun()
                            
                        except Exception as e:
                            if "429" in str(e):
                                intentos += 1
                                st.warning(f"⏳ Google está saturado. Reintentando en 2 segundos... ({intentos}/3)")
                                time.sleep(2) # Pausa técnica para liberar la "calle"
                            else:
                                st.error(f"❌ Error inesperado: {e}")
                                break # Si es otro error, no reintentamos

# --- PESTAÑA 2: MI PROGRESO (FILTRO POR NOMBRE) ---
with tab_personal:
    if nom_v == "N/A":
        st.warning("👈 Ingrese su DNI en la barra lateral.")
    else:
        st.markdown(f"##### 📈 Mi Actividad: {nom_v}")
        
        # Verificamos que df_registros exista y no esté vacío
        if 'df_registros' in locals() and not df_registros.empty:
            # 1. Limpieza y Filtro (Usamos copias para no afectar la base global)
            # Buscamos la columna exacta, usualmente es 'NOMBRE VENDEDOR' o 'VENDEDOR' según tu Sheets
            col_vendedor = "NOMBRE VENDEDOR" if "NOMBRE VENDEDOR" in df_registros.columns else df_registros.columns[3]
            
            df_temp = df_registros.copy()
            df_temp[col_vendedor] = df_temp[col_vendedor].astype(str).str.strip()
            df_mio = df_temp[df_temp[col_vendedor] == nom_v].copy()
            
            if df_mio.empty:
                st.info(f"Aún no existen registros guardados para: {nom_v}")
            else:
                tz = pytz.timezone('America/Lima')
                hoy = datetime.now(tz).strftime("%d/%m/%Y")
                
                # --- 1. MONITOR DIARIO (HOY) ---
                st.markdown("##### **1. Monitor Diario (Hoy)**")
                # Aseguramos que la columna FECHA exista antes de filtrar
                fecha_col = "FECHA" if "FECHA" in df_mio.columns else df_mio.columns[-2]
                df_mio_hoy = df_mio[df_mio[fecha_col] == hoy]
                
                if not df_mio_hoy.empty:
                    # Usamos DETALLE o la columna 5 que es donde está el tipo de gestión
                    det_col = "DETALLE" if "DETALLE" in df_mio.columns else df_mio.columns[5]
                    hora_col = "HORA" if "HORA" in df_mio.columns else df_mio.columns[-1]
                    
                    mi_rh = df_mio_hoy.pivot_table(index=col_vendedor, columns=hora_col, values=det_col, aggfunc="count", fill_value=0)
                    mi_rh["TOTAL"] = mi_rh.sum(axis=1)
                    st.dataframe(mi_rh.reset_index().rename(columns={col_vendedor: "VENDEDOR"}), use_container_width=True, hide_index=True) 
                else:
                    st.caption(f"Sin actividad hoy {hoy}")

                # --- 2. MATRIZ Y DONA (HOY) ---
                if not df_mio_hoy.empty:
                    st.markdown("##### **2. Matriz de Productividad (Hoy)**")
                    mi_tp = df_mio_hoy.pivot_table(index=col_vendedor, columns=det_col, values=fecha_col, aggfunc="count", fill_value=0)
                    mi_tp["TOTAL"] = mi_tp.sum(axis=1)
                    st.dataframe(mi_tp.reset_index().rename(columns={col_vendedor: "VENDEDOR"}), use_container_width=True, hide_index=True)

                    fig_m = px.pie(df_mio_hoy, names=det_col, hole=0.5)
                    fig_m.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=250, showlegend=True)
                    st.plotly_chart(fig_m, use_container_width=True)

                # --- 3. AVANCE DEL MES ---
                st.markdown("##### **3. Avance del Mes**")
                mi_rd = df_mio.pivot_table(index=col_vendedor, columns=fecha_col, values=det_col, aggfunc="count", fill_value=0)
                # Ordenar fechas de más reciente a más antigua
                mi_rd = mi_rd.reindex(sorted(mi_rd.columns, reverse=True), axis=1)
                mi_rd["TOTAL"] = mi_rd.sum(axis=1)
                
                st.dataframe(
                    mi_rd.reset_index().rename(columns={col_vendedor: "VENDEDOR"}).style.applymap(
                        lambda v: 'background-color: #90EE90;' if isinstance(v, (int, float)) and v >= 40 else '', 
                        subset=mi_rd.columns[:-1]
                    ), use_container_width=True, hide_index=True
                )
        else:
            st.warning("⚠️ Los datos no están disponibles en este momento. La base de datos está saturada, por favor espera un minuto y refresca la página.")
            
# --- PESTAÑA 3: DASHBOARD (ADMIN) ---
with tab2:
    st.markdown("##### 🔐 Acceso Administrador")
    col_adm1, col_adm2 = st.columns(2)
    with col_adm1: admin_user = st.text_input("Usuario", key="adm_u_final")
    with col_adm2: admin_pass = st.text_input("Contraseña", type="password", key="adm_p_final")

    if admin_user == "admin" and admin_pass == "Diamire2026*":
        st.success("🔓 Acceso Concedido")
        if not df_registros.empty:
            # FILTROS DE CONTROL
            f1, f2, f3 = st.columns(3)
            with f1: dia_sel = st.selectbox("📅 Día Control", sorted(df_registros["FECHA"].unique(), reverse=True))
            with f2:
                z_list = ["TODOS"] + sorted(df_registros["ZONAL"].unique().astype(str).tolist())
                z_sel = st.selectbox("Zonal", z_list)
            with f3:
                df_t = df_registros[df_registros["ZONAL"] == z_sel] if z_sel != "TODOS" else df_registros.copy()
                s_list = ["TODOS"] + sorted(df_t["SUPERVISOR"].unique().astype(str).tolist())
                s_sel = st.selectbox("Supervisor", s_list)
            
            df_f = df_t[df_t["SUPERVISOR"] == s_sel] if s_sel != "TODOS" else df_t.copy()

            # 1. MONITOR HORARIO
            st.divider()
            st.markdown("##### **1. Monitor Horario (Día Seleccionado)**")
            df_h = df_f[df_f["FECHA"] == dia_sel]
            if not df_h.empty:
                rh = df_h.pivot_table(index="NOMBRE VENDEDOR", columns="HORA", values="DETALLE", aggfunc="count", fill_value=0)
                rh["TOTAL"] = rh.sum(axis=1)
                st.dataframe(rh.sort_values(by="TOTAL", ascending=False), use_container_width=True)
            
            # 2. RANKING METAS
            st.divider()
            st.markdown("##### **2. Ranking Metas (Meta ≥ 40)**")
            df_ranking = df_f.copy()
            df_ranking["FECHA_CORTE"] = pd.to_datetime(df_ranking["FECHA"], dayfirst=True).dt.strftime('%d/%m')
            rd = df_ranking.pivot_table(index="NOMBRE VENDEDOR", columns="FECHA_CORTE", values="DETALLE", aggfunc="count", fill_value=0)
            rd = rd.reindex(sorted(rd.columns, reverse=True), axis=1)
            rd["TOTAL ACUM"] = rd.sum(axis=1)
            rd = rd.sort_values(by="TOTAL ACUM", ascending=False)
            
            st.dataframe(
                rd.style.applymap(
                    lambda v: 'background-color: #90EE90;' if isinstance(v, (int, float)) and v >= 40 else '', 
                    subset=rd.columns[:-1]
                ), use_container_width=True
            )

            # BOTÓN DESCARGA
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                rd.to_excel(wr, sheet_name='Ranking')
            st.download_button(label="📥 Descargar Ranking Metas (Excel)", data=buf.getvalue(), file_name=f"Ranking_{dia_sel}.xlsx", use_container_width=True)

            # 3. MATRIZ PRODUCTIVIDAD
            st.divider()
            st.markdown(f"##### **3. Matriz de Productividad ({z_sel})**")
            tp = df_f.pivot_table(index="NOMBRE VENDEDOR", columns="DETALLE", values="FECHA", aggfunc="count", fill_value=0)
            tp["TOTAL"] = tp.sum(axis=1)
            tp_final = pd.concat([tp, pd.DataFrame(tp.sum(), columns=["TOTAL GENERAL"]).T])
            st.dataframe(
                tp_final.style.set_properties(subset=(tp_final.index[-1:], slice(None)), **{'background-color': '#FFEB9C', 'font-weight': 'bold'}),
                use_container_width=True
            )
    elif admin_user != "" or admin_pass != "":
        st.error("❌ Credenciales incorrectas.")































