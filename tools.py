"""tools.py — Fonctions utilitaires d'analyse du plateau pour les agents.

Ces outils aident un agent à prendre ses décisions à partir de ``self.plateau``
(perception fixe) et de ``observation`` (perception dynamique). Ils reprennent les
notions de l'étude (partie 2) :

  * **terrain**  : un sommet du graphe (emplacement de colonie/ville) ;
  * **chemin**   : une arête (emplacement de route) ;
  * **distance** D(t1, t2) : plus petit nombre de chemins entre deux terrains ;
  * **distance pour un joueur** D_j(t1, t2) : idem, en n'empruntant que des chemins
    constructibles par le joueur (arête libre, sans traverser un adversaire) ;
  * **distance au joueur** D_j(t) : 0 si t est constructible maintenant, puis +1 par
    route à construire pour l'atteindre ;
  * **production** : espérance de ressources d'un emplacement, Q_s = Σ P(D = n).

Utilisation typique dans un agent :

    from tools import AnalyseurPlateau

    class MonAgent(AgentCatan):
        def nouvelle_partie(self, indice, plateau=None):
            super().nouvelle_partie(indice, plateau)
            self.an = AnalyseurPlateau(plateau)      # construit une fois par partie

        def jouer_tour(self, observation, actions):
            prod = self.an.production_joueur(observation, self.indice)
            ...

On peut aussi appeler les fonctions de module directement :

    import tools
    tools.ressources_adjacentes(self.plateau, sid)
    tools.distance_au_joueur(self.plateau, observation, self.indice)
"""

import math
from collections import deque

import Constantes as C

RESSOURCES = C.RESSOURCES          # ["B", "W", "S", "O", "C"]
DESERT = C.DESERT                  # "X"
PORT_GENERIQUE = C.DESERT          # les ports 3:1 sont notés "X"

# Coûts de construction (repris de Constantes, pour la commodité des agents).
COUTS = {
    "route": C.COUT_ROUTE,
    "colonie": C.COUT_COLONIE,
    "ville": C.COUT_VILLE,
    "dev": C.COUT_DEV,
}


# ======================================================================
#  Fonctions pures (probabilités / production)
# ======================================================================
def proba_des(num):
    """Probabilité d'obtenir ``num`` avec deux dés : P(D=n) = (6 - |n-7|)/36."""
    if not num:
        return 0.0
    return (6 - abs(7 - num)) / 36.0


def pips(num):
    """« Pips » du jeton (6 et 8 valent 5, 2 et 12 valent 1) = 36 · P(D=n)."""
    if not num:
        return 0
    return 6 - abs(7 - num)


# ======================================================================
#  Géométrie (réplique l'attribution d'ids de sommets du moteur)
# ======================================================================
def _coords_axiales(N):
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


