import streamlit as st
import polars as pl
import plotly.express as px
import json

# Configuración de página (quita márgenes grandes)
st.set_page_config(
    page_title="Delitos en Argentina",
    page_icon="🚓",
    layout="wide",  # ocupa todo el ancho
    initial_sidebar_state="collapsed"
)

# Color principal
ACCENT_COLOR = "#328ec0" 

# CSS para estilos
st.markdown(
    f"""
    <style>
    /* Quitar padding superior e izquierdo/derecho */
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }}

    /* Cambiar accent color (inputs, sliders, botones, etc.) */
    :root {{
        --primary-color: {ACCENT_COLOR};
        --accent-color: {ACCENT_COLOR};
        --secondary-background-color: #f0f2f6;
    }}

    /* Tabs: seleccionado */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        color: {ACCENT_COLOR} !important;
    }}

    /* Tabs: hover */
    .stTabs [data-baseweb="tab-list"] button:hover {{
        color: {ACCENT_COLOR} !important;
    }}

    /* Tabs: barrita animada (focus underline) */
    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: {ACCENT_COLOR} !important;
    }}

    /* Borde de filtros (selectbox, multiselect, input, etc.) */
    div[data-baseweb="select"] > div {{
        border: 0px solid {ACCENT_COLOR} !important;
        border-radius: 0.5rem !important;
    }}
    div[data-baseweb="input"] > div {{
        border: 0px solid {ACCENT_COLOR} !important;
        border-radius: 0.5rem !important;
    }}

    /* Multiselect: color de las cajitas de opciones seleccionadas */
    .stMultiSelect [data-baseweb="tag"] {{
        background-color: {ACCENT_COLOR} !important;
        color: white !important;
        border-radius: 0.5rem !important;
        padding: 2px 6px !important;
    }}

    .metric-card {{
        height: 11rem; /* Altura fija */
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        text-align: center;
        border: 0;
        color: white;
        display: flex;
        flex-direction: column;
        justify-content: space-between; /* Esto empuja el valor arriba y los textos abajo */
        margin-bottom: 1rem;
    }}

    /* Gradientes específicos por tipo de tarjeta */
    .metric-tasa {{ background: linear-gradient(to bottom right, #3fbbe2, #6392de); }}
    .metric-variacion {{ background: linear-gradient(to bottom right, #7b59b3, #5546b7); }}
    .metric-delitos {{ background: linear-gradient(to bottom right, #df437e, #b755a5); }}
    .metric-victimas {{ background: linear-gradient(to bottom right, #eeaf2a, #ef8154); }}

    .metric-value {{
        font-size: 2rem; /* tamaño grande */
        font-weight: bold;
        margin: 0; /* ya no hace falta margin-top: auto */
    }}

    .metric-title {{
        font-size: 1.1rem;
        margin: 0;
    }}

    .metric-subtitle {{
        font-size: 0.8rem;
        margin: 0;
    }}


    </style>
    """,
    unsafe_allow_html=True
)

# Función para cargar los datos
@st.cache_data
def load_data():
    try:
        df = pl.read_parquet('DATOS_SNIC_POB.parquet')
        return df
    except FileNotFoundError:
        st.error("No se encontró el archivo DATOS_SNIC_POB.parquet. Por favor, asegúrate de que esté en el directorio correcto.")
        return None
    
# Cargar datos
df = load_data()

# Título del dashboard
st.title("Delitos en Argentina")

# Tabs de navegación
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Vista general", "Categorías y tipos de delitos", "Comparar provincias", "Comparar departamentos", "Fuentes y metodología"])

