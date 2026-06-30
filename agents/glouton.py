"""Agent glouton — exemple heuristique simple (registré sous le nom « glouton »)."""

from agent import AgentCatan


class AgentGlouton(AgentCatan):
    """Exemple pédagogique : agent heuristique glouton.

    Montre comment exploiter à la fois ``observation`` (dynamique) et
    ``self.plateau`` (statique). Stratégie simple :
      - placement initial sur le sommet le plus productif (somme des « pips ») ;
      - voleur sur la tuile la plus productive ;
      - à son tour : ville > colonie > route > carte dev > passer.
    """

    NOM = "glouton"

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
        if actions.construire_villes:
            return actions.construire_villes[0]
        if actions.construire_colonies:
            return actions.construire_colonies[0]
        if actions.construire_routes:
            return self.rng.choice(actions.construire_routes)
        if actions.acheter_dev:
            return actions.acheter_dev
        return actions.passer