# ======================================================================
#  Analyseur de plateau
# ======================================================================
class AnalyseurPlateau:
    """Précalcule la structure du plateau et offre des méthodes d'analyse.

    À construire **une fois par partie** (le plateau statique ne change pas) :
    ``an = AnalyseurPlateau(plateau)``. Les méthodes « dynamiques » prennent
    ``observation`` en argument (l'état courant).
    """

    def __init__(self, plateau):
        self.plateau = plateau
        self.sommets = list(range(len(plateau["sommets"])))
        self.tuiles = plateau["tuiles"]

        # Ressource + numéro de chaque tuile, par coordonnée.
        self.tuile_coord = {(t["q"], t["r"]): (t["res"], t["num"]) for t in self.tuiles}

        # Adjacence entre sommets + arêtes incidentes (depuis les arêtes).
        self.voisins = {s: set() for s in self.sommets}
        self.aretes = [tuple(e) for e in plateau["aretes"]]
        for a, b in self.aretes:
            self.voisins[a].add(b)
            self.voisins[b].add(a)

        # Géométrie : id de sommet -> coordonnées, et tuile -> ses 6 coins.
        N = max((max(abs(t["q"]), abs(t["r"]), abs(t["q"] + t["r"]))
                 for t in self.tuiles), default=2)
        cles, self.pos, self.coins_tuile = {}, {}, {}
        for (q, r) in _coords_axiales(N):
            centre = _centre(q, r)
            ids = []
            for i in range(6):
                cx, cy = _coin(centre, i)
                cle = (round(cx, 2), round(cy, 2))
                if cle not in cles:
                    sid = len(cles)
                    cles[cle] = sid
                    self.pos[sid] = (cx, cy)
                ids.append(cles[cle])
            self.coins_tuile[(q, r)] = ids

        # Tuiles adjacentes à chaque sommet : liste de (q, r, res, num).
        self.tuiles_sommet = {s: [] for s in self.sommets}
        for (q, r), ids in self.coins_tuile.items():
            res, num = self.tuile_coord.get((q, r), (DESERT, None))
            for sid in ids:
                if sid in self.tuiles_sommet:
                    self.tuiles_sommet[sid].append((q, r, res, num))

        # Port éventuel de chaque sommet.
        self.port_sommet = {s["id"]: s.get("port") for s in plateau["sommets"]}

    # ------------------------------------------------------------------
    #  Extraction depuis l'observation (perception dynamique)
    # ------------------------------------------------------------------
    @staticmethod
    def _prop_sommets(observation):
        g = observation.get("graphe", {})
        return {int(k): v.get("joueur", -1) for k, v in g.get("sommets", {}).items()}

    @staticmethod
    def _villes(observation):
        g = observation.get("graphe", {})
        return {int(k) for k, v in g.get("sommets", {}).items() if v.get("ville")}

    @staticmethod
    def _prop_aretes(observation):
        g = observation.get("graphe", {})
        return {frozenset((a, b)): p for a, b, p in g.get("aretes", [])}

    # ------------------------------------------------------------------
    #  Requêtes statiques sur un emplacement (terrain)
    # ------------------------------------------------------------------
    def tuiles_adjacentes(self, sid):
        """Liste des ``(q, r, res, num)`` des tuiles touchant le sommet (désert inclus)."""
        return list(self.tuiles_sommet.get(sid, []))

    def ressources_adjacentes(self, sid):
        """Ressources productives adjacentes au sommet (désert exclu)."""
        return [res for (_q, _r, res, num) in self.tuiles_sommet.get(sid, [])
                if res != DESERT and num]

    def numeros_adjacents(self, sid):
        """Numéros des tuiles productives adjacentes au sommet."""
        return [num for (_q, _r, _res, num) in self.tuiles_sommet.get(sid, []) if num]

    def port(self, sid):
        """Type de port du sommet : une ressource (2:1), 'X' (3:1) ou None."""
        return self.port_sommet.get(sid)

    def esperance_production(self, sid):
        """Q_s : espérance de ressources/tour d'une colonie sur ce sommet."""
        return sum(proba_des(num) for (_q, _r, _res, num) in self.tuiles_sommet.get(sid, []))

    qualite_simple = esperance_production  # alias (notation Q_s de l'étude)

    def esperance_ressource(self, sid, res):
        """Espérance de production d'une ressource précise sur ce sommet."""
        return sum(proba_des(num) for (_q, _r, r, num) in self.tuiles_sommet.get(sid, [])
                   if r == res)

    def classer_par_production(self, sids):
        """Trie une liste de sommets par production décroissante (Q_s)."""
        return sorted(sids, key=self.esperance_production, reverse=True)

    # ------------------------------------------------------------------
    #  Graphe : distances entre terrains
    # ------------------------------------------------------------------
    def distance(self, t1, t2):
        """D(t1, t2) : plus petit nombre de chemins entre deux terrains."""
        if t1 == t2:
            return 0
        vus = {t1}
        dq = deque([(t1, 0)])
        while dq:
            s, d = dq.popleft()
            for v in self.voisins[s]:
                if v == t2:
                    return d + 1
                if v not in vus:
                    vus.add(v)
                    dq.append((v, d + 1))
        return math.inf

    def distances_depuis(self, t):
        """Distances de ``t`` vers tous les terrains atteignables (dict)."""
        dist = {t: 0}
        dq = deque([t])
        while dq:
            s = dq.popleft()
            for v in self.voisins[s]:
                if v not in dist:
                    dist[v] = dist[s] + 1
                    dq.append(v)
        return dist

    def distance_joueur(self, observation, t1, t2, joueur):
        """D_j(t1, t2) : distance n'empruntant que des chemins constructibles par
        ``joueur`` (arête libre ou lui appartenant), sans traverser un adversaire."""
        if t1 == t2:
            return 0
        prop_s = self._prop_sommets(observation)
        prop_e = self._prop_aretes(observation)
        vus = {t1}
        dq = deque([(t1, 0)])
        while dq:
            s, d = dq.popleft()
            o = prop_s.get(s, -1)
            if s != t1 and o != -1 and o != joueur:   # on ne traverse pas un adversaire
                continue
            for v in self.voisins[s]:
                proprio = prop_e.get(frozenset((s, v)), -1)
                if proprio in (-1, joueur):
                    if v == t2:
                        return d + 1
                    if v not in vus:
                        vus.add(v)
                        dq.append((v, d + 1))
        return math.inf

    # ------------------------------------------------------------------
    #  Placement / constructibilité
    # ------------------------------------------------------------------
    def proprietaire(self, observation, sid):
        """Indice du joueur possédant le sommet, ou -1 s'il est libre."""
        return self._prop_sommets(observation).get(sid, -1)

    def est_ville(self, observation, sid):
        return sid in self._villes(observation)

    def proprietaire_arete(self, observation, a, b):
        return self._prop_aretes(observation).get(frozenset((a, b)), -1)

    def sommets_du_joueur(self, observation, joueur):
        return [s for s, o in self._prop_sommets(observation).items() if o == joueur]

    def routes_du_joueur(self, observation, joueur):
        return [tuple(sorted(e)) for e, o in self._prop_aretes(observation).items()
                if o == joueur]

    def reseau(self, observation, joueur):
        """Sommets du réseau du joueur (extrémités de ses routes + ses bâtiments)."""
        res = set(self.sommets_du_joueur(observation, joueur))
        for e, o in self._prop_aretes(observation).items():
            if o == joueur:
                res.update(e)
        return res

    def respecte_distance(self, observation, sid):
        """Règle de distance : sommet libre et aucun voisin occupé."""
        prop_s = self._prop_sommets(observation)
        if prop_s.get(sid, -1) != -1:
            return False
        return all(prop_s.get(v, -1) == -1 for v in self.voisins[sid])

    def colonie_constructible(self, observation, sid, joueur):
        """Vrai si ``joueur`` peut construire une colonie sur ``sid`` maintenant
        (libre, règle de distance respectée, relié à une de ses routes)."""
        prop_s = self._prop_sommets(observation)
        prop_e = self._prop_aretes(observation)
        return self._constructible(prop_s, prop_e, sid, joueur)

    def _constructible(self, prop_s, prop_e, sid, joueur):
        if prop_s.get(sid, -1) != -1:
            return False
        if any(prop_s.get(v, -1) != -1 for v in self.voisins[sid]):
            return False
        return any(prop_e.get(frozenset((sid, v)), -1) == joueur for v in self.voisins[sid])

    def colonies_constructibles(self, observation, joueur):
        """Liste des sommets où ``joueur`` peut construire une colonie maintenant."""
        prop_s = self._prop_sommets(observation)
        prop_e = self._prop_aretes(observation)
        return [s for s in self.sommets if self._constructible(prop_s, prop_e, s, joueur)]

    def aretes_constructibles(self, observation, joueur):
        """Arêtes libres reliées au réseau du joueur (routes qu'il peut poser)."""
        reseau = self.reseau(observation, joueur)
        prop_e = self._prop_aretes(observation)
        return [(a, b) for (a, b) in self.aretes
                if prop_e.get(frozenset((a, b)), -1) == -1 and (a in reseau or b in reseau)]

    def distance_au_joueur(self, observation, joueur):
        """D_j(t) : dict ``{sommet: nb de routes}``. 0 pour les terrains
        constructibles maintenant, +1 par route à construire pour atteindre le terrain."""
        prop_s = self._prop_sommets(observation)
        prop_e = self._prop_aretes(observation)
        dist, dq = {}, deque()
        for s in self.sommets:
            if self._constructible(prop_s, prop_e, s, joueur):
                dist[s] = 0
                dq.append(s)
        while dq:
            t = dq.popleft()
            o = prop_s.get(t, -1)
            if o != -1 and o != joueur:        # on ne prolonge pas à travers un adversaire
                continue
            for v in self.voisins[t]:
                if prop_e.get(frozenset((t, v)), -1) == -1 and v not in dist:
                    dist[v] = dist[t] + 1
                    dq.append(v)
        return dist

    # ------------------------------------------------------------------
    #  Production, marché, voleur
    # ------------------------------------------------------------------
    def production_joueur(self, observation, joueur, tenir_compte_voleur=True):
        """Espérance de production par ressource du joueur (colonie ×1, ville ×2)."""
        prop_s = self._prop_sommets(observation)
        villes = self._villes(observation)
        voleur = tuple(observation.get("voleur", [None, None]))
        prod = {r: 0.0 for r in RESSOURCES}
        for sid, o in prop_s.items():
            if o != joueur:
                continue
            mult = 2 if sid in villes else 1
            for (q, r, res, num) in self.tuiles_sommet.get(sid, []):
                if not num or res == DESERT:
                    continue
                if tenir_compte_voleur and (q, r) == voleur:
                    continue
                prod[res] += proba_des(num) * mult
        return prod

    def production_totale(self, observation, joueur, **kw):
        """Espérance totale de ressources/tour du joueur (toutes ressources)."""
        return sum(self.production_joueur(observation, joueur, **kw).values())

    def ports_du_joueur(self, observation, joueur):
        """Ensemble des types de ports accessibles au joueur."""
        prop_s = self._prop_sommets(observation)
        return {self.port_sommet.get(sid) for sid, o in prop_s.items()
                if o == joueur and self.port_sommet.get(sid)}

    def meilleur_taux(self, observation, joueur, res):
        """Meilleur taux d'échange du joueur pour donner ``res`` (4, 3 ou 2)."""
        ports = self.ports_du_joueur(observation, joueur)
        taux = C.TAUX_BANQUE
        if PORT_GENERIQUE in ports:
            taux = min(taux, C.TAUX_PORT_GENERIQUE)
        if res in ports:
            taux = min(taux, C.TAUX_PORT_RESSOURCE)
        return taux

    def sommets_de_tuile(self, q, r):
        """Les 6 sommets (coins) d'une tuile — utile pour cibler le voleur."""
        return list(self.coins_tuile.get((q, r), []))

    def batiments_sur_tuile(self, observation, q, r):
        """Liste ``(sommet, joueur, ville)`` des bâtiments présents sur une tuile."""
        prop_s = self._prop_sommets(observation)
        villes = self._villes(observation)
        out = []
        for sid in self.coins_tuile.get((q, r), []):
            o = prop_s.get(sid, -1)
            if o != -1:
                out.append((sid, o, sid in villes))
        return out

    def voleur_menace(self, observation, joueur):
        """Vrai si le voleur est sur une tuile adjacente à un bâtiment du joueur."""
        vq, vr = observation.get("voleur", [None, None])
        for sid, o, _v in self.batiments_sur_tuile(observation, vq, vr):
            if o == joueur:
                return True
        return False

    # ------------------------------------------------------------------
    #  Ressources / coûts (depuis l'observation du joueur actif)
    # ------------------------------------------------------------------
    @staticmethod
    def peut_payer(observation, cout):
        """Vrai si le joueur actif peut payer ``cout`` (ex. ``COUTS['ville']``)."""
        res = observation.get("ressources", {})
        return all(res.get(r, 0) >= q for r, q in cout.items())

    @staticmethod
    def ressources_manquantes(observation, cout):
        """Dict des ressources (et quantités) manquantes pour payer ``cout``."""
        res = observation.get("ressources", {})
        return {r: q - res.get(r, 0) for r, q in cout.items() if res.get(r, 0) < q}


