"""view.py — Visualiseur de parties Catan (dearpygui).

Lance une interface graphique permettant de charger un fichier de sauvegarde
JSONL (produit par le moteur) et de rejouer la partie pas à pas :
  * le plateau hexagonal (tuiles, numéros, colonies/villes, routes, voleur) ;
  * les joueurs (points, cartes, chevaliers, route, bonus) ;
  * la main détaillée du joueur actif ;
  * le marché central (prix achat/vente) et l'historique des prix « façon bourse ».

Utilisation :
    python view.py                 # puis « Charger une sauvegarde »
    python view.py partie_00000.jsonl   # charge directement un fichier
"""

import bisect
import json
import math
import os
import sys

import dearpygui.dearpygui as dpg


# ======================================================================
#  Constantes d'affichage
# ======================================================================
RES = ["B", "W", "S", "O", "C"]
RES_NOM = {"B": "Bois", "W": "Blé", "S": "Mouton", "O": "Minerai", "C": "Argile",
           "X": "Désert"}
RES_COL = {
    "B": (56, 142, 60),    # bois  — vert
    "W": (242, 192, 55),   # blé   — jaune
    "S": (139, 195, 74),   # mouton— vert clair
    "O": (96, 125, 139),   # minerai — bleu-gris
    "C": (199, 91, 57),    # argile — terre cuite
    "X": (203, 188, 150),  # désert
}
JOUEUR_COL = [
    (231, 76, 60),    # rouge
    (52, 152, 219),   # bleu
    (236, 240, 241),  # blanc
    (230, 126, 34),   # orange
]
COUL_VOLEUR = (35, 35, 40)
COUL_ARETE = (90, 95, 110)
COUL_TEXTE = (230, 232, 238)

PHASES = {"PREP": "Préparation", "DES": "Lancer de dés",
          "JOUEUR": "Tour du joueur", "VOL": "Voleur"}

CANVAS = 540
PAD = 44

# État global du visualiseur
etat = {
    "meta": None, "steps": [], "resultat": None,
    "i": 0, "playing": False, "intervalle": 0.30,
    "pos": {}, "aretes": [], "tuiles": [],
    "scale": 1.0, "minx": 0, "maxy": 0, "offx": 0, "offy": 0,
    "n": 0, "noms": [], "types": [], "prix_max": 12.0,
    "charge": False,
}


# ======================================================================
#  Géométrie du plateau (réplique exacte de l'attribution d'ids du moteur)
# ======================================================================
def _coords_axiales(N=2):
    coords = []
    for q in range(-N, N + 1):
        for r in range(-N, N + 1):
            if -N <= -q - r <= N:
                coords.append((q, r))
    return coords


def _centre(q, r):
    return (math.sqrt(3) * (q + r / 2), 1.5 * r)


def _coin(c, i):
    a = math.radians(60 * i - 30)
    return (c[0] + math.cos(a), c[1] + math.sin(a))


def positions_sommets():
    """id de sommet -> position (unités plateau), identique au moteur."""
    cles, pos = {}, {}
    for (q, r) in _coords_axiales():
        c = _centre(q, r)
        for i in range(6):
            cx, cy = _coin(c, i)
            cle = (round(cx, 2), round(cy, 2))
            if cle not in cles:
                sid = len(cles)
                cles[cle] = sid
                pos[sid] = (cx, cy)
    return pos


# ======================================================================
#  Chargement d'une sauvegarde
# ======================================================================
def lire_sauvegarde(chemin):
    """Lit un fichier JSONL et renvoie (meta, steps, resultat)."""
    meta, steps, resultat = None, [], None
    with open(chemin, "r", encoding="utf-8") as fh:
        for ligne in fh:
            ligne = ligne.strip()
            if not ligne:
                continue
            o = json.loads(ligne)
            ty = o.get("type")
            if ty == "meta":
                meta = o
            elif ty == "step":
                steps.append(o)
            elif ty == "resultat":
                resultat = o
    return meta, steps, resultat


def _calculer_transform(pos):
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    spanx, spany = maxx - minx, maxy - miny
    scale = min((CANVAS - 2 * PAD) / spanx, (CANVAS - 2 * PAD) / spany)
    etat.update(scale=scale, minx=minx, maxy=maxy,
                offx=(CANVAS - spanx * scale) / 2,
                offy=(CANVAS - spany * scale) / 2)


