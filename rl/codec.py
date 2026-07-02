"""codec.py — Encodage observation <-> vecteur, et actions <-> espace discret.

Deux difficultés du RL sur ce jeu, résolues ici :

1. **Espace d'actions variable** : à chaque décision, la liste des actions légales
   change. On définit un espace discret **fixe** (une case par action possible du jeu)
   et, à chaque pas, un **masque** indiquant les actions légales. Le réseau ne choisit
   que parmi les cases autorisées.

2. **Observation en dictionnaire** : on l'aplatit en un vecteur de taille fixe,
   centré sur le joueur courant (« moi »), pour qu'il soit invariant à la place.
"""

import numpy as np

import tools

RES = tools.RESSOURCES                     # ["B", "W", "S", "O", "C"]
RES_IDX = {r: i for i, r in enumerate(RES)}
PORTS = RES + [tools.DESERT]               # types de port : ressources + "X" (3:1)


# ======================================================================
#  Codec des actions : espace discret fixe + masque
# ======================================================================
class CodecActions:
    """Bijection action <-> indice discret (l'agencement est fixe d'une partie à
    l'autre car la géométrie du plateau ne change pas)."""

    def __init__(self, plateau):
        self.aretes = sorted(tuple(sorted(e)) for e in plateau["aretes"])
        self.idx_arete = {e: i for i, e in enumerate(self.aretes)}
        self.n_aretes = len(self.aretes)                 # 72
        self.n_sommets = len(plateau["sommets"])         # 54
        self.tuiles = sorted((t["q"], t["r"]) for t in plateau["tuiles"])
        self.idx_tuile = {qr: i for i, qr in enumerate(self.tuiles)}
        self.n_tuiles = len(self.tuiles)                 # 19

        # Décalages (offsets) de chaque famille d'actions.
        self.O_PASSER = 0
        self.O_ROUTE = 1
        self.O_COLONIE = self.O_ROUTE + self.n_aretes
        self.O_VILLE = self.O_COLONIE + self.n_sommets
        self.O_DEV = self.O_VILLE + self.n_sommets
        self.O_CHEV = self.O_DEV + 1
        self.O_VOLEUR = self.O_CHEV + 1
        self.O_ACHAT = self.O_VOLEUR + self.n_tuiles
        self.O_VENTE = self.O_ACHAT + 5
        self.O_ECHANGE = self.O_VENTE + 5
        self.taille = self.O_ECHANGE + 20                # 232 pour le plateau standard

    def index(self, action):
        """Indice discret d'une action."""
        t = action["type"]
        if t == "passer":
            return self.O_PASSER
        if t in ("construire_route", "prep_route"):
            return self.O_ROUTE + self.idx_arete[tuple(sorted(action["arete"]))]
        if t in ("construire_colonie", "prep_colonie"):
            return self.O_COLONIE + action["sommet"]
        if t == "construire_ville":
            return self.O_VILLE + action["sommet"]
        if t == "acheter_dev":
            return self.O_DEV
        if t == "jouer_chevalier":
            return self.O_CHEV
        if t == "voleur":
            return self.O_VOLEUR + self.idx_tuile[tuple(action["tuile"])]
        if t == "marche_acheter":
            return self.O_ACHAT + RES_IDX[action["res"]]
        if t == "marche_vendre":
            return self.O_VENTE + RES_IDX[action["res"]]
        if t == "echange":
            d, r = RES_IDX[action["donne"]], RES_IDX[action["recoit"]]
            return self.O_ECHANGE + d * 4 + (r if r < d else r - 1)
        raise ValueError(f"Action inconnue pour le codec : {action!r}")

    def masque(self, actions):
        """Renvoie ``(masque, mapping)`` : un tableau booléen des actions légales et
        un dict ``{indice: action}`` pour retrouver l'action choisie."""
        m = np.zeros(self.taille, dtype=bool)
        mapping = {}
        for a in actions:
            i = self.index(a)
            m[i] = True
            mapping[i] = a
        return m, mapping


