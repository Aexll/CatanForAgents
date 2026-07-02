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
import glob
import json
import math
import os
import random
import sys

import dearpygui.dearpygui as dpg

import Constantes as C
from moteur import Moteur, Plateau
from joueur import creer_joueur, TYPES_JOUEURS


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

# Métriques tracées par joueur (clé, titre).
METRIQUES = [
    ("pv", "Points de victoire publics"),
    ("route", "Route la plus longue"),
    ("chev", "Chevaliers joués"),
    ("or", "Or"),
    ("ress", "Ressources (total)"),
]

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
            dpg.add_button(label="  Expérimentation  ", callback=_exp_ouvrir)
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

        # --- Courbes d'évolution (pleine largeur, en bas, en onglets) ---
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_text("COURBES D'ÉVOLUTION", color=(150, 200, 255))
            dpg.add_text("    Axe X :")
            dpg.add_radio_button(("par étape", "par tour"), horizontal=True,
                                 tag="mode_graphe", default_value="par étape",
                                 callback=_on_mode)
            dpg.add_text("(« par tour » regroupe les transactions d'un même tour)",
                         color=(140, 140, 150))
        with dpg.tab_bar(tag="onglets_courbes"):
            with dpg.tab(label="  Points / Route / Chevaliers  "):
                dpg.add_child_window(tag="zone_pts", height=270, border=False)
            with dpg.tab(label="  Or / Ressources  "):
                dpg.add_child_window(tag="zone_or", height=270, border=False)
            with dpg.tab(label="  Prix du marché  "):
                dpg.add_child_window(tag="zone_prix", height=270, border=False)

    # --- Dialogue de fichier ---
    import os
    chemin_defaut = os.path.abspath("sauvegardes") if os.path.isdir("sauvegardes") else os.getcwd()
    with dpg.file_dialog(directory_selector=False, show=False, tag="dlg_fichier",
                         width=720, height=420, callback=_on_fichier,
                         default_path=chemin_defaut):
        dpg.add_file_extension(".jsonl", color=(120, 200, 255))
        dpg.add_file_extension(".*")

    # --- Fenêtre d'expérimentation (cachée au départ) ---
    construire_exp_ui()
    with dpg.handler_registry():
        dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Left, callback=_exp_clic)


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

    # Précalcul (un seul passage) : prix + trajectoires par joueur, par étape ET
    # par tour ; main connue de chaque joueur.
    n = etat["n"]
    prix_max = 12.0
    histo_e = {r: [] for r in RES}
    histo_t = {r: [] for r in RES}
    traj_e = {cle: [[] for _ in range(n)] for cle, _ in METRIQUES}
    traj_t = {cle: [[] for _ in range(n)] for cle, _ in METRIQUES}
    or_courant = [None] * n                   # « or » : seul l'actif est connu
    xs_tour, tour_index = [], []
    hand_idx = {p: [] for p in range(n)}
    hand_val = {p: [] for p in range(n)}
    cur_tour, prev_p = -1, None
    for idx, s in enumerate(steps):
        p = s["joueur"]
        obs = s["observation"]
        nouveau_tour = p != prev_p
        if nouveau_tour:
            cur_tour += 1
            prev_p = p
            xs_tour.append(cur_tour)
            for r in RES:
                histo_t[r].append(None)
            for cle, _ in METRIQUES:
                for q in range(n):
                    traj_t[cle][q].append(None)
        tour_index.append(cur_tour)
        if obs.get("or") is not None and p is not None and 0 <= p < n:
            or_courant[p] = obs["or"]
        valeurs = {
            "pv":   obs.get("pv_publics") or [None] * n,
            "route": obs.get("longueur_routes") or [None] * n,
            "chev": obs.get("chevaliers_joues") or [None] * n,
            "ress": obs.get("ressources_adversaires") or [None] * n,
            "or":   list(or_courant),
        }
        pm = obs.get("prix_marche", {})
        for r in RES:
            v = pm.get(r)
            histo_e[r].append(v)
            histo_t[r][cur_tour] = v
            if v is not None:
                prix_max = max(prix_max, v)
        for cle, _ in METRIQUES:
            for q in range(n):
                val = valeurs[cle][q]
                traj_e[cle][q].append(val)
                traj_t[cle][q][cur_tour] = val
        if p is not None and 0 <= p < n:
            hand_idx[p].append(idx)
            hand_val[p].append({"ressources": obs.get("ressources", {}) or {},
                                "or": obs.get("or"),
                                "cartes_pv": obs.get("cartes_pv"),
                                "cartes_chevalier": obs.get("cartes_chevalier")})

    # Bornes hautes des axes Y (pour les courbes et le curseur).
    def _ymax(cle, defaut):
        vals = [v for q in range(n) for v in traj_e[cle][q] if v is not None]
        return (max(vals) if vals else defaut) + (2 if cle in ("or", "ress") else 1)
    ymax = {cle: _ymax(cle, 1) for cle, _ in METRIQUES}

    etat.update(prix_max=prix_max,
                xs_etape=list(range(len(steps))), histo_etape=histo_e,
                xs_tour=xs_tour, histo_tour=histo_t, tour_index=tour_index,
                traj_etape=traj_e, traj_tour=traj_t, ymax=ymax,
                hand_idx=hand_idx, hand_val=hand_val)

    _construire_table_joueurs()
    _construire_mains()
    _construire_marche()
    _construire_plots()
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


def _theme_serie(color, weight=2.0):
    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):  # s'applique aux line & inf_line series
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LineWeight, weight,
                                category=dpg.mvThemeCat_Plots)
    return t