def transform(bx, by):
    return (etat["offx"] + (bx - etat["minx"]) * etat["scale"],
            etat["offy"] + (etat["maxy"] - by) * etat["scale"])


# ======================================================================
#  Descriptions textuelles
# ======================================================================
def decrire(action):
    t = action.get("type")
    nom = lambda r: RES_NOM.get(r, r)
    return {
        "passer": "passe son tour",
        "construire_route": "construit une route",
        "construire_colonie": "construit une colonie",
        "construire_ville": "améliore une colonie en ville",
        "acheter_dev": "achète une carte développement",
        "jouer_chevalier": "joue une carte Chevalier",
        "prep_colonie": "place une colonie (préparation)",
        "prep_route": "place une route (préparation)",
    }.get(t) or {
        "marche_acheter": lambda: f"achète 1 {nom(action.get('res'))} au marché",
        "marche_vendre": lambda: f"vend 1 {nom(action.get('res'))} au marché",
        "echange": lambda: f"échange {action.get('taux')} {action.get('donne')} -> 1 {action.get('recoit')}",
        "voleur": lambda: f"déplace le voleur en {tuple(action.get('tuile', []))}",
    }.get(t, lambda: str(t))()


# ======================================================================
#  Construction de l'interface (statique)
# ======================================================================
def construire_ui():
    with dpg.window(tag="principal"):
        # --- Barre supérieure ---
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Charger une sauvegarde  ",
                           callback=lambda: dpg.show_item("dlg_fichier"))
            dpg.add_text("aucun fichier", tag="lbl_fichier", color=(150, 200, 255))
            dpg.add_text("", tag="lbl_partie", color=(180, 180, 190))
        dpg.add_separator()

        # --- Contrôles de lecture ---
        with dpg.group(horizontal=True):
            dpg.add_button(label="|<", callback=lambda: aller_a(0), width=40)
            dpg.add_button(label="<", callback=lambda: aller_a(etat["i"] - 1), width=40)
            dpg.add_button(label="Play", tag="btn_play", callback=basculer_play, width=70)
            dpg.add_button(label=">", callback=lambda: aller_a(etat["i"] + 1), width=40)
            dpg.add_button(label=">|", callback=lambda: aller_a(len(etat["steps"]) - 1), width=40)
            dpg.add_slider_int(tag="slider", default_value=0, min_value=0, max_value=0,
                               width=520, callback=lambda s, v: aller_a(v, depuis_slider=True))
            dpg.add_text("0 / 0", tag="lbl_compteur")
        with dpg.group(horizontal=True):
            dpg.add_text("Vitesse")
            dpg.add_slider_float(tag="vitesse", default_value=0.30, min_value=0.05,
                                 max_value=1.0, width=180, format="%.2f s/étape",
                                 callback=lambda s, v: etat.update(intervalle=v))
            dpg.add_text("", tag="lbl_info", color=COUL_TEXTE)
        dpg.add_separator()

        # --- Corps : plateau | panneaux ---
        with dpg.group(horizontal=True):
            with dpg.child_window(width=CANVAS + 24, height=560):
                dpg.add_drawlist(width=CANVAS, height=CANVAS, tag="board")
                dpg.add_text("", tag="lbl_resultat", color=(255, 215, 80))
            with dpg.child_window(width=652, height=560):
                dpg.add_text("JOUEURS", color=(150, 200, 255))
                dpg.add_child_window(tag="zone_joueurs", height=140, border=False)
                dpg.add_spacer(height=2)
                dpg.add_text("MAINS DES JOUEURS  (dernière main observée)",
                             color=(150, 200, 255))
                dpg.add_child_window(tag="zone_mains", height=170, border=False)
                dpg.add_spacer(height=2)
                dpg.add_text("MARCHÉ CENTRAL", color=(150, 200, 255))
                dpg.add_child_window(tag="zone_marche", height=180, border=False)

        # --- Historique des prix (pleine largeur, en bas) ---
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_text("HISTORIQUE DES PRIX", color=(150, 200, 255))
            dpg.add_radio_button(("par étape", "par tour"), horizontal=True,
                                 tag="mode_graphe", default_value="par étape",
                                 callback=_on_mode)
            dpg.add_text("(« par tour » regroupe les multiples transactions d'un même tour)",
                         color=(140, 140, 150))
        dpg.add_child_window(tag="zone_plot", height=250, border=False)

    # --- Dialogue de fichier ---
    import os
    chemin_defaut = os.path.abspath("sauvegardes") if os.path.isdir("sauvegardes") else os.getcwd()
    with dpg.file_dialog(directory_selector=False, show=False, tag="dlg_fichier",
                         width=720, height=420, callback=_on_fichier,
                         default_path=chemin_defaut):
        dpg.add_file_extension(".jsonl", color=(120, 200, 255))
        dpg.add_file_extension(".*")


