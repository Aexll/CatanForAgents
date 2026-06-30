"""Agent d'exemple — modèle commenté à copier pour créer le vôtre.

Copiez ce fichier dans le dossier ``agents/``, renommez la classe et le ``NOM``,
puis remplissez les méthodes. Toute méthode laissée de côté joue aléatoirement.
Une fois le fichier en place, l'agent est utilisable directement :

    python play.py --games 100 --j1 exemple --j2 random --j3 random --j4 random --cycle
"""

from agent import AgentCatan


class MonAgent(AgentCatan):
    """Un agent d'exemple. Remplacez la logique par la vôtre."""

    NOM = "exemple"           # nom utilisé en ligne de commande (--j1 exemple)

    # ------------------------------------------------------------------
    # 1) Placement d'une COLONIE de départ.
    #    `sommets` : identifiants de sommets autorisés. Renvoyez l'id choisi.
    #    `self.plateau["sommets"][sid]["tuiles"]` -> couples (ressource, numéro).
    # ------------------------------------------------------------------
    def placement_initial_colonie(self, observation, sommets):
        def production(sid):
            # Favorise les numéros proches de 7 (6 et 8 = 5 « pips »).
            return sum(6 - abs(7 - num)
                       for _res, num in self.plateau["sommets"][sid]["tuiles"]
                       if num)
        return max(sommets, key=production)

    # ------------------------------------------------------------------
    # 2) Placement d'une ROUTE de départ. `aretes` : arêtes `[a, b]` autorisées.
    # ------------------------------------------------------------------
    def placement_initial_route(self, observation, aretes):
        return self.rng.choice(aretes)

    # ------------------------------------------------------------------
    # 3) Déplacement du VOLEUR. `tuiles` : tuiles `[q, r]` autorisées.
    # ------------------------------------------------------------------
    def placement_voleur(self, observation, tuiles):
        num = {(t["q"], t["r"]): t["num"] for t in self.plateau["tuiles"]}
        pips = lambda n: 0 if not n else 6 - abs(7 - n)
        return max(tuiles, key=lambda qr: pips(num.get((qr[0], qr[1]))))

    # ------------------------------------------------------------------
    # 4) TOUR de jeu. `actions` regroupe les actions par catégorie
    #    (actions.construire_villes, actions.marche_achats[res], ...).
    #    Renvoyez UNE action.
    # ------------------------------------------------------------------
    def jouer_tour(self, observation, actions):
        if actions.construire_villes:
            return actions.construire_villes[0]
        if actions.construire_colonies:
            return actions.construire_colonies[0]
        # Acheter du bois au marché si on n'en a pas et qu'on en a les moyens.
        if "B" in actions.marche_achats and observation["ressources"]["B"] == 0:
            return actions.marche_achats["B"]
        if actions.construire_routes:
            return self.rng.choice(actions.construire_routes)
        if actions.acheter_dev:
            return actions.acheter_dev
        return actions.passer