def _plot_metrique(cle, titre, ylabel=""):
    """Crée un graphique (une courbe par joueur) pour une métrique."""
    with dpg.plot(label=titre, height=-1, width=-1, no_mouse_pos=False):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, tag=f"ax_{cle}_x")
        yax = dpg.add_plot_axis(dpg.mvYAxis, label=ylabel, tag=f"ax_{cle}_y")
        for p in range(etat["n"]):
            s = dpg.add_line_series([], [], label=etat["noms"][p], parent=yax,
                                    tag=f"s_{cle}_{p}")
            dpg.bind_item_theme(s, _theme_serie(coul_joueur(p)))
        cur = dpg.add_inf_line_series([0], parent=yax, tag=f"cur_{cle}")
        dpg.bind_item_theme(cur, _theme_serie((235, 235, 235), 1.4))


def _construire_plots():
    # Onglet « Points / Route / Chevaliers » : 3 graphiques côte à côte.
    dpg.delete_item("zone_pts", children_only=True)
    with dpg.subplots(1, 3, width=-1, height=-1, parent="zone_pts", link_all_x=True):
        _plot_metrique("pv", "Points de victoire publics")
        _plot_metrique("route", "Route la plus longue")
        _plot_metrique("chev", "Chevaliers joués")

    # Onglet « Or / Ressources » : 2 graphiques côte à côte.
    dpg.delete_item("zone_or", children_only=True)
    with dpg.subplots(1, 2, width=-1, height=-1, parent="zone_or", link_all_x=True):
        _plot_metrique("or", "Or (dernier connu par joueur)")
        _plot_metrique("ress", "Ressources en main (total)")

    # Onglet « Prix du marché » : un graphique pleine largeur (une courbe par ressource).
    dpg.delete_item("zone_prix", children_only=True)
    with dpg.plot(parent="zone_prix", height=-1, width=-1):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, tag="ax_prix_x")
        yax = dpg.add_plot_axis(dpg.mvYAxis, label="prix", tag="ax_prix_y")
        for r in RES:
            s = dpg.add_line_series([], [], label=RES_NOM[r], parent=yax, tag=f"serie_{r}")
            dpg.bind_item_theme(s, _theme_serie(RES_COL[r]))
        cur = dpg.add_inf_line_series([0], parent=yax, tag="cur_prix")
        dpg.bind_item_theme(cur, _theme_serie((235, 235, 235), 1.4))

    maj_graphe()


def maj_graphe():
    """Met à jour toutes les courbes selon le mode (par étape / par tour)."""
    tour = etat.get("mode") == "tour"
    xs = etat["xs_tour"] if tour else etat["xs_etape"]
    label = "tour" if tour else "étape"
    xmax = max(1, xs[-1] if xs else 1)

    # Prix du marché
    histo = etat["histo_tour"] if tour else etat["histo_etape"]
    for r in RES:
        dpg.set_value(f"serie_{r}", [xs, [v if v is not None else 0 for v in histo[r]]])
    dpg.configure_item("ax_prix_x", label=label)
    dpg.set_axis_limits("ax_prix_x", 0, xmax)
    dpg.set_axis_limits("ax_prix_y", 0, etat["prix_max"] + 1)

    # Métriques par joueur
    traj = etat["traj_tour"] if tour else etat["traj_etape"]
    for cle, _titre in METRIQUES:
        for p in range(etat["n"]):
            ys = [v if v is not None else 0 for v in traj[cle][p]]
            dpg.set_value(f"s_{cle}_{p}", [xs, ys])
        dpg.configure_item(f"ax_{cle}_x", label=label)
        dpg.set_axis_limits(f"ax_{cle}_x", 0, xmax)
        dpg.set_axis_limits(f"ax_{cle}_y", 0, etat["ymax"][cle])


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

    # --- Curseurs des graphiques (position selon le mode) ---
    xcur = etat["tour_index"][i] if etat.get("mode") == "tour" else i
    dpg.set_value("cur_prix", [[xcur]])
    for cle, _titre in METRIQUES:
        dpg.set_value(f"cur_{cle}", [[xcur]])

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
#  MODE EXPÉRIMENTATION
#  ------------------------------------------------------------------
#  Construire librement un état de jeu (tuiles, numéros, bâtiments,
#  routes, ressources, marché...) puis interroger un agent :
#  « quelle serait ta prochaine action dans cette position ? ».
#  Sert à vérifier le comportement d'un agent dans des contextes fixés
#  (où pose-t-il ses routes / colonies, où déplace-t-il le voleur...).
# ======================================================================
EXP_DIR = "experiences"           # dossier des tests enregistrés
NUMS = [None, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12]
DECISIONS = ("Tour (action principale)", "Voleur", "Placement colonie initiale")
_OUTIL_LBL = {"colonie": "Colonie / Ville", "route": "Route",
              "voleur": "Voleur", "tuile": "Tuile"}
_OUTIL_KEY = {v: k for k, v in _OUTIL_LBL.items()}

GEO = {}   # géométrie de référence (identique quel que soit le plateau)
exp = {}   # scénario courant + état vivant


def _num_lbl(v):
    return "-" if v is None else str(v)


def _num_val(s):
    return None if s in ("", "-") else int(s)


def _safe(nom):
    return "".join(c if (c.isalnum() or c in "-_ ") else "_" for c in nom).strip()


def _exp_geo():
    """Initialise (une fois) la géométrie de référence."""
    if GEO:
        return
    pl = Plateau(random.Random(12345))
    GEO["aretes"] = list(pl.aretes)
    GEO["pos"] = positions_sommets()
    GEO["ports"] = {sid: t for sid, t in pl.ports.items()}
    GEO["tuiles"] = [{"q": q, "r": r, "res": t["res"], "num": t["num"]}
                     for (q, r), t in sorted(pl.tuiles.items())]
    des = next(((q, r) for (q, r), t in pl.tuiles.items() if t["res"] == C.DESERT), (0, 0))
    GEO["desert"] = list(des)
    _calculer_transform(GEO["pos"])


