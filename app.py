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
        # Normalizamos encabezados para evitar errores por espacios
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
st.sidebar.caption("©2026 by Dubby System SA, Todos los derechos reservados")


# --- 5. CUERPO PRINCIPAL ---
st.header("📊 REGISTRO DE GESTIÓN DIARIA")
tab1, tab_personal, tab2 = st.tabs(["📝 REGISTRO", "📈 MI PROGRESO", "📊 DASHBOARD"])

# --- PESTAÑA 1: FORMULARIO (TUS REGLAS ORIGINALES) ---
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
                except Exception as e: st.error(f"Error: {e}")

# --- PESTAÑA 2: MI PROGRESO (DISEÑO ANTI-DESFASE) ---
with tab_personal:
    if nom_v == "N/A":
        st.warning("👈 Ingrese su DNI en la barra lateral.")
    else:
        # Título simple a la izquierda
        st.markdown(f"##### 📈 Mi Actividad: {nom_v}")
        
        if not df_registros.empty:
            col_target = "DOCUMENTO VENDEDOR"
            df_registros[col_target] = df_registros[col_target].astype(str).str.replace("'", "").str.strip()
            df_mio = df_registros[df_registros[col_target] == dni_clean].copy()
            
            if df_mio.empty:
                st.info("Sin registros.")
            else:
           
                # 1. MONITOR HORARIO (Simplificado para alineación)

              st.markdown("##### **1. Monitor Diario (Hoy)**")
                tz = pytz.timezone('America/Lima')
                hoy = datetime.now(tz).strftime("%d/%m/%Y")
                df_mio_hoy = df_mio[df_mio["FECHA"] == hoy]
                
                if not df_mio_hoy.empty:
                    mi_rh = df_mio_hoy.pivot_table(index="NOMBRE VENDEDOR", columns="HORA", values="DETALLE", aggfunc="count", fill_value=0)
                    mi_rh["TOTAL"] = mi_rh.sum(axis=1)

                    # --- MÉTODO DEFINITIVO: RESET_INDEX ---
                    # Pasamos el nombre del vendedor de 'índice' a 'columna real'
                    mi_rh_final = mi_rh.reset_index()
                    # Renombramos esa columna específicamente
                    mi_rh_final.rename(columns={"NOMBRE VENDEDOR": "VENDEDORES"}, inplace=True)

                    st.dataframe(
                        mi_rh_final, 
                        use_container_width=True,
                        hide_index=True, # <--- ESTO BORRA DEFINITIVAMENTE LOS NÚMEROS 0,1,2
                        column_config={
                            "VENDEDORES": st.column_config.Column(width="medium")
                        }
                    ) 
                else:
                    st.caption(f"Sin actividad hoy {hoy}")
                    
              # 2. MATRIZ Y DONA (SOLO DÍA PRESENTE)
                st.markdown("##### **2. Matriz de Productividad (Hoy)**")
                
                # --- FILTRO CLAVE: Solo registros de hoy ---
                fecha_hoy = pd.to_datetime("today").strftime('%d/%m/%Y') 
                df_hoy = df_mio[df_mio["FECHA"] == fecha_hoy]

                if not df_hoy.empty:
                    # --- 1. PRIMERO: EL CUADRO (MATRIZ) ---
                    mi_tp = df_hoy.pivot_table(index="NOMBRE VENDEDOR", columns="DETALLE", values="FECHA", aggfunc="count", fill_value=0)
                    mi_tp["TOTAL"] = mi_tp.sum(axis=1)
                    
                    # Estructura limpia sin números 0,1,2
                    mi_tp.index.name = "VENDEDORES"
                    
                    st.dataframe(
                        mi_tp,
                        use_container_width=True,
                        column_config={
                            "_index": st.column_config.Column("VENDEDORES", width="medium"),
                        }
                    )

                    # --- 2. LUEGO: LA DONA ---
                    fig_m = px.pie(df_hoy, names='DETALLE', hole=0.5)
                    fig_m.update_layout(
                        margin=dict(t=20, b=0, l=0, r=0),
                        height=250,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
                    )
                    st.plotly_chart(fig_m, use_container_width=True)
                    
                else:
                    st.info("Aún no tienes registros guardados hoy.")

                # 3. AVANCE DEL MES (RANKING)
                st.markdown("##### **3. Avance del Mes**")
                mi_rd = df_mio.pivot_table(index="NOMBRE VENDEDOR", columns="FECHA", values="DETALLE", aggfunc="count", fill_value=0)
                mi_rd = mi_rd.reindex(sorted(mi_rd.columns, reverse=True), axis=1)
                mi_rd["TOTAL"] = mi_rd.sum(axis=1)
                
                # st.table es más "estático" y respeta mejor la izquierda que st.dataframe
                st.table(mi_rd.style.applymap(lambda v: 'background-color: #90EE90;' if isinstance(v, (int, float)) and v >= 40 else '', subset=mi_rd.columns[:-1]))


        else:
            st.error("Error al cargar registros.")

