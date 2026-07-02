# Créer son propre agent Catan

Ce dossier contient les **agents** : des algorithmes qui jouent au Catan simplifié.
Pour créer le vôtre, il suffit d'**ajouter un fichier `.py` dans ce dossier** qui
définit une classe héritant de `AgentCatan`. Il est alors **détecté automatiquement**.

---

## 1. Démarrage rapide

Créez `agents/mon_agent.py` :

```python
from agent import AgentCatan

class MonAgent(AgentCatan):
    NOM = "mon_agent"          # nom utilisé en ligne de commande

    def jouer_tour(self, observation, actions):
        # Construire une ville si possible, sinon une colonie, sinon passer.
        if actions.construire_villes:
            return actions.construire_villes[0]
        if actions.construire_colonies:
            return actions.construire_colonies[0]
        return actions.passer
```

Puis lancez des parties :

```bash
python play.py --games 100 --j1 mon_agent --j2 random --j3 random --j4 random --cycle
```

C'est tout. Le nom (`--j1 mon_agent`) est l'attribut `NOM` (à défaut, le nom de la
classe en minuscules).

> Vous n'êtes **pas obligé** de tout implémenter : toute méthode non surchargée
> prend une décision **aléatoire** par défaut.



---

## 2. Les quatre décisions à implémenter

| Méthode | Quand | Reçoit | Renvoie |
|---|---|---|---|
| `placement_initial_colonie(observation, sommets)` | placement de départ | liste d'ids de sommets autorisés | l'**id** choisi |
| `placement_initial_route(observation, aretes)` | placement de départ | liste d'arêtes `[a, b]` | l'**arête** choisie |
| `placement_voleur(observation, tuiles)` | dé = 7 ou Chevalier | liste de tuiles `[q, r]` | la **tuile** choisie |
| `jouer_tour(observation, actions)` | pendant le tour | un objet `ActionsTour` | une **action** (dict) |

Ne surchargez **jamais** `decider` : elle aiguille automatiquement vers ces méthodes.

---

## 3. `observation` — ce que vous savez (perception dynamique)

`observation` est un dictionnaire :

```python
observation["ressources"]            # VOS ressources : {"B":1,"W":0,"S":2,"O":1,"C":0}
observation["or"]                    # votre or (entier)
observation["cartes_pv"]             # vos cartes Point de Victoire (privé)
observation["cartes_chevalier"]      # vos cartes Chevalier en main (privé)
observation["prix_marche"]           # {"B":10,"W":11,...} prix d'ACHAT au marché
observation["pv_publics"]            # [pv_j0, pv_j1, ...] points publics de chacun
observation["ressources_adversaires"]# [total_cartes_j0, ...] (on ne voit que le total)
observation["chevaliers_joues"]      # [n_j0, n_j1, ...] chevaliers joués par chacun
observation["longueur_routes"]       # [len_j0, len_j1, ...] plus longue route de chacun
observation["plus_grande_armee"]     # indice du détenteur, ou -1
observation["route_la_plus_longue"]  # indice du détenteur, ou -1
observation["voleur"]                # [q, r] position du voleur
observation["graphe"]["sommets"]     # {id: {"joueur": p, "ville": bool}} (occupés)
observation["graphe"]["aretes"]      # [[a, b, joueur], ...] routes construites
```

Ressources : `"B"`=bois, `"W"`=blé, `"S"`=mouton, `"O"`=minerai, `"C"`=argile.

Votre indice de joueur est `self.indice`.

---

## 4. `self.plateau` — le plateau fixe (perception statique)

Disponible dans toutes les méthodes (rempli en début de partie) :

```python
self.plateau["tuiles"]    # [{"q":0,"r":0,"res":"C","num":6}, ...]
self.plateau["sommets"]   # [{"id":0,"tuiles":[["B",8],["W",4]], "port":"X"}, ...]
self.plateau["aretes"]    # [[a, b], ...] toutes les arêtes du plateau
```

- `sommets` est indexé par id : `self.plateau["sommets"][sid]` donne les tuiles
  `(ressource, numéro)` adjacentes au sommet `sid`, et son `port` éventuel.