def _norm_etat(e):
    e = e or {}
    return {
        "ressources": {r: int((e.get("ressources") or {}).get(r, 0)) for r in C.RESSOURCES},
        "or": int(e.get("or", C.OR_INITIAL)),
        "chevalier": int(e.get("chevalier", 0)),
        "pv": int(e.get("pv", 0)),
        "kj": int(e.get("kj", 0)),
    }


def _exp_default():
    """Scénario vierge (plateau aléatoire, aucun bâtiment, mains vides)."""
    _exp_geo()
    prem = next((t for t in ("simple", "glouton", "axel") if t in TYPES_JOUEURS), "random")
    return {
        "moteur": None, "nom": "",
        "tuiles": [dict(t) for t in GEO["tuiles"]],
        "ports": dict(GEO["ports"]),
        "voleur": list(GEO["desert"]),
        "n": 4,
        "joueurs": [{"type": prem, "nom": "Agent"},
                    {"type": "random", "nom": "R2"},
                    {"type": "random", "nom": "R3"},
                    {"type": "random", "nom": "R4"}],
        "agent": 0, "pj": 0,
        "bat": {}, "rte": {},
        "etats": [_norm_etat(None) for _ in range(4)],
        "prix": {r: C.PRIX_INITIAL for r in C.RESSOURCES},
        "outil": "colonie", "tuile_sel": None, "decision": DECISIONS[0],
        "highlight": None, "resultat_txt": "", "actions": [], "action": None,
        "_snapshot": None,
    }


def _exp_tile(qr):
    for t in exp["tuiles"]:
        if (t["q"], t["r"]) == tuple(qr):
            return t
    return None


# ----------------------------------------------------------------------
#  Sérialisation disque
# ----------------------------------------------------------------------
def _exp_to_disk(sc):
    return {
        "nom": sc.get("nom", ""),
        "tuiles": sc["tuiles"],
        "ports": {str(k): v for k, v in sc["ports"].items()},
        "voleur": sc["voleur"], "n": sc["n"], "joueurs": sc["joueurs"],
        "agent": sc["agent"], "pj": sc["pj"],
        "bat": [{"sommet": sid, "joueur": b["joueur"], "ville": b["ville"]}
                for sid, b in sc["bat"].items()],
        "rte": [{"arete": [e[0], e[1]], "joueur": o} for e, o in sc["rte"].items()],
        "etats": sc["etats"], "prix": sc["prix"], "decision": sc["decision"],
    }


def _exp_from_disk(d):
    sc = _exp_default()
    sc["nom"] = d.get("nom", "")
    sc["tuiles"] = d.get("tuiles") or sc["tuiles"]
    if d.get("ports"):
        sc["ports"] = {int(k): v for k, v in d["ports"].items()}
    sc["voleur"] = d.get("voleur", sc["voleur"])
    sc["n"] = int(d.get("n", 4))
    js = d.get("joueurs") or sc["joueurs"]
    while len(js) < 4:
        js.append({"type": "random", "nom": f"J{len(js) + 1}"})
    sc["joueurs"] = js[:4]
    sc["agent"] = int(d.get("agent", 0))
    sc["pj"] = int(d.get("pj", 0))
    sc["bat"] = {int(b["sommet"]): {"joueur": int(b["joueur"]), "ville": bool(b["ville"])}
                 for b in d.get("bat", [])}
    sc["rte"] = {tuple(sorted(r["arete"])): int(r["joueur"]) for r in d.get("rte", [])}
    et = d.get("etats") or []
    sc["etats"] = [_norm_etat(et[p] if p < len(et) else None) for p in range(4)]
    sc["prix"] = {r: int((d.get("prix") or {}).get(r, C.PRIX_INITIAL)) for r in C.RESSOURCES}
    sc["decision"] = d.get("decision", DECISIONS[0])
    return sc


# ----------------------------------------------------------------------
#  Construction du moteur à partir d'un scénario + sondage de l'agent
# ----------------------------------------------------------------------
def _construire_moteur(sc):
    n = sc["n"]
    joueurs = [creer_joueur(sc["joueurs"][i]["type"], nom=sc["joueurs"][i]["nom"], seed=1234 + i)
               for i in range(n)]
    m = Moteur(joueurs, seed=0)
    # On garde la géométrie du plateau mais on remplace la composition.
    for t in sc["tuiles"]:
        m.plateau.tuiles[(t["q"], t["r"])] = {"res": t["res"], "num": t["num"]}
    m.plateau.ports = {int(k): v for k, v in sc["ports"].items()}
    # État dynamique remis à zéro
    ns = m.plateau.nb_sommets
    m.proprio_sommet = [-1] * ns
    m.ville_sommet = [False] * ns
    m.proprio_arete = {e: -1 for e in m.plateau.aretes}
    m.reseau = [set() for _ in range(n)]
    m.colonies_de = [set() for _ in range(n)]
    m.ports_de = [set() for _ in range(n)]
    m.nb_colonies = [0] * n
    m.nb_villes = [0] * n
    m._graphe_cache = None
    for sid, b in sc["bat"].items():
        p = b["joueur"]
        if p >= n:
            continue
        m._enregistrer_colonie(p, int(sid))
        if b["ville"]:
            m.ville_sommet[int(sid)] = True
            m.nb_villes[p] += 1
            m.nb_colonies[p] -= 1
            m.colonies_de[p].discard(int(sid))
    for e, p in sc["rte"].items():
        e = tuple(e)
        if p < n and e in m.proprio_arete:
            m.proprio_arete[e] = p
            m.reseau[p].update(e)
    for p in range(n):
        st = sc["etats"][p]
        m.ressources[p] = {r: int(st["ressources"].get(r, 0)) for r in C.RESSOURCES}
        m.cor[p] = int(st["or"])
        m.main_dev[p] = {C.DEV_CHEVALIER: int(st["chevalier"]), C.DEV_POINT: int(st["pv"])}
        m.chevaliers_joues[p] = int(st["kj"])
    m.prix = {r: int(sc["prix"].get(r, C.PRIX_INITIAL)) for r in C.RESSOURCES}
    m.voleur = list(sc["voleur"])
    m.proprio_armee = -1
    for p in range(n):
        m._maj_plus_grande_armee(p)
    m.proprio_route_longue = -1
    m.longueur_routes = [0] * n
    m._maj_route_longue()
    m.dev_joue_ce_tour = False
    m.phase = C.ETAT_JOUEUR
    ps = m.plateau.serialiser_statique()
    for i, j in enumerate(m.joueurs):
        j.nouvelle_partie(i, ps)
    return m


