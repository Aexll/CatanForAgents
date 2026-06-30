"""agent.py — Interface de haut niveau pour écrire son propre agent Catan.

Pour créer un agent, on ne touche PAS à ce fichier : on ajoute un fichier dans le
dossier ``agents/`` qui définit une classe héritant de ``AgentCatan`` (voir
``agents/COMMENT_CREER_UN_AGENT.md``). L'agent est alors détecté et utilisable
automatiquement (``python play.py --j1 mon_nom ...``).

Ce fichier fournit :
  * ``AgentCatan`` : la classe de base à sous-classer ;
  * ``ActionsTour`` : un objet qui regroupe les actions légales d'un tour par
    catégorie, pour les sélectionner facilement.
"""

import random

from joueur import Joueur


class ActionsTour:
    """Regroupe les actions légales d'un tour par catégorie, pour faciliter
    leur sélection. Fournie à ``AgentCatan.jouer_tour``.

    Attributs :
      - ``passer``              : l'action « passer » (toujours présente) ;
      - ``construire_routes``   : liste d'actions de construction de route ;
      - ``construire_colonies`` : liste d'actions de construction de colonie ;
      - ``construire_villes``   : liste d'actions de construction de ville ;
      - ``acheter_dev``         : action d'achat de carte développement, ou ``None`` ;
      - ``jouer_chevalier``     : action « jouer un chevalier », ou ``None`` ;
      - ``marche_achats``       : dict ``{ressource: action}`` d'achat au marché ;
      - ``marche_ventes``       : dict ``{ressource: action}`` de vente au marché ;
      - ``echanges``            : liste d'échanges port/banque ;
      - ``toutes``              : la liste brute de toutes les actions légales.

    On peut itérer dessus (``for action in actions``) et utiliser ``len(actions)``.
    Chaque « action » est un dict (cf. schéma dans la docstring d'``AgentCatan``).
    """

    def __init__(self, actions):
        self.toutes = actions
        self.passer = next((a for a in actions if a["type"] == "passer"), None)
        self.construire_routes   = [a for a in actions if a["type"] == "construire_route"]
        self.construire_colonies = [a for a in actions if a["type"] == "construire_colonie"]
        self.construire_villes   = [a for a in actions if a["type"] == "construire_ville"]
        self.acheter_dev     = next((a for a in actions if a["type"] == "acheter_dev"), None)
        self.jouer_chevalier = next((a for a in actions if a["type"] == "jouer_chevalier"), None)
        self.marche_achats = {a["res"]: a for a in actions if a["type"] == "marche_acheter"}
        self.marche_ventes = {a["res"]: a for a in actions if a["type"] == "marche_vendre"}
        self.echanges = [a for a in actions if a["type"] == "echange"]

    def __iter__(self):
        return iter(self.toutes)

    def __len__(self):
        return len(self.toutes)


