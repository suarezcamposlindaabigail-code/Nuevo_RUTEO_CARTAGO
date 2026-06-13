"""
Mapa de los Cantones de la Provincia de Cartago, Costa Rica
===========================================================
Siluetas reales basadas en coordenadas geográficas aproximadas de cada cantón.
Los polígonos reproducen la forma real de la provincia de Cartago.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.patches import Polygon as MplPolygon
import numpy as np

# ─── Coordenadas geográficas reales (lon, lat) de Cartago ───────────────
# Luego se normalizan al canvas 0-100
# Basadas en límites reales de cada cantón

# Centroides reales (lon, lat) aproximados
_CENTROIDS_GEO = {
    0: (-83.912, 9.856),   # CD Cartago (ligeramente desplazado del centroide del cantón)
    1: (-83.919, 9.864),   # Cartago
    2: (-83.841, 9.834),   # Paraíso
    3: (-83.985, 9.900),   # La Unión
    4: (-83.729, 9.843),   # Jiménez
    5: (-83.659, 9.882),   # Turrialba
    6: (-83.780, 9.798),   # Alvarado
    7: (-83.899, 9.802),   # Oreamuno
    8: (-83.941, 9.922),   # El Guarco
}

# Polígonos reales de cada cantón (lon, lat) — aproximaciones geográficas
# Basadas en la morfología real de la provincia de Cartago
_POLYS_GEO = {
    # Cartago – cantón central, forma irregular
    1: [
        (-83.979, 9.830), (-83.955, 9.815), (-83.918, 9.812),
        (-83.882, 9.820), (-83.863, 9.842), (-83.866, 9.870),
        (-83.885, 9.889), (-83.912, 9.896), (-83.945, 9.892),
        (-83.967, 9.877), (-83.979, 9.855),
    ],
    # Paraíso – al este de Cartago, forma alargada E-O
    2: [
        (-83.882, 9.820), (-83.863, 9.842), (-83.810, 9.835),
        (-83.792, 9.815), (-83.783, 9.793), (-83.800, 9.770),
        (-83.836, 9.762), (-83.868, 9.775), (-83.884, 9.800),
    ],
    # La Unión – al oeste, compacto
    3: [
        (-83.979, 9.830), (-83.979, 9.855), (-83.967, 9.877),
        (-83.985, 9.895), (-84.010, 9.910), (-84.030, 9.900),
        (-84.025, 9.870), (-84.010, 9.845), (-83.995, 9.828),
    ],
    # Jiménez – al noreste, tamaño mediano
    4: [
        (-83.810, 9.835), (-83.792, 9.815), (-83.760, 9.820),
        (-83.738, 9.842), (-83.712, 9.870), (-83.718, 9.900),
        (-83.740, 9.918), (-83.772, 9.912), (-83.798, 9.895),
        (-83.812, 9.868), (-83.815, 9.848),
    ],
    # Turrialba – el más grande, al este
    5: [
        (-83.712, 9.870), (-83.718, 9.900), (-83.740, 9.918),
        (-83.720, 9.960), (-83.680, 9.990), (-83.620, 10.000),
        (-83.580, 9.975), (-83.565, 9.940), (-83.580, 9.900),
        (-83.610, 9.870), (-83.650, 9.855), (-83.680, 9.845),
    ],
    # Alvarado – volcánico, norte, irregular
    6: [
        (-83.836, 9.762), (-83.800, 9.770), (-83.783, 9.793),
        (-83.760, 9.820), (-83.738, 9.842), (-83.718, 9.820),
        (-83.730, 9.790), (-83.756, 9.768), (-83.790, 9.745),
        (-83.820, 9.740),
    ],
    # Oreamuno – norte de Cartago, volcán Irazú
    7: [
        (-83.979, 9.830), (-83.955, 9.815), (-83.918, 9.812),
        (-83.882, 9.820), (-83.884, 9.800), (-83.868, 9.775),
        (-83.860, 9.750), (-83.880, 9.730), (-83.915, 9.728),
        (-83.945, 9.742), (-83.968, 9.762), (-83.980, 9.790),
    ],
    # El Guarco – sur de Cartago, alargado S-N
    8: [
        (-83.945, 9.892), (-83.912, 9.896), (-83.885, 9.889),
        (-83.875, 9.920), (-83.880, 9.955), (-83.905, 9.980),
        (-83.940, 9.988), (-83.968, 9.970), (-83.980, 9.945),
        (-83.972, 9.915),
    ],
}


def _normalize(coords_dict, poly_dict):
    """Normaliza coordenadas geo a canvas 0-100."""
    all_lons = [c[0] for c in coords_dict.values()]
    all_lats = [c[1] for c in coords_dict.values()]
    for pts in poly_dict.values():
        all_lons += [p[0] for p in pts]
        all_lats += [p[1] for p in pts]

    min_lon, max_lon = min(all_lons), max(all_lons)
    min_lat, max_lat = min(all_lats), max(all_lats)

    margin = 5

    def norm_lon(v):
        return margin + (v - min_lon) / (max_lon - min_lon) * (100 - 2 * margin)

    def norm_lat(v):
        return margin + (v - min_lat) / (max_lat - min_lat) * (100 - 2 * margin)

    centroids_norm = {k: (norm_lon(v[0]), norm_lat(v[1]))
                      for k, v in coords_dict.items()}
    polys_norm = {k: [(norm_lon(p[0]), norm_lat(p[1])) for p in pts]
                  for k, pts in poly_dict.items()}
    return centroids_norm, polys_norm


CENTROIDS, CANTON_POLYS = _normalize(_CENTROIDS_GEO, _POLYS_GEO)

# ─── Colores por cantón ──────────────────────────────────────────────────
CANTON_COLORS = {
    1: "#5b9bd5",   # Cartago       – azul
    2: "#70ad47",   # Paraíso       – verde
    3: "#ed7d31",   # La Unión      – naranja
    4: "#ffc000",   # Jiménez       – amarillo
    5: "#4bacc6",   # Turrialba     – celeste
    6: "#9dc3e6",   # Alvarado      – azul claro
    7: "#a9d18e",   # Oreamuno      – verde claro
    8: "#c5a3d0",   # El Guarco     – lila
}

# Colores para las rutas (hasta 21 viajes)
ROUTE_COLORS = [
    "#ff4757", "#2ed573", "#ffa502", "#1e90ff", "#ff6b81",
    "#f9ca24", "#6c5ce7", "#e17055", "#00cec9", "#fd79a8",
    "#55efc4", "#fdcb6e", "#74b9ff", "#a29bfe", "#fab1a0",
    "#81ecec", "#dfe6e9", "#ff7675", "#00b894", "#e84393",
    "#b2bec3",
]

LABEL = {
    0: "CD\nCartago",
    1: "Cartago",
    2: "Paraíso",
    3: "La\nUnión",
    4: "Jiménez",
    5: "Turrialba",
    6: "Alvarado",
    7: "Oreamuno",
    8: "El\nGuarco",
}

LABEL_OFFSET = {
    0: (4.5,  0.0),   # CD Cartago – a la derecha
    1: (-4.5, 0.0),   # Cartago – a la izquierda
    2: (3.5, -4.5),
    3: (-3.5, 0.0),
    4: (4.0,  0.0),
    5: (4.0,  0.0),
    6: (4.0, -3.0),
    7: (0.0, -5.0),
    8: (-1.0,  4.5),
}


# ─────────────────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────
def draw_cartago_map(routes_info: list,
                     title: str = "CVRP · Cartago",
                     figsize: tuple = (16, 12)) -> plt.Figure:
    """
    Dibuja el mapa de Cartago con siluetas reales y rutas CVRP superpuestas.
    Incluye distancias explícitas en cada arco.
    """
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#0f172a")
    ax.set_xlim(-2, 102)
    ax.set_ylim(-2, 102)
    ax.set_aspect("equal")
    ax.axis("off")

    # ── 1. Polígonos de cantones (silueta real) ───────────────────────
    for cid, poly_pts in CANTON_POLYS.items():
        arr = np.array(poly_pts)
        # Relleno con transparencia
        patch = MplPolygon(arr, closed=True,
                           facecolor=CANTON_COLORS[cid],
                           edgecolor="#0f172a",
                           linewidth=2.5,
                           alpha=0.25,
                           zorder=1)
        ax.add_patch(patch)
        # Borde bien definido
        border = MplPolygon(arr, closed=True,
                            facecolor="none",
                            edgecolor=CANTON_COLORS[cid],
                            linewidth=1.8,
                            alpha=0.80,
                            zorder=2)
        ax.add_patch(border)
        # Nombre del cantón dentro del polígono
        cx = np.mean([p[0] for p in poly_pts])
        cy = np.mean([p[1] for p in poly_pts])
        ax.text(cx, cy, LABEL[cid],
                fontsize=7, color=CANTON_COLORS[cid],
                alpha=0.65, ha="center", va="center",
                fontweight="bold", zorder=3,
                path_effects=[pe.withStroke(linewidth=2, foreground="#0f172a")])

    # ── 2. Rutas: flechas con offset para rutas paralelas ─────────────
    arc_drawn_count = {}
    arc_km_labels = {}  # Para anotar km de arcos

    from solver import DIST as DIST_TABLE
    from solver import CANTONES

    for idx, rinfo in enumerate(routes_info):
        color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
        route = rinfo["route"]

        for k in range(len(route) - 1):
            i, j = route[k], route[k + 1]
            arc_key = (i, j)
            arc_drawn_count[arc_key] = arc_drawn_count.get(arc_key, 0) + 1
            pass_num = arc_drawn_count[arc_key]

            xi, yi = CENTROIDS[i]
            xj, yj = CENTROIDS[j]

            rad = (pass_num - 1) * 0.25
            if pass_num % 2 == 0:
                rad = -rad

            ax.annotate(
                "",
                xy=(xj, yj),
                xytext=(xi, yi),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=color,
                    lw=2.0,
                    mutation_scale=12,
                    connectionstyle=f"arc3,rad={rad:.2f}",
                    alpha=0.88,
                ),
                zorder=5,
            )

            # Anotar km del arco (solo una vez por par de nodos)
            arc_canonical = (min(i, j), max(i, j))
            if arc_canonical not in arc_km_labels:
                arc_km_labels[arc_canonical] = True
                dist_km = DIST_TABLE[i][j]
                # Punto medio entre los dos nodos
                mx = (xi + xj) / 2
                my = (yi + yj) / 2
                # Pequeño offset perpendicular para no solapar con la flecha
                dx = xj - xi
                dy = yj - yi
                length = max((dx**2 + dy**2)**0.5, 0.001)
                # Perpendicular normalizado
                px = -dy / length * 2.5
                py =  dx / length * 2.5
                ax.text(mx + px, my + py, f"{dist_km} km",
                        fontsize=6.5, color="#fbbf24",
                        ha="center", va="center", zorder=8,
                        fontweight="bold",
                        path_effects=[pe.withStroke(linewidth=2.5,
                                                     foreground="#0f172a")])

    # ── 3. Nodos ──────────────────────────────────────────────────────
    for nid, (xc, yc) in CENTROIDS.items():
        if nid not in CANTON_POLYS and nid != 0:
            continue
        is_depot = nid == 0
        color    = "#ffd700" if is_depot else "#f1f5f9"
        size     = 280 if is_depot else 140
        zw       = 9 if is_depot else 7

        ax.scatter(xc, yc, s=size, color=color, zorder=zw,
                   edgecolors="#0f172a", linewidths=2.0)

        dx, dy = LABEL_OFFSET.get(nid, (3, -4))
        txt = ax.text(
            xc + dx, yc + dy,
            LABEL[nid],
            fontsize=8.5 if not is_depot else 9,
            color="#ffd700" if is_depot else "#e2e8f0",
            fontweight="bold",
            ha="center", va="center",
            zorder=10,
        )
        txt.set_path_effects([
            pe.withStroke(linewidth=3, foreground="#0f172a")
        ])

    # ── 4. Leyenda de rutas ───────────────────────────────────────────
    total_km = sum(r["km"] for r in routes_info)
    handles = []
    for rinfo in routes_info:
        stops_mid = [rinfo["route"][k] for k in range(1, len(rinfo["route"]) - 1)]
        # Nombre corto
        stops_str = "→".join(CANTONES[n].split()[0] for n in stops_mid)
        label = (f"V{rinfo['id']:02d}: {stops_str}  "
                 f"[{rinfo['total_pallets']} pal · {rinfo['km']} km]")
        handles.append(mpatches.Patch(
            color=ROUTE_COLORS[(rinfo["id"] - 1) % len(ROUTE_COLORS)],
            label=label,
        ))

    leg = ax.legend(
        handles=handles,
        loc="lower right",
        fontsize=6.0,
        facecolor="#1e293b",
        labelcolor="#e2e8f0",
        edgecolor="#334155",
        framealpha=0.97,
        ncol=2,
        title=f"  {len(routes_info)} viajes · {int(total_km)} km totales  ",
        title_fontsize=7.5,
        borderpad=0.9,
        labelspacing=0.45,
    )
    leg.get_title().set_color("#fbbf24")

    # ── 5. Título ────────────────────────────────────────────────────
    ax.set_title(
        title,
        color="#f1f5f9",
        fontsize=14,
        fontweight="bold",
        pad=14,
        loc="left",
    )

    # UCR tag
    ax.text(100, 99, "UCR · II-1122",
            color="#64748b", fontsize=7.5,
            ha="right", va="top", style="italic", zorder=10)

    # Brújula
    ax.text(3, 98, "N", color="#94a3b8", fontsize=11,
            fontweight="bold", ha="center", zorder=10)
    ax.annotate("", xy=(3, 95), xytext=(3, 91),
                arrowprops=dict(arrowstyle="-|>", color="#94a3b8", lw=1.5),
                zorder=10)

    # Nota km en arcos
    ax.text(3, 5, "● Los valores amarillos indican distancia (km) de cada tramo",
            color="#94a3b8", fontsize=6.5, ha="left", va="bottom", zorder=10,
            style="italic")

    plt.tight_layout(pad=1.0)
    return fig
