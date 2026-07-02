

from agent import AgentCatan
from tools import AnalyseurPlateau, proba_des, COUTS


class Simple3(AgentCatan):
    """
    Agent qui joue de manière simple, en essayant de construire des colonies et des villes
    """

    NOM = "trader"

    def nouvelle_partie(self, indice, plateau=None):
        super().nouvelle_partie(indice, plateau)
        self.an = AnalyseurPlateau(plateau)          # cache la structure du plateau


    def placement_initial_colonie(self, observation, sommets):
        return self.an.classer_par_production(sommets)[0]
        # return max(sommets, key=self._valeur_sommet)

    def placement_initial_route(self, observation, aretes):

        def _val_route(route):
            s1, s2 = route[0], route[1]
            somme = 0
            t1 = self.an.distances_depuis(s1)
            t2 = self.an.distances_depuis(s2)
            # print("Distances depuis ", s1, " : ", t1)
            keys = set(t1.keys()).union(set(t2.keys()))
            for s in keys:
                k = min(t1.get(s, 10),t2.get(s, 10))
                somme += 1/(k+1) * self.an.esperance_production(s)
            return somme

        aretes.sort(key=lambda x: _val_route(x),reverse=True)
        # print("placement route", aretes)
        return aretes[0]

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


        # si on a moyen de gagner avec la plus grande armée on le fait
        detenteur_armee = observation["plus_grande_armee"]
        if detenteur_armee != self.indice:
            if observation["chevaliers_joues"][self.indice] + observation["cartes_chevalier"] > observation["chevaliers_joues"][detenteur_armee] and actions.jouer_chevalier:
                return actions.jouer_chevalier


        # on essaye de construire une ville si on a les ressources
        if actions.construire_villes:
            return actions.construire_villes[0]
        # de meme pour les colonies
        if actions.construire_colonies:
            actions.construire_colonies.sort(key=lambda x: self.an.esperance_production(x["sommet"]))
            return actions.construire_colonies[-1]




        # # Choix des ressources à acheter pour construire les bâtiments

        ressources_manquantes = {
        "colonie": self.an.ressources_manquantes(observation, COUTS["colonie"]),
        "ville": self.an.ressources_manquantes(observation, COUTS["ville"]),
        "dev": self.an.ressources_manquantes(observation, COUTS["dev"]),
        "route": self.an.ressources_manquantes(observation, COUTS["route"]),
        }

        cout_construction = {}
        for construction, ressources in ressources_manquantes.items():
            cout = 0
            for ressource, manquant in ressources.items():
                cout += manquant * observation["prix_marche"][ressource] + (manquant * (manquant-1) // 2) # On prends en compte le fait que le prix augmente de 1 or par ressource achetée
            cout_construction[construction] = cout


        # print()
        # comme pas toutes les constructions se vallent on pondère le cout de chaque construction par un facteur qui dépend de la construction
        construction_ponderation = {
        "colonie": 2 if len(self.an.colonies_constructibles(observation,self.indice))!=0 else 0.1,
        "ville": 2,
        "dev": 0.5,
        "route": 1
        }

        choix_construction = min(cout_construction, key=lambda x: cout_construction[x] / construction_ponderation[x])
        ressources_a_garder = set(ressources_manquantes[choix_construction].keys())
        # print("Construction choisie : ", choix_construction, " avec un cout de ", cout_construction[choix_construction], " et une ponderation de ", construction_ponderation[choix_construction])
        for ressource, manquant in ressources_manquantes[choix_construction].items():
            if manquant > 0 and observation["or"] >= observation["prix_marche"][ressource]:
                return {"type": "marche_acheter", "res": ressource}


        

        if actions.construire_routes:
            
            def _val_route(route):
                s1, s2 = route[0], route[1]
                somme = 0
                t1 = self.an.distances_depuis(s1)
                t2 = self.an.distances_depuis(s2)
                # print("Distances depuis ", s1, " : ", t1)
                keys = set(t1.keys()).union(set(t2.keys()))
                for s in keys:
                    k = min(t1.get(s, 10),t2.get(s, 10))
                    if self.an.respecte_distance(observation, self.indice):
                        somme += 1/(k+1) * self.an.esperance_production(s)
                # print("valeur route ", route, " : ", somme)
                return somme

            # print("Routes possibles : ", actions.construire_routes)
            actions.construire_routes.sort(key=lambda x: _val_route(x["arete"]))
            return actions.construire_routes[-1]

        # On achete carte dev
        if actions.acheter_dev:
            return actions.acheter_dev
        

        # On cherches la valeur "perçue" pour le joueur de chaque ressource, en fonction de la production de ses colonies et villes
        # print()
        valeur_de_vente_percue = {r:observation["prix_marche"][r] * p * observation["ressources"][r] for r,p in self.an.production_joueur(observation, self.indice).items()}


        res_final = set(["B", "C", "W", "S", "O"]).difference(ressources_a_garder)
        for res in res_final:
            if observation["ressources"][res] > 1 and res in actions.marche_ventes and valeur_de_vente_percue[res] > -1:
                return actions.marche_ventes[res]



        # si on a plus de 7 ressources on vends les ressources les plus chères au marché
        # if sum(observation["ressources"].values()) > 7:
        #     prix_ressources = observation["prix_marche"]
        #     ressource_a_vendre = max(prix_ressources, key=prix_ressources.get)
        #     if ressource_a_vendre in actions.marche_ventes:
        #         return {"type": "marche_vendre", "res": ressource_a_vendre}

        return actions.passer