def _exp_probe(m, sc):
    """Renvoie (actions_legales, action choisie) pour la décision demandée."""
    p = sc["agent"]
    dec = sc["decision"]
    if dec == DECISIONS[1]:            # Voleur
        m.phase = C.ETAT_VOL
        actions = [{"type": "voleur", "tuile": [q, r]}
                   for (q, r) in m.plateau.tuiles if [q, r] != m.voleur]
    elif dec == DECISIONS[2]:          # Placement colonie initiale
        m.phase = C.ETAT_PREP
        actions = [{"type": "prep_colonie", "sommet": s}
                   for s in m._sommets_libres_distance()]
    else:                              # Tour (action principale)
        m.phase = C.ETAT_JOUEUR
        actions = m._actions_legales(p)
    if not actions:
        return [], None
    obs = m._observation(p)
    action = m.joueurs[p].decider(obs, list(actions))
    return actions, action


def _exp_highlight(action):
    if not action:
        return None
    t = action.get("type")
    if t in ("construire_route", "prep_route"):
        return ("route", tuple(sorted(action["arete"])))
    if t in ("construire_colonie", "construire_ville", "prep_colonie"):
        return ("sommet", action["sommet"])
    if t == "voleur":
        return ("tuile", tuple(action["tuile"]))
    return None


def _exp_appliquer_special(m, p, a):
    """Applique une décision hors phase principale (prep / voleur)."""
    t = a["type"]
    if t == "prep_colonie":
        m._enregistrer_colonie(p, a["sommet"])
        m._maj_route_longue()
    elif t == "prep_route":
        e = tuple(sorted(a["arete"]))
        m.proprio_arete[e] = p
        m.reseau[p].update(e)
        m._maj_route_longue([p])
    elif t == "voleur":
        m._deplacer_voleur(p, tuple(a["tuile"]))


def _exp_sync_from_moteur(m):
    """Recopie l'état vivant du moteur dans le scénario (après une action jouée)."""
    n = m.n
    exp["bat"] = {sid: {"joueur": m.proprio_sommet[sid], "ville": bool(m.ville_sommet[sid])}
                  for sid in range(m.plateau.nb_sommets) if m.proprio_sommet[sid] != -1}
    exp["rte"] = {e: o for e, o in m.proprio_arete.items() if o != -1}
    for p in range(n):
        exp["etats"][p]["ressources"] = {r: m.ressources[p][r] for r in C.RESSOURCES}
        exp["etats"][p]["or"] = m.cor[p]
        exp["etats"][p]["chevalier"] = m.main_dev[p][C.DEV_CHEVALIER]
        exp["etats"][p]["pv"] = m.main_dev[p][C.DEV_POINT]
        exp["etats"][p]["kj"] = m.chevaliers_joues[p]
    exp["prix"] = {r: m.prix[r] for r in C.RESSOURCES}
    exp["voleur"] = list(m.voleur)


# ----------------------------------------------------------------------
#  Interactions plateau (clic)
# ----------------------------------------------------------------------
def _exp_near_tile(lx, ly):
    best, bd = None, 1e18
    for t in exp["tuiles"]:
        cx, cy = transform(*_centre(t["q"], t["r"]))
        d = (cx - lx) ** 2 + (cy - ly) ** 2
        if d < bd:
            bd, best = d, t
    return best if bd <= (etat["scale"] * 0.95) ** 2 else None


def _exp_near_vertex(lx, ly):
    best, bd = None, 1e18
    for sid, (bx, by) in GEO["pos"].items():
        x, y = transform(bx, by)
        d = (x - lx) ** 2 + (y - ly) ** 2
        if d < bd:
            bd, best = d, sid
    return best if bd <= 15 ** 2 else None


def _exp_near_edge(lx, ly):
    best, bd = None, 1e18
    pos = GEO["pos"]
    for (a, c) in GEO["aretes"]:
        ax, ay = transform(*pos[a])
        cx, cy = transform(*pos[c])
        mx, my = (ax + cx) / 2, (ay + cy) / 2
        d = (mx - lx) ** 2 + (my - ly) ** 2
        if d < bd:
            bd, best = d, (a, c)
    return best if bd <= 13 ** 2 else None


def _exp_cycle_bat(sid):
    pj = exp["pj"]
    cur = exp["bat"].get(sid)
    if cur is None:
        exp["bat"][sid] = {"joueur": pj, "ville": False}
    elif cur["joueur"] == pj and not cur["ville"]:
        cur["ville"] = True
    elif cur["joueur"] == pj and cur["ville"]:
        del exp["bat"][sid]
    else:
        exp["bat"][sid] = {"joueur": pj, "ville": False}


def _exp_toggle_route(e):
    pj = exp["pj"]
    if exp["rte"].get(e) == pj:
        del exp["rte"][e]
    else:
        exp["rte"][e] = pj


