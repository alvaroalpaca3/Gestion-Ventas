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

# --- LOGO SEGURO ---
import os

# Buscamos el archivo en el sistema
if os.path.exists("logo.png"):
    try:
        # Usamos un contenedor para que si falla no rompa la app
        st.sidebar.image("logo.png", use_container_width=True)
    except:
        st.sidebar.write("🖼️ **Dimiare**") # Texto de respaldo si la imagen falla
else:
    st.sidebar.write("🖼️ **Dimiare**")

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
st.header("📊REGISTRO DE GESTIÓN DIARIA")

tab1, tab2 = st.tabs(["📝 REGISTRO", "📊 DASHBOARD"])

with tab1:
    st.markdown("#### 📝 REGISTRO DE VENTAS")
    
    detalle = st.selectbox("DETALLE DE GESTIÓN *", ["SELECCIONA", "VENTA FIJA", "NO-VENTA", "CLIENTE AGENDADO", "REFERIDO"])
    
    # Usamos el form_key para resetear el formulario tras guardar
    with st.form(key=f"registro_form_{st.session_state.form_key}"):
        # 1. Inicialización de variables
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

        # EL BOTÓN DEBE ESTAR DENTRO DEL BLOQUE 'WITH' (con 8 espacios de sangría)
        submit = st.form_submit_button("💾 GUARDAR GESTIÓN", use_container_width=True)

        # LA LÓGICA DE VALIDACIÓN TAMBIÉN DEBE ESTAR DENTRO DEL 'WITH'
        if submit:
            error = False
            # Validaciones de Seguridad y Acceso
            if nom_v == "N/A":
                st.error("❌ Acceso denegado: Ingrese su DNI en la barra lateral.")
                error = True
            elif detalle == "SELECCIONA":
                st.error("❌ Debe seleccionar un tipo de gestión.")
                error = True
                
            # Validación para VENTA / AGENDADO
            elif detalle in ["VENTA FIJA", "CLIENTE AGENDADO"]:
                if not n_cl.strip() or not dir_ins.strip() or not mail.strip():
                    st.error("❌ Nombre, Dirección y Email son obligatorios.")
                    error = True
                elif len(d_cl) != 8 or not d_cl.isdigit():
                    st.error("❌ DNI Cliente inválido.")
                    error = True
                elif len(c1) != 9 or not c1.isdigit():
                    st.error("❌ Celular Cliente inválido.")
                    error = True
                elif len(n_ped) != 10 or not n_ped.isdigit():
                    st.error("❌ N° Pedido debe tener 10 dígitos.")
                    error = True
                elif len(c_fe) != 13:
                    st.error("❌ El código FE debe tener 13 caracteres.")
                    error = True
                elif t_op == "SELECCIONA" or prod == "SELECCIONA":
                    st.error("❌ Seleccione Operación y Producto.")
                    error = True

            # Validación para REFERIDO (Campos obligatorios ahora)
            elif detalle == "REFERIDO":
                if not n_ref.strip():
                    st.error("❌ El nombre del referido es obligatorio.")
                    error = True
                elif len(c_ref) != 9 or not c_ref.isdigit():
                    st.error("❌ El Celular del Referido debe tener 9 dígitos numéricos.")
                    error = True

            # Validación NO-VENTA
            elif detalle == "NO-VENTA" and m_nv == "SELECCIONA":
                st.error("❌ Seleccione motivo de No-Venta.")
                error = True

            # --- GUARDADO FINAL ---
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
    
    # --- CSS PARA CENTRADO ---
    st.markdown("""
        <style>
            .stDataFrame th {text-align: center !important;}
            .stDataFrame td {text-align: center !important;}
        </style>
    """, unsafe_allow_html=True)
    
    if df_registros.empty:
        st.info("Aún no hay datos registrados.")
    else:
        # 1. Limpieza preventiva de datos para asegurar que sume todo
        df_registros['DETALLE'] = df_registros['DETALLE'].astype(str).str.strip().str.upper()

        # --- FILTROS ---
        c_f1, c_f2, c_f3 = st.columns(3)
        with c_f1:
            dias_unicos = sorted(df_registros["FECHA"].unique().tolist(), reverse=True)
            dia_sel = st.selectbox("📅 Día Control Horario", dias_unicos)
        with c_f2:
            zonales = ["TODOS"] + sorted(df_registros["ZONAL"].unique().astype(str).tolist())
            zonal_sel = st.selectbox("Zonal (Histórico)", zonales)
        with c_f3:
            # Filtrado dinámico
            df_temp = df_registros.copy()
            if zonal_sel != "TODOS":
                df_temp = df_temp[df_temp["ZONAL"] == zonal_sel]
            
            supervisores = ["TODOS"] + sorted(df_temp["SUPERVISOR"].unique().astype(str).tolist())
            sup_sel = st.selectbox("Supervisor (Histórico)", supervisores)

        # Aplicar filtros finales al DataFrame que usaremos
        df_final = df_temp.copy()
        if sup_sel != "TODOS":
            df_final = df_final[df_final["SUPERVISOR"] == sup_sel]

        # --- SECCIÓN 1: MONITOR HORARIO (HOY) ---
        st.divider()
        st.markdown(f"⏰ **Actividad por Horas ({dia_sel})**")
        df_hoy = df_final[df_final["FECHA"] == dia_sel]
        
        if not df_hoy.empty:
            # Contamos CUALQUIER gestión en DETALLE (Venta, No-Venta, Referido)
            ranking_h = df_hoy.pivot_table(index="NOMBRE VENDEDOR", columns="HORA", values="DETALLE", aggfunc="count", fill_value=0)
            ranking_h["TOTAL"] = ranking_h.sum(axis=1)
            ranking_h = ranking_h.sort_values(by="TOTAL", ascending=False)
            
            st.dataframe(
                ranking_h.astype(str).replace('0', '-').style.set_properties(**{'text-align': 'center'})
                .set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
                .set_properties(subset=['TOTAL'], **{'background-color': '#CCE5FF', 'color': '#004085', 'font-weight': 'bold'}),
                use_container_width=True
            )

        # --- SECCIÓN 2: RANKING DE METAS (HISTÓRICO) ---
        st.divider()
        st.markdown("🏆 **Ranking de Metas Diarias (Meta: ≥ 40)**")
        
        if not df_final.empty:
            ranking_d = df_final.pivot_table(index="NOMBRE VENDEDOR", columns="FECHA", values="DETALLE", aggfunc="count", fill_value=0)
            # Ordenar fechas de más reciente a más antigua
            ranking_d = ranking_d.reindex(sorted(ranking_d.columns, reverse=True), axis=1)
            
            cols_fechas = ranking_d.columns.tolist()
            ranking_d["TOTAL ACUMULADO"] = ranking_d.sum(axis=1)
            ranking_d = ranking_d.sort_values(by="TOTAL ACUMULADO", ascending=False)

            def style_metas(val):
                try:
                    if int(val) >= 40:
                        return 'background-color: #90EE90; color: #004D00; font-weight: bold; text-align: center;'
                except: pass
                return 'text-align: center;'

            st.dataframe(
                ranking_d.astype(str).style.set_properties(**{'text-align': 'center'})
                .set_table_styles([{'selector': 'th', 'props': [('text-align', 'center')]}])
                .applymap(style_metas, subset=cols_fechas)
                .set_properties(subset=['TOTAL ACUMULADO'], **{'background-color': '#CCE5FF', 'color': '#004085', 'font-weight': 'bold'})
                , use_container_width=True
            )

            # --- BOTÓN EXCEL ---
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                ranking_d.to_excel(writer, sheet_name='Ranking')
            st.download_button("📥 Descargar Reporte a Excel", data=buffer.getvalue(), 
                               file_name=f"Metas_Vendedores.xlsx", use_container_width=True)