# --- PESTAÑA 3: DASHBOARD (ADMIN - ALINEACIÓN IZQUIERDA & TABLAS PURAS) ---
with tab2:
    st.markdown("##### 🔐 Acceso Administrador")
    col_adm1, col_adm2 = st.columns(2)
    with col_adm1: admin_user = st.text_input("Usuario", key="adm_u_final")
    with col_adm2: admin_pass = st.text_input("Contraseña", type="password", key="adm_p_final")

    if admin_user == "admin" and admin_pass == "Diamire2026*":
        st.success("🔓 Acceso Concedido")
        if not df_registros.empty:
            df_registros['DETALLE'] = df_registros['DETALLE'].astype(str).str.strip().str.upper()
            
            # FILTROS
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
                rh = rh.sort_values(by="TOTAL", ascending=False)

                # --- CONFIGURACIÓN SIMPLE Y SEGURA ---
                rh.index.name = "VENDEDORES"

                st.dataframe(
                    rh, 
                    use_container_width=True,
                    column_config={
                        # Esto quita los números 0,1,2 y pone "VENDEDORES" a la izquierda
                        "_index": st.column_config.Column("VENDEDORES", width="medium"),
                        # Para el resto, Streamlit pondrá los números y títulos a la derecha por defecto
                    }
                )
            else:
                st.info("No hay datos para esta fecha.")
                
# 2. RANKING METAS
            st.divider()
            st.markdown("##### **2. Ranking Metas (Meta ≥ 40)**")
            
            # 1. Preparar datos con fecha corta
            df_ranking = df_f.copy()
            df_ranking["FECHA_CORTE"] = pd.to_datetime(df_ranking["FECHA"], dayfirst=True).dt.strftime('%d/%m')
            
            rd = df_ranking.pivot_table(index="NOMBRE VENDEDOR", columns="FECHA_CORTE", values="DETALLE", aggfunc="count", fill_value=0)
            rd = rd.reindex(sorted(rd.columns, reverse=True), axis=1)
            rd["TOTAL ACUM"] = rd.sum(axis=1)
            rd = rd.sort_values(by="TOTAL ACUM", ascending=False)

            # --- ESTRUCTURA CLAVE (IGUAL A LA MATRIZ) ---
            rd.index.name = "VENDEDORES"

            st.dataframe(
                rd.style.applymap(
                    lambda v: 'background-color: #90EE90;' if isinstance(v, (int, float)) and v >= 40 else '', 
                    subset=rd.columns[:-1]
                ).set_properties(**{'text-align': 'left'}),
                use_container_width=True,
                column_config={
                    "_index": st.column_config.Column("VENDEDORES", width="medium")
                }
            )

            # --- BOTÓN DE DESCARGA (UBICADO AQUÍ SEGÚN TU PEDIDO) ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                rd.to_excel(wr, sheet_name='Ranking_Metas')
            st.download_button(
                label="📥 Descargar Ranking Metas (Excel)",
                data=buf.getvalue(),
                file_name=f"Ranking_{dia_sel.replace('/','-')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

# 3. MATRIZ PRODUCTIVIDAD (VERSIÓN FINAL LIMPIA)
            st.divider()
            st.markdown(f"##### **3. Matriz de Productividad ({z_sel})**")
            
            # Crear la tabla base
            tp = df_f.pivot_table(index="NOMBRE VENDEDOR", columns="DETALLE", values="FECHA", aggfunc="count", fill_value=0)
            
            # 1. Totales
            tp["TOTAL"] = tp.sum(axis=1)
            tp = tp.sort_values(by="TOTAL", ascending=False)
            
            # 2. Fila de Totales Verticales
            df_totales_v = pd.DataFrame(tp.sum()).T
            df_totales_v.index = ["TOTAL GENERAL"]
            
            # 3. Unir
            tp_final = pd.concat([tp, df_totales_v])

            # --- ESTA ES LA PARTE CLAVE ---
            # Ponemos el nombre "VENDEDORES" al índice
            tp_final.index.name = "VENDEDORES"

            # Mostramos con st.dataframe (en lugar de st.table) 
            # porque permite ocultar la columna de números fácilmente
            st.dataframe(
                tp_final.style.set_properties(**{'text-align': 'left'})
                .set_properties(subset=(['TOTAL GENERAL'], slice(None)), **{'background-color': '#FFEB9C', 'font-weight': 'bold'}),
                use_container_width=True,
                column_config={
                    "_index": st.column_config.Column("VENDEDORES", width="medium")
                }
            )
            
    elif admin_user != "" or admin_pass != "":
        st.error("❌ Credenciales incorrectas.")