- `port` vaut `None`, une ressource (port 2:1) ou `"X"` (port générique 3:1).

---

## 5. `actions` — l'objet `ActionsTour` (dans `jouer_tour`)

Il regroupe les actions légales du tour par catégorie. Vous renvoyez **l'une d'elles** :

```python
actions.passer                 # action "passer" (toujours présente)
actions.construire_routes      # liste d'actions de construction de route
actions.construire_colonies    # liste d'actions de construction de colonie
actions.construire_villes      # liste d'actions de construction de ville
actions.acheter_dev            # action d'achat de carte dév., ou None
actions.jouer_chevalier        # action "jouer un chevalier", ou None
actions.marche_achats          # {ressource: action} pour ACHETER au marché
actions.marche_ventes          # {ressource: action} pour VENDRE au marché
actions.echanges               # liste d'échanges port/banque
actions.toutes                 # la liste brute de toutes les actions légales
```

Une catégorie vide (`[]` ou `None`) signifie que l'action n'est pas possible
(pas les ressources, rien à construire, etc.).

---

## 6. Recettes : comment faire telle ou telle action

Toutes ces actions se renvoient depuis `jouer_tour`.

**Passer le tour**
```python
return actions.passer
```

**Construire une ville / colonie / route** (la première proposée)
```python
return actions.construire_villes[0]      # si la liste n'est pas vide
return actions.construire_colonies[0]
return actions.construire_routes[0]
```

**Acheter une carte développement**
```python
if actions.acheter_dev:
    return actions.acheter_dev
```

**Jouer un Chevalier** (déclenche ensuite le déplacement du voleur)
```python
if actions.jouer_chevalier:
    return actions.jouer_chevalier
```

**Acheter une ressource au marché central** (ex. du bois)
```python
if "B" in actions.marche_achats:                 # achat possible (assez d'or)
    return actions.marche_achats["B"]
# équivalent explicite :
# return {"type": "marche_acheter", "res": "B"}
```

**Vendre une ressource au marché central** (ex. du minerai)
```python
if "O" in actions.marche_ventes:                 # vente possible (on en a au moins 1)
    return actions.marche_ventes["O"]
```

**Échanger avec un port / la banque** (donner plusieurs cartes contre 1)
```python
for e in actions.echanges:
    if e["donne"] == "W" and e["recoit"] == "O":  # donner du blé pour du minerai
        return e
# chaque échange = {"type":"echange","donne":r1,"taux":k,"recoit":r2}
# taux = 4 (banque), 3 (port générique) ou 2 (port de ressource)
```

