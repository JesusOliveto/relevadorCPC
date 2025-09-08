"""
Relevador de Instituciones Educativas en CPC (Comunicación Pública de la Ciencia)
Aplicación para BUSCAR y RELEVAR universidades que trabajan en:
- Comunicación Pública de la Ciencia
- Ciencia Abierta
- Diplomacia Científica

Busca universidades a través de Google y analiza sus contenidos.
Incluye soporte multiidioma (español, inglés, catalán, portugués, francés, etc.)

Autor: Sistema de Relevamiento CPC
Fecha: Septiembre 2025
"""

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse, quote
import io
from datetime import datetime
import json
import logging
import random

# Configuración de la página
st.set_page_config(
    page_title="Relevador CPC - Buscador de Universidades",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BuscadorUniversidades:
    def __init__(self):
        # Universidad de control (Jaume I)
        self.universidad_control = {
            "nombre": "Universitat Jaume I",
            "url": "https://www.uji.es",
            "pais": "España",
            "idioma": "Catalán/Español"
        }
        
        # Términos de búsqueda multiidioma para encontrar universidades
        self.terminos_busqueda_universidades = {
            "ciencia_abierta": [
                # Español
                "universidad ciencia abierta", "universitat ciència oberta", "universidad datos abiertos",
                "universidad acceso abierto", "universidad investigación abierta",
                # Inglés
                "university open science", "university open data", "university open access",
                "university open research", "university fair data",
                # Catalán
                "universitat ciència oberta", "universitat dades obertes", "universitat accés obert",
                # Portugués
                "universidade ciência aberta", "universidade dados abertos", "universidade acesso aberto",
                # Francés
                "université science ouverte", "université données ouvertes", "université accès libre",
                # Italiano
                "università scienza aperta", "università dati aperti", "università accesso aperto"
            ],
            "comunicacion_publica": [
                # Español
                "universidad comunicación científica", "universidad divulgación científica",
                "universidad comunicación pública ciencia", "universidad outreach científico",
                # Inglés
                "university science communication", "university public engagement science",
                "university science outreach", "university public understanding science",
                # Catalán
                "universitat comunicació científica", "universitat divulgació científica",
                "universitat comunicació pública ciència",
                # Portugués
                "universidade comunicação científica", "universidade divulgação científica",
                "universidade comunicação pública ciência",
                # Francés
                "université communication scientifique", "université vulgarisation scientifique",
                "université communication publique science",
                # Italiano
                "università comunicazione scientifica", "università divulgazione scientifica"
            ],
            "diplomacia_cientifica": [
                # Español
                "universidad diplomacia científica", "universidad cooperación internacional científica",
                "universidad política científica", "universidad ciencia global",
                # Inglés
                "university science diplomacy", "university scientific diplomacy",
                "university international scientific cooperation", "university global science",
                # Catalán
                "universitat diplomàcia científica", "universitat cooperació internacional científica",
                # Portugués
                "universidade diplomacia científica", "universidade cooperação internacional científica",
                # Francés
                "université diplomatie scientifique", "université coopération internationale scientifique",
                # Italiano
                "università diplomazia scientifica", "università cooperazione internazionale scientifica"
            ]
        }
        
        # Términos para validar contenido en sitios web (multiidioma)
        self.terminos_validacion = {
            "ciencia_abierta": [
                # Español
                "ciencia abierta", "datos abiertos", "acceso abierto", "investigación abierta",
                "repositorio institucional", "datos fair", "investigación reproducible",
                # Inglés
                "open science", "open data", "open access", "open research", "fair data",
                "institutional repository", "reproducible research", "transparent research",
                # Catalán
                "ciència oberta", "dades obertes", "accés obert", "investigació oberta",
                "repositori institucional", "investigació reproductible",
                # Portugués
                "ciência aberta", "dados abertos", "acesso aberto", "pesquisa aberta",
                "repositório institucional", "pesquisa reproduzível",
                # Francés
                "science ouverte", "données ouvertes", "accès libre", "recherche ouverte",
                "dépôt institutionnel", "recherche reproductible",
                # Italiano
                "scienza aperta", "dati aperti", "accesso aperto", "ricerca aperta",
                "repository istituzionale", "ricerca riproducibile"
            ],
            "comunicacion_publica": [
                # Español
                "comunicación científica", "divulgación científica", "comunicación pública de la ciencia",
                "cultura científica", "alfabetización científica", "museo de la ciencia",
                # Inglés
                "science communication", "public engagement", "science outreach", "science literacy",
                "public understanding of science", "science museum", "science culture",
                # Catalán
                "comunicació científica", "divulgació científica", "comunicació pública de la ciència",
                "cultura científica", "museu de la ciència",
                # Portugués
                "comunicação científica", "divulgação científica", "comunicação pública da ciência",
                "cultura científica", "museu de ciência",
                # Francés
                "communication scientifique", "vulgarisation scientifique", "culture scientifique",
                "musée de science", "médiation scientifique",
                # Italiano
                "comunicazione scientifica", "divulgazione scientifica", "cultura scientifica",
                "museo della scienza"
            ],
            "diplomacia_cientifica": [
                # Español
                "diplomacia científica", "cooperación internacional científica", "política científica",
                "ciencia global", "relaciones internacionales científicas",
                # Inglés
                "science diplomacy", "scientific diplomacy", "international scientific cooperation",
                "global science", "science policy", "international science relations",
                # Catalán
                "diplomàcia científica", "cooperació internacional científica", "política científica",
                # Portugués
                "diplomacia científica", "cooperação internacional científica", "política científica",
                # Francés
                "diplomatie scientifique", "coopération internationale scientifique", "politique scientifique",
                # Italiano
                "diplomazia scientifica", "cooperazione internazionale scientifica", "politica scientifica"
            ]
        }
        
        # Headers para requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.universidades_encontradas = []
        self.resultados_analisis = []
    
    
    def buscar_universidades_google(self, terminos_categoria, categoria, max_resultados=20):
        """Busca universidades en Google usando los términos de la categoría"""
        universidades_encontradas = []
        
        for termino in terminos_categoria[:5]:  # Limitar términos para no hacer demasiadas búsquedas
            try:
                # Construir URL de búsqueda de Google
                query = quote(termino)
                url_busqueda = f"https://www.google.com/search?q={query}&num=10"
                
                response = requests.get(url_busqueda, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Buscar enlaces en los resultados
                    for enlace in soup.find_all('a'):
                        href = enlace.get('href', '')
                        if '/url?q=' in href:
                            # Extraer URL real
                            url_real = href.split('/url?q=')[1].split('&')[0]
                            
                            # Verificar si es una universidad
                            if self.es_universidad(url_real, enlace.get_text()):
                                universidad_info = self.extraer_info_universidad(url_real, enlace.get_text())
                                if universidad_info and universidad_info not in universidades_encontradas:
                                    universidad_info['categoria_encontrada'] = categoria
                                    universidad_info['termino_busqueda'] = termino
                                    universidades_encontradas.append(universidad_info)
                                    
                                    if len(universidades_encontradas) >= max_resultados:
                                        break
                
                # Pausa entre búsquedas para no ser bloqueado
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                logger.error(f"Error en búsqueda de '{termino}': {str(e)}")
                continue
        
        return universidades_encontradas
    
    def es_universidad(self, url, texto):
        """Determina si una URL/texto corresponde a una universidad"""
        if not url or not isinstance(url, str):
            return False
        
        # Patrones de URLs universitarias
        patrones_universidad = [
            r'\.edu($|/)', r'\.ac\.', r'\.univ\.', r'university', r'universidad', r'universitat',
            r'universidade', r'université', r'università', r'college', r'instituto'
        ]
        
        # Verificar URL
        url_lower = url.lower()
        for patron in patrones_universidad:
            if re.search(patron, url_lower):
                return True
        
        # Verificar texto
        if texto:
            texto_lower = texto.lower()
            palabras_universidad = [
                'university', 'universidad', 'universitat', 'universidade', 
                'université', 'università', 'college', 'instituto', 'school'
            ]
            
            for palabra in palabras_universidad:
                if palabra in texto_lower:
                    return True
        
        return False
    
    def extraer_info_universidad(self, url, texto):
        """Extrae información básica de la universidad"""
        try:
            # Limpiar URL
            if url.startswith('http'):
                domain = urlparse(url).netloc
            else:
                return None
            
            # Extraer nombre de la universidad del texto o dominio
            nombre = self.limpiar_nombre_universidad(texto) or domain
            
            # Intentar determinar país por dominio
            pais = self.determinar_pais_por_dominio(domain)
            
            return {
                "nombre": nombre,
                "url": url,
                "dominio": domain,
                "pais": pais,
                "texto_original": texto[:200]
            }
            
        except Exception as e:
            logger.error(f"Error extrayendo info de universidad: {str(e)}")
            return None
    
    def limpiar_nombre_universidad(self, texto):
        """Limpia el nombre de la universidad del texto de búsqueda"""
        if not texto:
            return None
        
        # Remover texto innecesario común en resultados de Google
        texto_limpio = re.sub(r'\s*-\s*Google Search.*', '', texto, flags=re.IGNORECASE)
        texto_limpio = re.sub(r'\s*\|\s*.*', '', texto_limpio)
        texto_limpio = re.sub(r'\s*›.*', '', texto_limpio)
        
        # Mantener solo la primera parte si es muy largo
        if len(texto_limpio) > 100:
            texto_limpio = texto_limpio[:100] + "..."
        
        return texto_limpio.strip()
    
    def determinar_pais_por_dominio(self, dominio):
        """Determina el país basado en el dominio"""
        if not dominio:
            return "Desconocido"
        
        # Mapeo de dominios de países
        dominios_pais = {
            '.es': 'España', '.edu': 'Estados Unidos', '.uk': 'Reino Unido',
            '.ca': 'Canadá', '.au': 'Australia', '.de': 'Alemania',
            '.fr': 'Francia', '.it': 'Italia', '.br': 'Brasil',
            '.ar': 'Argentina', '.mx': 'México', '.cl': 'Chile',
            '.co': 'Colombia', '.pe': 'Perú', '.jp': 'Japón',
            '.cn': 'China', '.in': 'India', '.nl': 'Países Bajos',
            '.ch': 'Suiza', '.se': 'Suecia', '.no': 'Noruega'
        }
        
        for ext, pais in dominios_pais.items():
            if dominio.endswith(ext):
                return pais
        
        return "Internacional"
    
    def analizar_universidad(self, universidad):
        """Analiza una universidad específica buscando contenido relevante"""
        resultado = {
            "nombre": universidad["nombre"],
            "url": universidad["url"],
            "pais": universidad["pais"],
            "categoria_encontrada": universidad.get("categoria_encontrada", "Búsqueda"),
            "termino_busqueda": universidad.get("termino_busqueda", ""),
            "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "accesible": False,
            "idioma_detectado": "",
            "ciencia_abierta": {"encontrado": False, "terminos": [], "score": 0},
            "comunicacion_publica": {"encontrado": False, "terminos": [], "score": 0},
            "diplomacia_cientifica": {"encontrado": False, "terminos": [], "score": 0},
            "contenido_muestra": "",
            "urls_analizadas": []
        }
        
        try:
            # Obtener contenido principal
            response = requests.get(universidad["url"], headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                resultado["accesible"] = True
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Detectar idioma
                resultado["idioma_detectado"] = self.detectar_idioma(soup)
                
                # Extraer todo el texto
                texto_completo = soup.get_text()
                resultado["contenido_muestra"] = texto_completo[:500]
                resultado["urls_analizadas"].append(universidad["url"])
                
                # Buscar páginas adicionales relevantes
                urls_relevantes = self.encontrar_paginas_relevantes(soup, universidad["url"])
                
                # Analizar páginas adicionales (máximo 3)
                contenido_adicional = ""
                for url_adicional in urls_relevantes[:3]:
                    try:
                        resp_adicional = requests.get(url_adicional, headers=self.headers, timeout=10)
                        if resp_adicional.status_code == 200:
                            soup_adicional = BeautifulSoup(resp_adicional.text, 'html.parser')
                            contenido_adicional += " " + soup_adicional.get_text()
                            resultado["urls_analizadas"].append(url_adicional)
                        time.sleep(1)
                    except:
                        continue
                
                # Combinar todo el contenido
                todo_contenido = texto_completo + " " + contenido_adicional
                
                # Analizar contenido por categorías
                resultado["ciencia_abierta"]["terminos"] = self.buscar_terminos_en_texto(
                    todo_contenido, self.terminos_validacion["ciencia_abierta"]
                )
                resultado["comunicacion_publica"]["terminos"] = self.buscar_terminos_en_texto(
                    todo_contenido, self.terminos_validacion["comunicacion_publica"]
                )
                resultado["diplomacia_cientifica"]["terminos"] = self.buscar_terminos_en_texto(
                    todo_contenido, self.terminos_validacion["diplomacia_cientifica"]
                )
                
                # Calcular scores
                resultado["ciencia_abierta"]["score"] = len(resultado["ciencia_abierta"]["terminos"])
                resultado["ciencia_abierta"]["encontrado"] = resultado["ciencia_abierta"]["score"] > 0
                
                resultado["comunicacion_publica"]["score"] = len(resultado["comunicacion_publica"]["terminos"])
                resultado["comunicacion_publica"]["encontrado"] = resultado["comunicacion_publica"]["score"] > 0
                
                resultado["diplomacia_cientifica"]["score"] = len(resultado["diplomacia_cientifica"]["terminos"])
                resultado["diplomacia_cientifica"]["encontrado"] = resultado["diplomacia_cientifica"]["score"] > 0
                
        except Exception as e:
            logger.error(f"Error analizando {universidad['nombre']}: {str(e)}")
        
        return resultado
    
    def detectar_idioma(self, soup):
        """Detecta el idioma principal del contenido"""
        # Buscar en meta tags
        lang_tag = soup.find('html', attrs={'lang': True})
        if lang_tag:
            return lang_tag.get('lang', '')
        
        # Detectar por palabras comunes
        texto = soup.get_text().lower()
        
        idiomas_palabras = {
            'español': ['universidad', 'investigación', 'ciencia', 'estudiantes', 'facultad'],
            'catalán': ['universitat', 'investigació', 'ciència', 'estudiants', 'facultat'],
            'inglés': ['university', 'research', 'science', 'students', 'faculty'],
            'portugués': ['universidade', 'pesquisa', 'ciência', 'estudantes', 'faculdade'],
            'francés': ['université', 'recherche', 'science', 'étudiants', 'faculté'],
            'italiano': ['università', 'ricerca', 'scienza', 'studenti', 'facoltà']
        }
        
        scores = {}
        for idioma, palabras in idiomas_palabras.items():
            score = sum(1 for palabra in palabras if palabra in texto)
            scores[idioma] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "Desconocido"
    
    def encontrar_paginas_relevantes(self, soup, base_url):
        """Encuentra páginas relevantes para el análisis"""
        urls_relevantes = []
        
        # Palabras clave para páginas relevantes
        palabras_clave = [
            'research', 'investigación', 'investigació', 'pesquisa', 'recherche', 'ricerca',
            'science', 'ciencia', 'ciència', 'ciência', 'scienza',
            'open', 'abierto', 'obert', 'aberto', 'ouvert', 'aperto',
            'communication', 'comunicación', 'comunicació', 'comunicação', 'comunicazione',
            'outreach', 'divulgación', 'divulgació', 'divulgação',
            'policy', 'política', 'política', 'politique', 'politica'
        ]
        
        # Buscar enlaces relevantes
        for enlace in soup.find_all('a', href=True):
            href = enlace['href'].lower()
            texto = enlace.get_text().lower()
            
            # Verificar si contiene palabras clave
            if any(palabra in href or palabra in texto for palabra in palabras_clave):
                url_completa = urljoin(base_url, enlace['href'])
                if (url_completa not in urls_relevantes and 
                    len(urls_relevantes) < 15 and 
                    urlparse(url_completa).netloc == urlparse(base_url).netloc):
                    urls_relevantes.append(url_completa)
        
        return urls_relevantes
    
    def buscar_terminos_en_texto(self, texto, terminos):
        """Busca términos específicos en el texto y devuelve contexto"""
        texto_lower = texto.lower()
        terminos_encontrados = []
        
        for termino in terminos:
            if termino.lower() in texto_lower:
                # Encontrar contexto del término
                pattern = rf'.{{0,100}}{re.escape(termino.lower())}.{{0,100}}'
                matches = re.findall(pattern, texto_lower, re.IGNORECASE | re.DOTALL)
                
                if matches:
                    contexto = matches[0].replace('\n', ' ').replace('\t', ' ')
                    contexto = ' '.join(contexto.split())  # Limpiar espacios múltiples
                    
                    terminos_encontrados.append({
                        "termino": termino,
                        "contexto": contexto[:300] + "..." if len(contexto) > 300 else contexto
                    })
        
        return terminos_encontrados
    
    def analizar_universidad_control(self):
        """Analiza la universidad de control (Jaume I)"""
        return self.analizar_universidad(self.universidad_control)
    
    def ejecutar_busqueda_completa(self, progreso_callback=None):
        """Ejecuta la búsqueda completa por categorías"""
        self.universidades_encontradas = []
        self.resultados_analisis = []
        
        categorias = ['ciencia_abierta', 'comunicacion_publica', 'diplomacia_cientifica']
        total_pasos = len(categorias) + 1  # +1 para análisis
        
        # Primero analizar universidad de control
        if progreso_callback:
            progreso_callback(0, total_pasos, "Analizando universidad de control (Jaume I)")
        
        resultado_control = self.analizar_universidad_control()
        self.resultados_analisis.append(resultado_control)
        
        # Buscar universidades por cada categoría
        for i, categoria in enumerate(categorias):
            if progreso_callback:
                progreso_callback(i + 1, total_pasos, f"Buscando universidades en {categoria.replace('_', ' ')}")
            
            terminos = self.terminos_busqueda_universidades[categoria]
            universidades = self.buscar_universidades_google(terminos, categoria, max_resultados=10)
            
            for universidad in universidades:
                # Evitar duplicados
                if not any(u['url'] == universidad['url'] for u in self.universidades_encontradas):
                    self.universidades_encontradas.append(universidad)
        
        # Analizar universidades encontradas
        if progreso_callback:
            progreso_callback(len(categorias), total_pasos, "Analizando universidades encontradas")
        
        for universidad in self.universidades_encontradas:
            resultado = self.analizar_universidad(universidad)
            self.resultados_analisis.append(resultado)
            time.sleep(1)  # Pausa entre análisis
        
        return self.resultados_analisis
    
    def generar_excel(self):
        """Genera archivo Excel con los resultados"""
        if not self.resultados_analisis:
            return None
        
        # Preparar datos para DataFrame
        datos_excel = []
        
        for resultado in self.resultados_analisis:
            fila = {
                "Universidad": resultado["nombre"],
                "País": resultado["pais"],
                "URL": resultado["url"],
                "Categoría Encontrada": resultado.get("categoria_encontrada", "Control"),
                "Término de Búsqueda": resultado.get("termino_busqueda", ""),
                "Fecha Análisis": resultado["fecha_analisis"],
                "Sitio Accesible": "Sí" if resultado["accesible"] else "No",
                "Idioma Detectado": resultado.get("idioma_detectado", ""),
                
                # Ciencia Abierta
                "Ciencia Abierta": "Sí" if resultado["ciencia_abierta"]["encontrado"] else "No",
                "CA - Score": resultado["ciencia_abierta"]["score"],
                "CA - Términos": ", ".join([t["termino"] for t in resultado["ciencia_abierta"]["terminos"]]),
                
                # Comunicación Pública
                "Comunicación Pública": "Sí" if resultado["comunicacion_publica"]["encontrado"] else "No",
                "CP - Score": resultado["comunicacion_publica"]["score"],
                "CP - Términos": ", ".join([t["termino"] for t in resultado["comunicacion_publica"]["terminos"]]),
                
                # Diplomacia Científica
                "Diplomacia Científica": "Sí" if resultado["diplomacia_cientifica"]["encontrado"] else "No",
                "DC - Score": resultado["diplomacia_cientifica"]["score"],
                "DC - Términos": ", ".join([t["termino"] for t in resultado["diplomacia_cientifica"]["terminos"]]),
                
                "URLs Analizadas": "; ".join(resultado["urls_analizadas"]),
                "Contenido Muestra": resultado["contenido_muestra"]
            }
            datos_excel.append(fila)
        
        df = pd.DataFrame(datos_excel)
        
        # Crear archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Universidades Encontradas', index=False)
            
            # Hoja de resumen
            resumen = self.generar_resumen_busqueda()
            df_resumen = pd.DataFrame(resumen)
            df_resumen.to_excel(writer, sheet_name='Resumen Búsqueda', index=False)
        
        output.seek(0)
        return output
    
    def generar_resumen_busqueda(self):
        """Genera resumen de la búsqueda realizada"""
        if not self.resultados_analisis:
            return []
        
        total = len(self.resultados_analisis)
        accesibles = sum(1 for r in self.resultados_analisis if r["accesible"])
        
        con_ca = sum(1 for r in self.resultados_analisis if r["ciencia_abierta"]["encontrado"])
        con_cp = sum(1 for r in self.resultados_analisis if r["comunicacion_publica"]["encontrado"])
        con_dc = sum(1 for r in self.resultados_analisis if r["diplomacia_cientifica"]["encontrado"])
        
        # Análisis por países
        paises = {}
        for r in self.resultados_analisis:
            pais = r["pais"]
            if pais not in paises:
                paises[pais] = 0
            paises[pais] += 1
        
        # Análisis por idiomas
        idiomas = {}
        for r in self.resultados_analisis:
            idioma = r.get("idioma_detectado", "Desconocido")
            if idioma not in idiomas:
                idiomas[idioma] = 0
            idiomas[idioma] += 1
        
        resumen = [
            {"Métrica": "Total Universidades Encontradas", "Valor": total},
            {"Métrica": "Sitios Web Accesibles", "Valor": f"{accesibles}/{total} ({accesibles/total*100:.1f}%)"},
            {"Métrica": "Con Ciencia Abierta", "Valor": f"{con_ca} ({con_ca/total*100:.1f}%)"},
            {"Métrica": "Con Comunicación Pública", "Valor": f"{con_cp} ({con_cp/total*100:.1f}%)"},
            {"Métrica": "Con Diplomacia Científica", "Valor": f"{con_dc} ({con_dc/total*100:.1f}%)"},
            {"Métrica": "Países más representados", "Valor": ", ".join([f"{k}: {v}" for k, v in sorted(paises.items(), key=lambda x: x[1], reverse=True)[:5]])},
            {"Métrica": "Idiomas detectados", "Valor": ", ".join([f"{k}: {v}" for k, v in sorted(idiomas.items(), key=lambda x: x[1], reverse=True)])},
        ]
        
        return resumen

def main():
    """Función principal de la aplicación Streamlit"""
    
    # Título y descripción
    st.title("🔍 Buscador de Universidades en CPC")
    st.markdown("""
    ### Relevamiento Automático de Universidades en:
    - **Comunicación Pública de la Ciencia**
    - **Ciencia Abierta** 
    - **Diplomacia Científica**
    
    Esta aplicación **BUSCA** universidades en Google que trabajen en estos temas y analiza 
    su contenido en múltiples idiomas (español, inglés, catalán, portugués, francés, italiano).
    
    #### 🎯 Población de Control: Universitat Jaume I (Catalán/Español)
    """)
    
    # Sidebar con información
    st.sidebar.title("⚙️ Configuración de Búsqueda")
    
    # Inicializar el buscador
    if 'buscador' not in st.session_state:
        st.session_state.buscador = BuscadorUniversidades()
    
    buscador = st.session_state.buscador
    
    # Mostrar términos de búsqueda por categoría
    with st.sidebar.expander("🔍 Términos de Búsqueda por Categoría"):
        st.write("**Ciencia Abierta (ejemplos):**")
        st.write(", ".join(buscador.terminos_busqueda_universidades["ciencia_abierta"][:3]) + "...")
        
        st.write("**Comunicación Pública (ejemplos):**")
        st.write(", ".join(buscador.terminos_busqueda_universidades["comunicacion_publica"][:3]) + "...")
        
        st.write("**Diplomacia Científica (ejemplos):**")
        st.write(", ".join(buscador.terminos_busqueda_universidades["diplomacia_cientifica"][:3]) + "...")
    
    # Mostrar idiomas soportados
    with st.sidebar.expander("🌍 Idiomas Soportados"):
        st.write("• Español")
        st.write("• Inglés") 
        st.write("• Catalán")
        st.write("• Portugués")
        st.write("• Francés")
        st.write("• Italiano")
    
    # Universidad de control
    with st.sidebar.expander("🏛️ Universidad de Control"):
        control = buscador.universidad_control
        st.write(f"**{control['nombre']}**")
        st.write(f"País: {control['pais']}")
        st.write(f"Idioma: {control['idioma']}")
        st.write(f"URL: {control['url']}")
    
    # Botones principales
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🚀 Ejecutar Búsqueda y Análisis", type="primary", use_container_width=True):
            st.session_state.ejecutando_busqueda = True
    
    with col2:
        if st.button("🗑️ Limpiar", use_container_width=True):
            st.session_state.resultados_busqueda = None
            st.session_state.ejecutando_busqueda = False
            st.rerun()
    
    # Advertencias importantes
    st.warning("""
    ⚠️ **Importante:**
    - Esta herramienta realiza búsquedas reales en Google
    - El proceso puede tomar 10-15 minutos
    - Google puede limitar las búsquedas automáticas
    - Se recomienda usar con moderación
    """)
    
    # Ejecutar búsqueda
    if st.session_state.get('ejecutando_busqueda', False):
        st.markdown("---")
        st.subheader("🔄 Ejecutando Búsqueda y Análisis...")
        
        # Información del proceso
        st.info("""
        **Proceso en ejecución:**
        1. Análisis de universidad control (Jaume I)
        2. Búsqueda en Google por cada categoría
        3. Filtrado de universidades encontradas
        4. Análisis detallado de cada universidad
        5. Generación de resultados
        """)
        
        # Barra de progreso
        progreso = st.progress(0)
        status_text = st.empty()
        
        def actualizar_progreso(actual, total, descripcion):
            if total > 0:
                progreso.progress(actual / total)
            status_text.text(f"{descripcion} ({actual}/{total})")
        
        # Ejecutar búsqueda completa
        try:
            with st.spinner("Buscando y analizando universidades..."):
                resultados = buscador.ejecutar_busqueda_completa(actualizar_progreso)
                st.session_state.resultados_busqueda = resultados
                st.session_state.ejecutando_busqueda = False
            
            st.success("✅ Búsqueda y análisis completados!")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error durante la búsqueda: {str(e)}")
            st.session_state.ejecutando_busqueda = False
    
    # Mostrar resultados si existen
    if st.session_state.get('resultados_busqueda'):
        st.markdown("---")
        st.subheader("📊 Resultados de la Búsqueda")
        
        resultados = st.session_state.resultados_busqueda
        
        # Resumen ejecutivo
        total = len(resultados)
        accesibles = sum(1 for r in resultados if r["accesible"])
        con_ca = sum(1 for r in resultados if r["ciencia_abierta"]["encontrado"])
        con_cp = sum(1 for r in resultados if r["comunicacion_publica"]["encontrado"])
        con_dc = sum(1 for r in resultados if r["diplomacia_cientifica"]["encontrado"])
        
        # Métricas principales
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("🏛️ Total Encontradas", total)
        with col2:
            st.metric("🌐 Sitios Accesibles", f"{accesibles}/{total}")
        with col3:
            st.metric("📊 Ciencia Abierta", con_ca)
        with col4:
            st.metric("📢 Com. Pública", con_cp)
        with col5:
            st.metric("🤝 Diplomacia Cient.", con_dc)
        
        # Análisis por países
        paises = {}
        for r in resultados:
            pais = r["pais"]
            if pais not in paises:
                paises[pais] = 0
            paises[pais] += 1
        
        if len(paises) > 1:
            st.subheader("🌍 Distribución por Países")
            df_paises = pd.DataFrame(list(paises.items()), columns=['País', 'Cantidad'])
            df_paises = df_paises.sort_values('Cantidad', ascending=False)
            st.bar_chart(df_paises.set_index('País'))
        
        # Tabla resumen de resultados
        st.subheader("📋 Resumen de Universidades Encontradas")
        
        datos_tabla = []
        for r in resultados:
            datos_tabla.append({
                "Universidad": r["nombre"][:50] + "..." if len(r["nombre"]) > 50 else r["nombre"],
                "País": r["pais"],
                "Categoría": r.get("categoria_encontrada", "Control"),
                "Accesible": "✅" if r["accesible"] else "❌",
                "Idioma": r.get("idioma_detectado", "N/A"),
                "C. Abierta": "✅" if r["ciencia_abierta"]["encontrado"] else "❌",
                "C. Pública": "✅" if r["comunicacion_publica"]["encontrado"] else "❌",
                "Diplomacia": "✅" if r["diplomacia_cientifica"]["encontrado"] else "❌",
                "Score Total": (r["ciencia_abierta"]["score"] + 
                              r["comunicacion_publica"]["score"] + 
                              r["diplomacia_cientifica"]["score"])
            })
        
        df_resultados = pd.DataFrame(datos_tabla)
        st.dataframe(df_resultados, use_container_width=True)
        
        # Análisis detallado expandible
        st.subheader("🔍 Análisis Detallado por Universidad")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            filtro_pais = st.selectbox("Filtrar por país:", ["Todos"] + sorted(list(paises.keys())))
        with col2:
            filtro_categoria = st.selectbox("Filtrar por categoría:", 
                                          ["Todas", "Control", "ciencia_abierta", "comunicacion_publica", "diplomacia_cientifica"])
        with col3:
            solo_con_contenido = st.checkbox("Solo universidades con contenido relevante")
        
        # Aplicar filtros
        resultados_filtrados = resultados
        
        if filtro_pais != "Todos":
            resultados_filtrados = [r for r in resultados_filtrados if r["pais"] == filtro_pais]
        
        if filtro_categoria != "Todas":
            resultados_filtrados = [r for r in resultados_filtrados if r.get("categoria_encontrada", "Control") == filtro_categoria]
        
        if solo_con_contenido:
            resultados_filtrados = [r for r in resultados_filtrados if 
                                  (r["ciencia_abierta"]["encontrado"] or 
                                   r["comunicacion_publica"]["encontrado"] or 
                                   r["diplomacia_cientifica"]["encontrado"])]
        
        # Mostrar resultados filtrados
        for resultado in resultados_filtrados:
            tipo_emoji = "🎯" if resultado.get("categoria_encontrada") == "Control" else "🔍"
            
            with st.expander(f"{tipo_emoji} {resultado['nombre']} ({resultado['pais']})"):
                
                # Información general
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**URL:** {resultado['url']}")
                    st.write(f"**País:** {resultado['pais']}")
                    st.write(f"**Accesible:** {'Sí' if resultado['accesible'] else 'No'}")
                    st.write(f"**Categoría encontrada:** {resultado.get('categoria_encontrada', 'Control')}")
                
                with col2:
                    st.write(f"**Fecha análisis:** {resultado['fecha_analisis']}")
                    st.write(f"**Idioma detectado:** {resultado.get('idioma_detectado', 'N/A')}")
                    st.write(f"**URLs analizadas:** {len(resultado['urls_analizadas'])}")
                    if resultado.get('termino_busqueda'):
                        st.write(f"**Término de búsqueda:** {resultado['termino_busqueda']}")
                
                if resultado['accesible']:
                    # Análisis por categorías
                    st.write("---")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**📊 Ciencia Abierta:**")
                        if resultado['ciencia_abierta']['terminos']:
                            st.write(f"Score: {resultado['ciencia_abierta']['score']}")
                            for termino in resultado['ciencia_abierta']['terminos'][:3]:
                                st.write(f"• {termino['termino']}")
                        else:
                            st.write("❌ No encontrado")
                    
                    with col2:
                        st.write("**📢 Comunicación Pública:**")
                        if resultado['comunicacion_publica']['terminos']:
                            st.write(f"Score: {resultado['comunicacion_publica']['score']}")
                            for termino in resultado['comunicacion_publica']['terminos'][:3]:
                                st.write(f"• {termino['termino']}")
                        else:
                            st.write("❌ No encontrado")
                    
                    with col3:
                        st.write("**🤝 Diplomacia Científica:**")
                        if resultado['diplomacia_cientifica']['terminos']:
                            st.write(f"Score: {resultado['diplomacia_cientifica']['score']}")
                            for termino in resultado['diplomacia_cientifica']['terminos'][:3]:
                                st.write(f"• {termino['termino']}")
                        else:
                            st.write("❌ No encontrado")
                    
                    # Muestra de contenido
                    if resultado['contenido_muestra']:
                        st.write("**📄 Muestra del contenido:**")
                        st.text_area("", resultado['contenido_muestra'], height=100, key=f"contenido_{resultado['url']}")
                else:
                    st.error("❌ Sitio web no accesible durante el análisis")
        
        # Generar y descargar Excel
        st.markdown("---")
        st.subheader("📥 Exportar Resultados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Generar Excel Completo", use_container_width=True):
                with st.spinner("Generando archivo Excel..."):
                    excel_file = buscador.generar_excel()
                    
                    if excel_file:
                        st.download_button(
                            label="⬇️ Descargar Relevamiento_CPC.xlsx",
                            data=excel_file,
                            file_name=f"relevamiento_cpc_busqueda_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error("Error generando el archivo Excel")
        
        with col2:
            # Botón para nueva búsqueda
            if st.button("🔄 Nueva Búsqueda", use_container_width=True):
                st.session_state.resultados_busqueda = None
                st.session_state.buscador = BuscadorUniversidades()
                st.rerun()

if __name__ == "__main__":
    main()