def _exp_clic(sender, app_data):
    if not (dpg.does_item_exist("exp") and dpg.is_item_shown("exp")):
        return
    if not dpg.does_item_exist("exp_board"):
        return
    mx, my = dpg.get_mouse_pos(local=False)
    rx, ry = dpg.get_item_rect_min("exp_board")
    rw, rh = dpg.get_item_rect_size("exp_board")
    if not (rx <= mx <= rx + rw and ry <= my <= ry + rh):
        return
    lx, ly = mx - rx, my - ry
    outil = exp["outil"]
    if outil == "voleur":
        t = _exp_near_tile(lx, ly)
        if t:
            exp["voleur"] = [t["q"], t["r"]]
            _exp_dirty(); _exp_draw()
    elif outil == "tuile":
        t = _exp_near_tile(lx, ly)
        if t:
            exp["tuile_sel"] = (t["q"], t["r"])
            _exp_refresh_editeurs(); _exp_draw()
    elif outil == "route":
        e = _exp_near_edge(lx, ly)
        if e is not None:
            _exp_toggle_route(e)
            _exp_dirty(); _exp_draw()
    else:  # colonie / ville
        sid = _exp_near_vertex(lx, ly)
        if sid is not None:
            _exp_cycle_bat(sid)
            _exp_dirty(); _exp_draw()


# ----------------------------------------------------------------------
#  Dessin du plateau (depuis le scénario)
# ----------------------------------------------------------------------
def _exp_draw():
    b = "exp_board"
    if not dpg.does_item_exist(b):
        return
    dpg.delete_item(b, children_only=True)
    for t in exp["tuiles"]:
        q, r, res, num = t["q"], t["r"], t["res"], t["num"]
        coins = [list(transform(*_coin(_centre(q, r), i))) for i in range(6)]
        sel = exp["tuile_sel"] == (q, r)
        dpg.draw_polygon(coins, parent=b, thickness=(3 if sel else 2),
                         color=((250, 230, 120) if sel else (25, 27, 32)),
                         fill=RES_COL.get(res, (120, 120, 120)))
        cx, cy = transform(*_centre(q, r))
        if num:
            dpg.draw_circle([cx, cy], 15, parent=b, fill=(245, 240, 230), color=(40, 40, 40))
            col = (200, 40, 40) if num in (6, 8) else (40, 40, 40)
            dpg.draw_text([cx - (9 if num >= 10 else 5), cy - 9], str(num),
                          parent=b, size=18, color=col)
        else:
            dpg.draw_text([cx - 18, cy - 8], RES_NOM.get(res, ""), parent=b,
                          size=14, color=(60, 55, 45))
    pos = GEO["pos"]
    for (a, c) in GEO["aretes"]:
        dpg.draw_line(list(transform(*pos[a])), list(transform(*pos[c])),
                      parent=b, color=COUL_ARETE, thickness=2)
    ccx, ccy = transform(0, 0)
    for sid, port in exp["ports"].items():
        if sid not in pos:
            continue
        vx, vy = transform(*pos[sid])
        dx, dy = vx - ccx, vy - ccy
        d = math.hypot(dx, dy) or 1.0
        ox, oy = vx + dx / d * 14, vy + dy / d * 14
        coul = (255, 255, 255) if port == "X" else RES_COL.get(port, (200, 200, 200))
        dpg.draw_line([vx, vy], [ox, oy], parent=b, color=(70, 75, 90), thickness=2)
        dpg.draw_circle([ox, oy], 6, parent=b, fill=coul, color=(20, 20, 25), thickness=2)
    for (a, c), o in exp["rte"].items():
        if a in pos and c in pos:
            p1, p2 = list(transform(*pos[a])), list(transform(*pos[c]))
            dpg.draw_line(p1, p2, parent=b, color=(20, 20, 25), thickness=8)
            dpg.draw_line(p1, p2, parent=b, color=coul_joueur(o), thickness=5)
    vq, vr = exp["voleur"]
    vx, vy = transform(*_centre(vq, vr))
    dpg.draw_circle([vx, vy + 22], 11, parent=b, fill=COUL_VOLEUR, color=(220, 220, 220),
                    thickness=2)
    for sid, info in exp["bat"].items():
        if sid not in pos:
            continue
        x, y = transform(*pos[sid])
        col = coul_joueur(info["joueur"])
        if info["ville"]:
            dpg.draw_circle([x, y], 9, parent=b, fill=col, color=(20, 20, 25), thickness=2)
            dpg.draw_circle([x, y], 4, parent=b, fill=(20, 20, 25))
        else:
            dd = 7
            dpg.draw_polygon([[x - dd, y - dd], [x + dd, y - dd], [x + dd, y + dd],
                              [x - dd, y + dd]], parent=b, fill=col,
                             color=(20, 20, 25), thickness=2)
    hl = exp.get("highlight")
    if hl:
        kind, val = hl
        if kind == "route" and val[0] in pos and val[1] in pos:
            p1, p2 = list(transform(*pos[val[0]])), list(transform(*pos[val[1]]))
            dpg.draw_line(p1, p2, parent=b, color=(255, 235, 90), thickness=9)
            dpg.draw_line(p1, p2, parent=b, color=(255, 255, 255), thickness=3)
        elif kind == "sommet" and val in pos:
            x, y = transform(*pos[val])
            dpg.draw_circle([x, y], 14, parent=b, color=(255, 235, 90), thickness=3)
        elif kind == "tuile":
            x, y = transform(*_centre(*val))
            dpg.draw_circle([x, y], 26, parent=b, color=(255, 235, 90), thickness=3)


# ----------------------------------------------------------------------
#  Rafraîchissement de l'interface
# ----------------------------------------------------------------------
def _exp_refresh_liste():
    os.makedirs(EXP_DIR, exist_ok=True)
    noms = sorted(os.path.splitext(os.path.basename(f))[0]
                  for f in glob.glob(os.path.join(EXP_DIR, "*.json")))
    dpg.configure_item("exp_liste", items=noms)