**Construire à un endroit précis** (en inspectant l'action)
```python
for a in actions.construire_colonies:
    if a["sommet"] == 12:        # poser la colonie sur le sommet 12
        return a
```

> Vous pouvez aussi renvoyer directement un dictionnaire d'action
> (ex. `{"type": "marche_acheter", "res": "B"}`) : il sera accepté **s'il est légal**.

---

## 7. Exemple complet exploitant le plateau

```python
from agent import AgentCatan

class AgentMalin(AgentCatan):
    NOM = "malin"

    def _pips(self, num):                 # probabilité relative d'un numéro
        return 0 if not num else 6 - abs(7 - num)

    def placement_initial_colonie(self, observation, sommets):
        # Sommet le plus productif (somme des pips des tuiles adjacentes).
        return max(sommets, key=lambda sid: sum(
            self._pips(num) for _r, num in self.plateau["sommets"][sid]["tuiles"]))

    def placement_voleur(self, observation, tuiles):
        # Bloquer la tuile la plus productive.
        num = {(t["q"], t["r"]): t["num"] for t in self.plateau["tuiles"]}
        return max(tuiles, key=lambda qr: self._pips(num.get((qr[0], qr[1]))))

    def jouer_tour(self, observation, actions):
        if actions.construire_villes:
            return actions.construire_villes[0]
        if actions.construire_colonies:
            return actions.construire_colonies[0]
        # Compléter le bois manquant au marché si on peut se le payer.
        if "B" in actions.marche_achats and observation["ressources"]["B"] == 0:
            return actions.marche_achats["B"]
        if actions.construire_routes:
            return self.rng.choice(actions.construire_routes)
        if actions.acheter_dev:
            return actions.acheter_dev
        return actions.passer
```

Des aléas (`self.rng`) sont disponibles : `self.rng` est un `random.Random`
initialisé avec la graine de la partie (décisions reproductibles).

---

## 8. Lancer et comparer

```bash
# 500 parties, votre agent contre 3 aléatoires, en faisant tourner les places
python play.py --games 500 --j1 malin --j2 random --j3 random --j4 random --cycle

# duel de deux agents, en parallèle sur 8 cœurs
python play.py --games 1000 --j1 malin --j2 glouton --workers 8 --no-save
```

Le bilan affiche le nombre de victoires par type d'agent. Les parties sont
sauvegardées dans `sauvegardes/` (sauf avec `--no-save`) et peuvent être rejouées
visuellement avec `python view.py`.

---

## 9. Conseils

- **Renvoyez toujours une action légale** : pour `jouer_tour`, prenez-la dans
  `actions` (catégories ci-dessus) ; sinon une exception est levée.
- **Vérifiez qu'une catégorie n'est pas vide** avant d'y accéder
  (`if actions.construire_villes:`).
- **Une seule action par appel** : le moteur rappelle `jouer_tour` tant que vous
  ne renvoyez pas `actions.passer`. Vous pouvez donc enchaîner plusieurs achats /
  constructions sur un même tour, un appel à la fois.
- **Nom unique** : si deux agents déclarent le même `NOM`, le dernier chargé gagne
  (un avertissement s'affiche).

---

## 10. Boîte à outils d'analyse (`tools.py`)

`tools.py` fournit des fonctions prêtes à l'emploi pour analyser le plateau. Le plus
pratique est de construire un `AnalyseurPlateau` une fois par partie :

```python
from agent import AgentCatan
from tools import AnalyseurPlateau, COUTS

class MonAgent(AgentCatan):
    NOM = "mon_agent"

    def nouvelle_partie(self, indice, plateau=None):
        super().nouvelle_partie(indice, plateau)
        self.an = AnalyseurPlateau(plateau)          # cache la structure du plateau

    def jouer_tour(self, observation, actions):
        j = self.indice
        # meilleure colonie constructible selon la production espérée
        spots = self.an.colonies_constructibles(observation, j)
        if spots and actions.construire_colonies:
            meilleur = max(spots, key=self.an.esperance_production)
            for a in actions.construire_colonies:
                if a["sommet"] == meilleur:
                    return a
        return actions.passer
```

Fonctions utiles (méthodes de `AnalyseurPlateau`) :

| Appel | Renvoie |
|---|---|
| `an.ressources_adjacentes(sid)` | ressources productives autour d'un emplacement |
| `an.numeros_adjacents(sid)` / `an.port(sid)` | numéros des tuiles / type de port |
| `an.esperance_production(sid)` | Q_s = espérance de ressources/tour (métrique de l'étude) |
| `an.esperance_ressource(sid, res)` | espérance d'**une** ressource sur ce sommet |
| `an.distance(t1, t2)` | distance (nb de chemins) entre deux terrains |
| `an.distance_au_joueur(obs, j)` | dict `{terrain: nb de routes}` (0 = constructible) |
| `an.colonies_constructibles(obs, j)` | emplacements où poser une colonie maintenant |
| `an.aretes_constructibles(obs, j)` | routes que le joueur peut poser |
| `an.production_joueur(obs, j)` | production espérée par ressource (voleur pris en compte) |
| `an.meilleur_taux(obs, j, res)` | meilleur taux d'échange (4/3/2) via ses ports |
| `an.voleur_menace(obs, j)` | le voleur bloque-t-il un de ses terrains ? |
| `an.peut_payer(obs, COUTS["ville"])` | a-t-il de quoi payer un coût ? |
| `an.ressources_manquantes(obs, COUTS["ville"])` | ce qui lui manque pour ce coût |

Les mêmes fonctions existent aussi au niveau module :
`tools.ressources_adjacentes(self.plateau, sid)`, `tools.distance_au_joueur(...)`, etc.
