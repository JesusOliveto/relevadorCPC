# -*- coding: utf-8 -*-
"""
Relevador CPC (Comunicación Pública de la Ciencia)
--------------------------------------------------
- Busca universidades con Google Custom Search JSON API (Programmable Search Engine).
- Categorías: Ciencia Abierta, Comunicación Pública de la Ciencia, Diplomacia Científica.
- Analiza páginas (home + enlaces internos relevantes), detecta términos por categoría y exporta Excel.
- Compatible con Streamlit Cloud. Ajustes deprecados: width='stretch' y labels accesibles.

Autor: Sistema de Relevamiento CPC
Fecha: Septiembre 2025
"""

import os
import io
import re
import time
import json
import random
import requests
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote_plus
from datetime import datetime

# ==============================
# Config. Streamlit
# ==============================
st.set_page_config(
    page_title="Relevador CPC - Buscador de Universidades",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================
# Claves (Secrets / Entorno / Fallback)
# ==============================
API_KEY = (
    (st.secrets.get("GOOGLE_API_KEY") if hasattr(st, "secrets") else None)
    or os.getenv("GOOGLE_API_KEY")
)

CSE_CX = (
    (st.secrets.get("GOOGLE_CSE_CX") if hasattr(st, "secrets") else None)
    or os.getenv("GOOGLE_CSE_CX")
)

# URL pública del buscador (informativa)
CSE_PUBLIC_URL = "https://cse.google.com/cse?cx=d15e41407a20a49c6"

# ==============================
# Constantes y vocabularios
# ==============================
REQ_TIMEOUT = 12
HEADERS_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]
def _headers():
    return {"User-Agent": random.choice(HEADERS_POOL), "Accept-Language": "es-AR,es;q=0.9,en;q=0.8"}

TERMINOS_BUSQUEDA = {
    "ciencia_abierta": [
        '("open science" OR "open data" OR "open access") university',
        "universidad ciencia abierta",
        "universitat ciència oberta",
        "université science ouverte",
        "universidade ciência aberta",
        "università scienza aperta",
    ],
    "comunicacion_publica": [
        '("science communication" OR "public engagement") university',
        "universidad comunicación pública de la ciencia",
        "universitat comunicació científica",
        "université communication scientifique",
        "universidade comunicação científica",
    ],
    "diplomacia_cientifica": [
        '("science diplomacy") university',
        "universidad diplomacia científica",
        "universitat diplomàcia científica",
        "université diplomatie scientifique",
        "universidade diplomacia científica",
    ],
}

TERMINOS_VALIDACION = {
    "ciencia_abierta": [
        "open science", "ciencia abierta", "ciència oberta", "ciência aberta", "science ouverte",
        "open data", "datos abiertos", "dades obertes", "dados abertos", "données ouvertes",
        "open access", "acceso abierto", "accés obert", "acesso aberto", "accès libre",
        "fair data", "repositorio institucional", "institutional repository", "reproducible research",
    ],
    "comunicacion_publica": [
        "science communication", "comunicación científica", "comunicación pública de la ciencia",
        "public engagement", "outreach", "vulgarisation scientifique", "divulgação científica",
        "science literacy", "public understanding of science", "cultura científica",
    ],
    "diplomacia_cientifica": [
        "science diplomacy", "diplomacia científica", "diplomàcia científica", "diplomatie scientifique",
        "international scientific cooperation", "cooperación internacional científica",
        "science policy", "política científica",
    ],
}

# Dominios a excluir (rankings/directorios/etc.)
BAD_DOMAINS_SUBSTR = [
    "wikipedia.org", "wikidata.org", "web.archive.org",
    "blogspot.", "wordpress.", "medium.com",
    "topuniversities.", "timeshighereducation.", "theworlduniversityrankings",
    "4icu.org", "uni-rank", "edurank", "shanghairanking",
    "qs.com", "mastersportal", "bachelorstudies", "studocu", "prezi",
    "/ranking", "/rankings", "/directory", "/directorio",
]

CONTROL = {
    "nombre": "Universitat Jaume I",
    "url": "https://www.uji.es/",
    "pais": "España",
    "idioma": "Catalán/Español",
    "buscar_refuerzo": ['site:uji.es ("ciència oberta" OR "ciencia abierta" OR "open science")'],
}

# ==============================
# Utilidades
# ==============================
def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for bad in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        bad.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()

@st.cache_data(show_spinner=False, ttl=24*3600)
def http_get(url: str) -> tuple[int, str]:
    try:
        r = requests.get(url, headers=_headers(), timeout=REQ_TIMEOUT)
        return r.status_code, r.text
    except Exception:
        return 0, ""

def same_domain(a: str, b: str) -> bool:
    try:
        return urlparse(a).netloc == urlparse(b).netloc
    except:
        return False

