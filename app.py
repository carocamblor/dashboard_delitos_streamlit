import streamlit as st
import polars as pl
import plotly.express as px
import gc
import json

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
@st.cache_data(show_spinner=True, ttl=3600)  # <-- Agregar TTL para limpiar cache
def load_data():
    try:
        columns = [
            "anio", "categoria_delito", "codigo_delito_snic_nombre",
            "provincia_nombre", "depto_nombre_completo",
            "cantidad_hechos", "cantidad_victimas",
            "poblacion_departamento", "poblacion_provincia", "poblacion_pais"
        ]

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
    # NO clonar, usar directamente el LazyFrame
    df = df_lazy  # <-- Eliminar .clone()
    
    col1, col2 = st.columns([1, 4], gap="medium")

    with col1:
        st.markdown("**Filtros**")

        # Optimizar consultas: collect solo lo necesario
        años_disponibles = (
            df.select(pl.col("anio").unique().sort(descending=True))
            .collect()["anio"]
            .to_list()
        )
        año_seleccionado = st.selectbox("Año", años_disponibles)

        # Usar fetch() en lugar de collect() para listas pequeñas
        categorias_delito = ['Todas'] + (
            df.select(pl.col("categoria_delito").unique().sort())
            .collect()["categoria_delito"]
            .to_list()
        )
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito)
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # Tipos de delito
        if 'Todas' in categoria_delito_seleccionadas:
            tipos_disponibles = (
                df.select(pl.col("codigo_delito_snic_nombre").unique().sort())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )
        else:
            tipos_disponibles = (
                df.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                .select(pl.col("codigo_delito_snic_nombre").unique().sort())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )

        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito)
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        # Provincias
        provincias_disponibles = ['Todas'] + (
            df.select(pl.col("provincia_nombre").unique().sort())
            .collect()["provincia_nombre"]
            .to_list()
        )
        provincia_seleccionada = st.selectbox("Provincia", provincias_disponibles)

        # Departamentos
        if provincia_seleccionada != 'Todas':
            departamentos_disponibles = (
                df.filter(pl.col("provincia_nombre") == provincia_seleccionada)
                .select(pl.col("depto_nombre_completo").unique().sort())
                .collect()["depto_nombre_completo"]
                .to_list()
            )
        else:
            departamentos_disponibles = (
                df.select(pl.col("depto_nombre_completo").unique().sort())
                .collect()["depto_nombre_completo"]
                .to_list()
            )

        departamento = ['Todos'] + departamentos_disponibles
        departamento_seleccionado = st.selectbox("Departamento", departamento)

        st.divider()
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}

        • **Categorías:** {", ".join(map(str, categoria_delito_seleccionadas))}

        • **Tipos de delito:** {", ".join(map(str, tipo_delito_seleccionados))}

        • **Provincia:** {provincia_seleccionada}

        • **Departamento:** {departamento_seleccionado}
        """)

    with col2:
        # Construir queries lazy sin materializar
        df_filtered = df.filter(pl.col("anio") == año_seleccionado)
        año_anterior = año_seleccionado - 1
        df_anterior = df.filter(pl.col("anio") == año_anterior)

        # Aplicar filtros
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

        # OPTIMIZACIÓN: Calcular métricas en una sola query agregada
        metricas_año = df_filtered.select([
            pl.col("cantidad_hechos").sum().alias("total_hechos"),
            pl.col("cantidad_victimas").sum().alias("total_victimas"),
            pl.col(col_poblacion).max().alias("poblacion")
        ]).collect()

        metricas_prev = df_anterior.select([
            pl.col("cantidad_hechos").sum().alias("total_hechos"),
            pl.col(col_poblacion).max().alias("poblacion")
        ]).collect()

        metricas_año = metricas_año.fill_null(0)
        metricas_prev = metricas_prev.fill_null(0)

        # Extraer valores
        total_hechos = metricas_año["total_hechos"][0]
        total_victimas = metricas_año["total_victimas"][0]
        poblacion = metricas_año["poblacion"][0]
        
        total_hechos_prev = metricas_prev["total_hechos"][0]
        poblacion_prev = metricas_prev["poblacion"][0]

        # Liberar DataFrames inmediatamente
        del metricas_año, metricas_prev
        gc.collect()

        # Cálculos
        tasa = (total_hechos / poblacion) * 100000
        tasa_prev = (total_hechos_prev / poblacion_prev) * 100000 if poblacion_prev != 0 else 0
        variacion = ((tasa - tasa_prev) / tasa_prev) * 100 if tasa_prev != 0 else 0

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

        # NO clonar, construir query desde df original
        df_graficos = df  # <-- Eliminar .clone()

        # Aplicar filtros
        if "Todas" not in categoria_delito_seleccionadas and categoria_delito_seleccionadas:
            df_graficos = df_graficos.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))

        if "Todos" not in tipo_delito_seleccionados and tipo_delito_seleccionados:
            df_graficos = df_graficos.filter(pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados))

        if departamento_seleccionado != "Todos" and departamento_seleccionado:
            df_graficos = df_graficos.filter(pl.col("depto_nombre_completo") == departamento_seleccionado)
            poblacion_col = "poblacion_departamento"
        elif provincia_seleccionada != "Todas" and provincia_seleccionada:
            df_graficos = df_graficos.filter(pl.col("provincia_nombre") == provincia_seleccionada)
            poblacion_col = "poblacion_provincia"
        else:
            poblacion_col = "poblacion_pais"

        # Agrupar y calcular (lazy)
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
                ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / 
                 pl.col("tasa_delitos_anterior")).alias("variacion"),
            ])
            .select([  # <-- Seleccionar solo columnas necesarias
                "anio", "tasa_delitos", "variacion", "cantidad_hechos", "cantidad_victimas"
            ])
        )

        # Materializar solo una vez
        df_graficos_collected = df_graficos.collect()

        min_anio = df_graficos_collected["anio"].min()
        max_anio = df_graficos_collected["anio"].max()

        col_graficos1, col_graficos2 = st.columns([1, 1], gap="medium")

        with col_graficos1:
            st.markdown("###### Tasa de delitos")
            fig_evolucion = px.line(
                df_graficos_collected, x='anio', y='tasa_delitos',
                line_shape='spline', markers=True, color_discrete_sequence=['#3fbbe2']
            )
            fig_evolucion.update_layout(
                xaxis_title="", yaxis_title="", showlegend=False,
                plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
                height=200, margin=dict(l=0, r=30, t=0, b=0)
            )
            fig_evolucion.update_traces(
                line=dict(width=3), marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Tasa de delitos  %{y:,.2f}<extra></extra>"
            )
            fig_evolucion.update_xaxes(
                range=[min_anio-0.5, max_anio+0.5], tick0=min_anio, dtick=3,
                showgrid=True, gridcolor='lightgray'
            )
            fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")
            st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": False})
            
            # IMPORTANTE: Liberar figura
            del fig_evolucion
            
            st.markdown("###### Variación en la tasa de delitos")
            fig_variacion = px.line(
                df_graficos_collected, x='anio', y='variacion',
                line_shape='spline', markers=True, color_discrete_sequence=['#7b59b3']
            )
            fig_variacion.update_layout(
                xaxis_title="", yaxis_title="", showlegend=False,
                plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
                height=200, margin=dict(l=0, r=30, t=0, b=0)
            )
            fig_variacion.add_hline(y=0, line_dash="dash", line_color="darkgrey", line_width=2)
            fig_variacion.update_traces(
                line=dict(width=3), marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Variación  %{y:.2%}<extra></extra>"
            )
            fig_variacion.update_xaxes(
                range=[min_anio-0.5, max_anio+0.5], tick0=min_anio, dtick=3,
                showgrid=True, gridcolor='lightgray'
            )
            fig_variacion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")
            st.plotly_chart(fig_variacion, use_container_width=True, config={"displayModeBar": False})
            
            # Liberar figura
            del fig_variacion

        with col_graficos2:
            st.markdown("###### Cantidad de delitos")
            fig_delitos = px.line(
                df_graficos_collected, x='anio', y='cantidad_hechos',
                line_shape='spline', markers=True, color_discrete_sequence=['#df437e']
            )
            fig_delitos.update_layout(
                xaxis_title="", yaxis_title="", showlegend=False,
                plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
                height=200, margin=dict(l=0, r=30, t=0, b=0)
            )
            fig_delitos.update_traces(
                line=dict(width=3), marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Delitos  %{y:,.0f}<extra></extra>"
            )
            fig_delitos.update_xaxes(
                range=[min_anio-0.5, max_anio+0.5], tick0=min_anio, dtick=3,
                showgrid=True, gridcolor='lightgray'
            )
            fig_delitos.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")
            st.plotly_chart(fig_delitos, use_container_width=True, config={"displayModeBar": False})
            
            del fig_delitos

            st.markdown("###### Cantidad de víctimas")
            fig_victimas = px.line(
                df_graficos_collected, x='anio', y='cantidad_victimas',
                line_shape='spline', markers=True, color_discrete_sequence=['#ef8154']
            )
            fig_victimas.update_layout(
                xaxis_title="", yaxis_title="", showlegend=False,
                plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
                height=200, margin=dict(l=0, r=30, t=0, b=0)
            )
            fig_victimas.update_traces(
                line=dict(width=3), marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Víctimas  %{y:,.0f}<extra></extra>"
            )
            fig_victimas.update_xaxes(
                range=[min_anio-0.5, max_anio+0.5], tick0=min_anio, dtick=3,
                showgrid=True, gridcolor='lightgray'
            )
            fig_victimas.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")
            st.plotly_chart(fig_victimas, use_container_width=True, config={"displayModeBar": False})
            
            del fig_victimas

    # Liberar todo al final del tab
    del df_graficos_collected, df_filtered, df_anterior
    gc.collect()

    col_info1, col_info2 = st.columns([1, 1], gap = 'medium')

    with col_info1:
        st.info("Durante los últimos cuatro años, **la tasa de delitos creció a nivel nacional** y, en 2024, superó el pico que se había alcanzado en 2019, antes de la pandemia.")
    with col_info2:
        st.info("Si filtramos por **homicidios dolosos** como tipo de delito, se observa una tendencia a la baja: pasó de 7,50 cada 100.000 habitantes en 2014 a 3,68 en 2024.")

# ---- Categorías y tipos de delito ----
# ---- Categorías y tipos de delito ----
with tab2:
    # <CHANGE> Eliminar .clone() innecesario
    df = df_lazy  # NO clonar, usar directamente
    
    col1, col2 = st.columns([1, 4], gap="medium")

    # =======================
    # FILTROS
    # =======================
    with col1:
        st.markdown("**Filtros**")

        # Año - Optimizar query
        años_disponibles = (
            df.select(pl.col("anio").unique().sort(descending=True))
            .collect()["anio"]
            .to_list()
        )
        año_seleccionado = st.selectbox("Año", años_disponibles, key='Año tab2')

        # Categorías - Optimizar query
        categorias_delito = ['Todas'] + (
            df.select(pl.col("categoria_delito").unique().sort())
            .collect()["categoria_delito"]
            .to_list()
        )
        categoria_delito_seleccionadas = st.multiselect(
            "Categorías", categorias_delito, key='Categorías tab2'
        )
        if not categoria_delito_seleccionadas or 'Todas' in categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # Tipos de delito
        if 'Todas' in categoria_delito_seleccionadas:
            tipos_disponibles = (
                df.select(pl.col("codigo_delito_snic_nombre").unique().sort())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )
        else:
            tipos_disponibles = (
                df.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                .select(pl.col("codigo_delito_snic_nombre").unique().sort())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )
        
        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect(
            "Tipo de delito", tipos_delito, key='Tipo de delito tab2'
        )
        if not tipo_delito_seleccionados or 'Todos' in tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        # Provincia y departamento
        provincias_disponibles = ['Todas'] + (
            df.select(pl.col("provincia_nombre").unique().sort())
            .collect()["provincia_nombre"]
            .to_list()
        )
        provincia_seleccionada = st.selectbox("Provincia", provincias_disponibles, key='Provincia tab2')

        if provincia_seleccionada != 'Todas':
            departamentos_disponibles = (
                df.filter(pl.col("provincia_nombre") == provincia_seleccionada)
                .select(pl.col("depto_nombre_completo").unique().sort())
                .collect()["depto_nombre_completo"]
                .to_list()
            )
        else:
            departamentos_disponibles = (
                df.select(pl.col("depto_nombre_completo").unique().sort())
                .collect()["depto_nombre_completo"]
                .to_list()
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
        st.info("En 2024, más de la mitad de los delitos correspondieron a **delitos contra la propiedad,** principalmente robos y hurtos.")

        # <CHANGE> NO clonar df_lazy, construir query directamente
        df_filtrado = df_lazy.filter(pl.col("anio") == año_seleccionado)

        # Aplicar filtros de manera lazy
        if 'Todas' not in categoria_delito_seleccionadas:
            df_filtrado = df_filtrado.filter(
                pl.col("categoria_delito").is_in(categoria_delito_seleccionadas)
            )

        if 'Todos' not in tipo_delito_seleccionados:
            df_filtrado = df_filtrado.filter(
                pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados)
            )

        if departamento_seleccionado != 'Todos':
            df_filtrado = df_filtrado.filter(
                pl.col("depto_nombre_completo") == departamento_seleccionado
            )
        elif provincia_seleccionada != 'Todas':
            df_filtrado = df_filtrado.filter(
                pl.col("provincia_nombre") == provincia_seleccionada
            )

        # =======================
        # FUNCIÓN PARA GRAFICOS (OPTIMIZADA)
        # =======================
        def plot_top5(df_grouped, col_value, col_name_short, col_name_full, title):
            """
            Función optimizada para generar gráficos top 5.
            Libera memoria agresivamente después de cada paso.
            """
            # Asegurar que la columna numérica sea tipo float
            df_grouped = df_grouped.with_columns(pl.col(col_value).cast(pl.Float64))

            # <CHANGE> Calcular total y verificar en una sola operación
            total_result = df_grouped.select(pl.sum(col_value)).collect()
            total = total_result[0, 0]
            del total_result  # Liberar inmediatamente
            
            if total == 0 or total is None:
                st.warning(f"No hay datos suficientes para {title.lower()}.")
                del df_grouped
                gc.collect()
                return

            # Calcular porcentaje y truncar nombres (lazy)
            MAX_LEN = 28
            df_grouped = (
                df_grouped
                .with_columns((pl.col(col_value) / total).alias("porcentaje"))
                .with_columns(
                    pl.when(pl.col(col_name_full).cast(pl.Utf8).str.len_chars() <= MAX_LEN)
                    .then(pl.col(col_name_full).cast(pl.Utf8))
                    .otherwise(pl.col(col_name_full).cast(pl.Utf8).str.slice(0, MAX_LEN - 2) + "…")
                    .alias(col_name_short)
                )
                .sort("porcentaje", descending=True)
                .head(5)
            )

            # <CHANGE> Materializar solo el top 5 y convertir a pandas
            top5_pd = df_grouped.collect().to_pandas()
            
            # Liberar df_grouped inmediatamente
            del df_grouped
            gc.collect()

            # Agregar columna de texto con porcentaje
            top5_pd["porcentaje_text"] = (
                top5_pd["porcentaje"].mul(100).round(1).astype(str) + "%"
            )

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
            st.plotly_chart(
                fig, 
                use_container_width=True, 
                config={"displayModeBar": False}, 
                key=f"{title}_{col_value}"
            )

            # <CHANGE> Liberar memoria agresivamente
            del top5_pd, fig
            gc.collect()

        # =======================
        # GRÁFICOS
        # =======================
        # <CHANGE> Preparar queries lazy sin materializar
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

        # Generar gráficos (la función plot_top5 maneja la materialización y limpieza)
        plot_top5(
            df_categoria, 
            "cantidad_hechos", 
            "categoria_delito_short", 
            "categoria_delito", 
            "Top 5 categorías de delitos según su porcentaje"
        )
        
        plot_top5(
            df_tipo, 
            "cantidad_hechos", 
            "tipo_delito_short", 
            "codigo_delito_snic_nombre", 
            "Top 5 tipos de delitos según su porcentaje"
        )

        # =======================
        # INFO ADICIONAL
        # =======================
        st.info("Si filtramos por **Salta**, podemos notar que, **en 2024, el 24% de los delitos registrados en la provincia correspondieron a contravenciones**, en contraste con el 4% a nivel nacional. Es importante señalar que las contravenciones son faltas menores que no se reportan de manera uniforme entre las provincias, es decir, se trata de una categoría **heterogénea** entre jurisdicciones.")
        
        st.info("Si filtramos por **Salta** y por la categoría **Delitos contra la propiedad**, vemos que, en 2024, en esta provincia, el 36.1% de los delitos de esta categoría correspondieron a hurtos y el 32.6% a robos (excluyendo los agravados por resultado de lesiones y/o muertes).")

        st.info("En la pestaña _Comparar departamentos_, se observa que **Tordillo (Buenos Aires)** registró la mayor tasa de delitos en 2024. En esta pestaña, al filtrar por este departamento, puede verse que el 94% corresponden a **tenencia simple atenuada para uso personal de estupefacientes.**")

    # <CHANGE> Liberar toda la memoria al final del tab
    del df_filtrado
    gc.collect()

# ---- Comparar provincias ----
# ---- Comparar provincias ----
with tab3:
    # <CHANGE> Eliminar .clone() innecesario
    df = df_lazy  # NO clonar, usar directamente
    
    col1, col2 = st.columns([1, 4], gap="medium")

    # =======================
    # FILTROS
    # =======================
    with col1:
        st.markdown("**Filtros**")

        # Optimizar queries de filtros
        años_disponibles = (
            df.select(pl.col('anio').unique().sort(descending=True))
            .collect()["anio"]
            .to_list()
        )
        año_seleccionado = st.selectbox("Año", años_disponibles, key='Año tab3')

        categorias_delito = (
            df.select(pl.col('categoria_delito').unique().sort())
            .collect()["categoria_delito"]
            .to_list()
        )
        categoria_delito_seleccionadas = st.multiselect(
            "Categorías", categorias_delito, key='Categorías tab3'
        )
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # <CHANGE> Eliminar .lazy() redundante - df ya es LazyFrame
        if 'Todas' in categoria_delito_seleccionadas:
            tipos_disponibles = (
                df.select(pl.col('codigo_delito_snic_nombre').unique().sort())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )
        else:
            tipos_disponibles = (
                df.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                .select(pl.col("codigo_delito_snic_nombre").unique().sort())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )

        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect(
            "Tipo de delito", tipos_delito, key='Tipo de delito tab3'
        )
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        st.divider()
        st.info("Al seleccionar la categoría de **contrabando,** puede observarse que las provincias del **norte** presentan las mayores tasas.")
        st.info("Filtrando por **siembra y producción de estupefacientes** como tipo de delito, vemos que, en 2024, **La Pampa** tuvo la mayor tasa para este tipo de delito, mientras que, en 2022 y 2023, fue **San Luis**.")
        
        st.divider()
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}

        • **Categorías:** {", ".join([str(categoria) for categoria in categoria_delito_seleccionadas])}

        • **Tipos de delito:** {", ".join([str(delito) for delito in tipo_delito_seleccionados])}
        """)

        st.divider()
        st.info("Si utilizamos los gráficos de evolución para **comparar la tasa de delitos general de Santa Fe y Salta**, podemos ver que Santa Fe se ha mantenido relativamente estable durante los últimos 11 años, mientras que Salta muestra un comportamiento más volátil y una tendencia creciente.")


    # =======================
    # GRÁFICOS Y ANÁLISIS
    # =======================
    with col2:
        st.markdown(f"#### Comparación de la tasa de delitos por provincia")
        st.info(f"En 2024, Salta fue la provincia con mayor tasa de delitos.")

        # <CHANGE> Construir query lazy sin materializar
        df_filtrado = df.select([
            "anio", "categoria_delito", "codigo_delito_snic_nombre",
            "provincia_nombre", "cantidad_hechos", "poblacion_provincia"
        ])

        # Aplicar filtros en modo lazy
        if "Todas" not in categoria_delito_seleccionadas:
            df_filtrado = df_filtrado.filter(
                pl.col("categoria_delito").is_in(categoria_delito_seleccionadas)
            )

        if "Todos" not in tipo_delito_seleccionados:
            df_filtrado = df_filtrado.filter(
                pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados)
            )

        # <CHANGE> Construir df_evolucion completamente en modo lazy
        df_evolucion = (
            df_filtrado
            .group_by(["anio", "provincia_nombre"])
            .agg([
                pl.col("cantidad_hechos").sum().alias("cantidad_hechos"),
                pl.col("poblacion_provincia").first().alias("poblacion_provincia")
            ])
            .with_columns([
                ((pl.col("cantidad_hechos") / (pl.col("poblacion_provincia") / 100_000))
                 .round(2)
                 .alias("tasa_delitos"))
            ])
            .with_columns([
                pl.col("provincia_nombre").cast(pl.Utf8).alias("provincia_nombre_str")
            ])
        )

        # Liberar df_filtrado inmediatamente
        del df_filtrado
        gc.collect()

        # Definir reemplazos
        replacements_espacio = {
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del Fuego",
            "Ciudad Autónoma de Buenos Aires": "CABA"
        }

        replacements_mapa = {
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del Fuego",
            "Ciudad Autónoma de Buenos Aires": "Ciudad de Buenos Aires"
        }

        # <CHANGE> Aplicar transformaciones en modo lazy
        MAX_LEN = 28
        df_evolucion = (
            df_evolucion
            .with_columns([
                pl.col("provincia_nombre_str").replace(replacements_espacio).alias("provincia_nombre_espacio"),
                pl.col("provincia_nombre_str").replace(replacements_espacio).alias("provincia_nombre_short"),
                pl.col("provincia_nombre_str").replace(replacements_mapa).alias("provincia_nombre_mapa")
            ])
            .with_columns([
                pl.when(pl.col("provincia_nombre_short").str.len_chars() <= MAX_LEN)
                .then(pl.col("provincia_nombre_short"))
                .otherwise(pl.col("provincia_nombre_short").str.slice(0, MAX_LEN - 2) + "...")
                .alias("provincia_nombre_short")
            ])
            .sort(["provincia_nombre", "anio"])
            .with_columns([
                pl.col("tasa_delitos").shift(1).over("provincia_nombre").alias("tasa_delitos_anterior")
            ])
            .with_columns([
                ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / 
                 pl.col("tasa_delitos_anterior")).alias("variacion")
            ])
        )

        # <CHANGE> Filtrar año seleccionado en lazy y materializar solo ese subset
        df_año_seleccionado = (
            df_evolucion
            .filter(pl.col("anio") == año_seleccionado)
            .with_columns([
                pl.col("provincia_nombre_short").cast(pl.Utf8),
                pl.col("provincia_nombre_mapa").cast(pl.Utf8),
                pl.col("provincia_nombre").cast(pl.Utf8)
            ])
            .collect()  # Materializar solo el año seleccionado
            .to_pandas()  # Convertir a pandas para Plotly
        )

        altura_grafico = 24 * 25
        altura_mapa = 24 * 25
        custom_colorscale = ["#a5c6d9", "#328ec0"]

        col_ranking, col_mapa = st.columns([1, 1], gap='medium')

        # =======================
        # RANKING
        # =======================
        with col_ranking:
            st.markdown("###### Tasa de delitos por provincia")
            fig_ranking = px.bar(
                df_año_seleccionado,
                x='tasa_delitos',
                y='provincia_nombre_short',
                orientation='h',
                color='tasa_delitos',
                color_continuous_scale=custom_colorscale,
                text='tasa_delitos',
                custom_data=["provincia_nombre", "cantidad_hechos", "tasa_delitos", 
                            "poblacion_provincia", "anio"]
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
            st.plotly_chart(fig_ranking, use_container_width=True, 
                          config={"displayModeBar": False})
            
            # <CHANGE> Liberar figura inmediatamente
            del fig_ranking
            gc.collect()

        # =======================
        # MAPA
        # =======================
        with col_mapa:
            st.markdown("###### Mapa de delitos por provincia")

            fig_mapa = px.choropleth_mapbox(
                df_año_seleccionado,
                geojson=argentina_geo,
                featureidkey="properties.name",
                locations="provincia_nombre_mapa",
                color="tasa_delitos",
                color_continuous_scale=["#a5c6d9", "#1473a6"],
                mapbox_style="white-bg",
                opacity=0.7,
                hover_data=["provincia_nombre", "cantidad_hechos", "tasa_delitos", 
                           "poblacion_provincia", "anio"],
                labels={"tasa_delitos": "Tasa de delitos"}
            )
            fig_mapa.update_traces(
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                            "Tasa de delitos: %{customdata[2]:,.2f}<br>" +
                            "Cantidad de delitos: %{customdata[1]:,}<br>" +
                            "Población %{customdata[4]}: %{customdata[3]:,}<extra></extra>"
            )
            fig_mapa.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                height=altura_mapa,
                coloraxis_showscale=False,
                mapbox=dict(
                    style="white-bg",
                    center={"lat": -39.5, "lon": -64.0},
                    zoom=3
                ),
            )
            st.plotly_chart(fig_mapa, use_container_width=True)
            
            # <CHANGE> Liberar figura inmediatamente
            del fig_mapa
            gc.collect()

        # <CHANGE> Liberar DataFrame del año seleccionado
        del df_año_seleccionado
        gc.collect()
        
        # =======================
        # EVOLUCIÓN TEMPORAL
        # =======================
        st.markdown(f"#### Evolución a lo largo de los años")

        provincias_disponibles = ['Todas'] + (
            df.select(pl.col('provincia_nombre').unique().sort())
            .collect()["provincia_nombre"]
            .to_list()
        )
        provincia_seleccionada = st.multiselect(
            "Seleccionar provincias", 
            provincias_disponibles,  
            key='Provincia tab3', 
            default=['Salta', 'Santa Fe']
        )
        if 'Todas' in provincia_seleccionada or not provincia_seleccionada:
            provincia_seleccionada = ['Todas']

        st.markdown("###### Tasa de delitos por provincia")

        # <CHANGE> Filtrar provincias en modo lazy antes de materializar
        df_evolucion_filtrado = df_evolucion
        if "Todas" not in provincia_seleccionada and provincia_seleccionada:
            df_evolucion_filtrado = df_evolucion_filtrado.filter(
                pl.col("provincia_nombre").is_in(provincia_seleccionada)
            )

        # Aplicar mapeo de nombres
        nombre_mapeo = {
            "Ciudad Autónoma de Buenos Aires": "CABA",
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del fuego"
        }

        df_evolucion_filtrado = df_evolucion_filtrado.with_columns(
            pl.col("provincia_nombre").replace(nombre_mapeo).alias("provincia_nombre_short")
        )

        # <CHANGE> Materializar solo ahora que tenemos todos los filtros aplicados
        df_evolucion_pd = df_evolucion_filtrado.collect().to_pandas()

        # Definir colores
        colors = [
            '#3fbbe2', '#7b59b3', '#df437e', '#ef8154', '#1f77b4',
            '#2ca02c', '#e377c2', '#eeaf2a', "#C56074", '#CF54EF',
            '#59B3A8', '#437EDF', '#7EDF43', '#43DFA4', '#A71FB4',
            '#54C2EF', '#8154EF', '#B41F77', '#956fab', '#1FB4A7',
            "#00685a", '#007fa5', '#EF5475', '#5475EF',
        ]

        # Gráfico de evolución de tasa
        fig_evolucion = px.line(
            df_evolucion_pd, 
            x='anio', 
            y='tasa_delitos',
            line_shape='spline',
            markers=True,
            color='provincia_nombre_short',  
            custom_data=["provincia_nombre", "anio", "tasa_delitos", 
                        "cantidad_hechos", "poblacion_provincia"],
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

        fig_evolucion.update_traces(marker=dict(size=8))

        fig_evolucion.update_layout(
            xaxis_title="", yaxis_title="",
            showlegend=False, plot_bgcolor='white', paper_bgcolor='white',
            font=dict(size=12), height=400,
            margin=dict(l=0, r=120, t=0, b=0),
        )

        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")

        min_year = df_evolucion_pd["anio"].min()
        max_year = df_evolucion_pd["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year - 0.5, max_year + 0.5], dtick=1)

        # Crear mapa de colores
        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}

        # Agregar anotaciones
        for prov in df_evolucion_pd["provincia_nombre_short"].unique():
            df_prov = df_evolucion_pd[df_evolucion_pd["provincia_nombre_short"] == prov]
            ultimo_x = df_prov["anio"].max()
            ultimo_y = df_prov[df_prov["anio"] == ultimo_x]["tasa_delitos"].max()
            
            fig_evolucion.add_annotation(
                x=ultimo_x, y=ultimo_y, text=prov,
                showarrow=False, xanchor="left", xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        st.plotly_chart(fig_evolucion, use_container_width=False, 
                       config={"displayModeBar": True})
        
        # <CHANGE> Liberar figura
        del fig_evolucion
        gc.collect()

        # =======================
        # VARIACIÓN ANUAL
        # =======================
        st.markdown("###### Variación anual de la tasa de delitos por provincia")

        # <CHANGE> Filtrar en pandas (ya materializado)
        df_evolucion_var = df_evolucion_pd[df_evolucion_pd["anio"] >= 2014]

        fig_variacion = px.line(
            df_evolucion_var, 
            x='anio', 
            y='variacion',
            line_shape='spline',
            markers=True,
            color='provincia_nombre_short',  
            custom_data=["provincia_nombre", "anio", "variacion", 
                        "cantidad_hechos", "poblacion_provincia"],
            color_discrete_sequence=colors,
            title=""
        )

        for trace in fig_variacion.data:
            color = trace.line.color
            trace.hovertemplate = (
                f"<b><span style='color:{color}'>%{{customdata[0]}}</span></b><br>" +
                "Año %{customdata[1]}<br>" +
                "Variación: %{y:.2%}<br>" +
                "Cantidad de delitos: %{customdata[3]:,.0f}<br>" +
                "Población: %{customdata[4]:,.0f}<extra></extra>"
            )
            trace.line.width = 3

        fig_variacion.update_traces(marker=dict(size=8))

        fig_variacion.update_layout(
            xaxis_title="", yaxis_title="",
            showlegend=False, plot_bgcolor='white', paper_bgcolor='white',
            font=dict(size=12), height=400,
            margin=dict(l=0, r=120, t=0, b=0),
        )

        fig_variacion.add_hline(y=0, line_dash="dash", line_color="darkgrey", line_width=2)
        fig_variacion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")

        min_year = df_evolucion_var["anio"].min()
        max_year = df_evolucion_var["anio"].max()
        fig_variacion.update_xaxes(range=[min_year - 0.5, max_year + 0.5], dtick=1)

        color_map = {trace.name: trace.line.color for trace in fig_variacion.data}

        for prov in df_evolucion_var["provincia_nombre_short"].unique():
            df_prov = df_evolucion_var[df_evolucion_var["provincia_nombre_short"] == prov]
            ultimo_x = df_prov["anio"].max()
            ultimo_y = df_prov[df_prov["anio"] == ultimo_x]["variacion"].max()
            
            fig_variacion.add_annotation(
                x=ultimo_x, y=ultimo_y, text=prov,
                showarrow=False, xanchor="left", xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        st.plotly_chart(fig_variacion, use_container_width=False, 
                       config={"displayModeBar": True})

        # <CHANGE> Liberar toda la memoria al final del tab
        del fig_variacion, df_evolucion_pd, df_evolucion_var, color_map
        gc.collect()

# ---- Comparar departamentos ----
with tab4:
    # <CHANGE> Eliminar .clone() innecesario
    df = df_lazy  # NO clonar, usar directamente
    
    col1, col2 = st.columns([1, 4], gap="medium")

    # =======================
    # FILTROS
    # =======================
    with col1:
        st.markdown("**Filtros**")
        
        # Optimizar queries de filtros
        años_disponibles = (
            df.select(pl.col("anio").unique().sort(descending=True))
            .collect()["anio"]
            .to_list()
        )
        año_seleccionado = st.selectbox("Año", años_disponibles, key='Año tab4')

        categorias_delito = ['Todas'] + (
            df.select(pl.col("categoria_delito").unique().sort())
            .collect()["categoria_delito"]
            .to_list()
        )
        categoria_delito_seleccionadas = st.multiselect(
            "Categorías", categorias_delito, key='Categorías tab4'
        )
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            tipos_disponibles = (
                df.select(pl.col('codigo_delito_snic_nombre').unique().sort())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )
        else:
            tipos_disponibles = (
                df.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                .select(pl.col("codigo_delito_snic_nombre").unique().sort())
                .collect()["codigo_delito_snic_nombre"]
                .to_list()
            )
        
        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect(
            "Tipo de delito", tipos_delito, key='Tipo de delito tab4'
        )
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        provincias_disponibles = ['Todas'] + (
            df.select(pl.col("provincia_nombre").unique().sort())
            .collect()["provincia_nombre"]
            .to_list()
        )
        provincia_seleccionada = st.multiselect(
            "Provincias", provincias_disponibles, key='Provincia tab4', default=['Todas']
        )
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

        st.divider()

        st.info("Si comparamos **San Isidro y Tigre,** podemos ver que hasta 2020 mostraban trayectorias similares, pero desde 2021 sus dinámicas se invirtieron. San Isidro alcanzó un pico en 2022 y luego bajó, mientras que Tigre tuvo un mínimo en 2023 y se disparó en 2024.")

    # =======================
    # GRÁFICOS Y ANÁLISIS
    # =======================
    with col2:
        col_grafico_ranking, col_info = st.columns([11, 8], gap='medium')

        with col_grafico_ranking:
            st.markdown(f"#### Comparación de la tasa de delitos por departamento")

            # <CHANGE> NO clonar, construir query lazy directamente
            df_filtrado = df.with_columns(
                pl.col("depto_nombre_completo").cast(pl.Utf8)
            )

            # Aplicar todos los filtros en modo lazy
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

            # <CHANGE> Construir df_evolucion completamente en modo lazy
            df_evolucion = (
                df_filtrado
                .group_by(['anio', 'depto_nombre_completo'])
                .agg([
                    pl.col('cantidad_hechos').sum().alias('cantidad_hechos'),
                    pl.col('poblacion_departamento').first().alias('poblacion_departamento')
                ])
                .with_columns([
                    ((pl.col("cantidad_hechos") / (pl.col("poblacion_departamento") / 100_000))
                     .round(2)
                     .alias("tasa_delitos"))
                ])
                .sort(by=['depto_nombre_completo', 'anio'])
            )

            # Liberar df_filtrado inmediatamente
            del df_filtrado
            gc.collect()

            # <CHANGE> Filtrar año seleccionado y calcular top 5 en lazy
            MAX_LEN = 28
            df_año_seleccionado = (
                df_evolucion
                .filter(pl.col('anio') == año_seleccionado)
                .with_columns([
                    pl.when(pl.col("depto_nombre_completo").str.len_chars() <= MAX_LEN)
                    .then(pl.col("depto_nombre_completo"))
                    .otherwise(pl.col("depto_nombre_completo").str.slice(0, MAX_LEN-2) + "...")
                    .alias("departamento_nombre_short")
                ])
                .drop_nulls()
                .sort("tasa_delitos", descending=True)
                .head(5)
            )

            # Calcular altura antes de materializar
            n_filas_result = df_año_seleccionado.select(pl.count()).collect()
            n_filas = n_filas_result[0, 0]
            del n_filas_result
            gc.collect()
            
            altura_grafico = n_filas * 35

            # <CHANGE> Materializar solo el top 5
            df_año_seleccionado_pd = df_año_seleccionado.collect().to_pandas()

            # Liberar LazyFrame
            del df_año_seleccionado
            gc.collect()

            # Crear gráfico
            custom_colorscale = ["#e096b2", '#df437e']
            fig_ranking = px.bar(
                df_año_seleccionado_pd, 
                x='tasa_delitos', 
                y='departamento_nombre_short',
                orientation='h',
                height=altura_grafico,
                color='tasa_delitos',
                color_continuous_scale=custom_colorscale,
                text=df_año_seleccionado_pd['tasa_delitos'],
                custom_data=["depto_nombre_completo", "cantidad_hechos", "tasa_delitos", 
                            "poblacion_departamento"]
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
                xaxis_title="", yaxis_title="",
                showlegend=False, plot_bgcolor='white', paper_bgcolor='white',
                font=dict(size=10), height=altura_grafico,
                yaxis={'categoryorder':'total ascending'},
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(visible=False),
                barcornerradius=5
            )

            fig_ranking.update_coloraxes(showscale=False)
            fig_ranking.update_xaxes(showgrid=True, gridcolor="lightgrey", gridwidth=0.5)
            fig_ranking.add_shape(
                type="line", x0=0, x1=0, y0=-0.5, y1=n_filas-0.5, 
                line=dict(color="lightgrey", width=1)
            )
            
            st.plotly_chart(fig_ranking, use_container_width=True, 
                          config={"displayModeBar": False})

            # <CHANGE> Liberar memoria inmediatamente
            del df_año_seleccionado_pd, fig_ranking
            gc.collect()

        with col_info:
            st.info("""Llama la atención el caso de **Tordillo** (Buenos Aires), que en 2024 exhibe una tasa de delitos extraordinariamente alta debido a la combinación de una pequeña población y un gran número de hechos registrados. Utilizando la pestaña _Categorías y tipos de delitos_, podemos ver que la mayoría corresponden a delitos vinculados con la **Ley 23.737 (estupefacientes).**""")
        
        # =======================
        # EVOLUCIÓN TEMPORAL
        # =======================
        st.markdown(f"#### Evolución a lo largo de los años")

        # <CHANGE> Obtener departamentos disponibles según provincia
        if ('Todas' not in provincia_seleccionada and provincia_seleccionada):
            departamentos_disponibles = (
                df.filter(pl.col("provincia_nombre").is_in(provincia_seleccionada))
                .select(pl.col("depto_nombre_completo").unique().sort())
                .collect()["depto_nombre_completo"]
                .to_list()
            )
            departamentos_default = departamentos_disponibles[:2] if len(departamentos_disponibles) >= 2 else departamentos_disponibles
        else:
            departamentos_disponibles = (
                df.select(pl.col("depto_nombre_completo").unique().sort())
                .collect()["depto_nombre_completo"]
                .to_list()
            )
            departamentos_default = ['San Isidro, Buenos Aires', 'Tigre, Buenos Aires']

        departamentos_disponibles = ['Todos'] + departamentos_disponibles
        departamento_seleccionado = st.multiselect(
            "Seleccionar departamentos",
            departamentos_disponibles,
            key='Departamento tab4',
            default=departamentos_default
        )

        # <CHANGE> Aplicar filtro de departamentos en lazy antes de materializar
        df_evolucion_filtrado = df_evolucion
        
        if "Todos" not in departamento_seleccionado and departamento_seleccionado:
            df_evolucion_filtrado = df_evolucion_filtrado.filter(
                pl.col("depto_nombre_completo").is_in(departamento_seleccionado)
            )

        # <CHANGE> Calcular nombres cortos y variaciones en lazy
        df_evolucion_filtrado = (
            df_evolucion_filtrado
            .with_columns([
                pl.when(pl.col("depto_nombre_completo").str.len_chars() <= MAX_LEN)
                .then(pl.col("depto_nombre_completo"))
                .otherwise(pl.col("depto_nombre_completo").str.slice(0, MAX_LEN-2) + "...")
                .alias("departamento_nombre_short")
            ])
            .with_columns([
                pl.col("tasa_delitos").shift(1).over("depto_nombre_completo").alias("tasa_delitos_anterior")
            ])
            .with_columns([
                ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / 
                 pl.col("tasa_delitos_anterior")).alias("variacion")
            ])
            .select([
                "depto_nombre_completo", "departamento_nombre_short", "anio",
                "tasa_delitos", "variacion", "cantidad_hechos", "poblacion_departamento"
            ])
        )

        # <CHANGE> Materializar solo ahora con todos los filtros aplicados
        df_evolucion_pd = df_evolucion_filtrado.collect().to_pandas()

        # Liberar LazyFrames
        del df_evolucion, df_evolucion_filtrado
        gc.collect()

        st.markdown("###### Tasa de delitos por departamento")

        # Paleta de colores
        colors = [
            '#3fbbe2', '#7b59b3', '#df437e', '#ef8154', '#1f77b4', '#2ca02c',
            '#e377c2', '#eeaf2a', "#C56074", '#CF54EF', '#59B3A8', '#437EDF',
            '#7EDF43', '#43DFA4', '#A71FB4', '#54C2EF', '#8154EF', '#B41F77',
            '#1F2DB4', '#1FB4A7', "#bd5b34", '#77B41F', '#EF5475', '#5475EF',
        ]

        # Gráfico de evolución de tasa
        fig_evolucion = px.line(
            df_evolucion_pd,
            x='anio',
            y='tasa_delitos',
            line_shape='spline',
            markers=True,
            color='departamento_nombre_short',
            custom_data=["depto_nombre_completo", "anio", "tasa_delitos", 
                        "cantidad_hechos", "poblacion_departamento"],
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
            xaxis_title="", yaxis_title="",
            showlegend=False, plot_bgcolor='white', paper_bgcolor='white',
            font=dict(size=12), height=400,
            margin=dict(l=0, r=120, t=0, b=0),
        )
        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")
        
        min_year = df_evolucion_pd["anio"].min()
        max_year = df_evolucion_pd["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year - 0.5, max_year + 0.5], dtick=1)

        # Etiquetas finales con mismo color que línea
        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}
        for depto in df_evolucion_pd["departamento_nombre_short"].unique():
            df_depto = df_evolucion_pd[df_evolucion_pd["departamento_nombre_short"] == depto]
            ultimo_x = df_depto["anio"].max()
            ultimo_y = df_depto[df_depto["anio"] == ultimo_x]["tasa_delitos"].max()
            
            fig_evolucion.add_annotation(
                x=ultimo_x, y=ultimo_y, text=depto,
                showarrow=False, xanchor="left", xshift=10,
                font=dict(size=12, color=color_map[depto])
            )

        st.plotly_chart(fig_evolucion, use_container_width=False, 
                       config={"displayModeBar": True})
        
        # <CHANGE> Liberar figura inmediatamente
        del fig_evolucion
        gc.collect()

        # =======================
        # VARIACIÓN ANUAL
        # =======================
        st.markdown("###### Variación anual de la tasa de delitos por departamento")
        
        # <CHANGE> Filtrar en pandas (ya materializado)
        df_var_pd = df_evolucion_pd[df_evolucion_pd["anio"] >= 2010].copy()

        fig_var = px.line(
            df_var_pd,
            x='anio',
            y='variacion',
            line_shape='spline',
            markers=True,
            color='departamento_nombre_short',
            custom_data=["depto_nombre_completo", "anio", "variacion", 
                        "cantidad_hechos", "poblacion_departamento"],
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
            xaxis_title="", yaxis_title="",
            showlegend=False, plot_bgcolor='white', paper_bgcolor='white',
            font=dict(size=12), height=400,
            margin=dict(l=0, r=120, t=0, b=0),
        )
        fig_var.add_hline(y=0, line_dash="dash", line_color="darkgrey", line_width=2)
        fig_var.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")
        
        min_year = df_var_pd["anio"].min()
        max_year = df_var_pd["anio"].max()
        fig_var.update_xaxes(range=[min_year - 0.5, max_year + 0.5], dtick=1)

        # Etiquetas finales
        color_map = {trace.name: trace.line.color for trace in fig_var.data}
        for prov in df_var_pd["departamento_nombre_short"].unique():
            df_prov = df_var_pd[df_var_pd["departamento_nombre_short"] == prov]
            ultimo_x = df_prov["anio"].max()
            ultimo_y = df_prov[df_prov["anio"] == ultimo_x]["variacion"].max()
            
            fig_var.add_annotation(
                x=ultimo_x, y=ultimo_y, text=prov,
                showarrow=False, xanchor="left", xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        st.plotly_chart(fig_var, use_container_width=False, 
                       config={"displayModeBar": True})
        
        # <CHANGE> Liberar toda la memoria al final del tab
        del fig_var, df_var_pd, df_evolucion_pd, color_map
        gc.collect()

with tab5:
    col1, col2 = st.columns([1, 3], gap = "medium")

    with col1:
        st.markdown(f"#### Fuentes")
        st.info(
            """
            Los datos sobre los delitos por departamento se obtuvieron del sitio web del 
            [Ministerio de Seguridad de la Nación](https://www.argentina.gob.ar/seguridad/estadisticascriminales/bases-de-datos), 
            bajo la sección de estadísticas criminales, base de datos "SNIC - Departamentos. Mensual. Años 2000-2024". El mismo dataset también está disponible en [datos.gob.ar](https://datos.gob.ar/dataset?q=snic).
            """,
            )
        st.info(
            """Los datos de la población anual a nivel departamento se obtuvieron a partir de las proyecciones del INDEC, disponibles en su sitio web, en la sección de [estadísticas sobre la población](https://www.indec.gob.ar/indec/web/Nivel4-Tema-2-24-119).""" 
        )

    with col2:
        st.markdown(f"#### Metodología")
        st.markdown("**Creación del dataset**")
        st.info(
            """Utilizando la librería Polars en Google Colab, se tomaron los datos recolectados por el SNIC (Sistema Nacional de Información Criminal) y las proyecciones de población realizadas por el INDEC a nivel departamental, y se cruzaron ambas fuentes para obtener un dataset que contiene una fila por cada combinación de provincia, departamento, categoría y tipo de delito, con la cantidad correspondiente de hechos, víctimas y población a nivel departamental, provincial y nacional. [El código está disponible en este notebook de Google Colab](https://colab.research.google.com/drive/1YWjzinfXxcGgIHPhCizsOjG-HZQSrhIc?usp=sharing).""" 
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
            - **Registro heterogéneo de delitos**: la forma en que se registran los delitos puede variar entre provincias y departamentos, lo que afecta la comparabilidad entre jurisdicciones. Además, a lo largo de los años, algunos tipos de delitos utilizados para clasificar los hechos han cambiado, lo cual dificulta, en ciertos casos, analizar su evolución temporal. 
            """ 
        )