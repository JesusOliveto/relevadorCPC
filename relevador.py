"""
Relevador de Instituciones Educativas en CPC (Comunicación Pública de la Ciencia)
Aplicación para relevar universidades que trabajan en:
- Comunicación Pública de la Ciencia
- Ciencia Abierta
- Diplomacia Científica

Autor: Sistema de Relevamiento CPC
Fecha: Septiembre 2025
"""

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse
import io
from datetime import datetime
import json
import logging

# Configuración de la página
st.set_page_config(
    page_title="Relevador CPC - Instituciones Educativas",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RelevadorUniversidades:
    def __init__(self):
        self.universidades_base = [
            # Población de control
            {"nombre": "Universidad Jaume I", "url": "https://www.uji.es", "pais": "España", "tipo": "Control"},
            # Universidades adicionales para buscar
            {"nombre": "MIT", "url": "https://www.mit.edu", "pais": "Estados Unidos", "tipo": "Búsqueda"},
            {"nombre": "Stanford University", "url": "https://www.stanford.edu", "pais": "Estados Unidos", "tipo": "Búsqueda"},
            {"nombre": "University of Oxford", "url": "https://www.ox.ac.uk", "pais": "Reino Unido", "tipo": "Búsqueda"},
            {"nombre": "University of Cambridge", "url": "https://www.cam.ac.uk", "pais": "Reino Unido", "tipo": "Búsqueda"},
            {"nombre": "ETH Zurich", "url": "https://ethz.ch", "pais": "Suiza", "tipo": "Búsqueda"},
            {"nombre": "Universidad de Barcelona", "url": "https://www.ub.edu", "pais": "España", "tipo": "Búsqueda"},
            {"nombre": "Universidad Complutense Madrid", "url": "https://www.ucm.es", "pais": "España", "tipo": "Búsqueda"},
            {"nombre": "Universidad de Buenos Aires", "url": "https://www.uba.ar", "pais": "Argentina", "tipo": "Búsqueda"},
            {"nombre": "Universidade de São Paulo", "url": "https://www.usp.br", "pais": "Brasil", "tipo": "Búsqueda"},
            {"nombre": "University of Toronto", "url": "https://www.utoronto.ca", "pais": "Canadá", "tipo": "Búsqueda"},
            {"nombre": "Australian National University", "url": "https://www.anu.edu.au", "pais": "Australia", "tipo": "Búsqueda"},
            {"nombre": "University of Tokyo", "url": "https://www.u-tokyo.ac.jp", "pais": "Japón", "tipo": "Búsqueda"},
            {"nombre": "Tsinghua University", "url": "https://www.tsinghua.edu.cn", "pais": "China", "tipo": "Búsqueda"},
        ]
        
        # Términos de búsqueda para cada categoría
        self.terminos_ciencia_abierta = [
            "open science", "ciencia abierta", "open data", "datos abiertos",
            "open access", "acceso abierto", "open research", "investigación abierta",
            "fair data", "reproducible research", "transparent research"
        ]
        
        self.terminos_comunicacion_publica = [
            "science communication", "comunicación científica", "comunicación pública de la ciencia",
            "public engagement", "divulgación científica", "outreach", "science outreach",
            "public understanding of science", "science literacy", "alfabetización científica"
        ]
        
        self.terminos_diplomacia_cientifica = [
            "science diplomacy", "diplomacia científica", "scientific diplomacy",
            "international cooperation", "cooperación internacional científica",
            "global science", "science policy", "política científica"
        ]
        
        self.resultados = []
    
    def buscar_terminos_en_contenido(self, contenido, terminos):
        """Busca términos específicos en el contenido web"""
        contenido_lower = contenido.lower()
        terminos_encontrados = []
        
        for termino in terminos:
            if termino.lower() in contenido_lower:
                # Buscar contexto del término
                pattern = rf'.{{0,100}}{re.escape(termino.lower())}.{{0,100}}'
                matches = re.findall(pattern, contenido_lower, re.IGNORECASE)
                if matches:
                    terminos_encontrados.append({
                        "termino": termino,
                        "contexto": matches[0][:200] + "..." if len(matches[0]) > 200 else matches[0]
                    })
        
        return terminos_encontrados
    
    def obtener_contenido_web(self, url, timeout=10):
        """Obtiene el contenido HTML de una URL"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=timeout, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error al acceder a {url}: {str(e)}")
            return None
    
    def analizar_universidad(self, universidad):
        """Analiza una universidad específica"""
        resultado = {
            "nombre": universidad["nombre"],
            "url": universidad["url"],
            "pais": universidad["pais"],
            "tipo": universidad["tipo"],
            "fecha_revision": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "accesible": False,
            "ciencia_abierta": {"encontrado": False, "terminos": [], "score": 0},
            "comunicacion_publica": {"encontrado": False, "terminos": [], "score": 0},
            "diplomacia_cientifica": {"encontrado": False, "terminos": [], "score": 0},
            "contenido_analizado": "",
            "urls_analizadas": []
        }
        
        # Intentar acceder al sitio principal
        contenido_principal = self.obtener_contenido_web(universidad["url"])
        
        if contenido_principal:
            resultado["accesible"] = True
            soup = BeautifulSoup(contenido_principal, 'html.parser')
            
            # Extraer texto del contenido
            texto_contenido = soup.get_text()
            resultado["contenido_analizado"] = texto_contenido[:1000]  # Primeros 1000 caracteres
            resultado["urls_analizadas"].append(universidad["url"])
            
            # Buscar en páginas adicionales relevantes
            urls_adicionales = self.encontrar_urls_relevantes(soup, universidad["url"])
            
            # Analizar contenido principal y adicional
            todo_contenido = texto_contenido
            
            for url_adicional in urls_adicionales[:3]:  # Limitar a 3 URLs adicionales
                contenido_adicional = self.obtener_contenido_web(url_adicional)
                if contenido_adicional:
                    soup_adicional = BeautifulSoup(contenido_adicional, 'html.parser')
                    todo_contenido += " " + soup_adicional.get_text()
                    resultado["urls_analizadas"].append(url_adicional)
                time.sleep(1)  # Pausa entre requests
            
            # Analizar términos
            resultado["ciencia_abierta"]["terminos"] = self.buscar_terminos_en_contenido(
                todo_contenido, self.terminos_ciencia_abierta
            )
            resultado["comunicacion_publica"]["terminos"] = self.buscar_terminos_en_contenido(
                todo_contenido, self.terminos_comunicacion_publica
            )
            resultado["diplomacia_cientifica"]["terminos"] = self.buscar_terminos_en_contenido(
                todo_contenido, self.terminos_diplomacia_cientifica
            )
            
            # Calcular scores
            resultado["ciencia_abierta"]["score"] = len(resultado["ciencia_abierta"]["terminos"])
            resultado["ciencia_abierta"]["encontrado"] = resultado["ciencia_abierta"]["score"] > 0
            
            resultado["comunicacion_publica"]["score"] = len(resultado["comunicacion_publica"]["terminos"])
            resultado["comunicacion_publica"]["encontrado"] = resultado["comunicacion_publica"]["score"] > 0
            
            resultado["diplomacia_cientifica"]["score"] = len(resultado["diplomacia_cientifica"]["terminos"])
            resultado["diplomacia_cientifica"]["encontrado"] = resultado["diplomacia_cientifica"]["score"] > 0
        
        return resultado
    
    def encontrar_urls_relevantes(self, soup, base_url):
        """Encuentra URLs relevantes para buscar contenido específico"""
        urls_relevantes = []
        
        # Palabras clave para encontrar páginas relevantes
        palabras_clave = [
            "research", "investigacion", "ciencia", "science",
            "open", "abierto", "data", "datos", "policy",
            "comunicacion", "communication", "outreach"
        ]
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            texto = link.get_text().lower()
            
            # Verificar si contiene palabras clave
            if any(palabra in href or palabra in texto for palabra in palabras_clave):
                url_completa = urljoin(base_url, link['href'])
                if url_completa not in urls_relevantes and len(urls_relevantes) < 10:
                    urls_relevantes.append(url_completa)
        
        return urls_relevantes
    
    def ejecutar_relevamiento(self, progreso_callback=None):
        """Ejecuta el relevamiento completo"""
        self.resultados = []
        total = len(self.universidades_base)
        
        for i, universidad in enumerate(self.universidades_base):
            if progreso_callback:
                progreso_callback(i + 1, total, universidad["nombre"])
            
            resultado = self.analizar_universidad(universidad)
            self.resultados.append(resultado)
            
            # Pausa entre análisis para no sobrecargar servidores
            time.sleep(2)
        
        return self.resultados
    
    def generar_excel(self):
        """Genera un archivo Excel con los resultados"""
        # Preparar datos para el DataFrame
        datos_excel = []
        
        for resultado in self.resultados:
            fila = {
                "Universidad": resultado["nombre"],
                "País": resultado["pais"],
                "URL": resultado["url"],
                "Tipo": resultado["tipo"],
                "Fecha Revisión": resultado["fecha_revision"],
                "Sitio Accesible": "Sí" if resultado["accesible"] else "No",
                
                # Ciencia Abierta
                "Ciencia Abierta - Encontrado": "Sí" if resultado["ciencia_abierta"]["encontrado"] else "No",
                "Ciencia Abierta - Score": resultado["ciencia_abierta"]["score"],
                "Ciencia Abierta - Términos": ", ".join([t["termino"] for t in resultado["ciencia_abierta"]["terminos"]]),
                
                # Comunicación Pública
                "Comunicación Pública - Encontrado": "Sí" if resultado["comunicacion_publica"]["encontrado"] else "No",
                "Comunicación Pública - Score": resultado["comunicacion_publica"]["score"],
                "Comunicación Pública - Términos": ", ".join([t["termino"] for t in resultado["comunicacion_publica"]["terminos"]]),
                
                # Diplomacia Científica
                "Diplomacia Científica - Encontrado": "Sí" if resultado["diplomacia_cientifica"]["encontrado"] else "No",
                "Diplomacia Científica - Score": resultado["diplomacia_cientifica"]["score"],
                "Diplomacia Científica - Términos": ", ".join([t["termino"] for t in resultado["diplomacia_cientifica"]["terminos"]]),
                
                # URLs Analizadas
                "URLs Analizadas": "; ".join(resultado["urls_analizadas"]),
                "Contenido Muestra": resultado["contenido_analizado"][:500]
            }
            datos_excel.append(fila)
        
        df = pd.DataFrame(datos_excel)
        
        # Crear archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Relevamiento CPC', index=False)
            
            # Hoja adicional con resumen
            resumen_data = self.generar_resumen()
            df_resumen = pd.DataFrame(resumen_data)
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
        
        output.seek(0)
        return output
    
    def generar_resumen(self):
        """Genera un resumen de los resultados"""
        resumen = []
        
        total_universidades = len(self.resultados)
        accesibles = sum(1 for r in self.resultados if r["accesible"])
        
        con_ciencia_abierta = sum(1 for r in self.resultados if r["ciencia_abierta"]["encontrado"])
        con_comunicacion = sum(1 for r in self.resultados if r["comunicacion_publica"]["encontrado"])
        con_diplomacia = sum(1 for r in self.resultados if r["diplomacia_cientifica"]["encontrado"])
        
        resumen.append({"Métrica": "Total Universidades Analizadas", "Valor": total_universidades})
        resumen.append({"Métrica": "Sitios Accesibles", "Valor": f"{accesibles} ({accesibles/total_universidades*100:.1f}%)"})
        resumen.append({"Métrica": "Con Ciencia Abierta", "Valor": f"{con_ciencia_abierta} ({con_ciencia_abierta/total_universidades*100:.1f}%)"})
        resumen.append({"Métrica": "Con Comunicación Pública", "Valor": f"{con_comunicacion} ({con_comunicacion/total_universidades*100:.1f}%)"})
        resumen.append({"Métrica": "Con Diplomacia Científica", "Valor": f"{con_diplomacia} ({con_diplomacia/total_universidades*100:.1f}%)"})
        
        return resumen

def main():
    """Función principal de la aplicación Streamlit"""
    
    # Título y descripción
    st.title("🎓 Relevador de Instituciones Educativas en CPC")
    st.markdown("""
    ### Relevamiento de Universidades en:
    - **Comunicación Pública de la Ciencia**
    - **Ciencia Abierta** 
    - **Diplomacia Científica**
    
    Esta aplicación analiza los sitios web de universidades seleccionadas para identificar 
    contenido relacionado con estos temas estratégicos.
    """)
    
    # Sidebar con configuraciones
    st.sidebar.title("⚙️ Configuración")
    
    # Inicializar el relevador
    if 'relevador' not in st.session_state:
        st.session_state.relevador = RelevadorUniversidades()
    
    relevador = st.session_state.relevador
    
    # Mostrar universidades que se van a analizar
    with st.sidebar.expander("🏛️ Universidades a Analizar"):
        df_unis = pd.DataFrame(relevador.universidades_base)
        st.dataframe(df_unis[['nombre', 'pais', 'tipo']], use_container_width=True)
    
    # Mostrar términos de búsqueda
    with st.sidebar.expander("🔍 Términos de Búsqueda"):
        st.write("**Ciencia Abierta:**")
        st.write(", ".join(relevador.terminos_ciencia_abierta[:5]) + "...")
        
        st.write("**Comunicación Pública:**")
        st.write(", ".join(relevador.terminos_comunicacion_publica[:5]) + "...")
        
        st.write("**Diplomacia Científica:**")
        st.write(", ".join(relevador.terminos_diplomacia_cientifica[:5]) + "...")
    
    # Botón para ejecutar el relevamiento
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🚀 Ejecutar Relevamiento", type="primary", use_container_width=True):
            st.session_state.ejecutando = True
    
    with col2:
        if st.button("🗑️ Limpiar Resultados", use_container_width=True):
            st.session_state.resultados = None
            st.session_state.ejecutando = False
            st.rerun()
    
    # Ejecutar relevamiento
    if st.session_state.get('ejecutando', False):
        st.markdown("---")
        st.subheader("🔄 Ejecutando Relevamiento...")
        
        # Barra de progreso
        progreso = st.progress(0)
        status_text = st.empty()
        
        def actualizar_progreso(actual, total, universidad):
            progreso.progress(actual / total)
            status_text.text(f"Analizando: {universidad} ({actual}/{total})")
        
        # Ejecutar el relevamiento
        with st.spinner("Procesando universidades..."):
            resultados = relevador.ejecutar_relevamiento(actualizar_progreso)
            st.session_state.resultados = resultados
            st.session_state.ejecutando = False
        
        st.success("✅ Relevamiento completado!")
        st.rerun()
    
    # Mostrar resultados si existen
    if st.session_state.get('resultados'):
        st.markdown("---")
        st.subheader("📊 Resultados del Relevamiento")
        
        resultados = st.session_state.resultados
        
        # Resumen general
        col1, col2, col3, col4 = st.columns(4)
        
        total = len(resultados)
        accesibles = sum(1 for r in resultados if r["accesible"])
        con_ca = sum(1 for r in resultados if r["ciencia_abierta"]["encontrado"])
        con_cp = sum(1 for r in resultados if r["comunicacion_publica"]["encontrado"])
        con_dc = sum(1 for r in resultados if r["diplomacia_cientifica"]["encontrado"])
        
        with col1:
            st.metric("Total Analizadas", total)
        with col2:
            st.metric("Sitios Accesibles", f"{accesibles}/{total}")
        with col3:
            st.metric("Con Ciencia Abierta", con_ca)
        with col4:
            st.metric("Con Com. Pública", con_cp)
        
        # Tabla de resultados
        st.subheader("📋 Detalle de Resultados")
        
        # Preparar datos para mostrar
        datos_tabla = []
        for r in resultados:
            datos_tabla.append({
                "Universidad": r["nombre"],
                "País": r["pais"],
                "Accesible": "✅" if r["accesible"] else "❌",
                "Ciencia Abierta": "✅" if r["ciencia_abierta"]["encontrado"] else "❌",
                "Com. Pública": "✅" if r["comunicacion_publica"]["encontrado"] else "❌",
                "Diplomacia Cient.": "✅" if r["diplomacia_cientifica"]["encontrado"] else "❌",
                "Score CA": r["ciencia_abierta"]["score"],
                "Score CP": r["comunicacion_publica"]["score"],
                "Score DC": r["diplomacia_cientifica"]["score"]
            })
        
        df_resultados = pd.DataFrame(datos_tabla)
        st.dataframe(df_resultados, use_container_width=True)
        
        # Detalles expandibles por universidad
        st.subheader("🔍 Detalle por Universidad")
        
        for resultado in resultados:
            with st.expander(f"🏛️ {resultado['nombre']} ({resultado['pais']})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**URL:** {resultado['url']}")
                    st.write(f"**Accesible:** {'Sí' if resultado['accesible'] else 'No'}")
                    st.write(f"**Tipo:** {resultado['tipo']}")
                
                with col2:
                    st.write(f"**Fecha Análisis:** {resultado['fecha_revision']}")
                    st.write(f"**URLs Analizadas:** {len(resultado['urls_analizadas'])}")
                
                if resultado['accesible']:
                    # Mostrar términos encontrados
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Ciencia Abierta:**")
                        if resultado['ciencia_abierta']['terminos']:
                            for termino in resultado['ciencia_abierta']['terminos']:
                                st.write(f"- {termino['termino']}")
                        else:
                            st.write("No encontrado")
                    
                    with col2:
                        st.write("**Comunicación Pública:**")
                        if resultado['comunicacion_publica']['terminos']:
                            for termino in resultado['comunicacion_publica']['terminos']:
                                st.write(f"- {termino['termino']}")
                        else:
                            st.write("No encontrado")
                    
                    with col3:
                        st.write("**Diplomacia Científica:**")
                        if resultado['diplomacia_cientifica']['terminos']:
                            for termino in resultado['diplomacia_cientifica']['terminos']:
                                st.write(f"- {termino['termino']}")
                        else:
                            st.write("No encontrado")
        
        # Generar y descargar Excel
        st.markdown("---")
        st.subheader("📥 Descargar Resultados")
        
        if st.button("📊 Generar Excel", use_container_width=True):
            with st.spinner("Generando archivo Excel..."):
                excel_file = relevador.generar_excel()
                
                st.download_button(
                    label="⬇️ Descargar Relevamiento.xlsx",
                    data=excel_file,
                    file_name=f"relevamiento_cpc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

if __name__ == "__main__":
    main()