def _on_fichier(sender, app_data):
    chemin = app_data.get("file_path_name")
    if chemin:
        charger(chemin)


# ======================================================================
#  Chargement + (re)construction des panneaux dépendant de la partie
# ======================================================================
def charger(chemin):
    meta, steps, resultat = lire_sauvegarde(chemin)
    if meta is None or not steps:
        dpg.set_value("lbl_fichier", "fichier invalide")
        return
    etat.update(meta=meta, steps=steps, resultat=resultat, i=0, playing=False,
                charge=True)
    ps = meta["plateau_statique"]
    etat["tuiles"] = ps["tuiles"]
    etat["aretes"] = ps["aretes"]
    etat["pos"] = positions_sommets()
    _calculer_transform(etat["pos"])
    etat["types"] = meta.get("types_joueurs", [])
    etat["noms"] = meta.get("joueurs", [])
    etat["n"] = len(etat["types"])
    etat["mode"] = "etape"

    # Ports (perception fixe) : id de sommet -> type de port ('X' = générique 3:1).
    etat["ports"] = {s["id"]: s["port"] for s in ps["sommets"] if s.get("port")}

    # Historiques des prix : par étape et par tour ; + main connue de chaque joueur.
    prix_max = 12.0
    histo_e = {r: [] for r in RES}
    histo_t = {r: [] for r in RES}
    xs_tour, tour_index = [], []
    hand_idx = {p: [] for p in range(etat["n"])}
    hand_val = {p: [] for p in range(etat["n"])}
    cur_tour, prev_p = -1, None
    for idx, s in enumerate(steps):
        p = s["joueur"]
        obs = s["observation"]
        if p != prev_p:                       # nouvelle « main » de joueur
            cur_tour += 1
            prev_p = p
            xs_tour.append(cur_tour)
            for r in RES:
                histo_t[r].append(None)
        tour_index.append(cur_tour)
        pm = obs.get("prix_marche", {})
        for r in RES:
            v = pm.get(r)
            histo_e[r].append(v)
            histo_t[r][cur_tour] = v           # garde le dernier prix du tour
            if v is not None:
                prix_max = max(prix_max, v)
        if p is not None and 0 <= p < etat["n"]:
            hand_idx[p].append(idx)
            hand_val[p].append({"ressources": obs.get("ressources", {}) or {},
                                "or": obs.get("or"),
                                "cartes_pv": obs.get("cartes_pv"),
                                "cartes_chevalier": obs.get("cartes_chevalier")})
    etat.update(prix_max=prix_max,
                xs_etape=list(range(len(steps))), histo_etape=histo_e,
                xs_tour=xs_tour, histo_tour=histo_t, tour_index=tour_index,
                hand_idx=hand_idx, hand_val=hand_val)

    _construire_table_joueurs()
    _construire_mains()
    _construire_marche()
    _construire_plot()
    dpg.set_value("mode_graphe", "par étape")

    dpg.set_value("lbl_fichier", os.path.basename(chemin))
    pid = meta.get("partie")
    dpg.set_value("lbl_partie", f"— partie {pid} — {etat['n']} joueurs — {len(steps)} étapes")
    dpg.configure_item("slider", max_value=len(steps) - 1)
    dpg.set_item_label("btn_play", "Play")

    if resultat is not None and resultat.get("gagnant") is not None:
        g = resultat["gagnant"]
        pts = resultat.get("points", [])
        dpg.set_value("lbl_resultat",
                      f"Vainqueur : {etat['noms'][g]}  ({pts[g] if g < len(pts) else '?'} pts)")
    else:
        dpg.set_value("lbl_resultat", "")
    afficher(0)


def coul_joueur(p):
    return JOUEUR_COL[p % len(JOUEUR_COL)] if p is not None and p >= 0 else (120, 120, 120)


