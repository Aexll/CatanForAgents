

from agent import AgentCatan
from tools import AnalyseurPlateau, proba_des


class Simple2(AgentCatan):
    """
    Agent qui joue de manière simple, en essayant de construire des colonies et des villes
    """

    NOM = "simple2"

    def nouvelle_partie(self, indice, plateau=None):
        super().nouvelle_partie(indice, plateau)
        self.an = AnalyseurPlateau(plateau)          # cache la structure du plateau


    def placement_initial_colonie(self, observation, sommets):
        return self.an.classer_par_production(sommets)[0]
        # return max(sommets, key=self._valeur_sommet)

    def placement_voleur(self, observation, tuiles):
        if not self.plateau:
            return self.rng.choice(tuiles)
        
        res = []
        for t in tuiles:
            weight = 0
            for b in self.an.batiments_sur_tuile(observation, t[0], t[1]):
                num = self.an.tuile_coord[tuple(t)][1]
                if b[1] != self.indice:
                    weight += (2 if b[2] else 1) * proba_des(num)
                else:
                    weight -= (2 if b[2] else 1) * proba_des(num)
            res.append((t, weight))
        res.sort(key=lambda x: x[1], reverse=True)

        return res[0][0]

    def jouer_tour(self, observation, actions):

        # Scalping méchanique
        # for ressource_a, prix_a in observation["prix_marche"].items():
        #     for ressource_b, prix_b in observation["prix_marche"].items():
        #         if ressource_a != ressource_b and prix_a > (prix_b) * 5:
        #             if observation["ressources"][ressource_a] > 1:
        #                 return {"type": "marche_vendre", "res": ressource_a}
        #             if observation["prix_marche"][ressource_b] < observation["or"]:
        #                 return {"type": "marche_acheter", "res": ressource_b}
        #             for e in actions.echanges:
        #                 if e["donne"] == ressource_b and e["recoit"] == ressource_a:
        #                     return e
        

        # si le voleur est sur une de nos tuiles on le deplace
        if self.an.voleur_menace(observation, self.indice) and actions.jouer_chevalier:
            return actions.jouer_chevalier

        # on essaye de construire une ville si on a les ressources
        if actions.construire_villes:
            return actions.construire_villes[0]
        # de meme pour les colonies
        if actions.construire_colonies:
            actions.construire_colonies.sort(key=lambda x: self.an.esperance_production(x["sommet"]))
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
        if observation["or"] >= observation["prix_marche"]["O"] and observation["ressources"]["O"] < 3:
            return {"type": "marche_acheter", "res": "O"}



        cout_colonie = {"B": 1, "C": 1, "W": 1, "S": 1}
        cout_ville = {"W": 2, "O": 3}

        # On vends le surplus de ressources au marché si on a plus de 1 ressource et qu'on ne peut pas construire de routes
        if observation["ressources"]["B"] > 1 and "B" in actions.marche_ventes and not actions.construire_routes  and observation["prix_marche"]["B"] > 0:                 # vente possible (on en a au moins 1)
            return actions.marche_ventes["B"]
        
        if observation["ressources"]["C"] > 1 and "C" in actions.marche_ventes and not actions.construire_routes and observation["prix_marche"]["C"] > 0:                 # vente possible (on en a au moins 1)
            return actions.marche_ventes["C"]
        

        if actions.construire_routes:
            return self.rng.choice(actions.construire_routes)

        # On achete carte dev
        if actions.acheter_dev:
            return actions.acheter_dev
        

        # On vends le surplus de ressources au marché 
        if observation["ressources"]["W"] > 1 and "W" in actions.marche_ventes and observation["prix_marche"]["W"] > 0:                 # vente possible (on en a au moins 1)
            return actions.marche_ventes["W"]
        
        if observation["ressources"]["S"] > 1 and "S" in actions.marche_ventes and observation["prix_marche"]["S"] > 0:                 # vente possible (on en a au moins 1)
            return actions.marche_ventes["S"]
        
        if observation["ressources"]["O"] > 3 and "O" in actions.marche_ventes and observation["prix_marche"]["O"] > 0:                 # vente possible (on en a au moins 1)
            return actions.marche_ventes["O"]
        


        # si on a plus de 7 ressources on vends les ressources les plus chères au marché
        # if sum(observation["ressources"].values()) > 7:
        #     prix_ressources = observation["prix_marche"]
        #     ressource_a_vendre = max(prix_ressources, key=prix_ressources.get)
        #     if ressource_a_vendre in actions.marche_ventes:
        #         return {"type": "marche_vendre", "res": ressource_a_vendre}

        return actions.passer
