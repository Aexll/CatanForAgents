"""moteur.py — Moteur du jeu Catan (version simplifiée).

Le moteur gère les règles et l'état du jeu :
  * il lance des parties (machine d'état PREP -> DES <-> JOUEUR, avec l'état VOL) ;
  * il envoie l'état du jeu (observation) à chaque joueur et reçoit son action ;
  * il met à jour l'état et gère les conditions de fin de partie ;
  * il produit une sauvegarde JSONL : une ligne par décision, contenant l'état du
    jeu à l'instant t et l'action effectuée par le joueur actif.

L'interface visuelle (dearpygui) sera ajoutée plus tard.
"""

import json
import math
import os
import random

import Constantes as C


# ======================================================================
#  Plateau : graphe statique (tuiles, sommets, arêtes, ports)
# ======================================================================
class Plateau:
    """Plateau de jeu sous forme de graphe G = (V, E).

    Les sommets sont les intersections (colonies/villes) et les arêtes les
    routes. Les tuiles portent un couple (ressource, numéro) et sont repérées
    en coordonnées axiales (q, r).
    """

    def __init__(self, rng):
        self.tuiles = {}          # (q, r) -> {"res": str, "num": int|None}
        self.sommets_tuiles = {}  # id_sommet -> [(q, r), ...]
        self.aretes = []          # liste de tuples (a, b) triés, a < b
        self.voisins = {}         # id_sommet -> set(id_sommets adjacents)
        self.aretes_sommet = {}   # id_sommet -> [aretes incidentes]
        self.ports = {}           # id_sommet -> type de port (ressource ou DESERT)
        self.coins_tuile = {}     # (q, r) -> [6 ids de sommets, ordre des coins]
        self._generer(rng)

    # ------------------------------------------------------------------
    #  Génération
    # ------------------------------------------------------------------
    def _coords_axiales(self):
        """Coordonnées axiales des 19 tuiles d'un plateau de rayon 2."""
        N = C.RAYON_PLATEAU
        coords = []
        for q in range(-N, N + 1):
            for r in range(-N, N + 1):
                if -N <= -q - r <= N:
                    coords.append((q, r))
        return coords

    @staticmethod
    def _centre(q, r):
        """Centre (x, y) d'une tuile « pointy-top » en coordonnées axiales."""
        x = math.sqrt(3) * (q + r / 2)
        y = 1.5 * r
        return x, y

    @staticmethod
    def _coin(centre, i):
        """i-ème coin d'un hexagone pointy-top (i = 0..5)."""
        angle = math.radians(60 * i - 30)
        return centre[0] + math.cos(angle), centre[1] + math.sin(angle)

    def _generer(self, rng):
        coords = self._coords_axiales()

        # --- Attribution des ressources et des numéros ---
        ressources = list(C.COMPOSITION_TUILES)
        rng.shuffle(ressources)
        jetons = list(C.JETONS_NUMEROS)
        rng.shuffle(jetons)
        ji = 0
        for (q, r), res in zip(coords, ressources):
            if res == C.DESERT:
                self.tuiles[(q, r)] = {"res": C.DESERT, "num": None}
            else:
                self.tuiles[(q, r)] = {"res": res, "num": jetons[ji]}
                ji += 1

        # --- Sommets : déduplication des coins partagés ---
        cles = {}  # (x, y) arrondi -> id_sommet
        for (q, r) in coords:
            centre = self._centre(q, r)
            ids = []
            for i in range(6):
                cx, cy = self._coin(centre, i)
                cle = (round(cx, 2), round(cy, 2))
                if cle not in cles:
                    sid = len(cles)
                    cles[cle] = sid
                    self.sommets_tuiles[sid] = []
                sid = cles[cle]
                ids.append(sid)
                if (q, r) not in self.sommets_tuiles[sid]:
                    self.sommets_tuiles[sid].append((q, r))
            self.coins_tuile[(q, r)] = ids

        self.nb_sommets = len(cles)
        for sid in range(self.nb_sommets):
            self.voisins[sid] = set()
            self.aretes_sommet[sid] = []

        # --- Arêtes : coins consécutifs de chaque tuile ---
        compte_aretes = {}
        aretes = set()
        for (q, r), ids in self.coins_tuile.items():
            for i in range(6):
                a, b = ids[i], ids[(i + 1) % 6]
                e = (a, b) if a < b else (b, a)
                aretes.add(e)
                compte_aretes[e] = compte_aretes.get(e, 0) + 1
        self.aretes = sorted(aretes)
        for (a, b) in self.aretes:
            self.voisins[a].add(b)
            self.voisins[b].add(a)
            self.aretes_sommet[a].append((a, b))
            self.aretes_sommet[b].append((a, b))

        # --- Ports : répartis sur des arêtes de périmètre ---
        self._placer_ports(compte_aretes, rng)

    def _placer_ports(self, compte_aretes, rng):
        """Attribue les ports à des arêtes du périmètre (présentes dans 1 tuile)."""
        perimetre = sorted(e for e, n in compte_aretes.items() if n == 1)
        if not perimetre:
            return
        types = list(C.PORTS)
        rng.shuffle(types)
        # On répartit régulièrement les ports le long du périmètre.
        pas = max(1, len(perimetre) // len(types))
        choisies = perimetre[::pas][: len(types)]
        for (a, b), type_port in zip(choisies, types):
            self.ports[a] = type_port
            self.ports[b] = type_port

    # ------------------------------------------------------------------
    #  Accès statique
    # ------------------------------------------------------------------
    def tuiles_du_sommet(self, sid):
        """Liste des couples (ressource, numéro) des tuiles adjacentes au sommet."""
        couples = []
        for (q, r) in self.sommets_tuiles[sid]:
            t = self.tuiles[(q, r)]
            if t["res"] != C.DESERT:
                couples.append((t["res"], t["num"]))
        return couples

    def serialiser_statique(self):
        """Représentation JSON du graphe statique G_s (perception fixe)."""
        return {
            "tuiles": [
                {"q": q, "r": r, "res": t["res"], "num": t["num"]}
                for (q, r), t in sorted(self.tuiles.items())
            ],
            "sommets": [
                {
                    "id": sid,
                    "tuiles": [[res, num] for (res, num) in self.tuiles_du_sommet(sid)],
                    "port": self.ports.get(sid),
                }
                for sid in range(self.nb_sommets)
            ],
            "aretes": [[a, b] for (a, b) in self.aretes],
        }


# ======================================================================
#  Moteur : état dynamique et déroulement de la partie
# ======================================================================
class Moteur:
    """Moteur de partie : orchestre la machine d'état et la sauvegarde."""

    def __init__(self, joueurs, seed=None, chemin_sauvegarde=None, partie_id=0):
        self.joueurs = joueurs
        self.n = len(joueurs)
        if not (2 <= self.n <= 4):
            raise ValueError("Le jeu se joue de 2 à 4 joueurs.")
        self.rng = random.Random(seed)
        self.partie_id = partie_id
        self.chemin_sauvegarde = chemin_sauvegarde
        self._fichier = None
        self.t = 0  # compteur d'instants (lignes de sauvegarde)

        # --- Plateau (statique) ---
        self.plateau = Plateau(self.rng)

        # --- État dynamique ---
        self.proprio_sommet = [-1] * self.plateau.nb_sommets   # joueur ou -1
        self.ville_sommet = [False] * self.plateau.nb_sommets  # True = ville
        self.proprio_arete = {e: -1 for e in self.plateau.aretes}
        self.voleur = self._tuile_desert()
        self.prix = {res: C.PRIX_INITIAL for res in C.RESSOURCES}

        # --- État des joueurs ---
        self.ressources = [{res: 0 for res in C.RESSOURCES} for _ in range(self.n)]
        self.cor = [C.OR_INITIAL] * self.n
        self.main_dev = [{C.DEV_CHEVALIER: 0, C.DEV_POINT: 0} for _ in range(self.n)]
        self.chevaliers_joues = [0] * self.n
        self.proprio_armee = -1         # détenteur de la plus grande armée
        self.proprio_route_longue = -1  # détenteur de la route la plus longue

        # --- État incrémental (caches mis à jour à chaque construction) ---
        self.longueur_routes = [0] * self.n            # cache de la plus longue route
        self.nb_colonies = [0] * self.n                # colonies (non-villes) par joueur
        self.nb_villes = [0] * self.n                  # villes par joueur
        self.reseau = [set() for _ in range(self.n)]   # sommets reliés au réseau de p
        self.colonies_de = [set() for _ in range(self.n)]  # colonies de p (candidates ville)
        self.ports_de = [set() for _ in range(self.n)]     # types de ports accessibles à p
        self._graphe_cache = None  # graphe observé, reconstruit à chaque construction

        # --- Paquet de cartes développement ---
        self.paquet_dev = (
            [C.DEV_CHEVALIER] * C.NB_CHEVALIERS + [C.DEV_POINT] * C.NB_POINTS_VICTOIRE
        )
        self.rng.shuffle(self.paquet_dev)

        self.phase = C.ETAT_PREP
        self.gagnant = None
        self.dernier_de = None  # dernier lancer de dés (pour l'observation)

    # ------------------------------------------------------------------
    #  Utilitaires de plateau
    # ------------------------------------------------------------------
    def _tuile_desert(self):
        for (q, r), t in self.plateau.tuiles.items():
            if t["res"] == C.DESERT:
                return [q, r]
        return list(next(iter(self.plateau.tuiles)))

    def _sommets_libres_distance(self):
        """Sommets respectant la règle de distance (aucun voisin occupé)."""
        libres = []
        for sid in range(self.plateau.nb_sommets):
            if self.proprio_sommet[sid] != -1:
                continue
            if any(self.proprio_sommet[v] != -1 for v in self.plateau.voisins[sid]):
                continue
            libres.append(sid)
        return libres

    def _distance_ok(self, sid):
        """Vrai si aucun voisin du sommet n'est occupé (règle de distance)."""
        return all(self.proprio_sommet[v] == -1 for v in self.plateau.voisins[sid])

    def _enregistrer_colonie(self, p, sid):
        """Met à jour les caches incrémentaux lors de la pose d'une colonie."""
        self.proprio_sommet[sid] = p
        self.ville_sommet[sid] = False
        self.nb_colonies[p] += 1
        self.reseau[p].add(sid)
        self.colonies_de[p].add(sid)
        port = self.plateau.ports.get(sid)
        if port is not None:
            self.ports_de[p].add(port)
        self._graphe_cache = None

    # ------------------------------------------------------------------
    #  Marché et échanges
    # ------------------------------------------------------------------
    def _meilleur_taux(self, p, res):
        """Meilleur taux d'échange (port/banque) du joueur p pour donner ``res``."""
        ports = self.ports_de[p]
        taux = C.TAUX_BANQUE
        if C.DESERT in ports:
            taux = C.TAUX_PORT_GENERIQUE
        if res in ports:
            taux = min(taux, C.TAUX_PORT_RESSOURCE)
        return taux

    # ------------------------------------------------------------------
    #  Coûts
    # ------------------------------------------------------------------
    def _peut_payer(self, p, cout):
        return all(self.ressources[p][r] >= q for r, q in cout.items())

    def _payer(self, p, cout):
        for r, q in cout.items():
            self.ressources[p][r] -= q

    def _total_ressources(self, p):
        return sum(self.ressources[p].values())

    # ------------------------------------------------------------------
    #  Points de victoire
    # ------------------------------------------------------------------
    def _points(self, p, inclure_prive=True):
        pts = self.nb_colonies[p] + 2 * self.nb_villes[p]
        if self.proprio_armee == p:
            pts += C.BONUS_ARMEE
        if self.proprio_route_longue == p:
            pts += C.BONUS_ROUTE
        if inclure_prive:
            pts += self.main_dev[p][C.DEV_POINT]
        return pts

    def _maj_plus_grande_armee(self, p):
        n = self.chevaliers_joues[p]
        if n < C.ARMEE_MIN:
            return
        meilleur = -1 if self.proprio_armee == -1 else self.chevaliers_joues[self.proprio_armee]
        if n > meilleur:
            self.proprio_armee = p

    def _longueur_route(self, p):
        """Longueur de la plus longue chaîne continue de routes du joueur p.

        Plus long « trail » (sans réemprunter une arête) dans le sous-graphe des
        routes de p. Le passage est bloqué par une colonie/ville adverse : une
        telle intersection peut terminer une chaîne mais pas la prolonger.
        """
        aretes_p = [e for e in self.plateau.aretes if self.proprio_arete[e] == p]
        if not aretes_p:
            return 0
        incid = {}
        for (a, b) in aretes_p:
            incid.setdefault(a, []).append((b, (a, b)))
            incid.setdefault(b, []).append((a, (a, b)))

        def bloque(s):
            o = self.proprio_sommet[s]
            return o != -1 and o != p

        meilleur = 0

        def dfs(sommet, vues, profondeur):
            nonlocal meilleur
            if profondeur > meilleur:
                meilleur = profondeur
            # On peut démarrer sur une intersection adverse, mais pas la traverser.
            if profondeur > 0 and bloque(sommet):
                return
            for (voisin, e) in incid[sommet]:
                if e not in vues:
                    vues.add(e)
                    dfs(voisin, vues, profondeur + 1)
                    vues.remove(e)

        for depart in incid:
            dfs(depart, set(), 0)
        return meilleur

    def _maj_route_longue(self, joueurs=None):
        """Réévalue le détenteur de la route la plus longue (>= ROUTE_MIN segments).

        Recalcule et **met en cache** la longueur de route ; n'est appelée que
        lorsqu'une route ou une colonie change (pas à chaque observation).
        ``joueurs`` restreint le recalcul (une route ne change que la longueur de
        son poseur ; une colonie peut couper les routes adverses).
        """
        for p in (range(self.n) if joueurs is None else joueurs):
            self.longueur_routes[p] = self._longueur_route(p)
        longueurs = self.longueur_routes
        detenteur = self.proprio_route_longue
        # Le détenteur perd le titre si sa chaîne repasse sous le seuil.
        if detenteur != -1 and longueurs[detenteur] < C.ROUTE_MIN:
            detenteur = -1
        maxlen = max(longueurs)
        if maxlen >= C.ROUTE_MIN:
            meneurs = [p for p in range(self.n) if longueurs[p] == maxlen]
            # En cas d'égalité, le détenteur actuel conserve le titre.
            if detenteur not in meneurs:
                detenteur = meneurs[0]
        self.proprio_route_longue = detenteur

    def _verifier_victoire(self):
        for p in range(self.n):
            if self._points(p, inclure_prive=True) >= C.VICTOIRE_POINTS:
                self.gagnant = p
                return True
        return False

    # ==================================================================
    #  Déroulement de la partie
    # ==================================================================
    def jouer_partie(self):
        """Joue une partie complète et renvoie l'indice du joueur gagnant."""
        plateau_statique = self.plateau.serialiser_statique()
        for i, j in enumerate(self.joueurs):
            j.nouvelle_partie(i, plateau_statique)
        self._ouvrir_sauvegarde()
        try:
            self._ecrire_meta()
            self._phase_preparation()
            self.phase = C.ETAT_DES
            tour = 0
            while self.gagnant is None and tour < C.MAX_TOURS:
                for p in range(self.n):
                    self._tour_joueur(p)
                    tour += 1
                    if self.gagnant is not None:
                        break
            if self.gagnant is None:
                self.gagnant = self._meilleur_joueur()
            self._ecrire_resultat()
        finally:
            self._fermer_sauvegarde()
        return self.gagnant

    def _meilleur_joueur(self):
        return max(range(self.n), key=lambda p: self._points(p, inclure_prive=True))

    # ------------------------------------------------------------------
    #  Phase de préparation (placements initiaux, ordre serpent)
    # ------------------------------------------------------------------
    def _phase_preparation(self):
        self.phase = C.ETAT_PREP
        ordre = list(range(self.n)) + list(reversed(range(self.n)))
        for idx, p in enumerate(ordre):
            deuxieme = idx >= self.n
            # 1) Placer une colonie
            actions = [{"type": "prep_colonie", "sommet": s}
                       for s in self._sommets_libres_distance()]
            a = self._demander(p, actions)
            sid = a["sommet"]
            self._enregistrer_colonie(p, sid)
            self._maj_route_longue()  # une colonie peut couper une route (cohérence cache)
            if deuxieme:
                self._donner_ressources_initiales(p, sid)
            # 2) Placer une route adjacente
            adj = [e for e in self.plateau.aretes_sommet[sid]
                   if self.proprio_arete[e] == -1]
            actions = [{"type": "prep_route", "arete": list(e)} for e in adj]
            a = self._demander(p, actions)
            e = tuple(a["arete"])
            self.proprio_arete[e] = p
            self.reseau[p].update(e)
            self._graphe_cache = None
            self._maj_route_longue([p])

    def _donner_ressources_initiales(self, p, sid):
        for (res, _num) in self.plateau.tuiles_du_sommet(sid):
            self.ressources[p][res] += 1

    # ------------------------------------------------------------------
    #  Tour d'un joueur
    # ------------------------------------------------------------------
    def _tour_joueur(self, p):
        if self.gagnant is not None:
            return
        self.phase = C.ETAT_DES
        de = self._lancer_des()
        self.dernier_de = de
        if de == 7:
            self._defausse_sur_sept()
            self._phase_voleur(p)
        else:
            self._distribuer(de)
        if self._verifier_victoire():
            return

        # Phase d'actions principale
        self.phase = C.ETAT_JOUEUR
        self.dev_joue_ce_tour = False
        while self.gagnant is None:
            actions = self._actions_legales(p)
            a = self._demander(p, actions)
            if a["type"] == "passer":
                break
            self._appliquer_action(p, a)
            if self._verifier_victoire():
                break

    def _lancer_des(self):
        return self.rng.randint(1, 6) + self.rng.randint(1, 6)

    def _distribuer(self, de):
        """Distribue les ressources produites par le résultat des dés."""
        for (q, r), t in self.plateau.tuiles.items():
            if t["num"] != de or [q, r] == self.voleur:
                continue
            res = t["res"]
            for sid in self.plateau.coins_tuile[(q, r)]:
                p = self.proprio_sommet[sid]
                if p != -1:
                    self.ressources[p][res] += 2 if self.ville_sommet[sid] else 1

    # ------------------------------------------------------------------
    #  Défausse sur un 7
    # ------------------------------------------------------------------
    def _defausse_sur_sept(self):
        """Tout joueur ayant plus de 7 cartes en défausse la moitié (arrondie
        à l'inférieur). Les cartes perdues sont tirées au hasard : le joueur ne
        contrôle pas lesquelles il perd."""
        for p in range(self.n):
            total = self._total_ressources(p)
            if total > C.SEUIL_DEFAUSSE:
                self._defausser_aleatoire(p, total // 2)

    def _defausser_aleatoire(self, p, nombre):
        cartes = [r for r, n in self.ressources[p].items() for _ in range(n)]
        for carte in self.rng.sample(cartes, nombre):
            self.ressources[p][carte] -= 1

    # ------------------------------------------------------------------
    #  Phase voleur (état VOL)
    # ------------------------------------------------------------------
    def _phase_voleur(self, p):
        self.phase = C.ETAT_VOL
        actions = [
            {"type": "voleur", "tuile": [q, r]}
            for (q, r) in self.plateau.tuiles
            if [q, r] != self.voleur
        ]
        a = self._demander(p, actions)
        self._deplacer_voleur(p, tuple(a["tuile"]))
        self.phase = C.ETAT_JOUEUR

    def _deplacer_voleur(self, p, tuile):
        self.voleur = list(tuile)
        # Vole une ressource à un joueur adjacent (au hasard).
        victimes = set()
        for sid in self.plateau.coins_tuile[tuile]:
            q = self.proprio_sommet[sid]
            if q != -1 and q != p and self._total_ressources(q) > 0:
                victimes.add(q)
        if victimes:
            victime = self.rng.choice(sorted(victimes))
            dispo = [r for r, n in self.ressources[victime].items() for _ in range(n)]
            vole = self.rng.choice(dispo)
            self.ressources[victime][vole] -= 1
            self.ressources[p][vole] += 1

    # ------------------------------------------------------------------
    #  Actions légales (phase principale)
    # ------------------------------------------------------------------
    def _actions_legales(self, p):
        actions = [{"type": "passer"}]

        # Construire une route (arête libre reliée au réseau de p)
        if self._peut_payer(p, C.COUT_ROUTE):
            reseau = self.reseau[p]
            for e in self.plateau.aretes:
                if self.proprio_arete[e] == -1 and (e[0] in reseau or e[1] in reseau):
                    actions.append({"type": "construire_route", "arete": list(e)})

        # Construire une colonie (sur le réseau, libre, règle de distance)
        if self._peut_payer(p, C.COUT_COLONIE):
            for sid in sorted(self.reseau[p]):
                if self.proprio_sommet[sid] == -1 and self._distance_ok(sid):
                    actions.append({"type": "construire_colonie", "sommet": sid})

        # Améliorer une colonie en ville
        if self._peut_payer(p, C.COUT_VILLE):
            for sid in sorted(self.colonies_de[p]):
                actions.append({"type": "construire_ville", "sommet": sid})

        # Acheter une carte développement
        if self.paquet_dev and self._peut_payer(p, C.COUT_DEV):
            actions.append({"type": "acheter_dev"})

        # Jouer une carte chevalier
        if self.main_dev[p][C.DEV_CHEVALIER] > 0 and not self.dev_joue_ce_tour:
            actions.append({"type": "jouer_chevalier"})

        # Marché central : acheter / vendre
        for res in C.RESSOURCES:
            if self.cor[p] >= self.prix[res]:
                actions.append({"type": "marche_acheter", "res": res})
            if self.ressources[p][res] >= 1:
                actions.append({"type": "marche_vendre", "res": res})

        # Échanges port / banque
        for donne in C.RESSOURCES:
            taux = self._meilleur_taux(p, donne)
            if self.ressources[p][donne] >= taux:
                for recoit in C.RESSOURCES:
                    if recoit != donne:
                        actions.append({
                            "type": "echange", "donne": donne,
                            "taux": taux, "recoit": recoit,
                        })
        return actions

    # ------------------------------------------------------------------
    #  Application d'une action
    # ------------------------------------------------------------------
    def _appliquer_action(self, p, a):
        t = a["type"]
        if t == "construire_route":
            self._payer(p, C.COUT_ROUTE)
            e = tuple(a["arete"])
            self.proprio_arete[e] = p
            self.reseau[p].update(e)
            self._graphe_cache = None
            self._maj_route_longue([p])  # une route ne change que la longueur de p
        elif t == "construire_colonie":
            self._payer(p, C.COUT_COLONIE)
            self._enregistrer_colonie(p, a["sommet"])  # invalide aussi le cache graphe
            self._maj_route_longue()  # une colonie peut couper une route adverse
        elif t == "construire_ville":
            self._payer(p, C.COUT_VILLE)
            sid = a["sommet"]
            self.ville_sommet[sid] = True
            self.nb_villes[p] += 1
            self.nb_colonies[p] -= 1
            self.colonies_de[p].discard(sid)
            self._graphe_cache = None
        elif t == "acheter_dev":
            self._payer(p, C.COUT_DEV)
            carte = self.paquet_dev.pop()
            self.main_dev[p][carte] += 1
        elif t == "jouer_chevalier":
            self.main_dev[p][C.DEV_CHEVALIER] -= 1
            self.chevaliers_joues[p] += 1
            self.dev_joue_ce_tour = True
            self._maj_plus_grande_armee(p)
            self._phase_voleur(p)
        elif t == "marche_acheter":
            res = a["res"]
            self.cor[p] -= self.prix[res]
            self.ressources[p][res] += 1
            self.prix[res] += 1
        elif t == "marche_vendre":
            res = a["res"]
            gain = max(0, self.prix[res] - 1)
            self.cor[p] += gain
            self.ressources[p][res] -= 1
            self.prix[res] = max(C.PRIX_MIN, self.prix[res] - 1)
        elif t == "echange":
            self.ressources[p][a["donne"]] -= a["taux"]
            self.ressources[p][a["recoit"]] += 1
        else:
            raise ValueError(f"Action inconnue : {a!r}")

    # ==================================================================
    #  Observation (vecteur d'observation décrit dans l'étude)
    # ==================================================================
    def _graphe_observe(self):
        """Graphe dynamique (propriétaires) — mis en cache entre deux constructions."""
        if self._graphe_cache is None:
            sommets = {
                sid: {"joueur": self.proprio_sommet[sid], "ville": self.ville_sommet[sid]}
                for sid in range(self.plateau.nb_sommets)
                if self.proprio_sommet[sid] != -1
            }
            aretes = [[a, b, self.proprio_arete[(a, b)]]
                      for (a, b) in self.plateau.aretes
                      if self.proprio_arete[(a, b)] != -1]
            self._graphe_cache = {"sommets": sommets, "aretes": aretes}
        return self._graphe_cache

    def _observation(self, p):
        """Construit le vecteur d'observation du joueur actif p."""
        return {
            "graphe": self._graphe_observe(),
            "voleur": list(self.voleur),
            "ressources": dict(self.ressources[p]),
            "or": self.cor[p],
            "pv_publics": [self._points(q, inclure_prive=False) for q in range(self.n)],
            "cartes_pv": self.main_dev[p][C.DEV_POINT],
            "cartes_chevalier": self.main_dev[p][C.DEV_CHEVALIER],
            "ressources_adversaires": [self._total_ressources(q) for q in range(self.n)],
            "prix_marche": dict(self.prix),
            # Informations publiques pré-calculées (dérivables du graphe mais
            # coûteuses : on les expose directement pour le modèle de régression).
            "chevaliers_joues": list(self.chevaliers_joues),
            "longueur_routes": list(self.longueur_routes),
            "plus_grande_armee": self.proprio_armee,
            "route_la_plus_longue": self.proprio_route_longue,
        }

    # ==================================================================
    #  Sauvegarde JSONL
    # ==================================================================
    def _ouvrir_sauvegarde(self):
        if self.chemin_sauvegarde:
            os.makedirs(os.path.dirname(self.chemin_sauvegarde) or ".", exist_ok=True)
            self._fichier = open(self.chemin_sauvegarde, "w", encoding="utf-8")

    def _fermer_sauvegarde(self):
        if self._fichier:
            self._fichier.close()
            self._fichier = None

    def _ecrire(self, enregistrement):
        if self._fichier:
            self._fichier.write(json.dumps(enregistrement, ensure_ascii=False) + "\n")

    def _ecrire_meta(self):
        """Première ligne : métadonnées et graphe statique du plateau."""
        self._ecrire({
            "type": "meta",
            "partie": self.partie_id,
            "joueurs": [j.nom for j in self.joueurs],
            "types_joueurs": [j.__class__.__name__ for j in self.joueurs],
            "plateau_statique": self.plateau.serialiser_statique(),
        })

    def _ecrire_resultat(self):
        self._ecrire({
            "type": "resultat",
            "partie": self.partie_id,
            "gagnant": self.gagnant,
            "points": [self._points(p, inclure_prive=True) for p in range(self.n)],
        })

    def _demander(self, p, actions):
        """Envoie l'observation au joueur, reçoit son action, et la sauvegarde."""
        obs = self._observation(p)
        action = self.joueurs[p].decider(obs, actions)
        if action not in actions:
            raise ValueError(
                f"Le joueur {p} a renvoyé une action illégale : {action!r}"
            )
        self._ecrire({
            "type": "step",
            "t": self.t,
            "partie": self.partie_id,
            "phase": self.phase,
            "joueur": p,
            "de": self.dernier_de,
            "observation": obs,
            "actions_legales": actions,
            "action": action,
        })
        self.t += 1
        return action