def _construire_table_joueurs():
    dpg.delete_item("zone_joueurs", children_only=True)
    with dpg.table(parent="zone_joueurs", header_row=True, tag="tbl_j",
                   borders_innerH=True, borders_innerV=True, policy=dpg.mvTable_SizingStretchProp):
        for c in ("Joueur", "PV", "Cartes", "Chev.", "Route", "Bonus"):
            dpg.add_table_column(label=c)
        for p in range(etat["n"]):
            with dpg.table_row():
                dpg.add_text(etat["noms"][p], color=coul_joueur(p), tag=f"j{p}_nom")
                dpg.add_text("", tag=f"j{p}_pv")
                dpg.add_text("", tag=f"j{p}_cartes")
                dpg.add_text("", tag=f"j{p}_chev")
                dpg.add_text("", tag=f"j{p}_route")
                dpg.add_text("", tag=f"j{p}_bonus", color=(255, 215, 80))


def _construire_mains():
    dpg.delete_item("zone_mains", children_only=True)
    with dpg.group(horizontal=True, parent="zone_mains"):
        for p in range(etat["n"]):
            dpg.add_drawlist(width=156, height=150, tag=f"main_dl_{p}")


def main_connue(p, i):
    """Dernière main détaillée observée du joueur p à l'étape <= i (ou None)."""
    arr = etat["hand_idx"].get(p, [])
    k = bisect.bisect_right(arr, i) - 1
    return etat["hand_val"][p][k] if k >= 0 else None


def dessiner_main(p, i, actif):
    dl = f"main_dl_{p}"
    dpg.delete_item(dl, children_only=True)
    if p == actif:
        dpg.draw_rectangle([1, 1], [154, 148], parent=dl, color=(255, 215, 80),
                           thickness=2, rounding=4)
    dpg.draw_text([8, 6], etat["noms"][p], parent=dl, size=15, color=coul_joueur(p))
    hand = main_connue(p, i)
    if hand is None:
        dpg.draw_text([8, 40], "(pas encore joué)", parent=dl, size=13, color=(150, 150, 150))
        return
    ress = hand["ressources"] or {}
    for k, r in enumerate(RES):
        x = 18 + k * 28
        dpg.draw_circle([x, 40], 8, parent=dl, fill=RES_COL[r], color=(20, 20, 25), thickness=1)
        dpg.draw_text([x - 4, 54], str(ress.get(r, 0)), parent=dl, size=14, color=COUL_TEXTE)
    dpg.draw_text([8, 80], f"Or : {hand['or']}", parent=dl, size=14, color=(245, 210, 90))
    dpg.draw_text([8, 102], f"Chevaliers : {hand['cartes_chevalier']}", parent=dl,
                  size=13, color=COUL_TEXTE)
    dpg.draw_text([8, 122], f"PV cachés : {hand['cartes_pv']}", parent=dl,
                  size=13, color=COUL_TEXTE)


def _construire_marche():
    dpg.delete_item("zone_marche", children_only=True)
    with dpg.table(parent="zone_marche", header_row=True, tag="tbl_m",
                   borders_innerH=True, borders_innerV=True):
        for c in ("Ressource", "Achat", "Vente"):
            dpg.add_table_column(label=c)
        for r in RES:
            with dpg.table_row():
                dpg.add_text(RES_NOM[r], color=RES_COL[r])
                dpg.add_text("", tag=f"m{r}_achat")
                dpg.add_text("", tag=f"m{r}_vente")


def _theme_ligne(color):
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, 2.0, category=dpg.mvThemeCat_Plots)
    return t


def _construire_plot():
    dpg.delete_item("zone_plot", children_only=True)
    with dpg.plot(parent="zone_plot", height=230, width=-1):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="étape", tag="px")
        yax = dpg.add_plot_axis(dpg.mvYAxis, label="prix", tag="py")
        for r in RES:
            s = dpg.add_line_series([], [], label=r, parent=yax, tag=f"serie_{r}")
            dpg.bind_item_theme(s, _theme_ligne(RES_COL[r]))
        cur = dpg.add_line_series([0, 0], [0, etat["prix_max"]], label="curseur",
                                  parent=yax, tag="serie_curseur")
        dpg.bind_item_theme(cur, _theme_ligne((255, 255, 255)))
    maj_graphe()


