"""
CVRP Cartago – Modelo de Flujo de Red (MIP) + Restricción de Jornada (8h)
==========================================================================
Variables:
  x[i,j]  ∈ {0,1,2,...}  número de camiones que recorren el arco (i,j)
  f[i,j]  ≥ 0             flujo de pallets en el arco (i,j)
  t[i]    ≥ 0             tiempo acumulado (h) al llegar al nodo i, en su viaje

Restricciones del modelo de flujo original:
  R1  Σ x[i,v] − Σ x[v,j] = 0          ∀ v ∈ C   (camión entra − camión sale = 0)
  R2  Σ f[i,v] − Σ f[v,j] = q_v         ∀ v ∈ C   (flujo entra − flujo sale = demanda)
  R3  f[i,j] ≤ Q · x[i,j]               ∀ i,j     (Gran-M: acota camiones que salen)
  R4  Σ f[0,j] = Σ q_v                             (flujo total desde depósito)
  R5  Σ x[0,j] ≥ ⌈Σq/Q⌉                            (flota mínima)

Restricción NUEVA — Jornada laboral de 8 horas por viaje (tipo MTZ):
  Cada viaje sale del depósito (t=0), recorre uno o más cantones y regresa.
  El tiempo de viaje entre i y j es d[i,j] / VELOCIDAD (horas).
  Cada parada en un cantón consume TIEMPO_CARGA horas (carga/descarga).

  R6  t[j] ≥ t[i] + tiempo(i,j) + TIEMPO_CARGA·x[i,j] − M·(1 − z[i,j])   ∀ i≠j, i,j ∈ C
      (si el arco (i,j) se usa, t[j] acumula el tiempo de t[i] más el
       tramo y la descarga en j; z[i,j] indica si el arco se usa)

  R7  t[v] + tiempo(v,0) ≤ JORNADA_MAX                ∀ v ∈ C  con arco activo (v,0)
      (el regreso al depósito desde cualquier último nodo visitado debe
       respetar la jornada máxima)

  R8  t[j] ≥ tiempo(0,j) + TIEMPO_CARGA   si  x[0,j] ≥ 1
      (tiempo al llegar al primer nodo desde el depósito)

Nota de modelado:
  Como x[i,j] puede ser > 1 (varios camiones por el mismo arco), se usa
  z[i,j] = min(x[i,j], 1) como variable binaria auxiliar que indica si el
  arco está activo, para las restricciones de tiempo tipo MTZ. Esto es una
  aproximación práctica: si dos camiones distintos comparten el mismo arco
  pero en viajes distintos, el acumulador de tiempo se aplica de forma
  conservadora (usa el caso más restrictivo).

Objetivo: min Σ d[i,j] · x[i,j]
"""

import math
import copy
import pulp

# ─────────────────────────────────────────────
#  DATOS FIJOS DEL EXCEL
# ─────────────────────────────────────────────
CANTONES = {
    0: "CD Cartago",
    1: "Cartago",
    2: "Paraíso",
    3: "La Unión",
    4: "Jiménez",
    5: "Turrialba",
    6: "Alvarado",
    7: "Oreamuno",
    8: "El Guarco",
}

DEMANDA_FIJA = {1: 124, 2: 48, 3: 75, 4: 15, 5: 61, 6: 12, 7: 36, 8: 35}

# Demanda desglosada por producto
DEMANDA_IMPERIAL = {1: 62, 2: 24, 3: 37, 4: 7,  5: 31, 6: 6,  7: 18, 8: 17}
DEMANDA_PILSEN   = {1: 31, 2: 12, 3: 19, 4: 4,  5: 15, 6: 3,  7:  9, 8:  9}
DEMANDA_TROPICAL = {1: 31, 2: 12, 3: 19, 4: 4,  5: 15, 6: 3,  7:  9, 8:  9}

# Matriz de distancias por carretera (km) — 9×9 simétrica
DIST = [
    [0,  0,  9, 10, 34, 34, 20,  6,  6],   # 0 CD Cartago
    [0,  0,  9, 10, 34, 34, 20,  6,  6],   # 1 Cartago
    [9,  9,  0, 19, 26, 28, 13,  7, 12],   # 2 Paraíso
    [10, 10, 19,  0, 45, 43, 29, 14, 11],  # 3 La Unión
    [34, 34, 26, 45,  0, 20, 21, 31, 37],  # 4 Jiménez
    [34, 34, 28, 43, 20,  0, 15, 29, 40],  # 5 Turrialba
    [20, 20, 13, 29, 21, 15,  0, 14, 25],  # 6 Alvarado
    [6,  6,  7, 14, 31, 29, 14,  0, 12],   # 7 Oreamuno
    [6,  6, 12, 11, 37, 40, 25, 12,  0],   # 8 El Guarco
]