def _exp_refresh_editeurs():
    p = exp["pj"]
    st = exp["etats"][p]
    for r in C.RESSOURCES:
        dpg.set_value(f"exp_res_{r}", st["ressources"].get(r, 0))
    dpg.set_value("exp_or", st["or"])
    dpg.set_value("exp_chev", st["chevalier"])
    dpg.set_value("exp_pv", st["pv"])
    dpg.set_value("exp_kj", st["kj"])
    ts = exp.get("tuile_sel")
    if ts and _exp_tile(ts):
        t = _exp_tile(ts)
        dpg.set_value("exp_tile_res", t["res"])
        dpg.set_value("exp_tile_num", _num_lbl(t["num"]))


def _exp_maj_resultat():
    if dpg.does_item_exist("exp_result"):
        dpg.set_value("exp_result", exp.get("resultat_txt", ""))
    if not dpg.does_item_exist("exp_actions_zone"):
        return
    dpg.delete_item("exp_actions_zone", children_only=True)
    chosen = exp.get("action")
    for a in exp.get("actions", []):
        est = (a == chosen)
        dpg.add_text(("  >>  " if est else "       ") + decrire(a),
                     parent="exp_actions_zone",
                     color=(255, 215, 80) if est else (200, 205, 215))


def _exp_refresh_ui():
    dpg.set_value("exp_nom", exp.get("nom", ""))
    dpg.set_value("exp_outil", _OUTIL_LBL[exp["outil"]])
    dpg.set_value("exp_n", str(exp["n"]))
    for p in range(4):
        dpg.configure_item(f"exp_jrow_{p}", show=(p < exp["n"]))
        dpg.set_value(f"exp_jtype_{p}", exp["joueurs"][p]["type"])
        dpg.set_value(f"exp_jnom_{p}", exp["joueurs"][p]["nom"])
    labels = [f"J{p + 1}" for p in range(exp["n"])]
    dpg.configure_item("exp_pj", items=labels)
    dpg.configure_item("exp_agent", items=labels)
    dpg.set_value("exp_pj", f"J{exp['pj'] + 1}")
    dpg.set_value("exp_agent", f"J{exp['agent'] + 1}")
    dpg.set_value("exp_decision", exp["decision"])
    for r in C.RESSOURCES:
        dpg.set_value(f"exp_prix_{r}", exp["prix"][r])
    _exp_refresh_editeurs()
    _exp_refresh_liste()
    _exp_maj_resultat()


def _exp_load_scenario(sc):
    exp.clear()
    exp.update(sc)
    exp["moteur"] = None
    _exp_refresh_ui()
    _exp_draw()


def _exp_dirty():
    """L'état a changé : le moteur vivant est invalidé, le résultat effacé."""
    exp["moteur"] = None
    exp["highlight"] = None
    exp["action"] = None
    exp["actions"] = []
    exp["resultat_txt"] = "(état modifié — relancez le test)"
    _exp_maj_resultat()


# ----------------------------------------------------------------------
#  Callbacks widgets
# ----------------------------------------------------------------------
def _exp_on_outil(sender, val):
    exp["outil"] = _OUTIL_KEY.get(val, "colonie")


def _exp_on_pj(sender, val):
    exp["pj"] = int(val[1:]) - 1
    _exp_refresh_editeurs()


def _exp_on_agent(sender, val):
    exp["agent"] = int(val[1:]) - 1
    _exp_dirty()


def _exp_on_decision(sender, val):
    exp["decision"] = val
    _exp_dirty()


def _exp_on_jtype(sender, val, user_data):
    exp["joueurs"][user_data]["type"] = val
    _exp_dirty()


def _exp_on_jnom(sender, val, user_data):
    exp["joueurs"][user_data]["nom"] = val


def _exp_on_stat(sender, val, user_data):
    key, sub = user_data
    p = exp["pj"]
    if key == "res":
        exp["etats"][p]["ressources"][sub] = max(0, int(val))
    else:
        exp["etats"][p][key] = max(0, int(val))
    _exp_dirty()


def _exp_on_prix(sender, val, user_data):
    exp["prix"][user_data[1]] = max(C.PRIX_MIN, int(val))
    _exp_dirty()


def _exp_on_tile_res(sender, val):
    ts = exp.get("tuile_sel")
    t = _exp_tile(ts) if ts else None
    if not t:
        return
    t["res"] = val
    if val == C.DESERT:
        t["num"] = None
        dpg.set_value("exp_tile_num", "-")
    elif t["num"] is None:
        t["num"] = 6
        dpg.set_value("exp_tile_num", "6")
    _exp_dirty(); _exp_draw()


def _exp_on_tile_num(sender, val):
    ts = exp.get("tuile_sel")
    t = _exp_tile(ts) if ts else None
    if not t:
        return
    t["num"] = _num_val(val)
    if t["num"] is not None and t["res"] == C.DESERT:
        t["res"] = "B"
        dpg.set_value("exp_tile_res", "B")
    _exp_dirty(); _exp_draw()


def _exp_on_n(sender, val):
    n = int(val)
    exp["n"] = n
    exp["bat"] = {sid: b for sid, b in exp["bat"].items() if b["joueur"] < n}
    exp["rte"] = {e: o for e, o in exp["rte"].items() if o < n}
    exp["pj"] = min(exp["pj"], n - 1)
    exp["agent"] = min(exp["agent"], n - 1)
    for p in range(4):
        dpg.configure_item(f"exp_jrow_{p}", show=(p < n))
    labels = [f"J{p + 1}" for p in range(n)]
    dpg.configure_item("exp_pj", items=labels)
    dpg.configure_item("exp_agent", items=labels)
    dpg.set_value("exp_pj", f"J{exp['pj'] + 1}")
    dpg.set_value("exp_agent", f"J{exp['agent'] + 1}")
    _exp_dirty(); _exp_refresh_editeurs(); _exp_draw()


