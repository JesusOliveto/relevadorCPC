# -*- coding: utf-8 -*-
"""
Relevador de Instituciones Educativas en CPC (Comunicación Pública de la Ciencia)
- Busca universidades que publiquen sobre: Ciencia Abierta, Comunicación Pública de la Ciencia, Diplomacia Científica
- Analiza páginas, extrae señales (términos) y exporta a Excel.
- Funciona en Streamlit Cloud sin claves (DuckDuckGo HTML). Opcional: Bing Web Search API si BING_SUBSCRIPTION_KEY está definido.

Autor: Sistema de Relevamiento CPC
Fecha: Septiembre 2025
"""

import streamlit as st
import pandas as pd
import requests, re, time, io, random, json, os
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
from datetime import datetime

# --------------------------- Config Streamlit ---------------------------
st.set_page_config(
    page_title="Relevador CPC - Buscador de Universidades",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------- Constantes y vocabularios ---------------------------
HEADERS_LIST = [
    # Un pool básico de User-Agents “normales”
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

def _headers():
    return {"User-Agent": random.choice(HEADERS_LIST), "Accept-Language": "en,es;q=0.9"}

# términos de búsqueda (recortados; podés ampliar)
TERMINOS_BUSQUEDA = {
    "ciencia_abierta": [
        "university open science", "universidad ciencia abierta", "universitat ciència oberta",
        "université science ouverte", "universidade ciência aberta", "università scienza aperta",
        "university open data", "university open access", "universidad datos abiertos",
    ],
    "comunicacion_publica": [
        "university science communication", "universidad comunicación pública de la ciencia",
        "universitat comunicació científica", "université communication scientifique",
        "universidade comunicação científica",
    ],
    "diplomacia_cientifica": [
        "university science diplomacy", "universidad diplomacia científica",
        "universitat diplomàcia científica", "université diplomatie scientifique",
        "universidade diplomacia científica",
    ],
}

TERMINOS_VALIDACION = {
    "ciencia_abierta": [
        "open science","ciencia abierta","ciència oberta","ciência aberta","science ouverte",
        "open data","datos abiertos","dades obertes","dados abertos","données ouvertes",
        "open access","acceso abierto","accés obert","acesso aberto","accès libre",
        "fair data","repositorio institucional","institutional repository","reproducible research",
    ],
    "comunicacion_publica": [
        "science communication","comunicación científica","comunicación pública de la ciencia",
        "public engagement","outreach","vulgarisation scientifique","divulgação científica",
        "science literacy","public understanding of science","cultura científica",
    ],
    "diplomacia_cientifica": [
        "science diplomacy","diplomacia científica","diplomàcia científica","diplomatie scientifique",
        "international scientific cooperation","cooperación internacional científica",
        "science policy","política científica",
    ],
}

UNIVERSIDAD_PATTERNS = [
    r"\.edu($|/)", r"\.ac\.", r"\.uni\.", r"university", r"universidad", r"universitat",
    r"universidade", r"université", r"università", r"college", r"institute", r"instituto",
]

CONTROL = {
    "nombre": "Universitat Jaume I",
    "url": "https://www.uji.es/",
    "pais": "España",
    "idioma": "Catalán/Español",
    "buscar_refuerzo": ['ciència oberta', 'ciencia abierta', 'open science'],
}

MAX_TERM_LIST = 6     # top términos por categoría (para no eternizar)
MAX_RESULTS_PER_TERM = 12
MAX_FOLLOW_LINKS = 3
REQ_TIMEOUT = 12

# --------------------------- Helpers ---------------------------
def is_university(url: str, text_hint: str = "") -> bool:
    if not url: 
        return False
    u = url.lower()
    if any(re.search(p, u) for p in UNIVERSIDAD_PATTERNS):
        return True
    t = (text_hint or "").lower()
    return any(word in t for word in ["university","universidad","universitat","universidade","université","college","instituto"])

def same_domain(a: str, b: str) -> bool:
    try:
        return urlparse(a).netloc == urlparse(b).netloc
    except:
        return False

def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for bad in soup(["script","style","noscript","header","footer","nav"]):
        bad.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

@st.cache_data(show_spinner=False, ttl=24*3600)
def http_get(url: str) -> tuple[int,str]:
    try:
        r = requests.get(url, headers=_headers(), timeout=REQ_TIMEOUT)
        return r.status_code, r.text
    except Exception:
        return 0, ""

def find_relevant_links(base_url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    keys = [
        "research","investigación","investigació","pesquisa","recherche","ricerca",
        "science","ciencia","ciència","ciência","scienza",
        "open","abierto","obert","aberto","ouvert","aperto",
        "communication","comunicación","comunicació","comunicação","comunicazione",
        "outreach","divulgación","divulgació","divulgação",
        "policy","política","politique","politica",
        "open science","open data","open access","ciencia abierta","ciència oberta",
        "science communication","science diplomacy","diplomacia científica",
    ]
    urls, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        txt = a.get_text(" ").strip().lower()
        full = urljoin(base_url, href)
        if not same_domain(full, base_url): 
            continue
        low = (href + " " + txt).lower()
        if any(k in low for k in keys):
            if full not in seen:
                urls.append(full); seen.add(full)
        if len(urls) >= 15:
            break
    return urls

def search_duckduckgo(query: str, n: int = 10) -> list[tuple[str,str]]:
    # Usa la versión HTML estática (sin JS)
    q = quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={q}&kl=wt-wt"
    code, text = http_get(url)
    if code != 200:
        return []
    soup = BeautifulSoup(text, "html.parser")
    results = []
    for a in soup.select("a.result__a"):
        href = a.get("href")
        title = a.get_text(" ").strip()
        if href and href.startswith("http"):
            results.append((href, title))
        if len(results) >= n:
            break
    return results

def search_bing(query: str, n: int = 10) -> list[tuple[str,str]]:
    key = os.environ.get("BING_SUBSCRIPTION_KEY")
    if not key:
        return []
    endpoint = "https://api.bing.microsoft.com/v7.0/search"
    try:
        r = requests.get(endpoint, params={"q": query, "count": n, "mkt": "en-US"},
                         headers={"Ocp-Apim-Subscription-Key": key}, timeout=REQ_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        web_pages = data.get("webPages", {}).get("value", [])
        return [(item["url"], item.get("name","")) for item in web_pages]
    except Exception:
        return []

def search_universities_for_category(cat: str, limit_terms: int, max_results_per_term: int) -> list[dict]:
    out = []
    used_domains = set()
    terms = TERMINOS_BUSQUEDA[cat][:limit_terms]
    for term in terms:
        # Intentar Bing API; si no hay key, caer a DuckDuckGo
        hits = search_bing(term, n=max_results_per_term) or search_duckduckgo(term, n=max_results_per_term)
        for url, title in hits:
            if not is_university(url, title):
                continue
            dom = urlparse(url).netloc
            if dom in used_domains:
                continue
            used_domains.add(dom)
            out.append({"url": url, "titulo": title, "categoria": cat, "termino": term})
        # evitar rate-limit
        time.sleep(0.8)
    return out

def scan_site(url: str) -> dict:
    result = {
        "url": url, "accesible": False, "idioma": "", "contenido_muestra": "",
        "urls_analizadas": [], "scores": {"ciencia_abierta":0,"comunicacion_publica":0,"diplomacia_cientifica":0},
        "hits": {"ciencia_abierta":[], "comunicacion_publica":[], "diplomacia_cientifica":[]},
    }
    code, html = http_get(url)
    if code != 200:
        return result
    result["accesible"] = True
    text = clean_text(html)
    result["contenido_muestra"] = text[:600]
    result["urls_analizadas"].append(url)

    # idioma simple por palabras frecuentes
    lang_scores = {
        "español": sum(w in text.lower() for w in ["universidad","investigación","ciencia","estudiantes","facultad"]),
        "catalán": sum(w in text.lower() for w in ["universitat","investigació","ciència","estudiants","facultat"]),
        "inglés":  sum(w in text.lower() for w in ["university","research","science","students","faculty"]),
        "portugués": sum(w in text.lower() for w in ["universidade","pesquisa","ciência","estudantes","faculdade"]),
        "francés": sum(w in text.lower() for w in ["université","recherche","science","étudiants","faculté"]),
        "italiano": sum(w in text.lower() for w in ["università","ricerca","scienza","studenti","facoltà"]),
    }
    result["idioma"] = max(lang_scores, key=lang_scores.get) if any(lang_scores.values()) else "Desconocido"

    # seguir enlaces relevantes
    links = find_relevant_links(url, html)[:MAX_FOLLOW_LINKS]
    for lk in links:
        c2, h2 = http_get(lk)
        if c2 == 200:
            t2 = clean_text(h2)
            text += " " + t2
            result["urls_analizadas"].append(lk)
        time.sleep(0.5)

    low = text.lower()
    for cat, terms in TERMINOS_VALIDACION.items():
        for term in terms:
            if term.lower() in low:
                # capturar contexto
                m = re.search(r".{0,120}"+re.escape(term.lower())+r".{0,120}", low, re.DOTALL)
                ctx = m.group(0) if m else term
                ctx = re.sub(r"\s+", " ", ctx)[:240]
                result["hits"][cat].append({"termino": term, "contexto": ctx})
        result["scores"][cat] = len(result["hits"][cat])
    return result

def domain_name(url: str) -> str:
    try:
        return urlparse(url).netloc
    except:
        return url

def country_guess(domain: str) -> str:
    m = {
        ".es":"España",".edu":"Estados Unidos",".uk":"Reino Unido",".ca":"Canadá",".au":"Australia",".de":"Alemania",
        ".fr":"Francia",".it":"Italia",".br":"Brasil",".ar":"Argentina",".mx":"México",".cl":"Chile",".co":"Colombia",
        ".pe":"Perú",".jp":"Japón",".cn":"China",".in":"India",".nl":"Países Bajos",".ch":"Suiza",".se":"Suecia",".no":"Noruega"
    }
    for ext, pais in m.items():
        if domain.endswith(ext): return pais
    return "Internacional"

def force_find_control_pages(control: dict) -> list[str]:
    # Si la home de UJI no deja ver “ciència oberta”, buscar subpáginas relevantes
    seeds = []
    queries = [f'site:{urlparse(control["url"]).netloc} {q}' for q in control["buscar_refuerzo"]]
    for q in queries:
        hits = search_bing(q, n=5) or search_duckduckgo(q, n=5)
        for u,_ in hits:
            if same_domain(u, control["url"]):
                seeds.append(u)
        time.sleep(0.5)
    return list(dict.fromkeys(seeds))[:3]

# --------------------------- UI ---------------------------
st.title("🔍 Relevador CPC — Universidades que publican sobre Ciencia Abierta, CPC y Diplomacia Científica")
st.markdown("""
Esta app **busca** universidades en la web (DuckDuckGo / Bing), analiza sus sitios y exporta un Excel con señales por categoría.
""")

with st.sidebar:
    st.header("⚙️ Configuración")
    limit_terms = st.slider("Cantidad de términos por categoría", 3, 12, 6)
    max_results = st.slider("Resultados por término", 5, 20, 12)
    follow_links = st.slider("Enlaces internos a seguir por sitio", 0, 5, 3)
    MAX_TERM_LIST = limit_terms
    MAX_RESULTS_PER_TERM = max_results
    MAX_FOLLOW_LINKS = follow_links

    st.caption("Modo API (opcional): si definís **BING_SUBSCRIPTION_KEY** en Secrets, usaré Bing Web Search para más precisión.")

# Botones de acción
c1, c2 = st.columns([3,1])
with c1:
    go = st.button("🚀 Ejecutar búsqueda y análisis", type="primary", width="stretch")
with c2:
    clear = st.button("🗑️ Limpiar", width="stretch")

if clear:
    st.session_state.pop("results", None)
    st.rerun()

# --------------------------- Ejecución ---------------------------
if go:
    st.session_state["results"] = []
    progress = st.progress(0.0)
    status = st.empty()
    steps_total = 1 + 3  # control + 3 categorías
    step = 0

    # 1) Población de control (UJI)
    step += 1
    status.write(f"Analizando población de control: {CONTROL['nombre']} ({step}/{steps_total})")
    res_control = scan_site(CONTROL["url"])

    # Si no hubo señales, refuerzo con búsqueda interna site:
    if all(v == 0 for v in res_control["scores"].values()):
        seeds = force_find_control_pages(CONTROL)
        for s in seeds:
            code, html = http_get(s)
            if code == 200:
                t = clean_text(html)
                low = t.lower()
                for cat, terms in TERMINOS_VALIDACION.items():
                    for term in terms:
                        if term.lower() in low:
                            m = re.search(r".{0,120}"+re.escape(term.lower())+r".{0,120}", low, re.DOTALL)
                            ctx = m.group(0) if m else term
                            ctx = re.sub(r"\s+", " ", ctx)[:240]
                            res_control["hits"][cat].append({"termino": term, "contexto": ctx})
                    res_control["scores"][cat] = len(res_control["hits"][cat])
                res_control["urls_analizadas"].append(s)
                if any(v > 0 for v in res_control["scores"].values()):
                    break

    uni_row = {
        "Universidad": CONTROL["nombre"],
        "País": CONTROL["pais"],
        "URL": CONTROL["url"],
        "Categoría Encontrada": "Control",
        "Término de Búsqueda": "",
        "Fecha Análisis": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Sitio Accesible": "Sí" if res_control["accesible"] else "No",
        "Idioma Detectado": res_control["idioma"],
        "Ciencia Abierta": "Sí" if res_control["scores"]["ciencia_abierta"]>0 else "No",
        "CA - Score": res_control["scores"]["ciencia_abierta"],
        "CA - Términos": ", ".join(x["termino"] for x in res_control["hits"]["ciencia_abierta"]),
        "Comunicación Pública": "Sí" if res_control["scores"]["comunicacion_publica"]>0 else "No",
        "CP - Score": res_control["scores"]["comunicacion_publica"],
        "CP - Términos": ", ".join(x["termino"] for x in res_control["hits"]["comunicacion_publica"]),
        "Diplomacia Científica": "Sí" if res_control["scores"]["diplomacia_cientifica"]>0 else "No",
        "DC - Score": res_control["scores"]["diplomacia_cientifica"],
        "DC - Términos": ", ".join(x["termino"] for x in res_control["hits"]["diplomacia_cientifica"]),
        "URLs Analizadas": "; ".join(res_control["urls_analizadas"]),
        "Contenido Muestra": res_control["contenido_muestra"],
    }
    st.session_state["results"].append(uni_row)
    progress.progress(step/steps_total)

    # 2) Categorías
    for cat in ["ciencia_abierta","comunicacion_publica","diplomacia_cientifica"]:
        step += 1
        status.write(f"Buscando universidades: {cat.replace('_',' ').title()} ({step}/{steps_total})")

        candidates = search_universities_for_category(cat, MAX_TERM_LIST, MAX_RESULTS_PER_TERM)
        # Escanear cada candidato (1 por dominio)
        for c in candidates:
            dom = domain_name(c["url"])
            pais = country_guess(dom)
            scan = scan_site(c["url"])
            row = {
                "Universidad": dom,
                "País": pais,
                "URL": c["url"],
                "Categoría Encontrada": cat,
                "Término de Búsqueda": c["termino"],
                "Fecha Análisis": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Sitio Accesible": "Sí" if scan["accesible"] else "No",
                "Idioma Detectado": scan["idioma"],
                "Ciencia Abierta": "Sí" if scan["scores"]["ciencia_abierta"]>0 else "No",
                "CA - Score": scan["scores"]["ciencia_abierta"],
                "CA - Términos": ", ".join(x["termino"] for x in scan["hits"]["ciencia_abierta"]),
                "Comunicación Pública": "Sí" if scan["scores"]["comunicacion_publica"]>0 else "No",
                "CP - Score": scan["scores"]["comunicacion_publica"],
                "CP - Términos": ", ".join(x["termino"] for x in scan["hits"]["comunicacion_publica"]),
                "Diplomacia Científica": "Sí" if scan["scores"]["diplomacia_cientifica"]>0 else "No",
                "DC - Score": scan["scores"]["diplomacia_cientifica"],
                "DC - Términos": ", ".join(x["termino"] for x in scan["hits"]["diplomacia_cientifica"]),
                "URLs Analizadas": "; ".join(scan["urls_analizadas"]),
                "Contenido Muestra": scan["contenido_muestra"],
            }
            st.session_state["results"].append(row)
        progress.progress(step/steps_total)

    status.write("✅ Búsqueda finalizada")

# --------------------------- Presentación ---------------------------
if "results" in st.session_state and st.session_state["results"]:
    st.markdown("---")
    st.subheader("📊 Resultados")

    df = pd.DataFrame(st.session_state["results"])

    # Métricas rápidas
    total = len(df)
    accesibles = (df["Sitio Accesible"]=="Sí").sum()
    ca = (df["Ciencia Abierta"]=="Sí").sum()
    cp = (df["Comunicación Pública"]=="Sí").sum()
    dc = (df["Diplomacia Científica"]=="Sí").sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🏛️ Total", total)
    c2.metric("🌐 Accesibles", f"{accesibles}/{total}")
    c3.metric("📊 Ciencia Abierta", ca)
    c4.metric("📢 Com. Pública", cp)
    c5.metric("🤝 Diplomacia", dc)

    # Tabla
    st.dataframe(df[[
        "Universidad","País","Categoría Encontrada","Sitio Accesible","Idioma Detectado",
        "Ciencia Abierta","Comunicación Pública","Diplomacia Científica",
        "CA - Score","CP - Score","DC - Score","URL"
    ]], width="stretch")

    # Filtros simples
    with st.expander("🔍 Filtros"):
        cols = st.columns(3)
        with cols[0]:
            paises = ["Todos"] + sorted(df["País"].dropna().unique().tolist())
            f_pais = st.selectbox("País", paises)
        with cols[1]:
            cats = ["Todas","Control","ciencia_abierta","comunicacion_publica","diplomacia_cientifica"]
            f_cat = st.selectbox("Categoría", cats)
        with cols[2]:
            solo_contenido = st.checkbox("Solo con contenido relevante", value=False)

        filtered = df.copy()
        if f_pais != "Todos":
            filtered = filtered[filtered["País"]==f_pais]
        if f_cat != "Todas":
            filtered = filtered[filtered["Categoría Encontrada"]==f_cat]
        if solo_contenido:
            filtered = filtered[(filtered["Ciencia Abierta"]=="Sí") | (filtered["Comunicación Pública"]=="Sí") | (filtered["Diplomacia Científica"]=="Sí")]

        st.dataframe(filtered, width="stretch")

    # Detalle + muestra de contenido
    st.subheader("🔎 Detalle y muestra de contenido")
    for i, row in filtered.head(40).iterrows():
        with st.expander(f"🌐 {row['Universidad']} — {row['País']} [{row['Categoría Encontrada']}]"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**URL:** {row['URL']}")
                st.write(f"**Accesible:** {row['Sitio Accesible']}")
                st.write(f"**Idioma:** {row['Idioma Detectado']}")
            with c2:
                st.write(f"**CA Score:** {row['CA - Score']} — {row['CA - Términos']}")
                st.write(f"**CP Score:** {row['CP - Score']} — {row['CP - Términos']}")
                st.write(f"**DC Score:** {row['DC - Score']} — {row['DC - Términos']}")
            if isinstance(row.get("Contenido Muestra",""), str) and row["Contenido Muestra"]:
                st.text_area(
                    "Contenido de la página",
                    row["Contenido Muestra"],
                    height=120,
                    key=f"contenido_{i}",
                    label_visibility="collapsed"
                )

    # Exportar
    st.markdown("---")
    st.subheader("📥 Exportar Excel")

    if st.button("📊 Generar Excel Completo", width="stretch"):
        with st.spinner("Generando Excel..."):
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Universidades", index=False)
                resumen = pd.DataFrame([
                    {"Métrica":"Total", "Valor": total},
                    {"Métrica":"Accesibles", "Valor": f"{accesibles}/{total}"},
                    {"Métrica":"Con Ciencia Abierta", "Valor": ca},
                    {"Métrica":"Con Comunicación Pública", "Valor": cp},
                    {"Métrica":"Con Diplomacia Científica", "Valor": dc},
                ])
                resumen.to_excel(writer, sheet_name="Resumen", index=False)
            out.seek(0)
            st.download_button(
                label="⬇️ Descargar Relevamiento_CPC.xlsx",
                data=out,
                file_name=f"relevamiento_cpc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    st.markdown("¡Gracias por usar el Relevador CPC! 🧑‍🔬🌍")