# ======================================================================
#  Fonctions de module (analyseur mis en cache par plateau)
# ======================================================================
_CACHE = {}


def analyseur(plateau):
    """Renvoie un ``AnalyseurPlateau`` pour ``plateau`` (mis en cache par partie)."""
    a = _CACHE.get(id(plateau))
    if a is None or a.plateau is not plateau:
        a = AnalyseurPlateau(plateau)
        _CACHE[id(plateau)] = a
    return a


def ressources_adjacentes(plateau, sid):
    return analyseur(plateau).ressources_adjacentes(sid)


def tuiles_adjacentes(plateau, sid):
    return analyseur(plateau).tuiles_adjacentes(sid)


def esperance_production(plateau, sid):
    return analyseur(plateau).esperance_production(sid)


def distance(plateau, t1, t2):
    return analyseur(plateau).distance(t1, t2)


def distance_joueur(plateau, observation, t1, t2, joueur):
    return analyseur(plateau).distance_joueur(observation, t1, t2, joueur)


def distance_au_joueur(plateau, observation, joueur):
    return analyseur(plateau).distance_au_joueur(observation, joueur)


def colonies_constructibles(plateau, observation, joueur):
    return analyseur(plateau).colonies_constructibles(observation, joueur)


def production_joueur(plateau, observation, joueur, **kw):
    return analyseur(plateau).production_joueur(observation, joueur, **kw)


def meilleur_taux(plateau, observation, joueur, res):
    return analyseur(plateau).meilleur_taux(observation, joueur, res)
