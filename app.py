import streamlit as st
import polars as pl
import plotly.express as px
import gc
import json

import psutil
import os
import time

# ---------------- CONFIGURACIÓN DE PÁGINA ---------------- #
st.set_page_config(
    page_title="Delitos en Argentina",
    page_icon="🚓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

ACCENT_COLOR = "#328ec0"

# ---------------- CSS PERSONALIZADO ---------------- #
st.markdown(
    f"""
    <style>
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }}
    :root {{
        --primary-color: {ACCENT_COLOR};
        --accent-color: {ACCENT_COLOR};
        --secondary-background-color: #f0f2f6;
    }}
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        color: {ACCENT_COLOR} !important;
    }}
    .stTabs [data-baseweb="tab-list"] button:hover {{
        color: {ACCENT_COLOR} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: {ACCENT_COLOR} !important;
    }}
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{
        border: 0px solid {ACCENT_COLOR} !important;
        border-radius: 0.5rem !important;
    }}
    .stMultiSelect [data-baseweb="tag"] {{
        background-color: {ACCENT_COLOR} !important;
        color: white !important;
        border-radius: 0.5rem !important;
        padding: 2px 6px !important;
    }}
    .metric-card {{
        height: 11rem;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        text-align: center;
        color: white;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 1rem;
    }}
    .metric-tasa {{ background: linear-gradient(to bottom right, #3fbbe2, #6392de); }}
    .metric-variacion {{ background: linear-gradient(to bottom right, #7b59b3, #5546b7); }}
    .metric-delitos {{ background: linear-gradient(to bottom right, #df437e, #b755a5); }}
    .metric-victimas {{ background: linear-gradient(to bottom right, #eeaf2a, #ef8154); }}
    .metric-value {{ font-size: 2rem; font-weight: bold; margin: 0; }}
    .metric-title {{ font-size: 1.1rem; margin: 0; }}
    .metric-subtitle {{ font-size: 0.8rem; margin: 0; }}
    .stAlertContainer {{
        background: rgb(240, 242, 246) !important;
        color: #262730 !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- CARGA OPTIMIZADA DE DATOS ---------------- #
@st.cache_data(show_spinner=True)
def load_data():
    try:
        # Leer solo las columnas necesarias
        columns = [
            "anio", "categoria_delito", "codigo_delito_snic_nombre",
            "provincia_nombre", "depto_nombre_completo",
            "cantidad_hechos", "cantidad_victimas",
            "poblacion_departamento", "poblacion_provincia", "poblacion_pais"
        ]

        # Carga perezosa (lazy)
        df_lazy = (
            pl.scan_parquet("DATOS_SNIC_POB.parquet")
            .select(columns)
            .with_columns([
                pl.col("categoria_delito").cast(pl.Categorical),
                pl.col("codigo_delito_snic_nombre").cast(pl.Categorical),
                pl.col("provincia_nombre").cast(pl.Categorical),
                pl.col("depto_nombre_completo").cast(pl.Categorical),
                pl.col("anio").cast(pl.Int16),
                pl.col("cantidad_hechos").cast(pl.Int32),
                pl.col("cantidad_victimas").cast(pl.Int32),
                pl.col("poblacion_departamento").cast(pl.Int32),
                pl.col("poblacion_provincia").cast(pl.Int32),
                pl.col("poblacion_pais").cast(pl.Int32),
            ])
        )

        return df_lazy

    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return None

@st.cache_data
def load_geojson():
    try:
        with open("ar.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("No se encontró el archivo ar.json")
        return None

df_lazy = load_data()
argentina_geo = load_geojson()

# ---------------- TÍTULO ---------------- #
st.title("Delitos en Argentina")

# ---------------- TABS ---------------- #
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Vista general", 
    "Categorías y tipos de delitos", 
    "Comparar provincias", 
    "Comparar departamentos", 
    "Fuentes y metodología"
])

# ---------------- TAB 1: VISTA GENERAL ---------------- #
with tab1:
    df = df_lazy.clone()
    col1, col2 = st.columns([1, 4], gap="medium")

    # ------------------- FILTROS ------------------- #
    with col1:
        st.markdown("**Filtros**")

        # Filtro de año
        años_disponibles = (
            df.select(pl.col("anio").unique())
            .collect()["anio"]
            .to_list()
        )
        año_seleccionado = st.selectbox("Año", sorted(años_disponibles, reverse=True))

        # Categorías de delito
        categorias_delito = ['Todas'] + sorted(
            df.select(pl.col("categoria_delito").unique()).collect()["categoria_delito"].to_list()
        )
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito)
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # Tipos de delito dependientes de la categoría
        if 'Todas' in categoria_delito_seleccionadas:
            tipos_disponibles = sorted(
                df.select(pl.col("codigo_delito_snic_nombre").unique()).collect()["codigo_delito_snic_nombre"].to_list()
            )
        else:
            tipos_disponibles = (
                df.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                .select(pl.col("codigo_delito_snic_nombre").unique())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )
            tipos_disponibles = sorted(tipos_disponibles)

        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito)
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        # Provincias
        provincias_disponibles = ['Todas'] + sorted(
            df.select(pl.col("provincia_nombre").unique()).collect()["provincia_nombre"].to_list()
        )
        provincia_seleccionada = st.selectbox("Provincia", provincias_disponibles)

        # Departamentos dependientes de provincia
        if provincia_seleccionada != 'Todas':
            departamentos_disponibles = (
                df
                .filter(pl.col("provincia_nombre") == provincia_seleccionada)
                .select(pl.col("depto_nombre_completo").unique())
                .collect()["depto_nombre_completo"]
                .to_list()
            )
        else:
            departamentos_disponibles = sorted(
                df.select(pl.col("depto_nombre_completo").unique()).collect()["depto_nombre_completo"].to_list()
            )

        departamento = ['Todos'] + sorted(departamentos_disponibles)
        departamento_seleccionado = st.selectbox("Departamento", departamento)

        # Mostrar filtros aplicados
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}  
        
        • **Categorías:** {", ".join(map(str, categoria_delito_seleccionadas))}  
        
        • **Tipos de delito:** {", ".join(map(str, tipo_delito_seleccionados))}  
        
        • **Provincia:** {provincia_seleccionada}  
        
        • **Departamento:** {departamento_seleccionado}
        """)

    with col2:
        # Base Lazy
        df_filtered = df.filter(pl.col("anio") == año_seleccionado)
        año_anterior = año_seleccionado - 1
        df_anterior = df.filter(pl.col("anio") == año_anterior)

        # Aplicar filtros (sin cargar aún)
        if "Todas" not in categoria_delito_seleccionadas:
            df_filtered = df_filtered.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
            df_anterior = df_anterior.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))

        if "Todos" not in tipo_delito_seleccionados:
            df_filtered = df_filtered.filter(pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados))
            df_anterior = df_anterior.filter(pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados))

        if departamento_seleccionado != "Todos":
            df_filtered = df_filtered.filter(pl.col("depto_nombre_completo") == departamento_seleccionado)
            df_anterior = df_anterior.filter(pl.col("depto_nombre_completo") == departamento_seleccionado)
            col_poblacion = "poblacion_departamento"

        elif provincia_seleccionada != "Todas":
            df_filtered = df_filtered.filter(pl.col("provincia_nombre") == provincia_seleccionada)
            df_anterior = df_anterior.filter(pl.col("provincia_nombre") == provincia_seleccionada)
            col_poblacion = "poblacion_provincia"

        else:
            col_poblacion = "poblacion_pais"

        # Materializar recién ahora (carga real en memoria)
        df_año = df_filtered.collect(streaming=True)
        df_prev = df_anterior.collect(streaming=True)

        # Cálculos
        poblacion = df_año[col_poblacion].max()
        poblacion_prev = df_prev[col_poblacion].max()

        total_hechos = df_año["cantidad_hechos"].sum()
        total_hechos_prev = df_prev["cantidad_hechos"].sum()
        tasa = (total_hechos / poblacion) * 100000
        tasa_prev = (total_hechos_prev / poblacion_prev) * 100000
        variacion = ((tasa - tasa_prev) / tasa_prev) * 100 if tasa_prev != 0 else 0
        total_victimas = df_año["cantidad_victimas"].sum()

        st.markdown(f"#### Métricas {año_seleccionado}")

        if año_seleccionado != 2014:

            # Mostrar métricas
            col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
            
            with col_metric1:

                st.markdown(f"""
                <div class="metric-card metric-tasa">
                    <div class="metric-value">{tasa:,.2f}</div>
                    <div class="metric-title">Tasa de delitos</div>
                    <div class="metric-subtitle">Cantidad de delitos cada 100 mil habitantes</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_metric2:

                st.markdown(f"""
                <div class="metric-card metric-variacion">
                    <div class="metric-value">{variacion:.2f}%</div>
                    <div class="metric-title">Variación anual</div>
                    <div class="metric-subtitle">Cambio porcentual en la tasa respecto a {año_anterior}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_metric3:
                
                st.markdown(f"""
                <div class="metric-card metric-delitos">
                    <div class="metric-value">{total_hechos:,.0f}</div>
                    <div class="metric-title">Delitos</div>
                    <div class="metric-subtitle">Cantidad de hechos informados al SNIC</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_metric4:
            
                st.markdown(f"""
                <div class="metric-card metric-victimas">
                    <div class="metric-value">{total_victimas:,.0f}</div>
                    <div class="metric-title">Víctimas</div>
                    <div class="metric-subtitle">Cantidad total de víctimas</div>
                </div>
                """, unsafe_allow_html=True)
            
        else: 
            col_metric1, col_metric2, col_metric3 = st.columns(3)

            with col_metric1:
                st.markdown(f"""
                <div class="metric-card metric-tasa">
                    <div class="metric-value">{tasa:,.2f}</div>
                    <div class="metric-title">Tasa de delitos</div>
                    <div class="metric-subtitle">Delitos cada 100 mil habitantes</div>
                </div>
                """, unsafe_allow_html=True)

            with col_metric2:
                st.markdown(f"""
                <div class="metric-card metric-delitos">
                    <div class="metric-value">{total_hechos:,.0f}</div>
                    <div class="metric-title">Delitos</div>
                    <div class="metric-subtitle">Hechos informados al SNIC</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_metric3:
                st.markdown(f"""
                <div class="metric-card metric-victimas">
                    <div class="metric-value">{total_victimas:,.0f}</div>
                    <div class="metric-title">Víctimas</div>
                    <div class="metric-subtitle">Cantidad total de víctimas</div>
                </div>
                """, unsafe_allow_html=True)
        
        # Gráficos de evolución 
        st.markdown("#### Evolución a lo largo de los años")

        df_graficos = df_lazy.clone()

        # --- Aplicar filtros ---
        if "Todas" not in categoria_delito_seleccionadas and categoria_delito_seleccionadas:
            df_graficos = df_graficos.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))

        if "Todos" not in tipo_delito_seleccionados and tipo_delito_seleccionados:
            df_graficos = df_graficos.filter(pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados))

        if departamento_seleccionado != "Todos" and departamento_seleccionado:
            df_graficos = df_graficos.filter(pl.col("depto_nombre_completo") == departamento_seleccionado)
        elif (
            provincia_seleccionada != "Todas"
            and (departamento_seleccionado == "Todos" or not departamento_seleccionado)
            and provincia_seleccionada
        ):
            df_graficos = df_graficos.filter(pl.col("provincia_nombre") == provincia_seleccionada)

        # --- Determinar columna de población según nivel territorial ---
        if departamento_seleccionado != "Todos" and departamento_seleccionado:
            poblacion_col = "poblacion_departamento"
        elif (
            provincia_seleccionada != "Todas"
            and (departamento_seleccionado == "Todos" or not departamento_seleccionado)
            and provincia_seleccionada
        ):
            poblacion_col = "poblacion_provincia"
        else:
            poblacion_col = "poblacion_pais"

        # --- Agrupar y calcular métricas (lazy) ---
        df_graficos = (
            df_graficos
            .group_by("anio")
            .agg([
                pl.col("cantidad_hechos").sum().alias("cantidad_hechos"),
                pl.col(poblacion_col).first().alias("poblacion"),
                pl.col("cantidad_victimas").sum().alias("cantidad_victimas"),
            ])
            .sort("anio")
            .with_columns([
                (pl.col("cantidad_hechos") / (pl.col("poblacion") / 100000)).alias("tasa_delitos"),
            ])
            .with_columns([
                pl.col("tasa_delitos").shift(1).alias("tasa_delitos_anterior"),
            ])
            .with_columns([
                ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / pl.col("tasa_delitos_anterior")).alias("variacion"),
            ])
        )

        # --- Materializar LazyFrame justo antes de usarlo en los gráficos ---
        df_graficos = df_graficos.collect()

        # Liberar memoria de columnas temporales
        gc.collect()

        col_graficos1, col_graficos2 = st.columns([1, 1], gap="medium")

        min_anio = df_graficos["anio"].min()
        max_anio = df_graficos["anio"].max()

        # === Gráficos (idénticos visualmente a tu código original) ===
        with col_graficos1:
            st.markdown("###### Tasa de delitos")
            fig_evolucion = px.line(
                df_graficos, x='anio', y='tasa_delitos',
                line_shape='spline', markers=True, color_discrete_sequence=['#3fbbe2']
            )
            fig_evolucion.update_layout(
                xaxis_title="", yaxis_title="", showlegend=False,
                plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
                height=200, margin=dict(l=0, r=30, t=0, b=0)
            )
            fig_evolucion.update_traces(line=dict(width=3), marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Tasa de delitos  %{y:,.2f}<extra></extra>")
            fig_evolucion.update_xaxes(range=[min_anio-0.5, max_anio+0.5], tick0=min_anio, dtick=3,
                                    showgrid=True, gridcolor='lightgray')
            fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")
            st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": False})

            st.markdown("###### Variación en la tasa de delitos")
            fig_evolucion = px.line(
                df_graficos, x='anio', y='variacion',
                line_shape='spline', markers=True, color_discrete_sequence=['#7b59b3']
            )
            fig_evolucion.update_layout(
                xaxis_title="", yaxis_title="", showlegend=False,
                plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
                height=200, margin=dict(l=0, r=30, t=0, b=0)
            )
            fig_evolucion.add_hline(y=0, line_dash="dash", line_color="darkgrey", line_width=2)
            fig_evolucion.update_traces(line=dict(width=3), marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Variación  %{y:.2%}<extra></extra>")
            fig_evolucion.update_xaxes(range=[min_anio-0.5, max_anio+0.5], tick0=min_anio, dtick=3,
                                    showgrid=True, gridcolor='lightgray')
            fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")
            st.plotly_chart(fig_evolucion, use_container_width=True, config={"displayModeBar": False})

        with col_graficos2:
            st.markdown("###### Cantidad de delitos")
            # st.markdown("*La tasa de delitos es la cantidad de delitos cada 100,000 habitantes*")

            fig_evolucion = px.line(
                df_graficos, 
                x='anio', 
                y='cantidad_hechos',
                title="",
                line_shape='spline',
                markers=True,
                color_discrete_sequence=['#df437e']
            )
            
            fig_evolucion.update_layout(
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                height=200,
                margin=dict(l=0, r=30, t=0, b=0)
            )

            # Línea más gruesa
            fig_evolucion.update_traces(
                line=dict(width=3),
                marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Delitos  %{y:,.0f}<extra></extra>"
            )

            # Grilla y formato del eje Y con comas
            fig_evolucion.update_xaxes(
                range=[min_anio - 0.5, max_anio + 0.5],  # padding de medio año a cada lado
                tick0=min_anio,
                dtick=3,  # que muestre solo enteros (años)
                showgrid=True,
                gridcolor='lightgray'
            )
            fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")

            # Mostrar en Streamlit con modebar abajo a la derecha
            st.plotly_chart(fig_evolucion, use_container_width=True, config={"displayModeBar": False})

            st.markdown("###### Cantidad de víctimas")
            # st.markdown("*La tasa de delitos es la cantidad de delitos cada 100,000 habitantes*")
            
            fig_evolucion = px.line(
                df_graficos, 
                x='anio', 
                y='cantidad_victimas',
                title="",
                line_shape='spline',
                markers=True,
                color_discrete_sequence=['#ef8154']
            )
            
            fig_evolucion.update_layout(
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                height=200,
                margin=dict(l=0, r=30, t=0, b=0)
            )

            # Línea más gruesa
            fig_evolucion.update_traces(
                line=dict(width=3),
                marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Víctimas  %{y:,.0f}<extra></extra>"
            )

            # Grilla y formato del eje Y con comas
            fig_evolucion.update_xaxes(
                range=[min_anio - 0.5, max_anio + 0.5],  # padding de medio año a cada lado
                tick0=min_anio,
                dtick=3,  # que muestre solo enteros (años)
                showgrid=True,
                gridcolor='lightgray'
            )
            fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")

            # Mostrar en Streamlit con modebar abajo a la derecha
            st.plotly_chart(fig_evolucion, use_container_width=True, config={"displayModeBar": False})

    col_info1, col_info2 = st.columns([1, 1], gap = 'medium')

    with col_info1:
        st.info("Durante los últimos cuatro años, **la tasa de delitos creció a nivel nacional** y en 2024 superó el pico que se había alcanzado en 2019, previo a la pandemia.")
    with col_info2:
        st.info("Si filtramos por **homicidios dolosos**, se observa una tendencia a la baja: la tasa bajó de 7,50 cada 100.000 habitantes en 2014 a 3,68 en 2024.")

    del df_año, df_prev, df_filtered, df_anterior, df_graficos
    gc.collect()

# ---- Categorías y tipos de delito ----
with tab2:
    df = df.clone()
    col1, col2 = st.columns([1, 4], gap="medium")

    # =======================
    # FILTROS
    # =======================
    with col1:
        st.markdown("**Filtros**")

        # Año
        años_disponibles = sorted(
            df.select(pl.col("anio")).unique().collect()["anio"].to_list(),
            reverse=True
        )
        año_seleccionado = st.selectbox("Año", años_disponibles, key='Año tab2')

        # Categorías
        categorias_delito = ['Todas'] + sorted(
            df.select(pl.col("categoria_delito")).unique().collect()["categoria_delito"].to_list()
        )
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito, key='Categorías tab2')
        if not categoria_delito_seleccionadas or 'Todas' in categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # Tipos de delito
        if 'Todas' in categoria_delito_seleccionadas:
            tipos_disponibles = sorted(
                df.select(pl.col("codigo_delito_snic_nombre")).unique().collect()["codigo_delito_snic_nombre"].to_list()
            )
        else:
            tipos_disponibles = sorted(
                df.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                .select(pl.col("codigo_delito_snic_nombre"))
                .unique()
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )
        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito, key='Tipo de delito tab2')
        if not tipo_delito_seleccionados or 'Todos' in tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        # Provincia y departamento
        provincias_disponibles = ['Todas'] + sorted(
            df.select(pl.col("provincia_nombre")).unique().collect()["provincia_nombre"].to_list()
        )
        provincia_seleccionada = st.selectbox("Provincia", provincias_disponibles, key='Provincia tab2')

        if provincia_seleccionada != 'Todas':
            departamentos_disponibles = sorted(
                df.filter(pl.col("provincia_nombre") == provincia_seleccionada)
                .select(pl.col("depto_nombre_completo"))
                .unique()
                .collect()["depto_nombre_completo"]
                .to_list()
            )
        else:
            departamentos_disponibles = sorted(
                df.select(pl.col("depto_nombre_completo")).unique().collect()["depto_nombre_completo"].to_list()
            )
        departamento = ['Todos'] + departamentos_disponibles
        departamento_seleccionado = st.selectbox("Departamento", departamento, key='Departamento tab2')

        st.divider()
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}
        
        • **Categorías:** {", ".join(categoria_delito_seleccionadas)}
        
        • **Tipos de delito:** {", ".join(tipo_delito_seleccionados)}
        
        • **Provincia:** {provincia_seleccionada}
        
        • **Departamento:** {departamento_seleccionado}
        """)
    # =======================
    # FILTRO DE DATOS
    # =======================
    with col2:
        st.info("En 2024, más de la mitad de los delitos fueron **delitos contra la propiedad,** principalmente robos y hurtos.")

        # --- Inicializar lazy df ---
        df_filtrado = df_lazy.clone()

        # --- Aplicar filtros de manera lazy ---
        df_filtrado = df_filtrado.filter(pl.col("anio") == año_seleccionado)

        if 'Todas' not in categoria_delito_seleccionadas:
            df_filtrado = df_filtrado.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))

        if 'Todos' not in tipo_delito_seleccionados:
            df_filtrado = df_filtrado.filter(pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados))

        if departamento_seleccionado != 'Todos':
            df_filtrado = df_filtrado.filter(pl.col("depto_nombre_completo") == departamento_seleccionado)
        elif provincia_seleccionada != 'Todas':
            df_filtrado = df_filtrado.filter(pl.col("provincia_nombre") == provincia_seleccionada)

        # =======================
        # FUNCIÓN PARA GRAFICOS
        # =======================
        def plot_top5(df_grouped, col_value, col_name_short, col_name_full, title):
            # Asegurar que la columna numérica sea tipo float
            df_grouped = df_grouped.with_columns(pl.col(col_value).cast(pl.Float64))

            # Calcular porcentaje (lazy)
            total = df_grouped.select(pl.sum(col_value)).collect()[0,0]
            if total == 0 or total is None:
                st.warning(f"No hay datos suficientes para {title.lower()}.")
                return

            df_grouped = df_grouped.with_columns(
                (pl.col(col_value) / total).alias("porcentaje")
            )

            # Truncar nombres largos
            MAX_LEN = 28
            df_grouped = df_grouped.with_columns(
                pl.when(pl.col(col_name_full).cast(pl.Utf8).str.len_chars() <= MAX_LEN)
                .then(pl.col(col_name_full).cast(pl.Utf8))
                .otherwise(pl.col(col_name_full).cast(pl.Utf8).str.slice(0, MAX_LEN - 2) + "…")
                .alias(col_name_short)
            )

            # Top 5 (lazy -> collect a pandas)
            top5_pd = df_grouped.sort("porcentaje", descending=True).head(5).collect().to_pandas()

            # Agregar columna de texto con porcentaje
            top5_pd["porcentaje_text"] = top5_pd["porcentaje"].mul(100).round(1).astype(str) + "%"

            # Crear gráfico
            fig = px.bar(
                top5_pd,
                x="porcentaje",
                y=col_name_short,
                orientation="h",
                color="porcentaje",
                color_continuous_scale=["#c5b6dc", "#7b59b3"],
                text="porcentaje_text",
                custom_data=[col_name_full, col_value, "porcentaje"]
            )

            fig.update_traces(
                textposition="inside",
                insidetextanchor="start",
                textfont=dict(color="white"),
                texttemplate="  %{text}",
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                            "Porcentaje: %{customdata[2]:.2%}<br>" +
                            "Cantidad de delitos: %{customdata[1]:,}<extra></extra>"
            )

            fig.update_layout(
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(size=10),
                height=len(top5_pd) * 30,
                yaxis={"categoryorder": "total ascending"},
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(visible=False),
                bargap=0.2,
                barcornerradius=5
            )

            fig.update_coloraxes(showscale=False)
            fig.update_xaxes(
                tickformat=".0%",
                showgrid=True,
                gridcolor="lightgrey",
                gridwidth=0.5
            )

            fig.add_shape(
                type="line",
                x0=0, x1=0,
                y0=-0.5, y1=len(top5_pd) - 0.5,
                line=dict(color="lightgrey", width=1)
            )

            # Render del gráfico
            st.markdown(f"###### {title}")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"{title}_{col_value}")

            # Liberar memoria
            del top5_pd, df_grouped, fig
            gc.collect()

        # =======================
        # GRÁFICOS
        # =======================
        df_categoria = (
            df_filtrado
            .group_by("categoria_delito")
            .agg(pl.sum("cantidad_hechos").alias("cantidad_hechos"))
            .with_columns(pl.col("categoria_delito").cast(pl.Utf8))
        )

        df_tipo = (
            df_filtrado
            .group_by("codigo_delito_snic_nombre")
            .agg(pl.sum("cantidad_hechos").alias("cantidad_hechos"))
            .with_columns(pl.col("codigo_delito_snic_nombre").cast(pl.Utf8))
        )

        plot_top5(df_categoria, "cantidad_hechos", "categoria_delito_short", "categoria_delito", "Top 5 categorías de delitos según su porcentaje")
        plot_top5(df_tipo, "cantidad_hechos", "tipo_delito_short", "codigo_delito_snic_nombre", "Top 5 tipos de delitos según su porcentaje")

        # =======================
        # INFO ADICIONAL
        # =======================
        st.info("Si filtramos por Salta, podemos notar que **en Salta en 2024 el 24% de los delitos registrados fueron contravenciones,** en contraste con el 4% a nivel nacional. ¿Cuál puede ser la razón por la cual hay una mayor proporción de contravenciones en Salta?")

        st.info("Si vamos a la pestaña Comparar departamentos, podemos ver que **Tordillo (Buenos Aires)** registró la mayor tasa de delitos en 2024. Al filtrar por este departamento en esta pestaña, podemos notar que el 94% son por **tenencia atenuada para uso personal de estupefacientes.**")

        # Liberar memoria
        del df, df_filtrado, df_categoria, df_tipo
        gc.collect()

# ---- Comparar provincias ----
with tab3:
    df = df_lazy.clone()
    col1, col2 = st.columns([1, 4], gap="medium")

    with col1:
        st.markdown("**Filtros**")

        años_disponibles = sorted(df.select(pl.col('anio').unique()).collect()["anio"].to_list(), reverse=True)
        año_seleccionado = st.selectbox("Año", años_disponibles, key='Año tab3')

        categorias_delito = sorted(df.select(pl.col('categoria_delito').unique()).collect()["categoria_delito"].to_list())
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito, key='Categorías tab3')
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        if 'Todas' in categoria_delito_seleccionadas:
            tipos_disponibles = sorted(df.select(pl.col('codigo_delito_snic_nombre').unique()).collect()["codigo_delito_snic_nombre"].to_list())
        else:
            tipos_disponibles = (
                df.lazy()
                .filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                .select(pl.col("codigo_delito_snic_nombre").unique())
                .collect()
                .to_series()
                .to_list()
            )
            tipos_disponibles = sorted(tipos_disponibles)

        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito, key='Tipo de delito tab3')
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        st.divider()
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}

        • **Categorías:** {", ".join([str(categoria) for categoria in categoria_delito_seleccionadas])}

        • **Tipos de delito:** {", ".join([str(delito) for delito in tipo_delito_seleccionados])}
        """)

        st.divider()

        st.info("Si seleccionamos **homicidios dolosos** como tipo de delito, vemos que **Santa Fe** se posiciona en 2024 como la provincia con la mayor tasa del país.")
        st.info("Seleccionando la categoría de **contrabando,** vemos que **Formosa** es la provincia con mayor tasa de contrabando.")
        st.divider()
        st.info("Si utilizamos los gráficos de evolución para **comparar la tasa de delitos general de Santa Fe y Salta**, podermos ver que Santa Fe se ha mantenido relativamente estable en los últimos 15 años, mientras que Salta muestra un comportamiento más volátil y una tendencia creciente.")

    with col2:
        st.markdown(f"#### Comparación de la tasa de delitos por provincia")
        st.info(f"En 2024, Salta fue la provincia con mayor tasa de delitos.")

        # 🔹 Usar solo las columnas necesarias y convertir categóricas al vuelo
        df_filtrado = df.select([
            "anio", "categoria_delito", "codigo_delito_snic_nombre",
            "provincia_nombre", "cantidad_hechos", "poblacion_provincia"
        ])

        if "Todas" not in categoria_delito_seleccionadas:
            df_filtrado = df_filtrado.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))

        if "Todos" not in tipo_delito_seleccionados:
            df_filtrado = df_filtrado.filter(pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados))

        df_evolucion = (
            df_filtrado
            .group_by(["anio", "provincia_nombre"])
            .agg([
                pl.col("cantidad_hechos").sum().alias("cantidad_hechos"),
                pl.col("poblacion_provincia").first().alias("poblacion_provincia")
            ])
        )

        del df_filtrado  # liberar memoria

                # Calcular tasa de delitos
        df_evolucion = df_evolucion.with_columns(
            ((pl.col("cantidad_hechos") / (pl.col("poblacion_provincia") / 100_000)).round(2)).alias("tasa_delitos")
        )

        # Convertir a string antes de hacer los reemplazos
        df_evolucion = df_evolucion.with_columns(
            pl.col("provincia_nombre").cast(pl.Utf8).alias("provincia_nombre_str")
        )

        replacements_espacio = {
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del Fuego",
            "Ciudad Autónoma de Buenos Aires": "CABA"
        }

        replacements_mapa = {
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del Fuego",
            "Ciudad Autónoma de Buenos Aires": "Ciudad de Buenos Aires"
        }

        df_evolucion = df_evolucion.with_columns([
            pl.col("provincia_nombre_str").replace(replacements_espacio).alias("provincia_nombre_espacio"),
            pl.col("provincia_nombre_str").replace(replacements_espacio).alias("provincia_nombre_short"),
            pl.col("provincia_nombre_str").replace(replacements_mapa).alias("provincia_nombre_mapa")
        ])

        MAX_LEN = 28
        df_evolucion = df_evolucion.with_columns(
            pl.when(pl.col("provincia_nombre_short").str.len_chars() <= MAX_LEN)
            .then(pl.col("provincia_nombre_short"))
            .otherwise(pl.col("provincia_nombre_short").str.slice(0, MAX_LEN - 2) + "...")
            .alias("provincia_nombre_short")
        )

        df_evolucion = df_evolucion.sort(["provincia_nombre", "anio"])

        df_evolucion = df_evolucion.with_columns(
            pl.col("tasa_delitos").shift(1).over("provincia_nombre").alias("tasa_delitos_anterior")
        ).with_columns(
            ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / pl.col("tasa_delitos_anterior")).alias("variacion")
        )

        df_año_seleccionado = df_evolucion.clone().filter(pl.col("anio") == año_seleccionado)

        # 🔹 Convertir solo las columnas necesarias a string para Plotly
        df_año_seleccionado = df_año_seleccionado.with_columns([
            pl.col("provincia_nombre_short").cast(pl.Utf8),
            pl.col("provincia_nombre_mapa").cast(pl.Utf8),
            pl.col("provincia_nombre").cast(pl.Utf8)
        ])

        altura_grafico = 24 * 25
        altura_mapa = 24 * 25
        custom_colorscale = ["#a5c6d9", "#328ec0"]

        col_ranking, col_mapa = st.columns([1, 1], gap='medium')

        df_año_seleccionado_pd = df_año_seleccionado.collect().to_pandas()

        # 🔹 RANKING
        with col_ranking:
            st.markdown("###### Tasa de delitos por provincia")
            fig_ranking = px.bar(
                df_año_seleccionado_pd,  # Plotly necesita pandas
                x='tasa_delitos',
                y='provincia_nombre_short',
                orientation='h',
                color='tasa_delitos',
                color_continuous_scale=custom_colorscale,
                text='tasa_delitos',
                custom_data=["provincia_nombre", "cantidad_hechos", "tasa_delitos", "poblacion_provincia", "anio"]
            )
            fig_ranking.update_traces(
                textposition="inside",
                insidetextanchor="start",
                textfont=dict(color="white"),
                texttemplate="  %{text:,.2f}",
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                              "Tasa de delitos: %{customdata[2]:,.2f}<br>" +
                              "Cantidad de delitos: %{customdata[1]:,}<br>" +
                              "Población %{customdata[4]}: %{customdata[3]:,}<extra></extra>"
            )
            fig_ranking.update_layout(
                xaxis_title="", yaxis_title="",
                showlegend=False, plot_bgcolor='white', paper_bgcolor='white',
                font=dict(size=10), height=altura_grafico,
                yaxis={'categoryorder': 'total ascending'},
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(visible=False),
                barcornerradius=5
            )
            fig_ranking.update_coloraxes(showscale=False)
            fig_ranking.update_xaxes(showgrid=True, gridcolor="lightgrey", gridwidth=0.5)
            st.plotly_chart(fig_ranking, use_container_width=True, config={"displayModeBar": False})

        # MAPA
        with col_mapa:
            st.markdown("###### Mapa de delitos por provincia")

            fig = px.choropleth_mapbox(
                df_año_seleccionado_pd,
                geojson=argentina_geo,
                featureidkey="properties.name",
                locations="provincia_nombre_mapa",
                color="tasa_delitos",
                color_continuous_scale=["#a5c6d9", "#1473a6"],
                mapbox_style="white-bg",
                opacity=0.7,
                hover_data=["provincia_nombre", "cantidad_hechos", "tasa_delitos", "poblacion_provincia", "anio"],
                labels={"tasa_delitos": "Tasa de delitos"}
            )
            fig.update_traces(
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                            "Tasa de delitos: %{customdata[2]:,.2f}<br>" +
                            "Cantidad de delitos: %{customdata[1]:,}<br>" +
                            "Población %{customdata[4]}: %{customdata[3]:,}<extra></extra>"
            )
            fig.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                height=altura_mapa,
                coloraxis_showscale=False,
                mapbox=dict(
                    style="white-bg",
                    center={"lat": -39.5, "lon": -64.0},
                    zoom=3
                ),
            )
            st.plotly_chart(fig, use_container_width=True)

        del df_año_seleccionado
        gc.collect()
        
        st.markdown(f"#### Evolución a lo largo de los años")

        provincias_disponibles = ['Todas'] + sorted(df.select(pl.col('provincia_nombre').unique()).collect()["provincia_nombre"].to_list())
        provincia_seleccionada = st.multiselect("Seleccionar provincias", provincias_disponibles,  key = 'Provincia tab3', default = ['Salta', 'Santa Fe', ])
        if 'Todas' in provincia_seleccionada or not provincia_seleccionada:
            provincia_seleccionada = ['Todas']

        st.markdown("###### Tasa de delitos por provincia")

        if "Todas" not in provincia_seleccionada and provincia_seleccionada:
            df_evolucion = df_evolucion.filter(
                pl.col("provincia_nombre").is_in(provincia_seleccionada)
            )

        colors = [
            '#3fbbe2',
            '#7b59b3',
            '#df437e',
            '#ef8154',
            '#1f77b4',
            '#2ca02c',
            '#e377c2',
            '#eeaf2a',
            "#C56074",
            '#CF54EF',
            '#59B3A8',
            '#437EDF',
            '#7EDF43',
            '#43DFA4',
            '#A71FB4',
            '#54C2EF',
            '#8154EF',
            '#B41F77',
            '#956fab',
            '#1FB4A7',
            "#00685a",
            '#007fa5',
            '#EF5475',
            '#5475EF',
        ]

        nombre_mapeo = {
            "Ciudad Autónoma de Buenos Aires": "CABA",
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del fuego"
        }

        df_evolucion = df_evolucion.with_columns(
            pl.col("provincia_nombre").replace(nombre_mapeo).alias("provincia_nombre_short")
        )

        df_evolucion = df_evolucion.collect().to_pandas()

        fig_evolucion = px.line(
            df_evolucion, 
            x='anio', 
            y='tasa_delitos',
            line_shape='spline',
            markers=True,
            color='provincia_nombre_short',  
            custom_data=["provincia_nombre", "anio", "tasa_delitos", "cantidad_hechos", "poblacion_provincia"],
            color_discrete_sequence=colors,
            title=""
        )

        for trace in fig_evolucion.data:
            color = trace.line.color
            trace.hovertemplate = (
                f"<b><span style='color:{color}'>%{{customdata[0]}}</span></b><br>" +
                "Año %{customdata[1]}<br>" +
                "Tasa de delitos: %{customdata[2]:,.2f}<br>" +
                "Cantidad de delitos: %{customdata[3]:,.0f}<br>" +
                "Población: %{customdata[4]:,.0f}<extra></extra>"
            )
            trace.line.width = 3

        fig_evolucion.update_traces(
            marker=dict(size=8),
        )

        fig_evolucion.update_layout(
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            height=400,
            margin=dict(l=0, r=120, t=0, b=0),
        )

        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")

        min_year = df_evolucion["anio"].min()
        max_year = df_evolucion["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year -0.5, max_year + 0.5], dtick=1)

        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}

        for prov in df_evolucion["provincia_nombre_short"].unique().to_list():
            # df_prov = df_evolucion.filter(pl.col("provincia_nombre_short") == prov)
            df_prov = df_evolucion[df_evolucion["provincia_nombre_short"] == prov]
            
            ultimo_x = df_prov["anio"].max()
            
            ultimo_y = df_prov[df_prov["anio"] == ultimo_x]["tasa_delitos"].max()
            # ultimo_y = df_prov.filter(pl.col("anio") == ultimo_x).select(pl.col("tasa_delitos")).collect().item()
            
            fig_evolucion.add_annotation(
                x=ultimo_x,
                y=ultimo_y,
                text=prov,
                showarrow=False,
                xanchor="left",
                xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": True})

        st.markdown("###### Variación anual de la tasa de delitos por provincia")

        # df_evolucion_var = df_evolucion.filter(pl.col('anio') >= 2014)
        df_evolucion_var = df_evolucion[df_evolucion["anio"] >= 2014]

        fig_evolucion = px.line(
            df_evolucion_var, 
            x='anio', 
            y='variacion',
            line_shape='spline',
            markers=True,
            color='provincia_nombre_short',  
            custom_data=["provincia_nombre", "anio", "variacion", "cantidad_hechos", "poblacion_provincia"],
            color_discrete_sequence=colors,
            title=""
        )

        for trace in fig_evolucion.data:
            color = trace.line.color
            trace.hovertemplate = (
                f"<b><span style='color:{color}'>%{{customdata[0]}}</span></b><br>" +
                "Año %{customdata[1]}<br>" +
                "Variación: %{y:.2%}<br>" +
                "Cantidad de delitos: %{customdata[3]:,.0f}<br>" +
                "Población: %{customdata[4]:,.0f}<extra></extra>"
            )
            trace.line.width = 3

        fig_evolucion.update_traces(
            marker=dict(size=8),
        )

        fig_evolucion.update_layout(
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            height=400,
            margin=dict(l=0, r=120, t=0, b=0),
        )

        fig_evolucion.add_hline(y=0, line_dash="dash", line_color="darkgrey", line_width=2)

        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")

        min_year = df_evolucion_var["anio"].min()
        max_year = df_evolucion_var["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year - 0.5, max_year + 0.5], dtick=1)

        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}

        for prov in df_evolucion_var["provincia_nombre_short"].unique().to_list():
            df_prov = df_evolucion_var[df_evolucion_var["provincia_nombre_short"] == prov]
            # df_prov = df_evolucion_var.filter(pl.col("provincia_nombre_short") == prov)
            
            ultimo_x = df_prov["anio"].max()
            
            # ultimo_y = df_prov.filter(pl.col("anio") == ultimo_x)["variacion"].item()
            ultimo_y = df_prov[df_prov["anio"] == ultimo_x]["variacion"].max()
            
            fig_evolucion.add_annotation(
                x=ultimo_x,
                y=ultimo_y,
                text=prov,
                showarrow=False,
                xanchor="left",
                xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": True})

        # <CHANGE> Liberar memoria
        del df, df_año_seleccionado_pd, fig_ranking, fig, color_map
        gc.collect()

with tab4:
    df = df_lazy.clone()
    col1, col2 = st.columns([1, 4], gap="medium")

    with col1:
        st.markdown("**Filtros**")
        
        años_disponibles = sorted(df.select(pl.col("anio").unique()).collect()["anio"].to_list(), reverse=True)
        año_seleccionado = st.selectbox("Año", años_disponibles, key='Año tab4')

        categorias_delito = ['Todas'] + sorted(df.select(pl.col("categoria_delito").unique()).collect()["categoria_delito"].to_list())
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito, key='Categorías tab4')
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            tipos_disponibles = sorted(df.select(pl.col('codigo_delito_snic_nombre').unique()).collect()["codigo_delito_snic_nombre"].to_list())
        else:
            tipos_disponibles = (
                df
                .filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                .select(pl.col("codigo_delito_snic_nombre").unique())
                .collect()
                ["codigo_delito_snic_nombre"]
                .to_list()
            )
            tipos_disponibles = sorted(tipos_disponibles)
        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito, key='Tipo de delito tab4')
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        provincias_disponibles = ['Todas'] + sorted(df.select(pl.col("provincia_nombre").unique()).collect()["provincia_nombre"].to_list())
        provincia_seleccionada = st.multiselect("Provincias", provincias_disponibles, key='Provincia tab4', default=['Todas'])
        if 'Todas' in provincia_seleccionada or not provincia_seleccionada:
            provincia_seleccionada = ['Todas']

        st.divider()
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}

        • **Categorías:** {", ".join([str(categoria) for categoria in categoria_delito_seleccionadas])}

        • **Tipos de delito:** {", ".join([str(delito) for delito in tipo_delito_seleccionados])}
        
        • **Provincias:** {", ".join([str(provincia) for provincia in provincia_seleccionada])}
        """)

        st.info("Si comparamos **San Isidro y Tigre,** podemos ver que hasta 2020 mostraban trayectorias similares, pero desde 2021 sus dinámicas se invirtieron. San Isidro alcanzó un pico en 2022 y luego bajó, mientras que Tigre tuvo un mínimo en 2023 y se disparó en 2024.")

    with col2:
        col_grafico_ranking, col_info = st.columns([11, 8], gap='medium')

        with col_grafico_ranking:
            st.markdown(f"#### Comparación de la tasa de delitos por departamento")

            # Clonamos df para filtrar sin afectar el original
            df_filtrado = df.clone()

            df_filtrado = df_filtrado.with_columns(
                pl.col("depto_nombre_completo").cast(pl.Utf8)
            )

            if 'Todas' not in categoria_delito_seleccionadas and categoria_delito_seleccionadas:
                df_filtrado = df_filtrado.filter(
                    pl.col('categoria_delito').is_in(categoria_delito_seleccionadas)
                )
            
            if 'Todos' not in tipo_delito_seleccionados and tipo_delito_seleccionados:
                df_filtrado = df_filtrado.filter(
                    pl.col('codigo_delito_snic_nombre').is_in(tipo_delito_seleccionados)
                )

            if 'Todas' not in provincia_seleccionada and provincia_seleccionada:
                df_filtrado = df_filtrado.filter(
                    pl.col('provincia_nombre').is_in(provincia_seleccionada)
                )

            # Agrupamos por año y departamento
            df_evolucion = (
                df_filtrado.group_by(['anio', 'depto_nombre_completo'])
                .agg([
                    pl.col('cantidad_hechos').sum(),
                    pl.col('poblacion_departamento').first()
                ])
                .sort(by='cantidad_hechos', descending=True)
            )

            # Calculamos tasa de delitos
            df_evolucion = df_evolucion.with_columns(
                (pl.col("cantidad_hechos") / (pl.col("poblacion_departamento") / 100_000))
                .round(2)
                .alias("tasa_delitos")
            )

            # Liberamos memoria
            del df_filtrado

            df_evolucion = df_evolucion.sort(by=['depto_nombre_completo', 'anio'])

            # Filtramos solo el año seleccionado
            df_año_seleccionado = df_evolucion.filter(pl.col('anio') == año_seleccionado)

            # Acortamos nombres largos
            MAX_LEN = 28
            df_año_seleccionado = df_año_seleccionado.with_columns(
                pl.when(pl.col("depto_nombre_completo").str.len_chars() <= MAX_LEN)
                .then(pl.col("depto_nombre_completo"))
                .otherwise(pl.col("depto_nombre_completo").str.slice(0, MAX_LEN-2) + "...")
                .alias("departamento_nombre_short")
            )
            df_evolucion = df_evolucion.with_columns(
                pl.when(pl.col("depto_nombre_completo").str.len_chars() <= MAX_LEN)
                .then(pl.col("depto_nombre_completo"))
                .otherwise(pl.col("depto_nombre_completo").str.slice(0, MAX_LEN-2) + "...")
                .alias("departamento_nombre_short")
            )

            # Top 5 departamentos
            df_año_seleccionado = df_año_seleccionado.drop_nulls().sort("tasa_delitos", descending=True).head(5)
            n_filas = df_año_seleccionado.select(pl.count()).collect().item()
            altura_grafico = n_filas * 35

            df_año_seleccionado = df_año_seleccionado.collect().to_pandas()

            custom_colorscale = ["#e096b2", '#df437e']
            fig_ranking = px.bar(
                df_año_seleccionado, 
                x='tasa_delitos', 
                y='departamento_nombre_short',
                orientation='h',
                height=altura_grafico,
                color='tasa_delitos',
                color_continuous_scale=custom_colorscale,
                text=df_año_seleccionado['tasa_delitos'],
                custom_data=["depto_nombre_completo", "cantidad_hechos", "tasa_delitos", "poblacion_departamento"]
            )

            fig_ranking.update_traces(
                textposition="inside",
                insidetextanchor="start",
                textfont=dict(color="white"),
                texttemplate="  %{text:,.2f}",
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                            "Tasa de delitos: %{customdata[2]:,.2f}<br>" +
                            "Cantidad de delitos: %{customdata[1]:,}<br>" +
                            "Población: %{customdata[3]:,}<extra></extra>"
            )

            fig_ranking.update_layout(
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=10),
                height=altura_grafico,
                yaxis={'categoryorder':'total ascending'},
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(visible=False),
                barcornerradius=5
            )

            fig_ranking.update_coloraxes(showscale=False)
            fig_ranking.update_xaxes(showgrid=True, gridcolor="lightgrey", gridwidth=0.5)
            fig_ranking.add_shape(type="line", x0=0, x1=0, y0=-0.5, y1=5-0.5, line=dict(color="lightgrey", width=1))
            st.plotly_chart(fig_ranking, use_container_width=True, config={"displayModeBar": False})

            # Liberamos memoria del año seleccionado
            del df_año_seleccionado
            gc.collect()

        with col_info:
            st.info("""Llama la atención el caso de **Tordillo** (Buenos Aires), que en 2024 exhibe una tasa de delitos extraordinariamente alta debido a la combinación de una pequeña población y un gran número de hechos registrados. Utilizando la pestaña Categorías y tipos de delitos, podemos ver que la mayoría corresponden a delitos vinculados a la **ley 23.737 (estupefacientes).**
    En la pestaña de Vista general, si miramos hacia atrás, en 2013 Tordillo también había registrado un pico excepcional de **amenazas** (más de 2.000 hechos), lo que invita a cuestionar a qué se deben estos picos.""")
        
        # Evolución por departamento
        st.markdown(f"#### Evolución a lo largo de los años")

        # ---- Departamentos dependientes de provincia ----
        if ('Todas' not in provincia_seleccionada and provincia_seleccionada):
            departamentos_disponibles = (
                df
                .filter(pl.col("provincia_nombre").is_in(provincia_seleccionada))
                .select(pl.col("depto_nombre_completo").unique())
                .collect()
                ["depto_nombre_completo"]
                .to_list()
            )
            departamentos_disponibles = sorted(departamentos_disponibles)
            departamentos_default = departamentos_disponibles[:2]
        else:
            departamentos_disponibles = sorted(df.select(pl.col("depto_nombre_completo").unique()).collect()["depto_nombre_completo"].to_list())
            departamentos_default = ['San Isidro, Buenos Aires', 'Tigre, Buenos Aires']

        departamentos_disponibles = ['Todos'] + departamentos_disponibles
        departamento_seleccionado = st.multiselect(
            "Seleccionar departamentos",
            departamentos_disponibles,
            key='Departamento tab4',
            default=departamentos_default
        )

        # Filtrar df_evolucion
        if "Todos" not in departamento_seleccionado and departamento_seleccionado:
            df_evolucion = df_evolucion.filter(
                pl.col("depto_nombre_completo").is_in(departamento_seleccionado)
            )

        # Mantener solo columnas necesarias para gráficos
        df_evolucion = df_evolucion.select([
            "depto_nombre_completo", "departamento_nombre_short", "anio",
            "tasa_delitos", "cantidad_hechos", "poblacion_departamento"
        ])

        # Ordenar
        df_evolucion = df_evolucion.sort(["depto_nombre_completo", "anio"])

        # Calcular tasa_delitos_anterior y variación
        df_evolucion = df_evolucion.with_columns(
            pl.col("tasa_delitos").shift(1).over("depto_nombre_completo").alias("tasa_delitos_anterior")
        )
        df_evolucion = df_evolucion.with_columns(
            ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / pl.col("tasa_delitos_anterior")).alias("variacion")
        )

        st.markdown("###### Tasa de delitos por departamento")

        # Paleta de colores personalizada
        colors = [
            '#3fbbe2', '#7b59b3', '#df437e', '#ef8154', '#1f77b4', '#2ca02c',
            '#e377c2', '#eeaf2a', "#C56074", '#CF54EF', '#59B3A8', '#437EDF',
            '#7EDF43', '#43DFA4', '#A71FB4', '#54C2EF', '#8154EF', '#B41F77',
            '#1F2DB4', '#1FB4A7', "#bd5b34", '#77B41F', '#EF5475', '#5475EF',
        ]

        df_evolucion_pd = df_evolucion.collect().to_pandas()

        # ---- Gráfico Tasa de Delitos ----
        fig_evolucion = px.line(
            df_evolucion_pd,
            x='anio',
            y='tasa_delitos',
            line_shape='spline',
            markers=True,
            color='departamento_nombre_short',
            custom_data=["depto_nombre_completo", "anio", "tasa_delitos", "cantidad_hechos", "poblacion_departamento"],
            color_discrete_sequence=colors,
            title=""
        )

        for trace in fig_evolucion.data:
            color = trace.line.color
            trace.hovertemplate = (
                f"<b><span style='color:{color}'>%{{customdata[0]}}</span></b><br>"
                "Año %{customdata[1]}<br>"
                "Tasa de delitos: %{customdata[2]:,.2f}<br>"
                "Cantidad de delitos: %{customdata[3]:,.0f}<br>"
                "Población: %{customdata[4]:,.0f}<extra></extra>"
            )
            trace.line.width = 3

        fig_evolucion.update_traces(marker=dict(size=8))
        fig_evolucion.update_layout(
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            height=400,
            margin=dict(l=0, r=120, t=0, b=0),
        )
        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")
        min_year = df_evolucion_pd["anio"].min()
        max_year = df_evolucion_pd["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year - 0.5, max_year + 0.5], dtick=1)

        # Etiquetas finales con mismo color que línea
        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}
        for depto in df_evolucion_pd["departamento_nombre_short"].unique():
            # df_depto = df_evolucion_pd.filter(pl.col("departamento_nombre_short") == depto)
            df_depto = df_evolucion_pd[df_evolucion_pd["departamento_nombre_short"] == depto]
            ultimo_x = df_depto["anio"].max()
            # ultimo_y = df_depto.filter(pl.col("anio") == ultimo_x)["tasa_delitos"].item()
            ultimo_y = df_depto[df_depto["anio"] == ultimo_x]["tasa_delitos"].max()
            fig_evolucion.add_annotation(
                x=ultimo_x,
                y=ultimo_y,
                text=depto,
                showarrow=False,
                xanchor="left",
                xshift=10,
                font=dict(size=12, color=color_map[depto])
            )

        st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": True})
        del df_depto
        gc.collect()

        # ---- Gráfico Variación Anual ----
        st.markdown("###### Variación anual de la tasa de delitos por departamento")
        df_var = df_evolucion.filter(pl.col('anio') >= 2010).select([
            "depto_nombre_completo", "departamento_nombre_short", "anio",
            "variacion", "cantidad_hechos", "poblacion_departamento"
        ])

        df_var_pd = df_var.collect().to_pandas()

        fig_var = px.line(
            df_var_pd,
            x='anio',
            y='variacion',
            line_shape='spline',
            markers=True,
            color='departamento_nombre_short',
            custom_data=["depto_nombre_completo", "anio", "variacion", "cantidad_hechos", "poblacion_departamento"],
            color_discrete_sequence=colors,
            title=""
        )

        for trace in fig_var.data:
            color = trace.line.color
            trace.hovertemplate = (
                f"<b><span style='color:{color}'>%{{customdata[0]}}</span></b><br>"
                "Año %{customdata[1]}<br>"
                "Variación: %{y:.2%}<br>"
                "Cantidad de delitos: %{customdata[3]:,.0f}<br>"
                "Población: %{customdata[4]:,.0f}<extra></extra>"
            )
            trace.line.width = 3

        fig_var.update_traces(marker=dict(size=8))
        fig_var.update_layout(
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            height=400,
            margin=dict(l=0, r=120, t=0, b=0),
        )
        fig_var.add_hline(y=0, line_dash="dash", line_color="darkgrey", line_width=2)
        fig_var.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")
        min_year = df_var_pd["anio"].min()
        max_year = df_var_pd["anio"].max()
        fig_var.update_xaxes(range=[min_year - 0.5, max_year + 0.5], dtick=1)

        # Etiquetas finales con mismo color que línea
        color_map = {trace.name: trace.line.color for trace in fig_var.data}
        for prov in df_var_pd["departamento_nombre_short"].unique():
            # df_prov = df_var_pd.filter(pl.col("departamento_nombre_short") == prov)
            df_prov = df_var_pd[df_var_pd["departamento_nombre_short"] == prov]
            ultimo_x = df_prov["anio"].max()
            # ultimo_y = df_prov.filter(pl.col("anio") == ultimo_x)["variacion"].item()
            ultimo_y = df_prov[df_prov["anio"] == ultimo_x]["variacion"].max()
            fig_var.add_annotation(
                x=ultimo_x,
                y=ultimo_y,
                text=prov,
                showarrow=False,
                xanchor="left",
                xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        st.plotly_chart(fig_var, use_container_width=False, config={"displayModeBar": True})
        del df_var, df_var_pd, df_evolucion, df_evolucion_pd, df, fig_ranking, fig_evolucion, fig_var, color_map
        gc.collect()

with tab5:
    col1, col2 = st.columns([1, 3], gap = "medium")

    with col1:
        st.markdown(f"#### Fuentes")
        st.info(
            """
            Los datos sobre los delitos por departamento se obtuvieron de la página web del 
            [Ministerio de Seguridad Nacional](https://www.argentina.gob.ar/seguridad/estadisticascriminales/bases-de-datos), 
            bajo la sección de estadísticas criminales.  
            Los mismos datasets también están disponibles en [datos.gob.ar](https://datos.gob.ar/).
            """,
            )
        st.info(
            """Los datos de la población anual a nivel departamento se obtuvieron a partir de las proyecciones que realiza el INDEC, disponibles en su página web, en la sección de [estadísticas sobre la población](https://www.indec.gob.ar/indec/web/Nivel3-Tema-2-24).""" 
        )

    with col2:
        st.markdown(f"#### Metodología")
        st.markdown("**Creación del dataset**")
        st.info(
            """Utilizando la librería Polar en Google Colab, se tomaron los datos recolectados por el SNIC (Sistema Nacional de Información Criminal) y las proyecciones de población realizadas por el INDEC a nivel departamento; y se cruzaron ambas fuentes de datos para obtener un dataset que contiene una fila para cada combinación de provincia, departamento y tipo de delito, con su correspondiente cantidad de hechos y víctimas, y población a nivel departamento, provincia y país. [El código está disponible en este notebook de Google Colab.](https://colab.research.google.com/drive/1YWjzinfXxcGgIHPhCizsOjG-HZQSrhIc?usp=sharing).""" 
        )
        st.markdown("**Dashboard y métricas**")
        st.info(
            """El tablero fue construido con Streamlit. La tasa de delitos se calcula como la cantidad total de delitos (según los filtros aplicados) dividida por la población del año seleccionado para el departamento, provincia o país, y luego multiplicada por 100,000.""" 
        )
        st.markdown("**Utilidad**")
        st.info(
            """Este tablero permite analizar en profundidad los distintos tipos de delitos y su evolución a nivel país, provincia y departamento. Ayuda a identificar tendencias, comparar regiones y comprender la variación de los niveles de delitos a lo largo del tiempo. Todo esto facilita la detección de patrones y contribuye a la toma de decisiones basadas en datos para combatir el delito en nuestro país.""" 
        )
        st.markdown("**Limitaciones**")
        st.info(
            """
            - **Solo incluye los delitos reportados**: no todos los delitos son detectados y/o registrados, y las tasas de detección y registro pueden variar entre regiones y a lo largo del tiempo. Esto genera un sesgo que puede subestimar la cantidad real de delitos.
            - **Registro heterogéneo de delitos**: la forma en que se registran los delitos puede variar entre provincias y departamentos. Esto puede afectar la comparabilidad entre jurisdicciones.
            - **Precisión a nivel departamento**: en el nivel más granular, los datos pueden presentar inconsistencias. No siempre es seguro que las delimitaciones de departamentos utilizadas por el INDEC para estimar población coincidan con las del SNIC para atribuir delitos. Esto puede generar discrepancias al calcular tasas y dificultar las comparaciones entre departamentos.
            """ 
        )

process = psutil.Process(os.getpid())

while True:
    cpu_percent = process.cpu_percent(interval=1)  # % de CPU usado en el último segundo
    memory_mb = process.memory_info().rss / (1024**2)  # memoria residente en MB
    print(f"CPU: {cpu_percent}% | Memoria: {memory_mb:.2f} MB")
    time.sleep(2)  # espera 2 segundos antes de medir de nuevo