def _exp_on_liste(sender, val):
    pass  # chargement via le bouton « Charger »


# ----------------------------------------------------------------------
#  Actions (tester / jouer / réinitialiser / fichiers)
# ----------------------------------------------------------------------
def _exp_tester():
    try:
        if exp.get("moteur") is None:
            exp["moteur"] = _construire_moteur(exp)
            exp["_snapshot"] = json.loads(json.dumps(_exp_to_disk(exp)))
        actions, action = _exp_probe(exp["moteur"], exp)
    except Exception as e:
        exp["moteur"] = None
        exp["highlight"] = None
        exp["actions"] = []
        exp["action"] = None
        exp["resultat_txt"] = f"Erreur : {e}"
        _exp_maj_resultat(); _exp_draw()
        return
    exp["actions"] = actions
    exp["action"] = action
    exp["highlight"] = _exp_highlight(action)
    j = exp["joueurs"][exp["agent"]]
    if action is None:
        exp["resultat_txt"] = "Aucune action légale dans ce contexte."
    else:
        exp["resultat_txt"] = f"{j['nom']} [{j['type']}]  ->  {decrire(action)}"
    _exp_maj_resultat(); _exp_draw()


def _exp_jouer():
    if exp.get("moteur") is None or exp.get("action") is None:
        _exp_tester()
        return
    m, a, p = exp["moteur"], exp["action"], exp["agent"]
    try:
        if a["type"] == "passer":
            exp["resultat_txt"] = "L'agent passe (fin de tour)."
            exp["highlight"] = None
            _exp_maj_resultat()
            return
        if a["type"] in ("prep_colonie", "prep_route", "voleur"):
            _exp_appliquer_special(m, p, a)
        else:
            m._appliquer_action(p, a)
    except Exception as e:
        exp["resultat_txt"] = f"Erreur à l'application : {e}"
        _exp_maj_resultat()
        return
    _exp_sync_from_moteur(m)
    _exp_refresh_editeurs()
    _exp_tester()  # re-sonde sur le moteur vivant (déjà à jour)


def _exp_reset():
    snap = exp.get("_snapshot")
    if snap:
        sc = _exp_from_disk(snap)
        sc["nom"] = exp.get("nom", "")
        _exp_load_scenario(sc)
        exp["resultat_txt"] = "État réinitialisé (avant les actions jouées)."
    else:
        exp["moteur"] = None
        exp["highlight"] = None
        exp["actions"] = []
        exp["action"] = None
        exp["resultat_txt"] = ""
        _exp_draw()
    _exp_maj_resultat()


def _exp_nouveau():
    _exp_load_scenario(_exp_default())


def _exp_sauver():
    nom = (dpg.get_value("exp_nom") or "").strip()
    if not nom:
        exp["resultat_txt"] = "Donnez un nom au test avant d'enregistrer."
        _exp_maj_resultat()
        return
    exp["nom"] = nom
    os.makedirs(EXP_DIR, exist_ok=True)
    with open(os.path.join(EXP_DIR, _safe(nom) + ".json"), "w", encoding="utf-8") as fh:
        json.dump(_exp_to_disk(exp), fh, ensure_ascii=False, indent=2)
    _exp_refresh_liste()
    exp["resultat_txt"] = f"Test « {nom} » enregistré."
    _exp_maj_resultat()


def _exp_charger_sel():
    nom = dpg.get_value("exp_liste")
    if not nom:
        return
    for cand in (_safe(nom), nom):
        path = os.path.join(EXP_DIR, cand + ".json")
        if os.path.exists(path):
            break
    else:
        exp["resultat_txt"] = "Fichier introuvable."
        _exp_maj_resultat()
        return
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:
        exp["resultat_txt"] = f"Chargement impossible : {e}"
        _exp_maj_resultat()
        return
    sc = _exp_from_disk(d)
    sc["nom"] = nom
    _exp_load_scenario(sc)
    exp["resultat_txt"] = f"Test « {nom} » chargé."
    _exp_maj_resultat()


def _exp_supprimer():
    nom = dpg.get_value("exp_liste")
    if not nom:
        return
    for cand in (_safe(nom), nom):
        path = os.path.join(EXP_DIR, cand + ".json")
        if os.path.exists(path):
            os.remove(path)
            break
    _exp_refresh_liste()


def _exp_ouvrir():
    _exp_geo()
    if not exp:
        exp.update(_exp_default())
    dpg.configure_item("principal", show=False)
    dpg.configure_item("exp", show=True)
    dpg.set_primary_window("exp", True)
    _exp_refresh_ui()
    _exp_draw()


def _exp_retour():
    dpg.configure_item("exp", show=False)
    dpg.configure_item("principal", show=True)
    dpg.set_primary_window("principal", True)