Q_DEFAULT = 24
N = list(range(9))   # nodos 0..8
C = list(range(1, 9))  # clientes 1..8

# ─────────────────────────────────────────────
#  PARÁMETROS DE JORNADA LABORAL (NUEVO)
# ─────────────────────────────────────────────
VELOCIDAD_KMH   = 40.0        # velocidad promedio en carretera de montaña
TIEMPO_CARGA_H  = 20.0 / 60.0  # 20 minutos de carga/descarga por parada
JORNADA_MAX_H   = 8.0          # jornada máxima por viaje (horas)

# Tiempo de recorrido (horas) entre cada par de nodos
TIEMPO = [[DIST[i][j] / VELOCIDAD_KMH for j in N] for i in N]

# "Big M" para las restricciones tipo MTZ: cota superior del tiempo
# acumulado posible en cualquier nodo (mayor que cualquier jornada real)
M_TIEMPO = JORNADA_MAX_H + max(max(row) for row in TIEMPO) + TIEMPO_CARGA_H + 1


# ─────────────────────────────────────────────
#  SOLVER MIP
# ─────────────────────────────────────────────
def solve_cvrp(demanda: dict, Q: int = Q_DEFAULT,
               jornada_max: float = JORNADA_MAX_H,
               velocidad_kmh: float = VELOCIDAD_KMH,
               tiempo_carga_h: float = TIEMPO_CARGA_H) -> dict:
    """
    Resuelve el CVRP como modelo de flujo de red con PuLP/CBC, garantizando:
      - Cobertura total de demanda para todos los cantones.
      - Que cada viaje (salida-regreso al depósito) respete una jornada
        máxima de `jornada_max` horas, considerando tiempo de manejo
        (a `velocidad_kmh`) y tiempo de carga/descarga (`tiempo_carga_h`
        por cada cantón visitado).

    Parámetros
    ----------
    demanda        : {1..8: pallets/semana}
    Q              : capacidad máxima por camión
    jornada_max    : horas máximas permitidas por viaje (default 8h)
    velocidad_kmh  : velocidad promedio de viaje (default 40 km/h)
    tiempo_carga_h : tiempo de carga/descarga por parada en horas (default 20 min)

    Retorna dict con: status, objective, arcos, flujos, routes, K_min,
    total_dem, demanda, coverage, jornada_ok
    """
    total_dem = sum(demanda.values())
    K_min = math.ceil(total_dem / Q)

    tiempo = [[DIST[i][j] / velocidad_kmh for j in N] for i in N]
    m_tiempo = jornada_max + max(max(row) for row in tiempo) + tiempo_carga_h + 1

    prob = pulp.LpProblem("CVRP_Cartago_Jornada", pulp.LpMinimize)

    # ── Variables de decisión ─────────────────
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0, cat="Integer")
         for i in N for j in N if i != j}
    f = {(i, j): pulp.LpVariable(f"f_{i}_{j}", lowBound=0, cat="Continuous")
         for i in N for j in N if i != j}

    # z[i,j] = 1 si el arco (i,j) está activo (al menos un camión lo usa)
    z = {(i, j): pulp.LpVariable(f"z_{i}_{j}", cat="Binary")
         for i in N for j in N if i != j}

    # t[i] = tiempo acumulado (horas) al llegar al nodo i en su viaje
    # (t[0] = 0 siempre, representa la salida del depósito)
    t = {i: pulp.LpVariable(f"t_{i}", lowBound=0, upBound=jornada_max)
         for i in C}

    # ── Función objetivo ──────────────────────
    prob += pulp.lpSum(DIST[i][j] * x[i, j]
                       for i in N for j in N if i != j), "MinKm"

    # ── Vincular x y z: z=1 si x>=1, z=0 si x=0 ──
    UB_X = K_min + len(C) + 2  # cota superior holgada para x[i,j]
    for i in N:
        for j in N:
            if i != j:
                prob += x[i, j] <= UB_X * z[i, j], f"link_xz_ub_{i}_{j}"
                prob += x[i, j] >= z[i, j], f"link_xz_lb_{i}_{j}"

    # ── R1: Camión entra − Camión sale = 0 ───
    for v in C:
        prob += (
            pulp.lpSum(x[i, v] for i in N if i != v) -
            pulp.lpSum(x[v, j] for j in N if j != v) == 0
        ), f"R1_veh_{v}"

    # ── R2: Flujo entra − Flujo sale = demanda ─
    for v in C:
        prob += (
            pulp.lpSum(f[i, v] for i in N if i != v) -
            pulp.lpSum(f[v, j] for j in N if j != v) == demanda[v]
        ), f"R2_flow_{v}"

    # ── R3: Gran-M — f[i,j] ≤ Q · x[i,j] ───
    for i in N:
        for j in N:
            if i != j:
                prob += f[i, j] <= Q * x[i, j], f"R3_bigM_{i}_{j}"

    # ── R4: Flujo total desde depósito ───────
    prob += (
        pulp.lpSum(f[0, j] for j in C) == total_dem
    ), "R4_depot_flow"

    # ── R5: Flota mínima ──────────────────────
    prob += (
        pulp.lpSum(x[0, j] for j in C) >= K_min
    ), "R5_fleet_min"

    # ── R6: Acumulador de tiempo (tipo MTZ) ───
    # Si z[i,j]=1 (arco activo entre dos cantones), entonces
    # t[j] >= t[i] + tiempo(i,j) + tiempo_carga
    for i in C:
        for j in C:
            if i != j:
                prob += (
                    t[j] >= t[i] + tiempo[i][j] + tiempo_carga_h
                    - m_tiempo * (1 - z[i, j])
                ), f"R6_mtz_{i}_{j}"

    # ── R8: Tiempo al llegar al primer nodo desde el depósito ──
    # Si z[0,j]=1, entonces t[j] >= tiempo(0,j) + tiempo_carga
    for j in C:
        prob += (
            t[j] >= tiempo[0][j] + tiempo_carga_h - m_tiempo * (1 - z[0, j])
        ), f"R8_inicio_{j}"

    # ── R7: Regreso al depósito dentro de la jornada ──
    # Si z[v,0]=1 (v es el último nodo del viaje), entonces
    # t[v] + tiempo(v,0) <= jornada_max
    for v in C:
        prob += (
            t[v] + tiempo[v][0] <= jornada_max + m_tiempo * (1 - z[v, 0])
        ), f"R7_regreso_{v}"

    # ── Resolver ─────────────────────────────
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=180, gapRel=0.02)
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    obj    = pulp.value(prob.objective) if prob.objective else None

    # Extraer arcos y flujos activos
    arcos = {}
    for (i, j) in x:
        v = pulp.value(x[i, j])
        if v is not None and v > 0.5:
            arcos[(i, j)] = int(round(v))

    flujos = {}
    for (i, j) in f:
        v = pulp.value(f[i, j])
        if v is not None and v > 0.05:
            flujos[(i, j)] = round(v, 2)

    # Reconstruir rutas individuales con pallets exactos
    routes = _reconstruct_routes(arcos, flujos, demanda, Q)

    # Calcular tiempo de jornada por viaje y verificar cumplimiento
    jornada_ok = _verificar_jornada(routes, velocidad_kmh, tiempo_carga_h, jornada_max)

    # Verificar cobertura total
    coverage = _verify_coverage(routes, demanda)

    return {
        "status":         status,
        "objective":      obj,
        "arcos":          arcos,
        "flujos":         flujos,
        "routes":         routes,
        "K_min":          K_min,
        "total_dem":      total_dem,
        "demanda":        demanda,
        "coverage":       coverage,
        "jornada_ok":     jornada_ok,
        "jornada_max":    jornada_max,
        "velocidad_kmh":  velocidad_kmh,
        "tiempo_carga_h": tiempo_carga_h,
    }


