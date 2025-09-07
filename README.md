# Dashboard de Delitos en Argentina

Esta aplicación de Streamlit replica el dashboard de Power BI para visualizar datos de delitos en Argentina.

## Instalación

1. Instala las dependencias:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

2. Coloca el archivo `DATOS_SNIC_POB.parquet` en el mismo directorio que `app.py`

3. Ejecuta la aplicación:
\`\`\`bash
streamlit run app.py
\`\`\`

## Características

- **Vista general**: Métricas nacionales y evolución temporal
- **Provincias**: Análisis por provincia específica
- **Comparar provincias**: Mapa y ranking de provincias
- **Comparar evoluciones**: Comparación temporal entre provincias
- **Comparar departamentos**: Análisis comparativo de departamentos
- **Fuentes y metodología**: Información sobre los datos y cálculos

## Datos requeridos

El archivo `DATOS_SNIC_POB.parquet` debe contener las siguientes columnas:
- `provincia_nombre`
- `departamento_nombre`
- `anio`
- `codigo_delito_snic_nombre`
- `cantidad_hechos`
- `cantidad_victimas`
- `poblacion_provincia`
- `poblacion_departamento`
- `poblacion_pais`
- `mapa_provincia_nombre`
- `mapa_depto_nombre`
