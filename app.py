# Conector Streamlit Cloud, el puente entre un movil y nuestro motor

import streamlit as st
import dropbox
import pandas as pd
import io
from datetime import datetime

# --- CONFIGURACIÓN ---
# Aquí pegarás tu Token (entre las comillas)
DROPBOX_TOKEN = "sl.u.AGXRI3K_UoBkOGHoEX37oXnywVyfiKE-JhumRiC4i6sCyvjsNeMA3LcYWfWKIrsT0ZI_YQ8LtZx1qtlawSpUUuSzEYt_0Gk3i0cTJza-DcknXJP1mPw_ExGWa0Wrw9qGlxiehhrCgoHeMKNJMXYePhTXJeMTAelvIezdnvBus-rSrW5Xg0EZ-adG8Mi13It0ryMeUb1GDy3gqWgocPrpZSpXHuH8Ivxdtf_JDIyKxEEqlQmZBWorf5X1CzbGf0SOHbH8RvGRWdGGd3wgjW7eNwnMBiVIBGunhYoVZyETmpgo4PFp_lWEEi4uLxTsYvBUL1VqQnG2aQIdPgKJSZUvvzY2rYCoaHvwCY2ES60-cPbM3LtZo3yjxL9LvV34zi42CjA_o7gTGSl__py96rzQnAN2S1rpZB3sa98M7HsVm0PBdAa36XO8dOtPb11Z5BfFZBD9eWNcpEliJQsUudOhDhllxa186TMUun7IQh7Du2QRx6Q9aFONw_9JwMORClqV096RPudzNO0HBVE2NVAde8PpeklzDAZpJqH11yqGOJrKjFPPHmfRMSo_pWkQ4_viIqUaJ_HL3qMXRC-5KtZ0gxzxl0dQlJDUiTxpe0rD69ylPkhGFM61sVVHXnKR0hHEvExfAZOqSxarx1f08zCrahb9ABrQ_BdXEr0MdquX8I-PFM4mJNBz383R7aIuoQ7Y4ijpNYFlEPwJRgddalg0ez7IriDRSVW6MVBsLN6ktWMhZ_yWsVDeFyrBGllt56NDSo8-yWf79k8EHziq_xo5uBRWHZHk9tvBGBMQ3R2Qki7qQdX1jMLXL3q4g2m8uIp7RwRynV3Zqp918N-GTWF_B1hCqpWbyH3-ORXAjsnrBSADLAeD8iqhuIU9vbDekjCkEHom4c4I9nfJsS0nNvjrFKNsoNaEUYVzGK9cVS8MaQvAp7t5UvSbM_D4BY_cPtq1rItbxnPLlVqldnls9rPmdcgWUwlELRidxBUfW1HC3BVARMYVo6wY0B4F9J7bosxz0dC4wWGx85ej9bpxBue95Hau5bTsA_TBukh84fqGYZxx2QiLDBxSAa04myHb3oQwxsbOJj_qm4joB6kyjfWTvHdLTkOkoX4NTcC6ZQmj9kCmBvH8xFTzzJlB9CI1v3VOMkdBmhHr7RgKJVaMbEi9KNqw-AfO9TpyD1GAB5XwqLDohl4E43wNpgSrF4gTRC5nfvoWzqwrZN51ZWcqy0AL93dvV_wmDmMf_DRNDph-hUHFmIlUuENqKLEenYh_nQmq5TzDJlg_iMBk46FplLRdG2KGbeTHdzHrcaD1E_oC72ssXB8pXqB5kVzvI07Hw_A3llo" 
NOMBRE_ARCHIVO = "/GestionDiaria.xlsx" # Asegúrate que empiece con /

# --- FUNCIÓN PARA GUARDAR EN DROPBOX ---
def guardar_en_dropbox(nombre, nota):
    try:
        dbx = dropbox.Dropbox(DROPBOX_TOKEN)
        
        # 1. Descargar el archivo actual
        _, res = dbx.files_download(NOMBRE_ARCHIVO)
        df = pd.read_excel(io.BytesIO(res.content))
        
        # 2. Crear la nueva fila
        nueva_fila = {
            "Nombre": nombre,
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Nota": nota
        }
        
        # 3. Añadir la fila al Excel
        df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
        
        # 4. Volver a subir el archivo actualizado
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        dbx.files_upload(buffer.read(), NOMBRE_ARCHIVO, mode=dropbox.files.WriteMode.overwrite)
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- INTERFAZ PARA EL CELULAR ---
st.set_page_config(page_title="Registro Rápido", page_icon="📝")

st.title("📝 Nuevo Registro")
st.write("Completa los campos abajo:")

with st.form("mi_formulario", clear_on_submit=True):
    nombre_input = st.text_input("Tu Nombre")
    nota_input = st.text_area("Escribe la Nota o Actividad")
    
    boton = st.form_submit_button("Enviar Registro")

if boton:
    if nombre_input and nota_input:
        with st.spinner("Guardando en Dropbox..."):
            exito = guardar_en_dropbox(nombre_input, nota_input)
            if exito:
                st.success("¡Guardado correctamente! Ya puedes cerrar esta pestaña.")
    else:
        st.warning("Por favor rellena todos los campos.")