# ---- Vista general ----
with tab1:
    col1, col2 = st.columns([1, 4], gap = "medium")  # col1 más chica para filtros, col2 más grande para gráficos

    with col1:
        st.markdown("**Filtros**")
            
        # Filtro de año
        años_disponibles = sorted(df['anio'].unique(), reverse=True)
        año_seleccionado = st.selectbox("Año", años_disponibles)

        # ---- Categorías de delito ----
        categorias_delito = ['Todas'] + sorted(df['categoria_delito'].unique().to_list())
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito)
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # ---- Tipos de delito dependientes de categoría ----
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            tipos_disponibles = sorted(df['codigo_delito_snic_nombre'].unique().to_list())
        else:
            tipos_disponibles = (
                df
                .filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                ["codigo_delito_snic_nombre"]
                .unique()
                .to_list()
            )
            tipos_disponibles = sorted(tipos_disponibles)

        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito)
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        # ---- Provincia ----
        provincias_disponibles = ['Todas'] + sorted(df['provincia_nombre'].unique().to_list())
        provincia_seleccionada = st.selectbox("Provincia", provincias_disponibles)

        # ---- Departamentos dependientes de provincia ----
        if provincia_seleccionada != 'Todas' and provincia_seleccionada:
            departamentos_disponibles = (
                df
                .filter(pl.col("provincia_nombre") == provincia_seleccionada)
                ["depto_nombre_completo"]
                .unique()
                .to_list()
            )
            departamentos_disponibles = sorted(departamentos_disponibles)
            
        else:
            departamentos_disponibles = sorted(df['depto_nombre_completo'].unique().to_list())

        departamento = ['Todos'] + departamentos_disponibles
        departamento_seleccionado = st.selectbox("Departamento", departamento)

        # ---- Mostrar filtros aplicados ----
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}

        • **Categorías:** {", ".join([str(categoria) for categoria in categoria_delito_seleccionadas])}

        • **Tipos de delito:** {", ".join([str(delito) for delito in tipo_delito_seleccionados])}

        • **Provincia:** {provincia_seleccionada}
        
        • **Departamento:** {departamento_seleccionado}
        """)

    with col2:

        # Filtrar años
        df_año_seleccionado = df.filter(pl.col("anio") == año_seleccionado)
        año_anterior = año_seleccionado - 1
        df_año_anterior = df.filter(pl.col("anio") == año_anterior)

        # Filtro por categoría de delito
        if "Todas" not in categoria_delito_seleccionadas and categoria_delito_seleccionadas:
            df_año_seleccionado = df_año_seleccionado.filter(
                pl.col("categoria_delito").is_in(categoria_delito_seleccionadas)
            )
            df_año_anterior = df_año_anterior.filter(
                pl.col("categoria_delito").is_in(categoria_delito_seleccionadas)
            )

        # Filtro por tipo de delito
        if "Todos" not in tipo_delito_seleccionados and tipo_delito_seleccionados:
            df_año_seleccionado = df_año_seleccionado.filter(
                pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados)
            )
            df_año_anterior = df_año_anterior.filter(
                pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados)
            )

        # Filtros por región y población
        if departamento_seleccionado != "Todos" and departamento_seleccionado:
            df_año_seleccionado = df_año_seleccionado.filter(
                pl.col("depto_nombre_completo") == departamento_seleccionado
            )
            df_año_anterior = df_año_anterior.filter(
                pl.col("depto_nombre_completo") == departamento_seleccionado
            )
            poblacion = df_año_seleccionado["poblacion_departamento"].max()
            poblacion_año_anterior = df_año_anterior["poblacion_departamento"].max()

        elif (
            provincia_seleccionada != "Todas"
            and (departamento_seleccionado == "Todos" or not departamento_seleccionado)
            and provincia_seleccionada
        ):
            df_año_seleccionado = df_año_seleccionado.filter(
                pl.col("provincia_nombre") == provincia_seleccionada
            )
            df_año_anterior = df_año_anterior.filter(
                pl.col("provincia_nombre") == provincia_seleccionada
            )
            poblacion = df_año_seleccionado["poblacion_provincia"].max()
            poblacion_año_anterior = df_año_anterior["poblacion_provincia"].max()

        else:
            poblacion = df_año_seleccionado["poblacion_pais"].max()
            poblacion_año_anterior = df_año_anterior["poblacion_pais"].max()

        # Totales y tasas
        total_hechos_año_anterior = df_año_anterior["cantidad_hechos"].sum()
        total_hechos = df_año_seleccionado["cantidad_hechos"].sum()
        tasa = (total_hechos / poblacion) * 100000
        tasa_año_anterior = (total_hechos_año_anterior / poblacion_año_anterior) * 100000
        variación = ((tasa - tasa_año_anterior) / tasa_año_anterior) * 100

        total_victimas = df_año_seleccionado["cantidad_victimas"].sum()

        st.markdown(f"#### Métricas {año_seleccionado}")

        if año_seleccionado != 2010:

            # Mostrar métricas
            col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
            
            with col_metric1:

                st.markdown(f"""
                <div class="metric-card metric-tasa">
                    <div class="metric-value">{tasa:,.0f}</div>
                    <div class="metric-title">Tasa de delitos</div>
                    <div class="metric-subtitle">Cantidad de delitos cada 100 mil habitantes</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_metric2:

                st.markdown(f"""
                <div class="metric-card metric-variacion">
                    <div class="metric-value">{variación:.2f}%</div>
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
                    <div class="metric-value">{tasa:,.0f}</div>
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
        
        # Gráfico de evolución nacional
        st.markdown("#### Evolución a lo largo de los años")

        # Filtros
        if "Todas" not in categoria_delito_seleccionadas and categoria_delito_seleccionadas:
            df_graficos = df.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
        else:
            df_graficos = df

        if "Todos" not in tipo_delito_seleccionados and tipo_delito_seleccionados:
            df_graficos = df_graficos.filter(
                pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados)
            )

        if departamento_seleccionado != "Todos" and departamento_seleccionado:
            df_graficos = df_graficos.filter(pl.col("depto_nombre_completo") == departamento_seleccionado)

        elif (
            provincia_seleccionada != "Todas"
            and (departamento_seleccionado == "Todos" or not departamento_seleccionado)
            and provincia_seleccionada
        ):
            df_graficos = df_graficos.filter(pl.col("provincia_nombre") == provincia_seleccionada)        

        # Filtros por región y población
        if departamento_seleccionado != "Todos" and departamento_seleccionado:
            df_graficos = (
                df_graficos
                .group_by("anio")
                .agg([
                    pl.col("cantidad_hechos").sum(),
                    pl.col("poblacion_departamento").first(),
                    pl.col("cantidad_victimas").sum(),
                ])
                .sort("anio")
                .with_columns([
                    (pl.col("cantidad_hechos") / (pl.col("poblacion_departamento") / 100000)).alias("tasa_delitos"),
                ])
            )

        elif (
            provincia_seleccionada != "Todas"
            and (departamento_seleccionado == "Todos" or not departamento_seleccionado)
            and provincia_seleccionada
        ):
            df_graficos = (
                df_graficos
                .group_by("anio")
                .agg([
                    pl.col("cantidad_hechos").sum(),
                    pl.col("poblacion_provincia").first(),
                    pl.col("cantidad_victimas").sum(),
                ])
                .sort("anio")
                .with_columns([
                    (pl.col("cantidad_hechos") / (pl.col("poblacion_provincia") / 100000)).alias("tasa_delitos"),
                ])
            )

        else:
            df_graficos = (
                df_graficos
                .group_by("anio")
                .agg([
                    pl.col("cantidad_hechos").sum(),
                    pl.col("poblacion_pais").first(),
                    pl.col("cantidad_victimas").sum(),
                ])
                .sort("anio")
                .with_columns([
                    (pl.col("cantidad_hechos") / (pl.col("poblacion_pais") / 100000)).alias("tasa_delitos"),
                ])
            )

        df_graficos = (
            df_graficos
            .with_columns([
                pl.col("tasa_delitos").shift(1).alias("tasa_delitos_anterior"),
            ])
            .with_columns([
                ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / pl.col("tasa_delitos_anterior")).alias("variacion"),
            ])
        )

        col_graficos1, col_graficos2 = st.columns([1, 1], gap = "medium")

        min_anio = df_graficos["anio"].min()
        max_anio = df_graficos["anio"].max()

        with col_graficos1:

            st.markdown("###### Tasa de delitos")
            # st.markdown("*La tasa de delitos es la cantidad de delitos cada 100,000 habitantes*")

            fig_evolucion = px.line(
                df_graficos, 
                x='anio', 
                y='tasa_delitos',
                title="",
                line_shape='spline',
                markers=True,
                color_discrete_sequence=['#3fbbe2']
            )
            
            fig_evolucion.update_layout(
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                height=200,
                margin=dict(l=0, r=30, t=0, b=0),
            )

            # Línea más gruesa
            fig_evolucion.update_traces(
                line=dict(width=3),
                marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Tasa de delitos  %{y:,.0f}<extra></extra>"
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
            st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": False})

            st.markdown("###### Variación en la tasa de delitos")
            # st.markdown("*La tasa de delitos es la cantidad de delitos cada 100,000 habitantes*")
            
            fig_evolucion = px.line(
                df_graficos, 
                x='anio', 
                y='variacion',
                title="",
                line_shape='spline',
                markers=True,
                color_discrete_sequence=['#7b59b3']
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

            fig_evolucion.add_hline(y=0, line_dash="dash", line_color="darkgrey", line_width=2)

            # Línea más gruesa
            fig_evolucion.update_traces(
                line=dict(width=3),
                marker=dict(size=8),
                hovertemplate="Año  %{x}<br>Variación  %{y:.2%}<extra></extra>"
            )

            # Grilla y formato del eje Y con comas
            fig_evolucion.update_xaxes(
                range=[min_anio - 0.5, max_anio + 0.5],  # padding de medio año a cada lado
                tick0=min_anio,
                dtick=3,  # que muestre solo enteros (años)
                showgrid=True,
                gridcolor='lightgray'
            )
            fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")

            # Mostrar en Streamlit con modebar abajo a la derecha
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

# ---- Categorías y tipos de delito ----
with tab2:
    col1, col2 = st.columns([1, 4], gap = "medium")

    with col1:
        st.markdown("**Filtros**")
            
        # Filtro de año
        años_disponibles = sorted(df['anio'].unique(), reverse=True)
        año_seleccionado = st.selectbox("Año", años_disponibles, key = 'Año tab2')

        # ---- Categorías de delito ----
        categorias_delito = ['Todas'] + sorted(df['categoria_delito'].unique().to_list())
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito,  key = 'Categorías tab2')
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # ---- Tipos de delito dependientes de categoría ----
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            tipos_disponibles = sorted(df['codigo_delito_snic_nombre'].unique().to_list())
        else:
            tipos_disponibles = (
                df
                .filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                ["codigo_delito_snic_nombre"]
                .unique()
                .to_list()
            )
            tipos_disponibles = sorted(tipos_disponibles)
        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito,  key = 'Tipo de delito tab2')
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        # ---- Provincia ----
        provincias_disponibles = ['Todas'] + sorted(df['provincia_nombre'].unique().to_list())
        provincia_seleccionada = st.selectbox("Provincia", provincias_disponibles,  key = 'Provincia tab2')

        # ---- Departamentos dependientes de provincia ----
        if provincia_seleccionada != 'Todas' and provincia_seleccionada:
            departamentos_disponibles = (
                df
                .filter(pl.col("provincia_nombre") == provincia_seleccionada)
                ["depto_nombre_completo"]
                .unique()
                .to_list()
            )
            departamentos_disponibles = sorted(departamentos_disponibles)
        else:
            departamentos_disponibles = sorted(df['depto_nombre_completo'].unique().to_list())

        departamento = ['Todos'] + departamentos_disponibles
        departamento_seleccionado = st.selectbox("Departamento", departamento,  key = 'Departamento tab2')

        # ---- Mostrar filtros aplicados ----
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}

        • **Categorías:** {", ".join([str(categoria) for categoria in categoria_delito_seleccionadas])}

        • **Tipos de delito:** {", ".join([str(delito) for delito in tipo_delito_seleccionados])}

        • **Provincia:** {provincia_seleccionada}
        
        • **Departamento:** {departamento_seleccionado}
        """)

    with col2:

        # Filtrar datos según selección
        df_año_seleccionado = df.filter(pl.col("anio") == año_seleccionado)

        if 'Todas' not in categoria_delito_seleccionadas and categoria_delito_seleccionadas:
            df_año_seleccionado = df.filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
        
        if 'Todos' not in tipo_delito_seleccionados and tipo_delito_seleccionados:
            df_año_seleccionado = df.filter(pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados))

        if departamento_seleccionado != 'Todos' and departamento_seleccionado:
            df_año_seleccionado = df.filter(pl.col("depto_nombre_completo") == departamento_seleccionado)

        elif provincia_seleccionada != 'Todas' and (departamento_seleccionado == 'Todos' or not departamento_seleccionado) and provincia_seleccionada:
            df_año_seleccionado = df.filter(pl.col("provincia_nombre") == provincia_seleccionada)

        # Cálculos por categoría de delito
        df_categoria_delito = (
            df_año_seleccionado
            .group_by("categoria_delito")
            .agg([
                pl.col("cantidad_hechos").sum().alias("cantidad_hechos")
            ])
            .sort("cantidad_hechos", descending=True)
        )

        total_hechos = df_categoria_delito["cantidad_hechos"].sum()

        df_categoria_delito = df_categoria_delito.with_columns(
            (pl.col("cantidad_hechos") / total_hechos).alias("porcentaje_categoria")
        )

        # Cálculos por tipo de delito
        df_tipo_delito = (
            df_año_seleccionado
            .group_by("codigo_delito_snic_nombre")
            .agg([
                pl.col("cantidad_hechos").sum().alias("cantidad_hechos")
            ])
            .sort("cantidad_hechos", descending=True)
        )

        df_tipo_delito = df_tipo_delito.with_columns(
            (pl.col("cantidad_hechos") / total_hechos).alias("porcentaje_tipo_delito")
        )

        altura_grafico_categorias = df_categoria_delito.head(5).shape[0] * 35
        altura_grafico_tipos = df_tipo_delito.head(5).shape[0] * 35

        custom_colorscale = ["#c5b6dc", '#7b59b3']

        # Recortar títulos largos
        MAX_LEN = 28

        df_categoria_delito = df_categoria_delito.with_columns(
            pl.when(pl.col("categoria_delito").str.len_chars() <= MAX_LEN)
            .then(pl.col("categoria_delito"))
            .otherwise(pl.col("categoria_delito").str.slice(0, MAX_LEN - 2) + "...")
            .alias("categoria_delito_short")
        )

        df_tipo_delito = df_tipo_delito.with_columns(
            pl.when(pl.col("codigo_delito_snic_nombre").str.len_chars() <= MAX_LEN)
            .then(pl.col("codigo_delito_snic_nombre"))
            .otherwise(pl.col("codigo_delito_snic_nombre").str.slice(0, MAX_LEN - 2) + "...")
            .alias("tipo_delito_short")
        )

        # ==================================================
        # --- Gráfico categorías ---
        # ==================================================
        st.markdown("###### Top 5 categorías de delitos según su porcentaje")

        top5_categorias = df_categoria_delito.head(5)

        top5_categorias = top5_categorias.with_columns(
            pl.concat_str([
                (pl.col("porcentaje_categoria") * 100).round(1).cast(pl.Utf8),
                pl.lit("%")
            ]).alias("porcentaje_categoria_text")
        )

        fig_ranking = px.bar(
            top5_categorias.to_pandas(),  # Plotly Express necesita Pandas
            x='porcentaje_categoria', 
            y='categoria_delito_short',
            orientation='h',
            color='porcentaje_categoria',
            color_continuous_scale=custom_colorscale,
            text='porcentaje_categoria_text',  # usamos la columna formateada
            custom_data=["categoria_delito", "cantidad_hechos", "porcentaje_categoria"]
        )

        fig_ranking.update_traces(
            textposition="inside",
            insidetextanchor="start",   # alinea a la izquierda dentro de la barra
            textfont=dict(color="white"),
            texttemplate="  %{text}",   # agrega espacio antes del texto
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                        "Porcentaje: %{customdata[2]:.2%}<br>" +
                        "Cantidad de delitos: %{customdata[1]:,}<extra></extra>"
        )

        fig_ranking.update_layout(
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=10),
            height=altura_grafico_categorias,
            yaxis={'categoryorder':'total ascending'},
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False),
            barcornerradius=5
        )

        fig_ranking.update_coloraxes(showscale=False)

        fig_ranking.update_xaxes(
            tickformat=".0%",   # porcentaje sin decimales
            showgrid=True,      # mostrar líneas de fondo
            gridcolor="lightgrey",
            gridwidth=0.5
        )

        fig_ranking.add_shape(
            type="line",
            x0=0, x1=0,               # línea vertical en x=0
            y0=-0.5, y1=len(top5_categorias)-0.5,  # cubre todas las barras
            line=dict(color="lightgrey", width=1)
        )

        st.plotly_chart(fig_ranking, use_container_width=True, config={"displayModeBar": False})

        # ==================================================
        # --- Gráfico tipos ---
        # ==================================================
        st.markdown("###### Top 5 tipos de delitos según su porcentaje")

        top5_tipos = df_tipo_delito.head(5)

        top5_tipos = top5_tipos.with_columns(
            pl.concat_str([
                (pl.col("porcentaje_tipo_delito") * 100).round(1).cast(pl.Utf8),
                pl.lit("%")
            ]).alias("porcentaje_tipo_delito_text")
        )

        fig_ranking = px.bar(
            top5_tipos, 
            x='porcentaje_tipo_delito', 
            y='tipo_delito_short',
            orientation='h',
            color='porcentaje_tipo_delito',
            color_continuous_scale=custom_colorscale,
            text='porcentaje_tipo_delito_text',
            custom_data=["codigo_delito_snic_nombre", "cantidad_hechos", "porcentaje_tipo_delito"]
        )

        fig_ranking.update_traces(
            textposition="inside",
            insidetextanchor="start",
            textfont=dict(color="white"),
            texttemplate="  %{text}",
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                        "Porcentaje: %{customdata[2]:.2%}<br>" +
                        "Cantidad de delitos: %{customdata[1]:,}<extra></extra>"
        )

        fig_ranking.update_layout(
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=10),
            height=altura_grafico_tipos,
            yaxis={'categoryorder':'total ascending'},
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(visible=False),
            barcornerradius=5
        )

        fig_ranking.update_coloraxes(showscale=False)

        fig_ranking.update_xaxes(
            tickformat=".0%",   # porcentaje sin decimales
            showgrid=True,
            gridcolor="lightgrey",
            gridwidth=0.5
        )

        fig_ranking.add_shape(
            type="line",
            x0=0, x1=0,               # línea vertical en x=0
            y0=-0.5, y1=len(top5_categorias)-0.5,  # cubre todas las barras
            line=dict(color="lightgrey", width=1)
        )

        st.plotly_chart(fig_ranking, use_container_width=True, config={"displayModeBar": False})