def is_university(url: str, title: str = "") -> bool:
    if not url:
        return False
    u = url.lower()
    # filtrar directorios/rankings
    if any(b in u for b in BAD_DOMAINS_SUBSTR):
        return False
    # señales fuertes por dominio
    strong = any(re.search(p, u) for p in [
        r"\.edu($|/)", r"\.edu\.[a-z]+$", r"\.ac\.", r"\.ac$",
        r"\.uni\.", r"\.univ\.", r"\.edu\.", r"\.ac\.[a-z]+$"
    ])
    if strong:
        return True
    # título/texto
    t = (title or "").lower()
    words = ["university","universidad","universitat","universidade","université","università","college","instituto","institute"]
    if any(w in t for w in words) and not any(x in t for x in ["ranking","rankings","list","directorio","directory","top"]):
        return True
    # hostname con 'uni.' o 'univ.'
    host = urlparse(url).netloc.lower()
    if host.startswith("uni.") or host.startswith("univ."):
        return True
    return False

def country_guess(domain: str) -> str:
    m = {
        ".es":"España",".edu":"Estados Unidos",".uk":"Reino Unido",".ca":"Canadá",".au":"Australia",".de":"Alemania",
        ".fr":"Francia",".it":"Italia",".br":"Brasil",".ar":"Argentina",".mx":"México",".cl":"Chile",".co":"Colombia",
        ".pe":"Perú",".jp":"Japón",".cn":"China",".in":"India",".nl":"Países Bajos",".ch":"Suiza",".se":"Suecia",".no":"Noruega"
    }
    for ext, pais in m.items():
        if domain.endswith(ext): return pais
    return "Internacional"

def find_relevant_links(base_url: str, html: str, limit: int = 12) -> list[str]:
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
        if len(urls) >= limit:
            break
    return urls

# ==============================
# Google Custom Search (JSON API)
# ==============================
def google_cse_search(query: str, per_page: int = 10, pages: int = 3) -> list[dict]:
    """
    Devuelve lista de resultados: dict con keys: link, title, snippet.
    """
    results = []
    per_page = max(1, min(10, per_page))  # API permite num=1..10
    for p in range(pages):
        start = 1 + p * per_page  # start: 1-based
        params = {
            "key": API_KEY,
            "cx": CSE_CX,
            "q": query,
            "num": per_page,
            "start": start,
            "hl": "es",
            "safe": "off",
        }
        try:
            r = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=REQ_TIMEOUT)
            if r.status_code != 200:
                # 403/429 por cuota → salir temprano
                break
            data = r.json()
            items = data.get("items", [])
            for it in items:
                results.append({
                    "link": it.get("link"),
                    "title": it.get("title", ""),
                    "snippet": it.get("snippet", ""),
                })
            # Si no trajo nada, cortar
            if not items:
                break
        except Exception:
            break
        time.sleep(0.3)  # ser cortés con la API
    return results

def search_universities_for_category(cat: str, terms: list[str], per_page: int, pages: int) -> list[dict]:
    out, used_domains = [], set()
    for term in terms:
        hits = google_cse_search(term, per_page=per_page, pages=pages)
        for h in hits:
            url, title = h.get("link"), h.get("title","")
            if not url:
                continue
            if not is_university(url, title):
                continue
            dom = urlparse(url).netloc.lower()
            if any(bad in dom for bad in BAD_DOMAINS_SUBSTR):
                continue
            if dom in used_domains:
                continue
            used_domains.add(dom)
            out.append({"url": url, "titulo": title, "categoria": cat, "termino": term})
        time.sleep(0.2)
    return out

# ==============================
# Análisis de sitio
# ==============================
def scan_site(url: str, follow_links: int = 3) -> dict:
    result = {
        "url": url, "accesible": False, "idioma": "", "contenido_muestra": "",
        "urls_analizadas": [], "scores": {"ciencia_abierta":0,"comunicacion_publica":0,"diplomacia_cientifica":0},
        "hits": {"ciencia_abierta":[], "comunicacion_publica":[], "diplomacia_cientifica":[]},
    }
    code, html = http_get(url)
    if code != 200 or not html:
        return result
    result["accesible"] = True
    text = clean_text(html)
    result["contenido_muestra"] = text[:600]
    result["urls_analizadas"].append(url)

    # idioma simple por palabras frecuentes
    low = text.lower()
    lang_scores = {
        "español": sum(w in low for w in ["universidad","investigación","ciencia","estudiantes","facultad"]),
        "catalán": sum(w in low for w in ["universitat","investigació","ciència","estudiants","facultat"]),
        "inglés":  sum(w in low for w in ["university","research","science","students","faculty"]),
        "portugués": sum(w in low for w in ["universidade","pesquisa","ciência","estudantes","faculdade"]),
        "francés": sum(w in low for w in ["université","recherche","science","étudiants","faculté"]),
        "italiano": sum(w in low for w in ["università","ricerca","scienza","studenti","facoltà"]),
    }
    result["idioma"] = max(lang_scores, key=lang_scores.get) if any(lang_scores.values()) else "Desconocido"

    # Seguir enlaces internos relevantes
    links = find_relevant_links(url, html, limit=12)[:follow_links]
    for lk in links:
        c2, h2 = http_get(lk)
        if c2 == 200 and h2:
            t2 = clean_text(h2)
            low += " " + t2.lower()
            result["urls_analizadas"].append(lk)
        time.sleep(0.25)

    # Scoring por categoría
    for cat, terms in TERMINOS_VALIDACION.items():
        for term in terms:
            tl = term.lower()
            if tl in low:
                m = re.search(r".{0,120}"+re.escape(tl)+r".{0,120}", low, re.DOTALL)
                ctx = m.group(0) if m else tl
                ctx = re.sub(r"\s+", " ", ctx)[:240]
                result["hits"][cat].append({"termino": term, "contexto": ctx})
        result["scores"][cat] = len(result["hits"][cat])
    return result

