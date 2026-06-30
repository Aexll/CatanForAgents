"""Agent « axel » — variante glouton qui complète ses ressources au marché."""

from agent import AgentCatan


class AgentGlouton2(AgentCatan):
    """Variante glouton : achète au marché les ressources manquantes.

    Montre comment exploiter à la fois ``observation`` (dynamique) et
    ``self.plateau`` (statique). Stratégie simple :
      - placement initial sur le sommet le plus productif (somme des « pips ») ;
      - voleur sur la tuile la plus productive ;
      - à son tour : ville > colonie > (achat des ressources manquantes) > route
        > carte dev > passer.
    """

    NOM = "axel"

    @staticmethod
    def _pips(num):
        # « pips » = poids de probabilité du jeton (6 et 8 valent 5, 2 et 12 valent 1).
        return 0 if not num else 6 - abs(7 - num)

    def _valeur_sommet(self, sid):
        if not self.plateau:
            return 0
        return sum(self._pips(num)
                   for _res, num in self.plateau["sommets"][sid]["tuiles"])

    def placement_initial_colonie(self, observation, sommets):
        return max(sommets, key=self._valeur_sommet)

    def placement_voleur(self, observation, tuiles):
        if not self.plateau:
            return self.rng.choice(tuiles)
        num = {(t["q"], t["r"]): t["num"] for t in self.plateau["tuiles"]}
        return max(tuiles, key=lambda qr: self._pips(num.get((qr[0], qr[1]))))

    def jouer_tour(self, observation, actions):

        # on essaye de construire une ville si on a les ressources
        if actions.construire_villes:
            return actions.construire_villes[0]
        # de meme pour les colonies
        if actions.construire_colonies:
            return actions.construire_colonies[0]

        # si c'est un problème de ressources on essaye d'acheter les ressources manquantes au marché
        if observation["or"] >= observation["prix_marche"]["B"] and observation["ressources"]["B"] < 1:
            return {"type": "marche_acheter", "res": "B"}
        if observation["or"] >= observation["prix_marche"]["C"] and observation["ressources"]["C"] < 1:
            return {"type": "marche_acheter", "res": "C"}
        if observation["or"] >= observation["prix_marche"]["W"] and observation["ressources"]["W"] < 1:
            return {"type": "marche_acheter", "res": "W"}
        if observation["or"] >= observation["prix_marche"]["S"] and observation["ressources"]["S"] < 1:
            return {"type": "marche_acheter", "res": "S"}

        if actions.construire_routes:
            return self.rng.choice(actions.construire_routes)

        if actions.acheter_dev:
            return actions.acheter_dev

        # si on a plus de 7 ressources on vends les ressources les plus chères au marché
        # if sum(observation["ressources"].values()) > 7:
        #     prix_ressources = observation["prix_marche"]
        #     ressource_a_vendre = max(prix_ressources, key=prix_ressources.get)
        #     if ressource_a_vendre in actions.marche_ventes:
        #         return {"type": "marche_vendre", "res": ressource_a_vendre}

        return actions.passer
