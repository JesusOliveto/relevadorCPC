# Relevador CPC - Comunicación Pública de la Ciencia

## Descripción
Aplicación en Python/Streamlit para relevar instituciones educativas que trabajan en:
- **Comunicación Pública de la Ciencia**
- **Ciencia Abierta**
- **Diplomacia Científica**

## Características Principales

### 🎯 Funcionalidades
- Análisis automatizado de sitios web de universidades
- Búsqueda de términos específicos en múltiples idiomas
- Generación de reportes en Excel
- Interfaz web intuitiva con Streamlit
- Población de control (Universidad Jaume I)

### 🔍 Términos de Búsqueda
La aplicación busca términos relacionados con:

**Ciencia Abierta:**
- open science, ciencia abierta
- open data, datos abiertos
- open access, acceso abierto
- fair data, reproducible research

**Comunicación Pública:**
- science communication, comunicación científica
- public engagement, divulgación científica
- outreach, science literacy

**Diplomacia Científica:**
- science diplomacy, diplomacia científica
- international cooperation
- global science, science policy

### 🏛️ Universidades Incluidas
- Universidad Jaume I (población de control)
- MIT, Stanford, Oxford, Cambridge
- ETH Zurich, universidades españolas
- Universidades latinoamericanas
- Y más instituciones internacionales

## Instalación y Uso

### Requisitos Previos
- Python 3.8 o superior
- Entorno virtual (recomendado)

### Instalación Local
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
streamlit run relevador.py
```

### Uso en Streamlit Cloud
1. Subir archivos a GitHub
2. Conectar repositorio en Streamlit Cloud
3. Seleccionar `relevador.py` como archivo principal
4. Deployer automáticamente

## Uso de la Aplicación

### 1. Configuración
- La aplicación viene preconfigurada con universidades y términos
- Puedes revisar la lista en el sidebar

### 2. Ejecutar Relevamiento
- Hacer clic en "🚀 Ejecutar Relevamiento"
- Esperar mientras analiza cada universidad
- Ver progreso en tiempo real

### 3. Revisar Resultados
- **Métricas generales:** Resumen del análisis
- **Tabla de resultados:** Vista general por universidad
- **Detalle expandible:** Información específica por institución

### 4. Exportar Datos
- Generar archivo Excel con todos los resultados
- Incluye hoja principal y hoja de resumen
- Descarga automática

## Estructura del Reporte Excel

### Hoja 1: Relevamiento CPC
- Universidad, País, URL
- Fecha de revisión
- Resultados por categoría (Ciencia Abierta, Comunicación Pública, Diplomacia Científica)
- Términos encontrados y contexto
- URLs analizadas

### Hoja 2: Resumen
- Estadísticas generales
- Porcentajes de cobertura
- Métricas de análisis

## Notas Técnicas

### Metodología
1. **Acceso Web:** Utiliza requests con headers apropiados
2. **Análisis de Contenido:** BeautifulSoup para parsing HTML
3. **Búsqueda Inteligente:** Localiza URLs relevantes automáticamente
4. **Análisis Multiidioma:** Términos en español e inglés
5. **Rate Limiting:** Pausas entre requests para no sobrecargar servidores

### Limitaciones
- Depende de la accesibilidad de los sitios web
- Algunos sitios pueden bloquear scraping
- Análisis basado en contenido público disponible
- Términos de búsqueda predefinidos

### Consideraciones Éticas
- Respeta robots.txt cuando es posible
- Implementa delays entre requests
- No almacena contenido completo de sitios
- Solo accede a información públicamente disponible

## Personalización

### Agregar Universidades
Modificar la lista `universidades_base` en la clase `RelevadorUniversidades`:

```python
{"nombre": "Nueva Universidad", "url": "https://...", "pais": "País", "tipo": "Búsqueda"}
```

### Modificar Términos
Actualizar las listas de términos en `__init__`:
- `terminos_ciencia_abierta`
- `terminos_comunicacion_publica`
- `terminos_diplomacia_cientifica`

## Desarrollado para
Proyecto de relevamiento de instituciones educativas en Comunicación Pública de la Ciencia, Ciencia Abierta y Diplomacia Científica.

---
**Fecha:** Septiembre 2025
**Tecnologías:** Python, Streamlit, Pandas, BeautifulSoup, Requests
