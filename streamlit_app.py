import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ======================================================
# Datos de conexión a Supabase (mantén el formato proporcionado)
# ======================================================
url = "https://ipwhnkvepshnbrpymwmn.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlwd2hua3ZlcHNobmJycHltd21uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQyMjA0MzksImV4cCI6MjA1OTc5NjQzOX0.R7QApURC5kdpjjXDKasQdtDQBIL_C6xnuSdqcDuZpBM"
supabase = create_client(url, key)
st.write("Conexión a Supabase establecida.")

# ======================================================
# Dashboard de Quejas
# ======================================================
# Aplicar algunos estilos personalizados
st.markdown(
    """
    <style>
    .main {background-color: #F9F9F9; padding: 1rem; }
    h1 {color: #2C3E50; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;}
    .metric {font-size: 1.5rem; color: #2C3E50; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

st.title("Dashboard de Quejas")
st.markdown("---")

# Botón para actualizar los datos (limpia la caché)
if st.button("Actualizar datos"):
    st.cache_data.clear()

# ======================================================
# Función para cargar todos los datos desde Supabase con paginación
# ======================================================
@st.cache_data(ttl=60)
def load_all_data(batch_size=1000):
    start = 0
    all_records = []
    while True:
        res = supabase.table("quejas_ordenes") \
                      .select("*", count="exact") \
                      .range(start, start + batch_size - 1) \
                      .execute()
        batch = res.data
        if not batch:
            break
        all_records.extend(batch)
        if len(batch) < batch_size:
            break
        start += batch_size
    return pd.DataFrame(all_records)

# Cargar los datos desde Supabase
df = load_all_data()

# Convertir la columna "fecha" a datetime, si es necesario
if "fecha" in df.columns:
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

# ======================================================
# Panel de Filtros en la barra lateral (sidebar)
# ======================================================
st.sidebar.markdown("## Filtros de Quejas")

# Filtro de Marca
if "marca" in df.columns:
    marcas = sorted(df["marca"].dropna().unique())
else:
    marcas = []
selected_marca = st.sidebar.selectbox("Selecciona una marca:", ["Todas"] + marcas)

# Filtro de Plataforma
if "plataforma" in df.columns:
    plataformas = sorted(df["plataforma"].dropna().unique())
else:
    plataformas = []
selected_plataforma = st.sidebar.selectbox("Selecciona una plataforma:", ["Todas"] + plataformas)

# Filtro de Turno
if "turno" in df.columns:
    turnos = sorted(df["turno"].dropna().unique())
else:
    turnos = []
selected_turno = st.sidebar.selectbox("Selecciona el turno:", ["Todos"] + ["Matutino", "Vespertino"])

# Filtro por rango de fechas
if "fecha" in df.columns and not df["fecha"].empty:
    min_date = df["fecha"].min().date()
    max_date = df["fecha"].max().date()
else:
    min_date = datetime.today().date()
    max_date = datetime.today().date()

start_date = st.sidebar.date_input("Fecha inicio:", min_value=min_date, max_value=max_date, value=min_date)
end_date = st.sidebar.date_input("Fecha fin:", min_value=min_date, max_value=max_date, value=max_date)

# ======================================================
# Filtrado del DataFrame según filtros seleccionados
# ======================================================
filtered_df = df.copy()

if selected_marca != "Todas" and "marca" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["marca"] == selected_marca]

if selected_plataforma != "Todas" and "plataforma" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["plataforma"] == selected_plataforma]

if selected_turno != "Todos" and "turno" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["turno"] == selected_turno]

if "fecha" in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df["fecha"].dt.date >= start_date) &
                              (filtered_df["fecha"].dt.date <= end_date)]

# ======================================================
# Sección de Métricas Generales
# ======================================================
st.markdown("## Métricas Generales")
total_ordenes = len(filtered_df)
total_quejas = filtered_df["tiene_queja"].sum() if "tiene_queja" in filtered_df.columns else 0
porc_quejas = (total_quejas / total_ordenes * 100) if total_ordenes > 0 else 0

# Métrica de retrasos: Total Retrasos y % de retrasos (ordenes con retraso > 0)
if "retraso" in filtered_df.columns:
    total_retrasos = filtered_df["retraso"].sum()
    num_ordenes_retrasadas = filtered_df[filtered_df["retraso"].notnull() & (filtered_df["retraso"] > 0)].shape[0]
    porc_retrasos = (num_ordenes_retrasadas / total_ordenes * 100) if total_ordenes > 0 else 0
else:
    total_retrasos = 0
    porc_retrasos = 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total de Órdenes", total_ordenes)
col2.metric("Total de Quejas", total_quejas)
col3.metric("% de Quejas", f"{porc_quejas:.2f}%")
col4.metric("Total Retrasos", total_retrasos)
col5.metric("% de Retrasos", f"{porc_retrasos:.2f}%")
st.markdown("---")

# ======================================================
# Sección: Comentarios y Quejas por Categoría
# ======================================================
st.markdown("## Comentarios y Quejas por Categoría")
if "tiene_queja" in filtered_df.columns:
    df_quejas = filtered_df[filtered_df["tiene_queja"] == 1].copy()
else:
    df_quejas = pd.DataFrame()

if not df_quejas.empty:
    if "comentario" in df_quejas.columns and "categoria" in df_quejas.columns:
        df_comentarios = df_quejas[
            df_quejas["comentario"].notna() & (df_quejas["comentario"].str.strip() != "")
        ][["categoria", "comentario"]]
        if not df_comentarios.empty:
            st.markdown("**Comentarios registrados y su categoría:**")
            st.dataframe(df_comentarios)
        else:
            st.write("No se encontraron comentarios registrados.")
    else:
        st.write("No hay datos de comentarios o categoría.")
    
    if "categoria" in df_quejas.columns:
        tabla_categorias = df_quejas.groupby("categoria").size().reset_index(name="Cantidad de Quejas")
        st.markdown("**Número de Quejas por Categoría:**")
        st.dataframe(tabla_categorias)
else:
    st.write("No hay quejas registradas para mostrar.")
st.markdown("---")

# ======================================================
# Sección: Número Total de Quejas por Marca
# ======================================================
st.markdown("## Número Total de Quejas por Marca")
if "tiene_queja" in filtered_df.columns and "marca" in filtered_df.columns:
    df_quejas_marca = filtered_df[filtered_df["tiene_queja"] == 1].copy()
    if not df_quejas_marca.empty:
        tabla_marcas = df_quejas_marca.groupby("marca").size().reset_index(name="Total de Quejas")
        st.dataframe(tabla_marcas)
    else:
        st.write("No hay quejas registradas para mostrar por marca.")
else:
    st.write("No hay datos de marca o quejas.")