def force_find_control(control: dict) -> dict:
    """
    Si la home de UJI no muestra términos (por banners), refuerza con búsqueda site:.
    """
    res = scan_site(control["url"], follow_links=3)
    if any(v > 0 for v in res["scores"].values()):
        return res
    # Búsqueda específica dentro del dominio
    for q in control["buscar_refuerzo"]:
        hits = google_cse_search(q, per_page=10, pages=2)
        for h in hits:
            u = h.get("link", "")
            if not u or not same_domain(u, control["url"]):
                continue
            c2, h2 = http_get(u)
            if c2 == 200 and h2:
                t2 = clean_text(h2).lower()
                for cat, terms in TERMINOS_VALIDACION.items():
                    for term in terms:
                        tl = term.lower()
                        if tl in t2:
                            m = re.search(r".{0,120}"+re.escape(tl)+r".{0,120}", t2, re.DOTALL)
                            ctx = m.group(0) if m else tl
                            ctx = re.sub(r"\s+", " ", ctx)[:240]
                            res["hits"][cat].append({"termino": term, "contexto": ctx})
                    res["scores"][cat] = len(res["hits"][cat])
                res["urls_analizadas"].append(u)
                if any(v > 0 for v in res["scores"].values()):
                    return res
    return res

# ==============================
# UI
# ==============================
st.title("🔍 Relevador CPC — Universidades con Ciencia Abierta, CPC y Diplomacia Científica")
st.caption("Motor: Google Custom Search JSON API (Programmable Search Engine).")
with st.expander("ℹ️ Motor configurado"):
    st.write(f"**CX**: `{CSE_CX}` — [Ver buscador público]({CSE_PUBLIC_URL})")

with st.sidebar:
    st.header("⚙️ Configuración de búsqueda")
    terms_per_cat = st.slider("Términos por categoría", 3, 12, 6)
    per_page = st.slider("Resultados por página (CSE permite 1–10)", 1, 10, 10)
    pages = st.slider("Páginas por término", 1, 5, 3)
    follow_links = st.slider("Enlaces internos a seguir por sitio", 0, 5, 3)

# Acciones
c1, c2 = st.columns([3,1])
with c1:
    go = st.button("🚀 Ejecutar búsqueda y análisis", type="primary", width="stretch")
with c2:
    clear = st.button("🗑️ Limpiar", width="stretch")

if clear:
    st.session_state.pop("results", None)
    st.rerun()

# ==============================
# Ejecución
# ==============================
if go:
    if not API_KEY or not CSE_CX:
        st.error("Falta configurar GOOGLE_API_KEY y/o GOOGLE_CSE_CX. Cargalos en Secrets o variables de entorno.")
    else:
        st.session_state["results"] = []
        progress = st.progress(0.0)
        status = st.empty()
        steps_total = 1 + 3  # control + 3 categorías
        step = 0

        # 1) Control: UJI
        step += 1
        status.write(f"Analizando población de control: {CONTROL['nombre']} ({step}/{steps_total})")
        res_control = force_find_control(CONTROL)

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
        for cat in ["ciencia_abierta", "comunicacion_publica", "diplomacia_cientifica"]:
            step += 1
            status.write(f"Buscando universidades: {cat.replace('_',' ').title()} ({step}/{steps_total})")
            term_list = TERMINOS_BUSQUEDA[cat][:terms_per_cat]
            candidates = search_universities_for_category(cat, term_list, per_page, pages)

            for c in candidates:
                dom = urlparse(c["url"]).netloc.lower()
                pais = country_guess(dom)
                scan = scan_site(c["url"], follow_links=follow_links)
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

# ==============================
# Presentación resultados
# ==============================
if "results" in st.session_state and st.session_state["results"]:
    st.markdown("---")
    st.subheader("📊 Resultados")

    df = pd.DataFrame(st.session_state["results"])

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

    st.dataframe(df[[
        "Universidad","País","Categoría Encontrada","Sitio Accesible","Idioma Detectado",
        "Ciencia Abierta","Comunicación Pública","Diplomacia Científica",
        "CA - Score","CP - Score","DC - Score","URL"
    ]], width="stretch")

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
            filtered = filtered[
                (filtered["Ciencia Abierta"]=="Sí") |
                (filtered["Comunicación Pública"]=="Sí") |
                (filtered["Diplomacia Científica"]=="Sí")
            ]

        st.dataframe(filtered, width="stretch")

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
            # label no vacío + oculto
            st.text_area(
                "Contenido de la página",
                row.get("Contenido Muestra","") or "",
                height=120,
                key=f"contenido_{i}",
                label_visibility="collapsed"
            )

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
            st.success("✅ Listo")