# ----------------------------------------------------------------------
#  Construction de la fenêtre d'expérimentation
# ----------------------------------------------------------------------
def construire_exp_ui():
    types = sorted(TYPES_JOUEURS)
    with dpg.window(tag="exp", show=False):
        with dpg.group(horizontal=True):
            dpg.add_button(label="  < Retour au visualiseur  ", callback=_exp_retour)
            dpg.add_text("MODE EXPÉRIMENTATION", color=(150, 200, 255))
            dpg.add_spacer(width=20)
            dpg.add_text("Test :")
            dpg.add_input_text(tag="exp_nom", hint="nom du test", width=200)
            dpg.add_button(label="Enregistrer", callback=_exp_sauver)
            dpg.add_button(label="Nouveau", callback=_exp_nouveau)
        dpg.add_separator()

        with dpg.group(horizontal=True):
            # --- Colonne 1 : plateau + outils ---
            with dpg.child_window(width=CANVAS + 24, height=660):
                dpg.add_drawlist(width=CANVAS, height=CANVAS, tag="exp_board")
                dpg.add_text("Outil de clic :")
                dpg.add_radio_button(tuple(_OUTIL_LBL.values()), tag="exp_outil",
                                     horizontal=True, default_value="Colonie / Ville",
                                     callback=_exp_on_outil)
                with dpg.group(horizontal=True):
                    dpg.add_text("Joueur édité :")
                    dpg.add_radio_button(("J1", "J2", "J3", "J4"), tag="exp_pj",
                                         horizontal=True, default_value="J1",
                                         callback=_exp_on_pj)
                dpg.add_text("Clic gauche sur le plateau : pose / retire selon l'outil.\n"
                             "Colonie : clics successifs = colonie -> ville -> vide.",
                             color=(140, 140, 150))

            # --- Colonne 2 : édition ---
            with dpg.child_window(width=352, height=660):
                with dpg.collapsing_header(label="Tuile sélectionnée", default_open=True):
                    dpg.add_text("(outil « Tuile » puis clic sur une tuile)",
                                 color=(140, 140, 150))
                    with dpg.group(horizontal=True):
                        dpg.add_text("Ressource")
                        dpg.add_combo(["B", "W", "S", "O", "C", "X"], tag="exp_tile_res",
                                      width=80, default_value="B", callback=_exp_on_tile_res)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Numéro   ")
                        dpg.add_combo([_num_lbl(v) for v in NUMS], tag="exp_tile_num",
                                      width=80, default_value="-", callback=_exp_on_tile_num)
                with dpg.collapsing_header(label="Mains du joueur édité", default_open=True):
                    for r in C.RESSOURCES:
                        with dpg.group(horizontal=True):
                            dpg.add_text(RES_NOM[r].ljust(8), color=RES_COL[r])
                            dpg.add_input_int(tag=f"exp_res_{r}", width=120, step=1,
                                              min_value=0, min_clamped=True,
                                              user_data=("res", r), callback=_exp_on_stat)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Or      ", color=(245, 210, 90))
                        dpg.add_input_int(tag="exp_or", width=120, step=1, min_value=0,
                                          min_clamped=True, user_data=("or", None),
                                          callback=_exp_on_stat)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Cartes Chevalier")
                        dpg.add_input_int(tag="exp_chev", width=90, min_value=0,
                                          min_clamped=True, user_data=("chevalier", None),
                                          callback=_exp_on_stat)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Cartes PV       ")
                        dpg.add_input_int(tag="exp_pv", width=90, min_value=0,
                                          min_clamped=True, user_data=("pv", None),
                                          callback=_exp_on_stat)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Chevaliers joués")
                        dpg.add_input_int(tag="exp_kj", width=90, min_value=0,
                                          min_clamped=True, user_data=("kj", None),
                                          callback=_exp_on_stat)
                with dpg.collapsing_header(label="Marché (prix d'achat)"):
                    for r in C.RESSOURCES:
                        with dpg.group(horizontal=True):
                            dpg.add_text(RES_NOM[r].ljust(8), color=RES_COL[r])
                            dpg.add_input_int(tag=f"exp_prix_{r}", width=120,
                                              min_value=C.PRIX_MIN, min_clamped=True,
                                              user_data=("prix", r), callback=_exp_on_prix)
                with dpg.collapsing_header(label="Joueurs"):
                    with dpg.group(horizontal=True):
                        dpg.add_text("Nombre")
                        dpg.add_combo(["2", "3", "4"], tag="exp_n", width=60,
                                      default_value="4", callback=_exp_on_n)
                    for p in range(4):
                        with dpg.group(horizontal=True, tag=f"exp_jrow_{p}"):
                            dpg.add_text(f"J{p + 1}")
                            dpg.add_combo(types, tag=f"exp_jtype_{p}", width=110,
                                          default_value="random", user_data=p,
                                          callback=_exp_on_jtype)
                            dpg.add_input_text(tag=f"exp_jnom_{p}", width=100,
                                               user_data=p, callback=_exp_on_jnom)
                    with dpg.group(horizontal=True):
                        dpg.add_text("Agent testé :")
                        dpg.add_radio_button(("J1", "J2", "J3", "J4"), tag="exp_agent",
                                             horizontal=True, default_value="J1",
                                             callback=_exp_on_agent)

            # --- Colonne 3 : tests enregistrés + sondage ---
            with dpg.child_window(width=322, height=660):
                dpg.add_text("TESTS ENREGISTRÉS", color=(150, 200, 255))
                dpg.add_listbox([], tag="exp_liste", num_items=7, width=-1,
                                callback=_exp_on_liste)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Charger", callback=_exp_charger_sel)
                    dpg.add_button(label="Supprimer", callback=_exp_supprimer)
                    dpg.add_button(label="Actualiser", callback=lambda: _exp_refresh_liste())
                dpg.add_separator()
                dpg.add_text("DÉCISION À TESTER", color=(150, 200, 255))
                dpg.add_radio_button(DECISIONS, tag="exp_decision",
                                     default_value=DECISIONS[0], callback=_exp_on_decision)
                dpg.add_button(label="  >  Tester la prochaine action  ",
                               callback=_exp_tester, width=-1)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Jouer l'action >>", callback=_exp_jouer)
                    dpg.add_button(label="Réinitialiser", callback=_exp_reset)
                dpg.add_separator()
                dpg.add_text("", tag="exp_result", color=(255, 215, 80), wrap=300)
                dpg.add_text("Actions légales (choix en surbrillance) :",
                             color=(150, 200, 255))
                dpg.add_child_window(tag="exp_actions_zone", height=-1, border=True)


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
    dpg.create_viewport(title="Catan — Visualiseur de parties", width=1240, height=1015)
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
