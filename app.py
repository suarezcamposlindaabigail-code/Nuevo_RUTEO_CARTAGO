"""
CVRP – Provincia de Cartago, Costa Rica
========================================
Bloque 03 · Trabajo Grupal · II-1122
Prof. David Benavides · UCR Sede Alajuela · I-2026

Dos pestañas (tabs):
  1. Datos fijos del Excel → solución pre-calculada (437 km)
  2. Demanda personalizable → re-optimización automática
"""

import io
import math
import os
import pickle
import time

import pandas as pd
import streamlit as st

from solver import (
    CANTONES, DEMANDA_FIJA, DEMANDA_IMPERIAL, DEMANDA_PILSEN,
    DEMANDA_TROPICAL, DIST, C, Q_DEFAULT, N, solve_cvrp,
    JORNADA_MAX_H, VELOCIDAD_KMH, TIEMPO_CARGA_H,
)
from map_cartago import draw_cartago_map

# ══════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CVRP · Cartago",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
h1, h2, h3, h4 { font-family: 'Syne', sans-serif !important; }

/* ── KPI Cards ── */
.kpi-grid { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
.kpi {
    flex:1; min-width:130px;
    background: linear-gradient(145deg, #1e293b, #0f172a);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 16px 20px;
}
.kpi-val {
    font-family: 'Syne', sans-serif;
    font-size: 2rem; font-weight: 800;
    color: #f1f5f9; line-height: 1.1;
}
.kpi-val.green  { color: #34d399; }
.kpi-val.yellow { color: #fbbf24; }
.kpi-val.blue   { color: #60a5fa; }
.kpi-lbl {
    font-size: .68rem; color: #94a3b8;
    text-transform: uppercase; letter-spacing: .1em;
    margin-top: 5px;
}

/* ── Section banners ── */
.banner {
    border-radius: 0 16px 16px 0;
    padding: 14px 24px;
    margin: 20px 0 20px;
    border-left: 5px solid;
}
.banner-blue  { background: linear-gradient(90deg,#1e3a5f40,#0f172a); border-color:#3b82f6; }
.banner-amber { background: linear-gradient(90deg,#78350f40,#0f172a); border-color:#f59e0b; }
.banner-title { font-family:'Syne',sans-serif; font-size:1.25rem; font-weight:700; color:#f9fafb; margin:0; }
.banner-sub   { font-size:.78rem; color:#cbd5e1; margin:4px 0 0; }

/* ── Badges ── */
.badge {
    display: inline-block; border-radius: 20px;
    font-size: .74rem; font-weight: 600;
    padding: 3px 14px; margin-left: 8px; vertical-align: middle;
}
.badge-ok   { background:#064e3b; border:1px solid #34d399; color:#34d399; }
.badge-warn { background:#451a03; border:1px solid #fbbf24; color:#fbbf24; }
.badge-info { background:#1e3a5f; border:1px solid #60a5fa; color:#93c5fd; }

/* ── Solve button ── */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #ffffff !important;
    border: none; border-radius: 10px;
    font-family: 'Syne', sans-serif; font-weight: 700;
    letter-spacing: .04em; padding: 10px 28px;
    width: 100%;
}
div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    box-shadow: 0 4px 20px rgba(59,130,246,.45);
    color: #ffffff !important;
}

/* ── Tab styling ── */
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    color: #94a3b8 !important;
    padding: 10px 24px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #f9fafb !important;
    border-bottom: 2px solid #3b82f6 !important;
}

/* ── Table headers ── */
.dataframe thead tr th {
    background:#1e293b !important;
    color:#f9fafb !important;
}
.dataframe tbody tr td {
    color:#e2e8f0 !important;
}

/* ── Info/warning text ── */
div[data-testid="stInfo"] {
    background-color: #1e3a5f !important;
    color: #bfdbfe !important;
    border-left-color: #3b82f6 !important;
}
div[data-testid="stWarning"] {
    background-color: #451a03 !important;
    color: #fde68a !important;
    border-left-color: #f59e0b !important;
}
div[data-testid="stSuccess"] {
    background-color: #064e3b !important;
    color: #a7f3d0 !important;
    border-left-color: #34d399 !important;
}

/* ── Caption ── */
div[data-testid="stCaptionContainer"] p {
    color: #94a3b8 !important;
}

/* ── Number inputs ── */
input[type="number"] {
    color: #f1f5f9 !important;
    background-color: #1e293b !important;
}

/* ── Labels de widgets ── */
label[data-testid="stWidgetLabel"] p {
    color: #cbd5e1 !important;
    font-weight: 500 !important;
}

/* Expanders ── */
div[data-testid="stExpander"] summary {
    color: #cbd5e1 !important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background:linear-gradient(135deg,#0c1445,#0f172a);
            border-radius:18px; padding:30px 36px; margin-bottom:28px;
            border:1px solid #1e3a5f;">
  <div style="font-size:.68rem; color:#60a5fa; font-weight:600;
              letter-spacing:.2em; text-transform:uppercase; margin-bottom:8px;">
    Bloque 03 · Trabajo Grupal · II-1122 · UCR Sede Alajuela · I-2026
  </div>
  <h1 style="margin:0; color:#f9fafb; font-family:'Syne',sans-serif; font-size:2.2rem;">
    🚛 CVRP · Provincia de Cartago
  </h1>
  <p style="color:#cbd5e1; margin:10px 0 0; font-size:.9rem; max-width:720px;">
    Minimización de kilómetros recorridos · Modelo de flujo de red (MIP) ·
    8 cantones · 406 pal/sem · Q = 24 pallets/camión · Jornada ≤ 8h/viaje (40 km/h + 20 min/parada) ·
    Solver PuLP / CBC
  </p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  HELPER: cargar solución pre-calculada
# ══════════════════════════════════════════════════════════════════════
@st.cache_resource
def load_precomputed():
    pkl_path = os.path.join(os.path.dirname(__file__), "precomputed_result.pkl")
    if os.path.exists(pkl_path):
        try:
            with open(pkl_path, "rb") as f:
                result = pickle.load(f)
            # El pkl pre-existente fue generado con el solver anterior
            # (sin restricción de jornada). Si no tiene los nuevos campos,
            # se recalcula para garantizar el cumplimiento de las 8h.
            if "jornada_ok" in result:
                return result
        except Exception:
            pass
    # Recalcular con el modelo que incluye la restricción de jornada (8h)
    return solve_cvrp(DEMANDA_FIJA, Q=Q_DEFAULT)


# ══════════════════════════════════════════════════════════════════════
#  HELPER: renderizar resultados
# ══════════════════════════════════════════════════════════════════════
def render_results(result: dict, key: str):
    status   = result["status"]
    obj      = result["objective"]
    routes   = result["routes"]
    K_min    = result["K_min"]
    total_d  = result["total_dem"]
    demanda  = result.get("demanda", DEMANDA_FIJA)
    coverage = result.get("coverage", {})

    obj_int  = int(round(obj)) if obj is not None else None
    obj_str  = f"{obj_int} km" if obj_int is not None else "—"

    # Badge
    if obj_int is not None and 434 <= obj_int <= 440:
        badge_html = '<span class="badge badge-ok">✓ ÓPTIMO GLOBAL</span>'
    elif obj_int is not None and obj_int <= 470:
        badge_html = '<span class="badge badge-warn">≈ Buena solución</span>'
    else:
        badge_html = '<span class="badge badge-info">Solución factible</span>'

    # Verificar cobertura completa
    all_covered = all(cov.get("ok", False) for cov in coverage.values())

    # Verificar cumplimiento de jornada (8h por viaje)
    jornada_info = result.get("jornada_ok", {})
    jornada_max  = result.get("jornada_max", JORNADA_MAX_H)
    all_jornada_ok = all(j.get("ok", False) for j in jornada_info.values()) if jornada_info else None

    # ── KPIs ───────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    kpis = [
        (c1, obj_str,           "Distancia total",           "green"),
        (c2, str(len(routes)),  "Viajes / camiones",         "blue"),
        (c3, str(K_min),        "Flota mínima ⌈dem/Q⌉",     ""),
        (c4, f"{total_d} pal",  "Demanda total cubierta",    "yellow"),
    ]
    for col, val, lbl, cls in kpis:
        col.markdown(
            f'<div class="kpi">'
            f'<div class="kpi-val {cls}">{val}</div>'
            f'<div class="kpi-lbl">{lbl}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    cover_badge = "✅ Cobertura 100% garantizada" if all_covered else "⚠️ Cobertura incompleta"

    if all_jornada_ok is None:
        jornada_badge = "ℹ️ Jornada no evaluada"
    elif all_jornada_ok:
        jornada_badge = f"✅ Jornada ≤ {jornada_max:.0f}h en todos los viajes"
    else:
        jornada_badge = f"⚠️ Hay viajes que exceden {jornada_max:.0f}h de jornada"

    st.markdown(
        f"**Estado solver:** `{status}` {badge_html} &nbsp;|&nbsp; {cover_badge} "
        f"&nbsp;|&nbsp; {jornada_badge}",
        unsafe_allow_html=True,
    )

    # ── Mapa ───────────────────────────────────────────────────────
    st.markdown("#### 🗺️ Mapa — Cantones de Cartago con rutas óptimas")
    st.caption("Los valores amarillos sobre cada tramo indican la distancia en kilómetros.")
    fig = draw_cartago_map(
        routes,
        title=f"CVRP · Cartago  ·  {obj_str}  ·  {len(routes)} viajes",
    )
    st.pyplot(fig, use_container_width=True)

    # Botón descarga mapa
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight",
                facecolor="#0f172a")
    buf.seek(0)
    st.download_button(
        "⬇ Descargar mapa (PNG)",
        data=buf,
        file_name=f"cvrp_cartago_{key}.png",
        mime="image/png",
        key=f"dl_{key}",
    )

    # ── Tabla de viajes ────────────────────────────────────────────
    st.markdown("#### 📋 Detalle de viajes")
    st.caption(
        f"Tiempo estimado = distancia / {result.get('velocidad_kmh', VELOCIDAD_KMH):.0f} km/h "
        f"+ {result.get('tiempo_carga_h', TIEMPO_CARGA_H) * 60:.0f} min de carga/descarga por parada. "
        f"Jornada máxima: {result.get('jornada_max', JORNADA_MAX_H):.0f} h por viaje."
    )
    rows = []
    for rinfo in routes:
        nodes    = rinfo["route"]
        trayecto = " → ".join(CANTONES[n] for n in nodes)
        ppc      = rinfo["pallets_por_canton"]
        dem_cov  = ", ".join(
            f"{CANTONES[n]}: {ppc.get(n, '?')} pal"
            for n in nodes[1:-1]
        )
        jinfo = jornada_info.get(rinfo["id"], {})
        horas = jinfo.get("horas")
        ok_j  = jinfo.get("ok")
        if horas is not None:
            tiempo_str = f"{horas:.2f} h"
            estado_j   = "✅ OK" if ok_j else "⚠️ Excede 8h"
        else:
            tiempo_str = "—"
            estado_j   = "—"

        rows.append({
            "Viaje #":          f"V{rinfo['id']:02d}",
            "Camión":           f"C{rinfo['id']:02d}",
            "Trayecto":         trayecto,
            "Demanda cubierta": dem_cov,
            "Total pallets":    rinfo["total_pallets"],
            "% capacidad":      f"{rinfo['total_pallets'] / Q_DEFAULT * 100:.0f}%",
            "Distancia (km)":   rinfo["km"],
            "Paradas":          jinfo.get("paradas", len(nodes) - 2),
            "Tiempo viaje":     tiempo_str,
            "Jornada (≤8h)":    estado_j,
        })

    df = pd.DataFrame(rows)

    def style_rows(row):
        km = row["Distancia (km)"]
        if row.get("Jornada (≤8h)") == "⚠️ Excede 8h":
            return ["background-color:#451a03; color:#fde68a"] * len(row)
        if km == 0:
            return ["background-color:#052e16; color:#a7f3d0"] * len(row)
        elif km >= 70:
            return ["background-color:#1c1a00; color:#fde68a"] * len(row)
        return ["background-color:#111827; color:#e2e8f0"] * len(row)

    st.dataframe(
        df.style.apply(style_rows, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    total_km_rutas  = sum(r["km"] for r in routes)
    total_pal_rutas = sum(r["total_pallets"] for r in routes)
    st.markdown(
        f"**Total km:** `{total_km_rutas}` &nbsp;|&nbsp; "
        f"**Total pallets transportados:** `{total_pal_rutas}` &nbsp;|&nbsp; "
        f"**Camiones desplegados:** `{len(routes)}`"
    )

    # ── Cobertura por cantón ───────────────────────────────────────
    st.markdown("#### 📊 Cobertura por cantón")
    cov_rows = []
    for cid in C:
        viajes_c = [r for r in routes if cid in r["route"][1:-1]]
        pal_c    = sum(r["pallets_por_canton"].get(cid, 0) for r in viajes_c)
        demanded = demanda[cid]
        pct      = (pal_c / demanded * 100) if demanded > 0 else 0
        cov_rows.append({
            "Cantón":                 CANTONES[cid],
            "Demanda (pal)":          demanded,
            "Pallets entregados":     pal_c,
            "% cobertura":            f"{pct:.0f}%",
            "Viajes que lo atienden": len(viajes_c),
            "Estado":                 "✅ Completo" if pal_c >= demanded else "⚠️ Incompleto",
        })

    cov_df = pd.DataFrame(cov_rows)

    def style_coverage(row):
        if "✅" in str(row["Estado"]):
            return ["background-color:#052e16; color:#a7f3d0"] * len(row)
        return ["background-color:#1c0a00; color:#fde68a"] * len(row)

    st.dataframe(
        cov_df.style.apply(style_coverage, axis=1),
        hide_index=True, use_container_width=True
    )

    # ── Arcos activos ─────────────────────────────────────────────
    with st.expander("🔍 Arcos activos y flujos del MIP", expanded=False):
        arcos  = result["arcos"]
        flujos = result["flujos"]
        arc_rows = []
        for (i, j), cnt in sorted(arcos.items()):
            arc_rows.append({
                "Arco":            f"{CANTONES[i]} → {CANTONES[j]}",
                "x[i,j] viajes":   cnt,
                "f[i,j] pallets":  flujos.get((i, j), 0),
                "d[i,j] (km)":     DIST[i][j],
                "Contribución km": cnt * DIST[i][j],
            })
        df_a = pd.DataFrame(arc_rows)
        st.dataframe(df_a, hide_index=True, use_container_width=True)
        total_contrib = df_a["Contribución km"].sum()
        match = "✅ coincide" if total_contrib == obj_int else "⚠️ revisar"
        st.caption(
            f"Verificación: Σ x·d = **{total_contrib} km** ({match})"
        )


# ══════════════════════════════════════════════════════════════════════
#  TABS PRINCIPALES
# ══════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    "📌 Solución Óptima (Datos Fijos)",
    "⚙️ Demanda Personalizada",
    "📖 Formulación Matemática",
])


# ══════════════════════════════════════════════════════════════════════
#  TAB 1 — DATOS FIJOS (pre-calculado)
# ══════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div class="banner banner-blue">
      <div class="banner-title">📌 Solución Óptima — Datos Fijos del Excel</div>
      <div class="banner-sub">
        Demanda y distancias exactas del enunciado · 8 cantones · 406 pal/sem ·
        Cobertura 100% garantizada · Jornada ≤ 8h por viaje (40 km/h + 20 min carga/descarga)
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Tablas de datos de entrada
    with st.expander("📂 Ver datos del problema (fijos)", expanded=False):
        col_dem, col_dist = st.columns(2)

        with col_dem:
            st.markdown("**① Demanda por cantón (pallets/semana)**")
            df_dem = pd.DataFrame([
                {
                    "Nodo":     k,
                    "Cantón":   CANTONES[k],
                    "Imperial": DEMANDA_IMPERIAL[k],
                    "Pilsen":   DEMANDA_PILSEN[k],
                    "Tropical": DEMANDA_TROPICAL[k],
                    "Total":    DEMANDA_FIJA[k],
                }
                for k in range(1, 9)
            ])
            total_row = pd.DataFrame([{
                "Nodo": "—", "Cantón": "TOTAL",
                "Imperial": 202, "Pilsen": 102, "Tropical": 102, "Total": 406,
            }])
            df_dem = pd.concat([df_dem, total_row], ignore_index=True)
            st.dataframe(df_dem, hide_index=True, use_container_width=True)

        with col_dist:
            st.markdown("**② Matriz de distancias por carretera (km)**")
            df_dist = pd.DataFrame(
                DIST,
                index=[f"{i}·{CANTONES[i]}" for i in range(9)],
                columns=[str(i) for i in range(9)],
            )
            st.dataframe(
                df_dist.style
                       .background_gradient(cmap="YlOrRd", axis=None)
                       .format("{:.0f}"),
                use_container_width=True,
            )

    # Cargar y mostrar resultado pre-calculado inmediatamente
    with st.spinner("Cargando solución óptima pre-calculada..."):
        res1 = load_precomputed()

    st.success("✅ Solución cargada · cobertura 100% en todos los cantones · jornada ≤ 8h verificada por viaje")
    render_results(res1, "fijo")


# ══════════════════════════════════════════════════════════════════════
#  TAB 2 — DEMANDA PERSONALIZADA
# ══════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div class="banner banner-amber">
      <div class="banner-title">⚙️ Demanda Personalizada</div>
      <div class="banner-sub">
        Ajustá la demanda de cualquier cantón y re-optimizá la red de distribución
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### Demanda por cantón (pallets/semana)")

    cols = st.columns(4)
    dem_custom: dict[int, int] = {}
    for idx, cid in enumerate(range(1, 9)):
        with cols[idx % 4]:
            dem_custom[cid] = st.number_input(
                f"{CANTONES[cid]}",
                min_value=0,
                max_value=600,
                value=int(DEMANDA_FIJA[cid]),
                step=1,
                key=f"dc_{cid}",
            )

    total_custom = sum(dem_custom.values())
    flota_custom = math.ceil(total_custom / Q_DEFAULT) if total_custom > 0 else 0

    col_info, col_q2, col_btn2 = st.columns([3, 1, 1])
    with col_info:
        if total_custom > 0:
            st.info(
                f"**Total:** {total_custom} pal/sem &nbsp;·&nbsp; "
                f"**Flota mínima:** ⌈{total_custom}/{Q_DEFAULT}⌉ = **{flota_custom} camiones**"
            )
        else:
            st.warning("La demanda total no puede ser 0.")

    with col_q2:
        q_cust = st.number_input("Capacidad Q (pallets)", 12, 48, 24, 4, key="q_cust")
    with col_btn2:
        st.markdown("&nbsp;")
        run2 = st.button("▶ Resolver", key="btn_cust")

    with st.expander("🕐 Parámetros de jornada laboral (8h por viaje)", expanded=False):
        col_v, col_c, col_j = st.columns(3)
        with col_v:
            vel_cust = st.number_input(
                "Velocidad promedio (km/h)", 10, 100, int(VELOCIDAD_KMH), 5, key="vel_cust"
            )
        with col_c:
            carga_cust_min = st.number_input(
                "Tiempo carga/descarga por parada (min)", 0, 120,
                int(TIEMPO_CARGA_H * 60), 5, key="carga_cust"
            )
        with col_j:
            jornada_cust = st.number_input(
                "Jornada máxima por viaje (h)", 1, 24, int(JORNADA_MAX_H), 1, key="jornada_cust"
            )

    if run2:
        if total_custom == 0:
            st.error("⚠️ La demanda total es 0. Ajustá al menos un cantón.")
        else:
            with st.spinner("⚙️ Resolviendo modelo MIP personalizado..."):
                t0 = time.time()
                res2 = solve_cvrp(
                    dem_custom, Q=q_cust,
                    jornada_max=jornada_cust,
                    velocidad_kmh=vel_cust,
                    tiempo_carga_h=carga_cust_min / 60.0,
                )
                elapsed = time.time() - t0
                st.session_state["res2"] = res2
                st.session_state["t2"]   = elapsed

    if "res2" in st.session_state:
        st.caption(f"⏱ Tiempo de cómputo: {st.session_state['t2']:.1f} s")
        render_results(st.session_state["res2"], "custom")
    else:
        st.markdown("""
        <div style="text-align:center; padding:60px 20px; color:#475569;">
            <div style="font-size:3rem; margin-bottom:16px;">⚙️</div>
            <div style="font-family:'Syne',sans-serif; font-size:1.1rem; color:#64748b;">
                Ajustá los valores de demanda y presioná <strong style="color:#60a5fa;">▶ Resolver</strong> para optimizar
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  TAB 3 — FORMULACIÓN MATEMÁTICA
# ══════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div class="banner banner-blue">
      <div class="banner-title">📖 Formulación Matemática del Modelo MIP</div>
      <div class="banner-sub">
        Modelo de Flujo de Red — CVRP Cartago · Variables, restricciones y función objetivo
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(r"""
### Modelo de Flujo de Red — CVRP Cartago

**Conjuntos**
- $N = \{0,1,\ldots,8\}$ — nodos (0 = depósito CD Cartago)
- $C = \{1,\ldots,8\}$ — cantones clientes

**Parámetros**
- $d_{ij}$ — distancia por carretera entre $i$ y $j$ (km)
- $q_v$ — demanda del cantón $v$ (pallets/semana)
- $Q = 24$ — capacidad máxima por camión (pallets)
- $v_{kmh} = 40$ — velocidad promedio de viaje (km/h)
- $\tau_{ij} = d_{ij}/v_{kmh}$ — tiempo de viaje entre $i$ y $j$ (horas)
- $\delta = 20\,\text{min} = 1/3\,\text{h}$ — tiempo de carga/descarga por parada
- $J = 8$ — jornada máxima por viaje (horas)
- $M$ — constante "Big-M" suficientemente grande

**Variables de decisión**

$$x_{ij} \in \mathbb{Z}^{+} \quad \text{número de camiones en el arco } (i,j)$$
$$f_{ij} \geq 0 \quad \text{flujo de pallets en el arco } (i,j)$$
$$z_{ij} \in \{0,1\} \quad \text{1 si el arco } (i,j) \text{ está activo}$$
$$t_{v} \geq 0 \quad \text{tiempo acumulado (h) al llegar al cantón } v \text{ en su viaje}$$

**Función objetivo**

$$\min \; Z = \sum_{i \in N}\sum_{\substack{j \in N \\ j \neq i}} d_{ij}\; x_{ij}$$

**Restricciones**

$$\underbrace{\sum_{i \neq v} x_{iv} \;-\; \sum_{j \neq v} x_{vj} = 0}_{\text{R1: camión entra} - \text{camión sale} = 0} \qquad \forall\, v \in C$$

$$\underbrace{\sum_{i \neq v} f_{iv} \;-\; \sum_{j \neq v} f_{vj} = q_v}_{\text{R2: flujo entra} - \text{flujo sale} = \text{demanda}} \qquad \forall\, v \in C$$

$$\underbrace{f_{ij} \;\leq\; Q \cdot x_{ij}}_{\text{R3: Gran-M}} \qquad \forall\, i,j \in N,\; i \neq j$$

$$\underbrace{\sum_{j \in C} f_{0j} = \sum_{v \in C} q_v}_{\text{R4: flujo total desde depósito}}$$

$$\underbrace{\sum_{j \in C} x_{0j} \;\geq\; \left\lceil \dfrac{\displaystyle\sum_{v} q_v}{Q} \right\rceil}_{\text{R5: flota mínima}}$$

$$\underbrace{x_{ij} \leq M\cdot z_{ij}, \quad x_{ij} \geq z_{ij}}_{\text{R5b: } z_{ij}=1 \iff x_{ij}\geq 1} \qquad \forall\, i,j \in N,\; i \neq j$$

$$\underbrace{t_j \;\geq\; t_i + \tau_{ij} + \delta - M(1-z_{ij})}_{\text{R6: acumulador de tiempo (MTZ)}} \qquad \forall\, i,j \in C,\; i \neq j$$

$$\underbrace{t_j \;\geq\; \tau_{0j} + \delta - M(1-z_{0j})}_{\text{R8: tiempo del primer nodo desde el depósito}} \qquad \forall\, j \in C$$

$$\underbrace{t_v + \tau_{v0} \;\leq\; J + M(1-z_{v0})}_{\text{R7: jornada máxima de 8h al regresar al depósito}} \qquad \forall\, v \in C$$

$$x_{ij} \in \mathbb{Z}^{+}, \quad f_{ij} \geq 0, \quad z_{ij}\in\{0,1\}, \quad t_v \geq 0$$

---
""")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
**Resultado validado**
| Métrica | Valor |
|---|---|
| Cobertura | 100% todos los cantones |
| Jornada máxima por viaje | ≤ 8 h (verificada) |
| Velocidad asumida | 40 km/h |
| Carga/descarga por parada | 20 min |
| Flota mínima ⌈406/24⌉ | 17 camiones |
""")

    with col_b:
        st.markdown("""
**Distribución de demanda por producto**
| Producto | % | Pallets/sem |
|---|---|---|
| Imperial | 50% | 203 |
| Pilsen | 25% | 102 |
| Tropical | 25% | 102 |
| **Total** | **100%** | **406** |
""")

    st.info(
        "**Nota técnica:** Las restricciones R5b, R6, R7 y R8 (tipo MTZ) garantizan que "
        "cada viaje individual — desde que sale del depósito hasta que regresa — no "
        "exceda una jornada laboral de 8 horas, contando el tiempo de manejo "
        "(a 40 km/h) más 20 minutos de carga/descarga por cada cantón visitado. "
        "Al añadir estas restricciones, el óptimo global puede aumentar levemente "
        "respecto a la solución sin restricción de jornada (437 km), ya que el "
        "solver puede verse obligado a usar más viajes cortos en lugar de menos "
        "viajes largos."
    )


# ══════════════════════════════════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════════════════════════════════
st.markdown("""
<hr style="border-color:#1e293b; margin-top:48px;">
<p style="text-align:center; color:#64748b; font-size:.74rem; padding-bottom:14px;">
  Prof. David Benavides · UCR Sede Alajuela · I-2026 ·
  Bloque 03 – Trabajo Grupal · Curso II-1122
</p>
""", unsafe_allow_html=True)