# --- SECCIÓN 3: COMPOSICIÓN DE GESTIONES (GRÁFICA DE DONA) ---
            st.divider()
            st.markdown(f"📊 **Composición de Gestiones ({zonal_sel} - {sup_sel})**")

            if not df_final.empty:
                # 1. LIMPIEZA CRÍTICA: Quitamos espacios y uniformamos mayúsculas
                df_temp_graf = df_final.copy()
                df_temp_graf['DETALLE'] = df_temp_graf['DETALLE'].astype(str).str.strip().str.upper()

                # 2. Agrupamos sumando las ocurrencias
                df_donut = df_temp_graf['DETALLE'].value_counts().reset_index()
                df_donut.columns = ['Gestión', 'Total']
                
                # 3. Calculamos el total real de la suma
                total_real = int(df_donut['Total'].sum())

                import plotly.express as px
                
                # 4. Creamos la Dona
                fig = px.pie(
                    df_donut, 
                    values='Total', 
                    names='Gestión', 
                    hole=0.5,
                    color_discrete_sequence=px.colors.qualitative.Safe,
                    template='plotly_white'
                )

                # 5. Etiquetas: Cantidad + Porcentaje
                fig.update_traces(
                    texttemplate='<b>%{label}</b><br>%{value} uds.<br>%{percent}',
                    textposition='outside',
                    pull=[0.02] * len(df_donut),
                    marker=dict(line=dict(color='#FFFFFF', width=2))
                )

                # 6. Texto Central SINCRONIZADO
                fig.add_annotation(
                    text=f"TOTAL<br><b>{total_real}</b>",
                    showarrow=False,
                    font=dict(size=22, color='#004085'),
                    x=0.5, y=0.5
                )

                # 7. Ajustes de diseño
                fig.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                    height=500,
                    margin=dict(l=50, r=50, t=30, b=100)
                )

                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.warning("No hay datos para mostrar en la gráfica.")
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.warning("No hay datos para mostrar en la gráfica.")