class AgentCatan(Joueur):
    """Classe à sous-classer pour implémenter son propre algorithme de Catan.

    Définissez un attribut de classe ``NOM`` (le nom utilisé en ligne de commande,
    ex. ``--j1 mon_agent``). S'il est absent, le nom de la classe en minuscules est
    utilisé.

    Surchargez seulement les méthodes qui vous intéressent ; celles que vous ne
    surchargez pas prennent une décision **aléatoire** par défaut :

      - ``placement_initial_colonie(observation, sommets)`` -> identifiant de sommet
      - ``placement_initial_route(observation, aretes)``    -> arête ``[a, b]``
      - ``placement_voleur(observation, tuiles)``           -> tuile ``[q, r]``
      - ``jouer_tour(observation, actions)``                -> une action (dict)

    Ne surchargez **pas** ``decider`` : elle aiguille automatiquement le moteur
    vers la bonne méthode ci-dessus.

    ------------------------------------------------------------------
    Données fournies
    ------------------------------------------------------------------
    ``observation`` (perception **dynamique**, dict) contient notamment :
      - ``"graphe"``        : {"sommets": {id: {"joueur", "ville"}}, "aretes": [[a,b,joueur]]}
      - ``"voleur"``        : [q, r] — position du voleur
      - ``"ressources"``    : {ressource: quantité} — VOS ressources
      - ``"or"``            : votre or
      - ``"pv_publics"``    : [points par joueur]
      - ``"cartes_pv"``     : vos cartes Point de Victoire (privé)
      - ``"cartes_chevalier"`` : vos cartes Chevalier en main (privé)
      - ``"ressources_adversaires"`` : [total de cartes par joueur]
      - ``"prix_marche"``   : {ressource: prix}
      - ``"chevaliers_joues"`` : [chevaliers joués par joueur]
      - ``"longueur_routes"``  : [longueur de route par joueur]
      - ``"plus_grande_armee"`` / ``"route_la_plus_longue"`` : indice du détenteur, ou -1

    ``self.plateau`` (perception **fixe**, dict) contient :
      - ``"tuiles"``  : [{"q", "r", "res", "num"}, ...]
      - ``"sommets"`` : [{"id", "tuiles": [[res, num], ...], "port"}, ...]  (indexé par id)
      - ``"aretes"``  : [[a, b], ...]

    ------------------------------------------------------------------
    Schéma des actions (ce que ``jouer_tour`` peut renvoyer)
    ------------------------------------------------------------------
      {"type": "passer"}
      {"type": "construire_route",   "arete": [a, b]}
      {"type": "construire_colonie", "sommet": id}
      {"type": "construire_ville",   "sommet": id}
      {"type": "acheter_dev"}
      {"type": "jouer_chevalier"}
      {"type": "marche_acheter", "res": r}
      {"type": "marche_vendre",  "res": r}
      {"type": "echange", "donne": r1, "taux": k, "recoit": r2}

    Le plus simple est de renvoyer une action issue de l'objet ``ActionsTour``
    fourni (ex. ``actions.construire_villes[0]`` ou ``actions.passer``).
    """

    NOM = None  # nom du type (CLI) ; si None, le nom de la classe en minuscules

    def __init__(self, nom=None, seed=None):
        super().__init__(nom)
        self.rng = random.Random(seed)

    # ---- Aiguillage (NE PAS surcharger) -----------------------------
    def decider(self, observation, actions_legales):
        types = {a["type"] for a in actions_legales}
        if types == {"prep_colonie"}:
            sommets = [a["sommet"] for a in actions_legales]
            return self._resoudre(
                self.placement_initial_colonie(observation, sommets),
                actions_legales, cle="sommet")
        if types == {"prep_route"}:
            aretes = [a["arete"] for a in actions_legales]
            return self._resoudre(
                self.placement_initial_route(observation, aretes),
                actions_legales, cle="arete")
        if types == {"voleur"}:
            tuiles = [a["tuile"] for a in actions_legales]
            return self._resoudre(
                self.placement_voleur(observation, tuiles),
                actions_legales, cle="tuile")
        choix = self.jouer_tour(observation, ActionsTour(actions_legales))
        return self._resoudre(choix, actions_legales, cle=None)

    # ---- Méthodes à surcharger (défauts aléatoires) -----------------
    def placement_initial_colonie(self, observation, sommets):
        """Choisit le sommet où poser une colonie de départ (renvoie un id)."""
        return self.rng.choice(sommets)

    def placement_initial_route(self, observation, aretes):
        """Choisit l'arête où poser une route de départ (renvoie ``[a, b]``)."""
        return self.rng.choice(aretes)

    def placement_voleur(self, observation, tuiles):
        """Choisit la tuile où déplacer le voleur (renvoie ``[q, r]``)."""
        return self.rng.choice(tuiles)

    def jouer_tour(self, observation, actions):
        """Choisit l'action du tour (renvoie une action de ``actions``)."""
        return self.rng.choice(actions.toutes)

    # ---- Résolution interne -----------------------------------------
    def _resoudre(self, choix, actions, cle):
        """Convertit la valeur renvoyée par l'agent en une action légale."""
        if isinstance(choix, dict):
            if choix in actions:
                return choix
            raise ValueError(f"{self.nom} : action renvoyée illégale : {choix!r}")
        if cle is None:
            raise ValueError(
                f"{self.nom} : jouer_tour doit renvoyer une action (dict).")
        for a in actions:
            v = a.get(cle)
            if v == choix or (isinstance(v, list)
                              and isinstance(choix, (list, tuple))
                              and list(choix) == v):
                return a
        raise ValueError(f"{self.nom} : choix illégal {choix!r} pour « {cle} ».")