def maj_graphe():
    """Met à jour les séries du graphique selon le mode (étape / tour)."""
    if etat.get("mode") == "tour":
        xs, histo, label = etat["xs_tour"], etat["histo_tour"], "tour"
    else:
        xs, histo, label = etat["xs_etape"], etat["histo_etape"], "étape"
    for r in RES:
        dpg.set_value(f"serie_{r}", [xs, [v if v is not None else 0 for v in histo[r]]])
    dpg.configure_item("px", label=label)
    dpg.set_axis_limits("px", 0, max(1, xs[-1] if xs else 1))
    dpg.set_axis_limits("py", 0, etat["prix_max"] + 1)


def _on_mode(sender, value):
    etat["mode"] = "tour" if value.startswith("par tour") else "etape"
    if etat["charge"]:
        maj_graphe()
        afficher(etat["i"])


# ======================================================================
#  Affichage d'une étape
# ======================================================================
def aller_a(i, depuis_slider=False):
    if not etat["charge"]:
        return
    i = max(0, min(i, len(etat["steps"]) - 1))
    etat["i"] = i
    if not depuis_slider:
        dpg.set_value("slider", i)
    afficher(i)


def basculer_play():
    if not etat["charge"]:
        return
    etat["playing"] = not etat["playing"]
    dpg.set_item_label("btn_play", "Pause" if etat["playing"] else "Play")


def afficher(i):
    if not etat["charge"]:
        return
    s = etat["steps"][i]
    obs = s["observation"]
    actif = s["joueur"]

    # --- Bandeau d'info ---
    de = s.get("de")
    phase = PHASES.get(s.get("phase"), s.get("phase"))
    nom_actif = etat["noms"][actif] if actif is not None and actif < len(etat["noms"]) else "?"
    info = f"Phase : {phase}    |    Actif : {nom_actif}"
    if de:
        info += f"    |    Dé : {de}"
    info += f"    |    Action : {decrire(s.get('action', {}))}"
    dpg.set_value("lbl_info", info)
    dpg.set_value("lbl_compteur", f"{i + 1} / {len(etat['steps'])}   (t={s['t']})")

    # --- Joueurs ---
    pv = obs.get("pv_publics", [])
    radv = obs.get("ressources_adversaires", [])
    chev = obs.get("chevaliers_joues", [])
    route = obs.get("longueur_routes", [])
    armee = obs.get("plus_grande_armee", -1)
    rlongue = obs.get("route_la_plus_longue", -1)
    for p in range(etat["n"]):
        marque = "> " if p == actif else "   "
        dpg.set_value(f"j{p}_nom", marque + etat["noms"][p])
        dpg.set_value(f"j{p}_pv", str(pv[p]) if p < len(pv) else "?")
        dpg.set_value(f"j{p}_cartes", str(radv[p]) if p < len(radv) else "?")
        dpg.set_value(f"j{p}_chev", str(chev[p]) if p < len(chev) else "?")
        dpg.set_value(f"j{p}_route", str(route[p]) if p < len(route) else "?")
        bonus = []
        if armee == p:
            bonus.append("Armée")
        if rlongue == p:
            bonus.append("Route")
        dpg.set_value(f"j{p}_bonus", " + ".join(bonus))

    # --- Mains des joueurs (dernière observée) ---
    for p in range(etat["n"]):
        dessiner_main(p, i, actif)

    # --- Marché ---
    pm = obs.get("prix_marche", {})
    for r in RES:
        prix = pm.get(r, 0)
        dpg.set_value(f"m{r}_achat", str(prix))
        dpg.set_value(f"m{r}_vente", str(max(0, prix - 1)))

    # --- Curseur du graphique (position selon le mode) ---
    xcur = etat["tour_index"][i] if etat.get("mode") == "tour" else i
    dpg.set_value("serie_curseur", [[xcur, xcur], [0, etat["prix_max"] + 1]])

    # --- Plateau ---
    dessiner(obs)