# ---- Comparar provincias ----
with tab3:
    col1, col2 = st.columns([1, 4], gap = "medium")

    with col1:
        st.markdown("**Filtros**")
            
        # Filtro de año
        años_disponibles = sorted(df['anio'].unique(), reverse=True)
        año_seleccionado = st.selectbox("Año", años_disponibles, key = 'Año tab3')

        # ---- Categorías de delito ----
        categorias_delito = ['Todas'] + sorted(df['categoria_delito'].unique().to_list())
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito,  key = 'Categorías tab3')
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # ---- Tipos de delito dependientes de categoría ----
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            tipos_disponibles = sorted(df['codigo_delito_snic_nombre'].unique().to_list())
        else:
            tipos_disponibles = (
                df
                .filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                ["codigo_delito_snic_nombre"]
                .unique()
                .to_list()
            )
            tipos_disponibles = sorted(tipos_disponibles)
        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito,  key = 'Tipo de delito tab3')
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        # ---- Mostrar filtros aplicados ----
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}

        • **Categorías:** {", ".join([str(categoria) for categoria in categoria_delito_seleccionadas])}

        • **Tipos de delito:** {", ".join([str(delito) for delito in tipo_delito_seleccionados])}
        """)

    with col2:

        st.markdown(f"#### Comparación de la tasa de delitos por provincia")

        # Filtrar datos según selección
        df_filtrado = df

        if "Todas" not in categoria_delito_seleccionadas and categoria_delito_seleccionadas:
            df_filtrado = df_filtrado.filter(
                pl.col("categoria_delito").is_in(categoria_delito_seleccionadas)
            )

        if "Todos" not in tipo_delito_seleccionados and tipo_delito_seleccionados:
            df_filtrado = df_filtrado.filter(
                pl.col("codigo_delito_snic_nombre").is_in(tipo_delito_seleccionados)
            )

        # Agrupar por año y provincia
        df_evolucion = (
            df_filtrado
            .group_by(["anio", "provincia_nombre"])
            .agg([
                pl.col("cantidad_hechos").sum().alias("cantidad_hechos"),
                pl.col("poblacion_provincia").first().alias("poblacion_provincia")
            ])
            .sort("cantidad_hechos", descending=True)
        )

        # Calcular tasa de delitos
        df_evolucion = df_evolucion.with_columns(
            ((pl.col("cantidad_hechos") / (pl.col("poblacion_provincia") / 100_000)).round(0)).alias("tasa_delitos")
        )

        # Reemplazo nombres largos para visualización
        replacements_espacio = {
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del Fuego",
            "Ciudad Autónoma de Buenos Aires": "CABA"
        }

        replacements_mapa = {
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del Fuego",
            "Ciudad Autónoma de Buenos Aires": "Ciudad de Buenos Aires"
        }

        df_evolucion = df_evolucion.with_columns([
            pl.col("provincia_nombre").replace(replacements_espacio).alias("provincia_nombre_espacio"),
            pl.col("provincia_nombre").replace(replacements_espacio).alias("provincia_nombre_short"),
            pl.col("provincia_nombre").replace(replacements_mapa).alias("provincia_nombre_mapa")
        ])

        # Recortar nombres largos
        MAX_LEN = 28
        df_evolucion = df_evolucion.with_columns(
            pl.when(pl.col("provincia_nombre_short").str.len_chars() <= MAX_LEN)
            .then(pl.col("provincia_nombre_short"))
            .otherwise(pl.col("provincia_nombre_short").str.slice(0, MAX_LEN-2) + "...")
            .alias("provincia_nombre_short")
        )

        # Ordenar
        df_evolucion = df_evolucion.sort(["provincia_nombre", "anio"])

        # Calcular tasa_delitos_anterior y variación
        df_evolucion = df_evolucion.with_columns(
            pl.col("tasa_delitos").shift(1).over("provincia_nombre").alias("tasa_delitos_anterior")
        ).with_columns(
            ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / pl.col("tasa_delitos_anterior")).alias("variacion")
        )

        # Filtrar año seleccionado
        df_año_seleccionado = df_evolucion.filter(pl.col("anio") == año_seleccionado)

        # Altura de gráfico y colores
        altura_grafico = 24 * 25
        custom_colorscale = ["#a5c6d9", "#328ec0"]

        col_ranking, col_mapa = st.columns([1, 1], gap = 'medium')

        # ==================================================
        # --- Gráfico categorías ---
        # ==================================================
        with col_ranking:
            st.markdown("###### Tasa de delitos por provincia")

            fig_ranking = px.bar(
                df_año_seleccionado, 
                x='tasa_delitos', 
                y='provincia_nombre_short',
                orientation='h',
                color='tasa_delitos',
                color_continuous_scale=custom_colorscale,
                text=df_año_seleccionado['tasa_delitos'],
                custom_data=["provincia_nombre", "cantidad_hechos", "tasa_delitos"]
            )

            fig_ranking.update_traces(
                textposition="inside",
                insidetextanchor="start",   # alinea a la izquierda dentro de la barra
                textfont=dict(color="white"),
                texttemplate="  %{text}",   # agrega espacio antes del texto
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                            "Tasa de delitos: %{customdata[2]:,}<br>" +
                            "Cantidad de delitos: %{customdata[1]:,}<extra></extra>"
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

            fig_ranking.update_xaxes(
                showgrid=True,
                gridcolor="lightgrey",
                gridwidth=0.5
            )

            fig_ranking.add_shape(
                type="line",
                x0=0, x1=0,               # línea vertical en x=0
                y0=-0.5, y1=len(df_año_seleccionado)-0.5,  # cubre todas las barras
                line=dict(color="lightgrey", width=1)
            )

            st.plotly_chart(fig_ranking, use_container_width=True, config={"displayModeBar": False})

        with col_mapa:
            st.markdown("###### Mapa de delitos por provincia")
            custom_colorscale = ["#a5c6d9", "#1473a6"]

            with open("ar.json", "r", encoding="utf-8") as f:
                argentina_geo = json.load(f)

            fig = px.choropleth_mapbox(
                df_año_seleccionado,
                geojson=argentina_geo,
                featureidkey="properties.name",  # nombre de la provincia en el GeoJSON
                locations="provincia_nombre_mapa",  # columna de tu df
                color="tasa_delitos",
                color_continuous_scale=custom_colorscale,
                mapbox_style="white-bg",  # fondo blanco
                opacity=0.7,
                hover_data=["provincia_nombre", "cantidad_hechos", "tasa_delitos"],  # datos para hover
                labels={"tasa_delitos": "Tasa de delitos"}
            )

            # Formatear hover como en las barras
            fig.update_traces(
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                            "Tasa de delitos: %{customdata[2]:,}<br>" +
                            "Cantidad de delitos: %{customdata[1]:,}<extra></extra>"
            )

            fig.update_layout(
                title="",
                margin={"r":0,"t":0,"l":0,"b":0},
                height=altura_grafico,          # igual que las barras
                coloraxis_showscale=False,      # quitar la escala
                mapbox=dict(
                    style="white-bg",
                    center={"lat": -39.5, "lon": -64.0},  # centro aproximado de Argentina
                    zoom=3                             # zoom suficiente para ver todo el país
                ),
            )

            st.plotly_chart(fig, use_container_width=True)

        
        st.markdown(f"#### Evolución a lo largo de los años")

        # ---- Provincia ----
        provincias_disponibles = ['Todas'] + sorted(df['provincia_nombre'].unique().to_list())
        provincia_seleccionada = st.multiselect("Seleccionar provincias", provincias_disponibles,  key = 'Provincia tab3', default = ['Buenos Aires', 'Santa Fe', 'Salta'])
        if 'Todas' in provincia_seleccionada or not provincia_seleccionada:
            provincia_seleccionada = ['Todas']

        st.markdown("###### Tasa de delitos por provincia")

        # Filtrar provincias seleccionadas
        if "Todas" not in provincia_seleccionada and provincia_seleccionada:
            df_evolucion = df_evolucion.filter(
                pl.col("provincia_nombre").is_in(provincia_seleccionada)
            )

        # Paleta de colores personalizada
        colors = [
            '#3B73AA', '#2E8484', '#2E2E84', '#506295', '#956fab', '#d87cad',
            '#842E59', '#007fa5', '#00a4ae', '#15c79f', '#658bb9', '#b7758a',
            '#804458', '#00b3a6', '#298c85', '#35c191', '#0097fa', '#00685a',
            '#3d4756', '#00c6c9', '#95baec', '#00b3ff', '#93e483', '#2e5984'
        ]

        # Diccionario para nombres cortos
        nombre_mapeo = {
            "Ciudad Autónoma de Buenos Aires": "CABA",
            "Tierra del Fuego, Antártida e Islas del Atlántico Sur": "Tierra del fuego"
        }

        # Crear columna con nombre abreviado
        df_evolucion = df_evolucion.with_columns(
            pl.col("provincia_nombre").replace(nombre_mapeo).alias("provincia_nombre_short")
        )

        # Figura principal
        fig_evolucion = px.line(
            df_evolucion, 
            x='anio', 
            y='tasa_delitos',
            line_shape='spline',
            color='provincia_nombre_short',  
            custom_data=["provincia_nombre", "anio", "tasa_delitos", "cantidad_hechos", "poblacion_provincia"],
            color_discrete_sequence=colors,  # <- usar paleta personalizada
            title=""
        )

        # Hover con nombre completo y mismo color que la línea
        for trace in fig_evolucion.data:
            color = trace.line.color
            trace.hovertemplate = (
                f"<b><span style='color:{color}'>%{{customdata[0]}}</span></b><br>" +
                "Año %{customdata[1]}<br>" +
                "Tasa de delitos: %{customdata[2]:,.0f}<br>" +
                "Cantidad de delitos: %{customdata[3]:,.0f}<br>" +
                "Población: %{customdata[4]:,.0f}<extra></extra>"
            )
            trace.line.width = 3

        # Quitar leyenda
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

        # Ajustar eje Y
        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")

        # Ajustar eje X al máximo año + espacio
        min_year = df_evolucion["anio"].min()
        max_year = df_evolucion["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year, max_year + 0.5], dtick=1)  # dtick=1 asegura solo enteros

        # Etiquetas finales con mismo color que línea
        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}

        # Iterar sobre provincias únicas
        for prov in df_evolucion["provincia_nombre_short"].unique().to_list():
            df_prov = df_evolucion.filter(pl.col("provincia_nombre_short") == prov)
            
            # Último año
            ultimo_x = df_prov["anio"].max()
            
            # Tasa_delitos correspondiente al último año
            ultimo_y = df_prov.filter(pl.col("anio") == ultimo_x)["tasa_delitos"].item()
            
            # Agregar anotación en Plotly
            fig_evolucion.add_annotation(
                x=ultimo_x,
                y=ultimo_y,
                text=prov,
                showarrow=False,
                xanchor="left",
                xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        # Mostrar en Streamlit
        st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": True})

        st.markdown("###### Variación anual de la tasa de delitos por provincia")

        df_evolucion = df_evolucion.filter(pl.col('anio') >= 2010)

        # Figura principal
        fig_evolucion = px.line(
            df_evolucion, 
            x='anio', 
            y='variacion',
            line_shape='spline',
            color='provincia_nombre_short',  
            custom_data=["provincia_nombre", "anio", "variacion", "cantidad_hechos", "poblacion_provincia"],
            color_discrete_sequence=colors,  # <- usar paleta personalizada
            title=""
        )

        # Hover con nombre completo y mismo color que la línea
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

        # Quitar leyenda
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

        # Ajustar eje Y
        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")

        # Ajustar eje X al máximo año + espacio
        min_year = df_evolucion["anio"].min()
        max_year = df_evolucion["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year, max_year + 0.5], dtick=1)  # dtick=1 asegura solo enteros

        # Etiquetas finales con mismo color que línea
        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}

        # Iterar sobre provincias únicas
        for prov in df_evolucion["provincia_nombre_short"].unique().to_list():
            df_prov = df_evolucion.filter(pl.col("provincia_nombre_short") == prov)
            
            # Último año
            ultimo_x = df_prov["anio"].max()
            
            # Variación correspondiente al último año
            ultimo_y = df_prov.filter(pl.col("anio") == ultimo_x)["variacion"].item()
            
            # Agregar anotación en Plotly
            fig_evolucion.add_annotation(
                x=ultimo_x,
                y=ultimo_y,
                text=prov,
                showarrow=False,
                xanchor="left",
                xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        # Mostrar en Streamlit
        st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": True})

with tab4:
    col1, col2 = st.columns([1, 4], gap = "medium")

    with col1:
        st.markdown("**Filtros**")
            
        # Filtro de año
        años_disponibles = sorted(df['anio'].unique(), reverse=True)
        año_seleccionado = st.selectbox("Año", años_disponibles, key = 'Año tab4')

        # ---- Categorías de delito ----
        categorias_delito = ['Todas'] + sorted(df['categoria_delito'].unique().to_list())
        categoria_delito_seleccionadas = st.multiselect("Categorías", categorias_delito,  key = 'Categorías tab4')
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            categoria_delito_seleccionadas = ['Todas']

        # ---- Tipos de delito dependientes de categoría ----
        if 'Todas' in categoria_delito_seleccionadas or not categoria_delito_seleccionadas:
            tipos_disponibles = sorted(df['codigo_delito_snic_nombre'].unique().to_list())
        else:
            tipos_disponibles = (
                df
                .filter(pl.col("categoria_delito").is_in(categoria_delito_seleccionadas))
                ["codigo_delito_snic_nombre"]
                .unique()
                .to_list()
            )
            tipos_disponibles = sorted(tipos_disponibles)
        tipos_delito = ['Todos'] + tipos_disponibles
        tipo_delito_seleccionados = st.multiselect("Tipo de delito", tipos_delito,  key = 'Tipo de delito tab4')
        if 'Todos' in tipo_delito_seleccionados or not tipo_delito_seleccionados:
            tipo_delito_seleccionados = ['Todos']

        # ---- Provincia ----
        provincias_disponibles = ['Todas'] + sorted(df['provincia_nombre'].unique().to_list())
        provincia_seleccionada = st.multiselect("Provincias", provincias_disponibles,  key = 'Provincia tab4', default = ['Todas'])
        if 'Todas' in provincia_seleccionada or not provincia_seleccionada:
            provincia_seleccionada = ['Todas']

        # ---- Mostrar filtros aplicados ----
        st.markdown("**Filtros aplicados**")
        st.markdown(f"""
        • **Año:** {año_seleccionado}

        • **Categorías:** {", ".join([str(categoria) for categoria in categoria_delito_seleccionadas])}

        • **Tipos de delito:** {", ".join([str(delito) for delito in tipo_delito_seleccionados])}

        • **Provincias:** {", ".join([str(provincia) for provincia in provincia_seleccionada])}
        """)

    with col2:
        st.markdown(f"#### Comparación de la tasa de delitos por departamento")

        # Filtrar datos según selección
        df_filtrado = df

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

        df_evolucion = df_filtrado.group_by(['anio', 'depto_nombre_completo']).agg([
            pl.col('cantidad_hechos').sum(),
            pl.col('poblacion_departamento').first()
        ]).sort(by = 'cantidad_hechos', descending=True)

        df_evolucion = df_evolucion.with_columns(
            (pl.col("cantidad_hechos") / (pl.col("poblacion_departamento") / 100_000))
            .round(0)
            .alias("tasa_delitos")
        )
        
        df_evolucion = df_evolucion.sort(by = ['depto_nombre_completo', 'anio'])

        # df_evolucion['depto_nombre_completo_espacio'] = '  ' + df_evolucion['depto_nombre_completo'].replace({'Tierra del Fuego, Antártida e Islas del Atlántico Sur': 'Tierra del Fuego', 'Ciudad Autónoma de Buenos Aires': 'CABA'})

        df_año_seleccionado = df_evolucion.filter(pl.col('anio') == año_seleccionado)

        altura_grafico = 24 * 25

        custom_colorscale = ["#e096b2", '#df437e']

        MAX_LEN = 28  # cantidad de caracteres visibles

        # Recortar nombres largos
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

        # ==================================================
        # --- Gráfico categorías ---
        # ==================================================
        st.markdown("###### Top 5 departamentos con mayor tasa de delitos")

        df_año_seleccionado = df_año_seleccionado.drop_nulls()

        # Seleccionar top 5 por tasa_delitos
        df_año_seleccionado = df_año_seleccionado.sort("tasa_delitos", descending=True).head(5)

        # Altura del gráfico
        altura_grafico = df_año_seleccionado.shape[0] * 35

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
            insidetextanchor="start",   # alinea a la izquierda dentro de la barra
            textfont=dict(color="white"),
            texttemplate="  %{text}",   # agrega espacio antes del texto
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                        "Tasa de delitos: %{customdata[2]:,}<br>" +
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

        fig_ranking.update_xaxes(
            showgrid=True,
            gridcolor="lightgrey",
            gridwidth=0.5
        )

        fig_ranking.add_shape(
            type="line",
            x0=0, x1=0,               # línea vertical en x=0
            y0=-0.5, y1=len(top5_categorias)-0.5,  # cubre todas las barras
            line=dict(color="lightgrey", width=1)
        )

        st.plotly_chart(fig_ranking, use_container_width=True, config={"displayModeBar": False})
   
        st.markdown(f"#### Evolución a lo largo de los años")

        # ---- Departamentos dependientes de provincia ----
        if ('Todas' not in provincia_seleccionada and provincia_seleccionada):
            departamentos_disponibles = (
                df
                .filter(pl.col("provincia_nombre").is_in(provincia_seleccionada))
                ["depto_nombre_completo"]
                .unique()
                .to_list()
            )
            departamentos_disponibles = sorted(departamentos_disponibles)
        else:
            departamentos_disponibles = sorted(df['depto_nombre_completo'].unique().to_list())

        departamentos_disponibles = ['Todos'] + departamentos_disponibles
        departamento_seleccionado = st.multiselect("Seleccionar departamentos", departamentos_disponibles,  key = 'Departamento tab4', default = ['San Isidro, Buenos Aires', 'Tigre, Buenos Aires'])

        # Filtrar df_evolucion
        if "Todos" not in departamento_seleccionado and departamento_seleccionado:
            df_evolucion = df_evolucion.filter(
                pl.col("depto_nombre_completo").is_in(departamento_seleccionado)
            )

        # Ordenar
        df_evolucion = df_evolucion.sort(["depto_nombre_completo", "anio"])

        # Calcular tasa_delitos_anterior y variación
        df_evolucion = df_evolucion.with_columns(
            pl.col("tasa_delitos").shift(1).over("depto_nombre_completo").alias("tasa_delitos_anterior"),
        ).with_columns(
            ((pl.col("tasa_delitos") - pl.col("tasa_delitos_anterior")) / pl.col("tasa_delitos_anterior")).alias("variacion")
        )

        st.markdown("###### Tasa de delitos por departamento")

        # Paleta de colores personalizada
        colors = [
            '#3B73AA', '#2E8484', '#2E2E84', '#506295', '#956fab', '#d87cad',
            '#842E59', '#007fa5', '#00a4ae', '#15c79f', '#658bb9', '#b7758a',
            '#804458', '#00b3a6', '#298c85', '#35c191', '#0097fa', '#00685a',
            '#3d4756', '#00c6c9', '#95baec', '#00b3ff', '#93e483', '#2e5984'
        ]

        # Diccionario para nombres cortos

        # Figura principal
        fig_evolucion = px.line(
            df_evolucion, 
            x='anio', 
            y='tasa_delitos',
            line_shape='spline',
            color='departamento_nombre_short',  
            custom_data=["depto_nombre_completo", "anio", "tasa_delitos", "cantidad_hechos", "poblacion_departamento"],
            color_discrete_sequence=colors,  # <- usar paleta personalizada
            title=""
        )

        # Hover con nombre completo y mismo color que la línea
        for trace in fig_evolucion.data:
            color = trace.line.color
            trace.hovertemplate = (
                f"<b><span style='color:{color}'>%{{customdata[0]}}</span></b><br>" +
                "Año %{customdata[1]}<br>" +
                "Tasa de delitos: %{customdata[2]:,.0f}<br>" +
                "Cantidad de delitos: %{customdata[3]:,.0f}<br>" +
                "Población: %{customdata[4]:,.0f}<extra></extra>"
            )
            trace.line.width = 3

        # Quitar leyenda
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

        # Ajustar eje Y
        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=",")

        # Ajustar eje X al máximo año + espacio
        min_year = df_evolucion["anio"].min()
        max_year = df_evolucion["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year, max_year + 0.5], dtick=1)  # dtick=1 asegura solo enteros

        # Etiquetas finales con mismo color que línea
        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}

        # Iterar sobre departamentos únicos
        for depto in df_evolucion["departamento_nombre_short"].unique().to_list():
            df_depto = df_evolucion.filter(pl.col("departamento_nombre_short") == depto)
            
            # Último año
            ultimo_x = df_depto["anio"].max()
            
            # Tasa_delitos correspondiente al último año
            ultimo_y = df_depto.filter(pl.col("anio") == ultimo_x)["tasa_delitos"].item()
            
            # Agregar anotación en Plotly
            fig_evolucion.add_annotation(
                x=ultimo_x,
                y=ultimo_y,
                text=depto,
                showarrow=False,
                xanchor="left",
                xshift=10,
                font=dict(size=12, color=color_map[depto])
            )

        # Mostrar en Streamlit
        st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": True})

        st.markdown("###### Variación anual de la tasa de delitos por departamento")

        df_evolucion = df_evolucion.filter(pl.col('anio') >= 2010)

        # Figura principal
        fig_evolucion = px.line(
            df_evolucion, 
            x='anio', 
            y='variacion',
            line_shape='spline',
            color='departamento_nombre_short',  
            custom_data=["depto_nombre_completo", "anio", "variacion", "cantidad_hechos", "poblacion_departamento"],
            color_discrete_sequence=colors,  # <- usar paleta personalizada
            title=""
        )

        # Hover con nombre completo y mismo color que la línea
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

        # Quitar leyenda
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

        # Ajustar eje Y
        fig_evolucion.update_yaxes(showgrid=True, gridcolor='lightgray', tickformat=".0%")

        # Ajustar eje X al máximo año + espacio
        min_year = df_evolucion["anio"].min()
        max_year = df_evolucion["anio"].max()
        fig_evolucion.update_xaxes(range=[min_year, max_year + 0.5], dtick=1)  # dtick=1 asegura solo enteros

        # Etiquetas finales con mismo color que línea
        color_map = {trace.name: trace.line.color for trace in fig_evolucion.data}

        # Iterar sobre departamentos únicos
        for prov in df_evolucion["departamento_nombre_short"].unique().to_list():
            df_prov = df_evolucion.filter(pl.col("departamento_nombre_short") == prov)
            
            # Último año
            ultimo_x = df_prov["anio"].max()
            
            # Variación correspondiente al último año
            ultimo_y = df_prov.filter(pl.col("anio") == ultimo_x)["variacion"].item()
            
            # Agregar anotación en Plotly
            fig_evolucion.add_annotation(
                x=ultimo_x,
                y=ultimo_y,
                text=prov,
                showarrow=False,
                xanchor="left",
                xshift=10,
                font=dict(size=12, color=color_map[prov])
            )

        # Mostrar en Streamlit
        st.plotly_chart(fig_evolucion, use_container_width=False, config={"displayModeBar": True})

with tab5:
    col1, col2 = st.columns([1, 3], gap = "medium")

    with col1:
        st.subheader("Filtros")

    with col2:
        st.subheader("Gráficos")
        st.info("Aquí se mostrarán los gráficos por provincia.")