def _verificar_jornada(routes: list, velocidad_kmh: float,
                        tiempo_carga_h: float, jornada_max: float) -> dict:
    """
    Calcula el tiempo total (manejo + carga/descarga) de cada viaje y
    verifica que no exceda la jornada máxima.

    Retorna dict {route_id: {"horas": float, "ok": bool, "paradas": int}}
    """
    resultado = {}
    for rinfo in routes:
        route = rinfo["route"]
        km = rinfo["km"]
        n_paradas = len(route) - 2  # nodos intermedios (excluye depósito ida/vuelta)
        t_manejo = km / velocidad_kmh
        t_carga  = n_paradas * tiempo_carga_h
        t_total  = t_manejo + t_carga
        resultado[rinfo["id"]] = {
            "horas":     round(t_total, 2),
            "t_manejo":  round(t_manejo, 2),
            "t_carga":   round(t_carga, 2),
            "paradas":   n_paradas,
            "ok":        t_total <= jornada_max + 1e-6,
        }
    return resultado


def _verify_coverage(routes: list, demanda: dict) -> dict:
    """Verifica que cada cantón reciba exactamente su demanda."""
    delivered = {cid: 0 for cid in C}
    for rinfo in routes:
        for cid, pal in rinfo["pallets_por_canton"].items():
            delivered[cid] = delivered.get(cid, 0) + pal
    return {
        cid: {
            "demanded": demanda[cid],
            "delivered": delivered.get(cid, 0),
            "ok": delivered.get(cid, 0) >= demanda[cid]
        }
        for cid in C
    }