def dessiner(obs):
    dpg.delete_item("board", children_only=True)
    b = "board"

    # Tuiles + jetons
    for t in etat["tuiles"]:
        q, r, res, num = t["q"], t["r"], t["res"], t["num"]
        coins = [transform(*_coin(_centre(q, r), i)) for i in range(6)]
        coins = [[x, y] for (x, y) in coins]
        dpg.draw_polygon(coins, parent=b, color=(25, 27, 32),
                         fill=RES_COL.get(res, (120, 120, 120)), thickness=2)
        cx, cy = transform(*_centre(q, r))
        if num:
            rouge = num in (6, 8)
            dpg.draw_circle([cx, cy], 15, parent=b, fill=(245, 240, 230), color=(40, 40, 40))
            col = (200, 40, 40) if rouge else (40, 40, 40)
            dpg.draw_text([cx - (9 if num >= 10 else 5), cy - 9], str(num),
                          parent=b, size=18, color=col)
        else:
            dpg.draw_text([cx - 18, cy - 8], RES_NOM.get(res, ""), parent=b,
                          size=14, color=(60, 55, 45))

    # Arêtes (réseau de routes, en gris)
    pos = etat["pos"]
    for (a, c) in etat["aretes"]:
        if a in pos and c in pos:
            dpg.draw_line(list(transform(*pos[a])), list(transform(*pos[c])),
                          parent=b, color=COUL_ARETE, thickness=2)

    # Ports (perception fixe) : petit rond décalé vers l'extérieur du plateau.
    ccx, ccy = transform(0, 0)
    for sid, port in etat.get("ports", {}).items():
        if sid not in pos:
            continue
        vx, vy = transform(*pos[sid])
        dx, dy = vx - ccx, vy - ccy
        d = math.hypot(dx, dy) or 1.0
        ox, oy = vx + dx / d * 14, vy + dy / d * 14
        coul = (255, 255, 255) if port == "X" else RES_COL.get(port, (200, 200, 200))
        dpg.draw_line([vx, vy], [ox, oy], parent=b, color=(70, 75, 90), thickness=2)
        dpg.draw_circle([ox, oy], 6, parent=b, fill=coul, color=(20, 20, 25), thickness=2)

    # Routes construites
    for (a, c, prop) in obs.get("graphe", {}).get("aretes", []):
        if a in pos and c in pos:
            p1, p2 = list(transform(*pos[a])), list(transform(*pos[c]))
            dpg.draw_line(p1, p2, parent=b, color=(20, 20, 25), thickness=8)
            dpg.draw_line(p1, p2, parent=b, color=coul_joueur(prop), thickness=5)

    # Voleur
    vq, vr = obs.get("voleur", [0, 0])
    vx, vy = transform(*_centre(vq, vr))
    dpg.draw_circle([vx, vy + 22], 11, parent=b, fill=COUL_VOLEUR, color=(220, 220, 220),
                    thickness=2)

    # Colonies / villes
    for sid, info in obs.get("graphe", {}).get("sommets", {}).items():
        sid = int(sid)
        if sid not in pos:
            continue
        x, y = transform(*pos[sid])
        col = coul_joueur(info.get("joueur"))
        if info.get("ville"):
            dpg.draw_circle([x, y], 9, parent=b, fill=col, color=(20, 20, 25), thickness=2)
            dpg.draw_circle([x, y], 4, parent=b, fill=(20, 20, 25))
        else:
            d = 7
            dpg.draw_polygon([[x - d, y - d], [x + d, y - d], [x + d, y + d], [x - d, y + d]],
                             parent=b, fill=col, color=(20, 20, 25), thickness=2)


# ======================================================================
#  Thème
# ======================================================================
def appliquer_theme():
    with dpg.theme() as th:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (28, 30, 36))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (34, 37, 44))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (45, 49, 58))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (58, 90, 130))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (74, 114, 165))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (58, 90, 130))
            dpg.add_theme_color(dpg.mvThemeCol_Text, COUL_TEXTE)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
    dpg.bind_theme(th)


# ======================================================================
#  Point d'entrée
# ======================================================================
def main():
    import time
    dpg.create_context()
    construire_ui()
    appliquer_theme()
    dpg.set_global_font_scale(1.15)
    dpg.create_viewport(title="Catan — Visualiseur de parties", width=1240, height=980)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("principal", True)

    if len(sys.argv) > 1:
        charger(sys.argv[1])

    dernier = time.perf_counter()
    while dpg.is_dearpygui_running():
        if etat["playing"] and etat["charge"]:
            now = time.perf_counter()
            if now - dernier >= etat["intervalle"]:
                dernier = now
                if etat["i"] + 1 >= len(etat["steps"]):
                    etat["playing"] = False
                    dpg.set_item_label("btn_play", "Play")
                else:
                    aller_a(etat["i"] + 1)
        dpg.render_dearpygui_frame()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