# ======================================================================
#  Encodeur d'observation : dict -> vecteur fixe
# ======================================================================
class EncodeurObservation:
    """Aplatit l'observation (dict) en un vecteur ``float32`` de taille fixe,
    centré sur le joueur ``moi``."""

    def __init__(self, plateau, n_joueurs=4):
        self.an = tools.AnalyseurPlateau(plateau)
        self.n_joueurs = n_joueurs
        self.n_sommets = self.an.sommets and len(self.an.sommets)
        self.aretes = sorted(tuple(sorted(e)) for e in plateau["aretes"])
        self.tuiles = sorted((t["q"], t["r"]) for t in plateau["tuiles"])
        # Taille du vecteur : déduite en encodant une observation minimale.
        qr0 = self.tuiles[0]
        obs0 = {"graphe": {"sommets": {}, "aretes": []}, "voleur": list(qr0),
                "ressources": {r: 0 for r in RES}, "or": 0, "cartes_pv": 0,
                "cartes_chevalier": 0, "pv_publics": [0] * n_joueurs,
                "ressources_adversaires": [0] * n_joueurs,
                "prix_marche": {r: 0 for r in RES},
                "chevaliers_joues": [0] * n_joueurs, "longueur_routes": [0] * n_joueurs,
                "plus_grande_armee": -1, "route_la_plus_longue": -1}
        self.taille = len(self.encoder(obs0, 0))

    def encoder(self, obs, moi):
        an = self.an
        prop_s = an._prop_sommets(obs)
        villes = an._villes(obs)
        prop_e = an._prop_aretes(obs)
        voleur = tuple(obs.get("voleur", [None, None]))
        v = []

        # --- Par sommet (terrain) : propriété, ville, constructible, production, port ---
        for s in range(len(an.sommets)):
            o = prop_s.get(s, -1)
            v += [1.0 if o == moi else 0.0,
                  1.0 if (o != -1 and o != moi) else 0.0,
                  1.0 if o == -1 else 0.0,
                  1.0 if s in villes else 0.0,
                  1.0 if an._constructible(prop_s, prop_e, s, moi) else 0.0,
                  an.esperance_production(s)]
            port = an.port_sommet.get(s)
            v += [1.0 if port == p else 0.0 for p in PORTS]

        # --- Par arête (chemin) : propriété ---
        for e in self.aretes:
            o = prop_e.get(frozenset(e), -1)
            v += [1.0 if o == moi else 0.0,
                  1.0 if (o != -1 and o != moi) else 0.0,
                  1.0 if o == -1 else 0.0]

        # --- Par tuile : ressource, pips, voleur ---
        for qr in self.tuiles:
            res, num = an.tuile_coord.get(qr, (tools.DESERT, None))
            v += [1.0 if res == rr else 0.0 for rr in PORTS]     # B,W,S,O,C,X
            v += [tools.pips(num) / 5.0, 1.0 if qr == voleur else 0.0]

        # --- Scalaires globaux (centrés sur moi) ---
        ress = obs.get("ressources", {})
        v += [ress.get(r, 0) / 10.0 for r in RES]
        v += [obs.get("or", 0) / 50.0, obs.get("cartes_pv", 0) / 5.0,
              obs.get("cartes_chevalier", 0) / 5.0]
        pm = obs.get("prix_marche", {})
        v += [pm.get(r, 0) / 20.0 for r in RES]
        for cle, echelle in [("pv_publics", 10.0), ("ressources_adversaires", 20.0),
                             ("chevaliers_joues", 5.0), ("longueur_routes", 15.0)]:
            lst = obs.get(cle, [])
            v += [(lst[k] if k < len(lst) else 0) / echelle for k in range(self.n_joueurs)]
        v += [1.0 if obs.get("plus_grande_armee", -1) == moi else 0.0,
              1.0 if obs.get("route_la_plus_longue", -1) == moi else 0.0]
        prod = an.production_joueur(obs, moi)
        v += [prod[r] for r in RES]

        return np.asarray(v, dtype=np.float32)