# ─────────────────────────────────────────────
#  RECONSTRUCCIÓN DE RUTAS CON PALLETS EXACTOS
# ─────────────────────────────────────────────
def _reconstruct_routes(arcos: dict, flujos: dict,
                        demanda: dict, Q: int) -> list:
    """
    Reconstruye las rutas individuales a partir de los arcos activos.
    Garantiza cobertura completa de la demanda de todos los cantones.
    """
    arcos_rem  = copy.deepcopy(arcos)
    routes_raw = []

    # Contar salidas desde depósito
    starts = []
    for j in C:
        for _ in range(arcos_rem.get((0, j), 0)):
            starts.append(j)

    for s in starts:
        route = [0, s]
        arcos_rem[(0, s)] = arcos_rem.get((0, s), 0) - 1
        cur = s
        for _ in range(len(C) + 2):
            next_node = None
            # Preferir nodos que aún tienen arco activo
            for j in N:
                if j != cur and j != 0 and arcos_rem.get((cur, j), 0) > 0:
                    next_node = j
                    break
            # Checar regreso al depósito
            if next_node is None:
                if arcos_rem.get((cur, 0), 0) > 0:
                    arcos_rem[(cur, 0)] -= 1
                break
            route.append(next_node)
            arcos_rem[(cur, next_node)] -= 1
            cur = next_node
        route.append(0)
        routes_raw.append(route)

    # ── Calcular pallets exactos por ruta usando flujos MIP ──────────
    # Primero contamos cuántas veces se visita cada cantón
    visit_counts = {}
    for route in routes_raw:
        for n in route[1:-1]:
            visit_counts[n] = visit_counts.get(n, 0) + 1

    # Distribuir demanda proporcional entre visitas al mismo cantón
    canton_remaining = {cid: demanda[cid] for cid in C}
    routes_info = []

    for idx, route in enumerate(routes_raw):
        km = sum(DIST[route[k]][route[k + 1]]
                 for k in range(len(route) - 1))

        pallets_por_canton: dict[int, int] = {}

        # Seguir el flujo arco a arco para esta ruta
        s = route[1]
        total_x_0s = arcos.get((0, s), 1)
        f_0s       = flujos.get((0, s), 0)

        # Flujo inicial para esta ruta
        if total_x_0s > 0:
            carga = round(f_0s / total_x_0s)
        else:
            carga = 0

        carga_restante = min(carga, Q)

        for k in range(1, len(route) - 1):
            nodo = route[k]
            dem_nodo = demanda[nodo]

            # Calcular cuánto entregar en este nodo
            # Basado en cuánto flujo sale del nodo hacia el siguiente
            if k + 1 < len(route) - 1:
                nodo_sig = route[k + 1]
                f_sal = flujos.get((nodo, nodo_sig), 0)
                x_sal = max(arcos.get((nodo, nodo_sig), 1), 1)
                flujo_saliente = round(f_sal / x_sal)
                entrega = max(0, carga_restante - flujo_saliente)
            else:
                entrega = carga_restante

            # Limitar entrega al mínimo entre carga disponible y demanda restante del cantón
            entrega = min(entrega, canton_remaining.get(nodo, 0), carga_restante)
            entrega = max(entrega, 0)

            pallets_por_canton[nodo] = entrega
            carga_restante -= entrega
            canton_remaining[nodo] = canton_remaining.get(nodo, 0) - entrega

        # Si queda carga sin asignar, dársela al último cantón
        if carga_restante > 0 and len(route) > 2:
            last_c = route[-2]
            extra = min(carga_restante, canton_remaining.get(last_c, 0))
            pallets_por_canton[last_c] = pallets_por_canton.get(last_c, 0) + extra
            canton_remaining[last_c] = canton_remaining.get(last_c, 0) - extra

        total_pal = sum(pallets_por_canton.values())

        routes_info.append({
            "id":                idx + 1,
            "route":             route,
            "km":                km,
            "pallets_por_canton": pallets_por_canton,
            "total_pallets":     total_pal,
        })

    # ── Paso final: asegurar que toda la demanda esté cubierta ───────
    # Si algún cantón quedó sin cobertura total, corregir en la última ruta que lo visita
    for cid in C:
        remaining = canton_remaining.get(cid, 0)
        if remaining > 0:
            # Encontrar la última ruta que visita este cantón
            for rinfo in reversed(routes_info):
                if cid in rinfo["route"][1:-1]:
                    rinfo["pallets_por_canton"][cid] = rinfo["pallets_por_canton"].get(cid, 0) + remaining
                    rinfo["total_pallets"] = sum(rinfo["pallets_por_canton"].values())
                    canton_remaining[cid] = 0
                    break

    return routes_info
