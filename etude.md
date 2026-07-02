Analyse mathématique du jeu "Catan"

Le jeu "Catan" est un jeu de société stratégique qui implique la collecte de ressources, la construction de routes et de colonies, et l'interaction avec d'autres joueurs.


pour rendre plus simple le système de commerce et de négociation, nous utiliserons une version simplifiée du jeu, possèdant un marché
central, ainsi qu'une nouvelle ressource d'or, qui pourra être utilisée pour acheter des ressources à un taux variable.

Cette version simplifiée retire les interactions directes entre les joueurs, et se concentre sur la gestion des ressources et la planification stratégique. mais tout en gardant l'essence du jeu original.


dans un premier temps les cartes développement seront grandement simplifiées,


le jeu original comporte des cartes développement suivantes: 

Les cartes Chevalier (14 cartes) : permettent de déplacer le voleur et voler une ressource à un autre joueur. de plus le joueur qui possède le plus de cartes chevalier (après 3) peut obtenir la carte "plus grande armée" qui vaut 2 points de victoire.



Les cartes Progrès (6 cartes)

Ces cartes offrent des bonus tactiques en ressources ou en construction. Il en existe 3 types différents, chacun présent en 2 exemplaires :

Construction de routes (x2) : Vous permet de placer gratuitement 2 routes sur le plateau.

Invention / Progrès scientifique (x2) : Vous permet de prendre gratuitement 2 cartes Ressource de votre choix dans la banque.

Monopole (x2) : Vous nommez une ressource (par exemple : le blé). Tous les autres joueurs doivent vous donner toutes les cartes de cette ressource qu'ils ont en main.


Les cartes Point de Victoire (5 exemplaires)
Ces cartes représentent des bâtiments ou des lieux importants de votre colonie.
Effet : Chaque carte vaut 1 point de victoire.
Particularité : Contrairement aux autres cartes Développement, vous ne les révélez pas aux autres joueurs lorsque vous les piochez. Vous les gardez cachées en main et vous ne les dévoilez qu'à la toute fin de la partie pour annoncer votre victoire lorsque vous atteignez les 10 points.


Dans notre version simplifiée, nous retirons les cartes Progrès.
ainsi chaques joueur à ses points de victoires 'public' et 'privé'. Les points de victoire publics sont visibles par tous les joueurs, tandis que les points de victoire privés sont cachés jusqu'à la fin du jeu.

le fait de retirer les cartes Progrès simplifie la perception des joueurs pour le RL.



---

Plus grande armée et route la plus longue

deux récompenses accordent chacune 2 points de victoire publics, et sont transférables au cours de la partie :

- Plus grande armée : accordée au joueur ayant joué le plus de cartes Chevalier, dès lors qu'il en a joué au moins 3. si un autre joueur le dépasse strictement (en nombre de chevaliers joués), la récompense change de main.

- Route la plus longue : accordée au joueur possédant la plus longue chaîne continue de routes, d'au moins 5 segments. en cas d'égalité, le détenteur actuel conserve la récompense. une chaîne ne peut pas traverser une intersection occupée par une colonie ou une ville adverse : une colonie adverse peut donc couper une route et faire perdre (ou réduire) la plus longue route.



---

Marché central:

chaques joueur commence la partie avec 10 d'or, et le marché central est initialisé
avec un prix initial de 10 d'or pour chaque ressource. Le prix des ressources au marché central évolue en fonction de l'offre et de la demande, et les joueurs peuvent acheter ou vendre des ressources à ce marché.
à chaques ressources achetées, le prix de la ressource augmente de 1 d'or, et à chaques ressources vendues, le prix de la ressource diminue de 1 d'or. Le prix des ressources ne peut pas descendre en dessous de 1 d'or. mais peut augmenter sans limite.

exemple : si le prix du bois est de 10 d'or, et qu'un joueur achète 2 bois, le prix du bois passera à 12 d'or. et le joueur aura dépensé 21 d'or (10 + 11). si un autre joueur vend 1 bois, le prix du bois passera à 11 d'or. et le joueur recevra 11 d'or pour la vente.

pour l'aspect visuel, on a pour chaques ressources deux prix, vente et achat, avec 1 d'or d'écart.

|Bois |
|-----|
|achat 10 |
|vente 9 |


---


Plateau et Perception


Nous distinguons deux types de perception dans le jeu : 

celle qui est fixé, qui ne varie pas au cours de la partie, 
et celle qui est dynamique, qui évolue en fonction des actions des joueurs.


dans la perception fixé nous incluons les éléments suivants :
- la disposition des tuileset les numéros associés à chaque tuile.
- la disposition des ports et leur type.

dans la perception dynamique nous incluons les éléments suivants :
- position des colonies villes et des routes des joueurs.
- poisition du voleur.
- les ressources possédées le joueur
- le nombre de ressources possédées par les autres joueurs.
- le cout des ressources au marché central.


certaines choses ne seront pas ajouté directement à la perception dynamique, mais seront plutôt des informations que le joueur pourra déduire à partir de ses observations

nous n'incluons pas dans la perception dynamique les éléments suivants :
- les ressources possédées par les autres joueurs.
- les ressources disponibles dans la banque.
- le nombre de cartes développement possédées par les autres joueurs.
- le nombre de points de victoire des autres joueurs.

---

Tours d'un joueur


les dés sont lancé, et les ressources sont distribuées en fonction du résultat des dés et de la position des colonies et villes des joueurs.

en suite si le dé n'a pas fait 7, le joueur peut ainsi jouer son tour (Normalement)
s'il a fait 7 il peut alors déplacer le voleur et voler une ressource à un autre joueur, puis il peut jouer son tour normalement.

de plus, lorsqu'un 7 est obtenu, chaque joueur (y compris le joueur actif) possédant plus de 7 cartes ressource doit en défausser la moitié (arrondie à l'entier inférieur). ces cartes sont choisies aléatoirement : le joueur ne contrôle pas les cartes qu'il perd.

l'effet de déplacement du voleur sera représenté par un état particulier de la machine d'état du jeu, nomons l'état VOL
qui pourras aussi être déclanché au moment ou un joueur joue une carte chevalier.


au moment du tours les actions suivantes sont possibles pour le joueur :

- Acheter et Vendre des ressources au marché central.
- échanger des ressources avec les ports (ou 4 pour 1 avec la banque).
- Construire des routes, colonies et villes.
- Acheter des cartes développement.
- Jouer une carte chevalier
- passer


celà permet de créer une routine indépendante des autres joueurs
mais tout en gardant l'interaction indirecte avec les autres joueurs à travers le marché central et les cartes chevalier.


--- 


Machine d'état du jeu


Le jeux posséde une machine d'état qui représente les différentes phases du jeu et les transitions entre elles. Les états principaux sont les suivants :


- État de préparation : Les joueurs placent leurs colonies et routes initiales sur le plateau.

- État de lancer de dés : les dés sont lancés pour déterminer quelles ressources sont produites et distribuées aux joueurs.

- État de tour du joueur : Le joueur actif peut effectuer ses actions (acheter/vendre des ressources, construire, jouer des cartes, etc.).


GLOBAL :

PREP -> DES <-> JOUEUR


JOUEUR :

DEBUT DE TOUR -|Carte Voleur|-> VOL
|
v
JEUX <-|Carte Voleur|-> VOL
|
v
PASS



---

Représentation du plateau 

Le plateau de jeu est représenté par un graphe, où les sommets représentent les intersections (où les colonies et villes peuvent être construites) et les arêtes représentent les routes. Chaque sommet est associé à une tuile de ressource, et chaque tuile a un numéro qui détermine la production de ressources lorsque ce numéro est lancé avec les dés.


pour simplifier nous nomerons les ressources: 

B : bois
W : blé (wheat)
S : mouton (sheep)
O : minerais (ore)
C : argile (clay)
X : rien (desert ou mer)


Le plateau est une grille hexagonale, ainsi nous utiliserons un système de coordonnées "Axial"
la position de chaque tuile sera représentée par un couple (q, r), où q est la coordonnée horizontale et r est la coordonnée verticale. 

ainsi la tuile (0,0) sera la tuile centrale du plateau,
la tuile (1,0) sera la tuile à sa droite
(0,1) bas à droite
(-1,1) bas à gauche
(-1,0) à gauche
(0,-1) haut à gauche
(1,-1) haut à droite


un plateau est donc une liste de tuiles, chaque tuile étant représentée par un triplet (q, r, r, n),
où (q, r) sont les coordonnées de la tuile, r est le type de ressource et n est le numéro associé à la tuile.

(0,0, C, 6) : la tuile centrale est une tuile d'argile avec le numéro 6

....


Pour représenter le placement des villes et colonies, nous utiliserons un graphe G = (V, E), où V est l'ensemble des sommets représentant les intersections et E est l'ensemble des arêtes représentant les routes. Chaque sommet v ∈ V peut être occupé par une colonie ou une ville appartenant à un joueur. Les arêtes e ∈ E représentent les routes construites par les joueurs entre les intersections.


chaques somet v ∈ V est représenté par 3 couples (r, n) ou r est une ressource et n est le numéro associé à la tuile. cependant, contrairement aux tuiles, les port apparaissent sous la forme d'un couple (r, -1) où r est le type de ressource du port, ou (X, -1) pour un port 3 pour 1.
ainsi que un index représentant le joueur qui possède la colonie ou la ville sur ce sommet, ou -1 si le sommet est libre. puis une valeur booléenne indiquant si le sommet est occupé par une ville (true) ou une colonie (false).

exemple : ((B,8),(W, 4),(C, -1), -1, false) : sommet libre, adjacent à une tuile de bois avec le numéro 8, une tuile de blé avec le numéro 4 et un port 1:2 d'argile.



chaques arête e ∈ E est représentée par un triplet (v1, v2, r) où v1 et v2 sont les sommets qu'elle relie, ainsi que r représentant le joueur qui possède la route sur cette arête, ou -1 si l'arête est libre.


ainsi le graph G remplaces toutes autres représentations du plateau,

pour conclure la partie représentation, 

un joueur a accès aux informations suivantes:

- le graph G
- les ressources possédées par le joueur (sous forme d'un dictionnaire {ressource: quantité})
- les points de victoire publics de chaque joueur (sous forme d'une liste [points_joueur1, points_joueur2, ...])
- les cartes point de victoire possédées par le joueur (un entier)
- les cartes chevalier possédées par le joueur (un entier, en main, privé)
- le nombre de ressources possédées par les autres joueurs (sous forme d'une liste [ressources_joueur1, ressources_joueur2, ...])
- le prix des ressources au marché central (sous forme d'un dictionnaire {ressource: prix})
- le nombre de chevaliers joués par chaque joueur (sous forme d'une liste [chevaliers_joueur1, ...], information publique)
- la longueur de la route la plus longue de chaque joueur (sous forme d'une liste [longueur_joueur1, ...])
- le détenteur de la plus grande armée (un entier, ou -1 si personne)
- le détenteur de la route la plus longue (un entier, ou -1 si personne)

les trois dernières familles d'informations sont en théorie déductibles du graphe G (les chevaliers joués sont publics, et les longueurs de route se calculent à partir des arêtes). cependant, calculer la route la plus longue revient à résoudre un problème de plus long chemin (combinatoire, global), qu'un modèle de régression ne saura pas reconstituer à partir de la seule structure du graphe. comme ces informations sont publiques, nous les pré-calculons et les exposons directement dans l'observation : cela ne révèle aucune information cachée et évite au modèle d'avoir à les reconstruire.

celà sera en suite utiliser par le model d'apprentissage par renforcement pour prendre des décisions.



---

Structure du programme

pour pouvoir faire jouer des agents intelligents, nous avons déjà besoin d'un moteur du jeu, qui gère les règles et l'état du jeu.

Il doit pouvoir lancer des parties, envoyer l'état du jeu à chaque joueur, recevoir les actions des joueurs, et mettre à jour l'état du jeu en conséquence, gérer les conditions de fin de partie.

de plus le moteur doit pouvoir générer une sauvegare de la partie, sous forme d'un fichier JSONL
ou chaques lignes indique l'état du jeu à un moment t, ainsi que l'action effectuée par le joueur actif à ce moment t.

Il doit aussi être muni d'un systeme de représentation visuelle, (avec dearpygui) pour permettre de visualiser le déroulement de la partie.

la structure du programme sera donc composée de plusieurs modules :

- moteur.py : Contient la logique du jeu, les règles, la machine d'état, et la gestion des tours des joueurs.
- joueur.py : Contient la classe de base représentant un joueur, contenant donc les fonctions pour recevoir l'état du jeu, décider d'une action, et envoyer cette action au moteur.
plusieurs classes dérivées de cette classe de base pourront être créées pour représenter différents types de joueurs (joueurs humains, joueurs IA, etc.).
- Constantes.py : Contient les constantes du jeu, telles que les types de ressources, les types de cartes développement, les coûts de construction, etc.
- play.py : Contient le code pour lancer une partie, initialiser les joueurs, et gérer le déroulement de la partie.

exemple d'utilisation du programme :
`python play.py --games 500 --j1 rl --j2 random --j3 random --j4 random --cycle` : lance 500 partie avec 4 joueurs, dont 3 randoms et un joueur utilisant l'algorithme d'apprentissage par renforcement.
ou la disposition des joueurs cycle entre chaques parties.




---

# PARTIE 2


trouver une métrique corélée à la victoire.

beaucoup des désision à catan sont des compromis entre plusieurs objectifs, et il est difficile de savoir si une décision est bonne ou mauvaise. pour résoudre ce problème, il peut être intéréssant
de calculer différentes métriques, et observer leur corrélation avec la victoire. 

si ces métriques sont pertinentes, elles pourront être utilisées dans les algorithmes d'agents


**Definitions**

nous nomerons un **terrain**, un noeud du graphe G, qui est un emplacement de colonie ou ville.
et **chemin** les arêtes du graphe G, sur lesquelles des routes peuvent être construites. 

ainsi tout chemin est adjacent à deux terrains, et tout terrain est adjacent à 3 chemins.

la **distance** $D(t_1,t_2)$ entre deux terrains est le plus petit nombre de chemins qu'il faut parcourir pour aller d'un terrain à l'autre 

> un terrains est toujours à distance 0 de lui même, et deux terrains adjacents sont à distance 1.


la **distance pour un joueur** $D_j(t_1,t_2)$ entre deux terrains $t_1$ et $t_2$ est le plus petit nombre de chemins constructible par le joueur, qu'il faut parcourir pour aller d'un terrain à l'autre.


Il est important de bien comprendre les règles de placement sur les colonies et les routes
en effet, un joueur ne peut pas construire une colonie sur un terrain adjacent à une autre colonie ou ville. de plus une route ne peut pas traverser une colonie ou ville adverse.

Ainsi pour qu'un terrain soit constructible par un joueur, il faut qu'il soit à distance 2 de toutes autre colonies ou villes, et qu'il soit adjacent à au moins un chemin constructible par le joueur.


nous pouvons ainsi créer une nouvelle mesure :
La **distance au joueur** d'un terrain $t$ pour un joueur $j$, notée $D_j(t)$
définit récursivement comme suit :
vaut 0 si $t$ est constructible par le joueur $j$
Si $D_j(t) = n$ et que $t'$ est adjacent à $t$ par un chemin constructible par le joueur $j$, alors $D_j(t') = n + 1$.


## I - choix du placement inital

### 1 - metrique de production

dans les parties de catan professionnelles, 5 minutes sont consacrées au placement initial des colonies et routes. le placement initial est crucial, il détermine:
- les ressources que le joueur pourra produire
- le placement des futurs routes et colonies


la première choses pertinente à calculer est l'espérance de production des emplacement

le plateau est composé de 19 tuiles, chacune ayant un numéro associé. les numéros vont de 2 à 12, et 
il y a un seul 2 et 12, et deux de chaque numéro de 3 à 11. le 7 est absent.

> la production d'une tuile de numéro 12 a une probabilité de 1/36


Commençons par les bases,

Notons la variable aléatoire D le résultat du lancer de deux dés à 6 faces. la probabilité d'obtenir un numéro n est donnée par la formule suivante :

$P(D=n) = \frac{6 - |n-7|}{36}$

Notons $X_i$ la variable aléatoire représentant le nombre de ressources produites par la tuile $i$, et notons $n_i$ le numéro associé à la tuile $i$. 

On remarque que $X_i$ suit une loi de Bernoulli, avec une probabilité de succès égale à la probabilité d'obtenir le numéro $n_i$ sur le lancer de dés, $P(D=n_i)$. Ainsi, l'espérance de $X_i$ est donnée par :

$$E[X_i] = P(D=n_i)$$

ainsi une colonie construite sur une intersection adjacente à 3 tuiles $i$, $j$ et $k$ produira en moyenne :

$$E[X_i + X_j + X_k] = E[X_i] + E[X_j] + E[X_k] = P(D=n_i) + P(D=n_j) + P(D=n_k)$$

> par indépendance des variables aléatoires $X_i$, $X_j$ et $X_k$.


exemple : une colonie construite sur une intersection adjacente aux tuiles de numéros 6, 12 et 3 produira en moyenne :
5/36 + 1/36 + 2/36 = 8/36 ressources par tour.

on peut donc donner une mesure simple de la qualité d'un emplacement grace à cette methode.

notons $Q_s(i)$ la qualité "simple" d'un emplacement $i$

nous utiliserons plusieurs autres mesure de Qualité dans la suite.


## 2 - placement simple des routes

le but principale des routes et de pouvoir construire de nouvelles colonies.

une façon simple de mesurer la qualité d'un chemin est de faire la somme pondéré des Qualités des emplacements accessibles par les routes construites à partir de l'emplacement initial.


une route doit obligatoirement construite adjacente à une colonie ou ville ou bien à une autre route du joueur. ainsi nomons "depart" l'emplacement de départ de la route, et "arrivée" l'emplacement d'arrivée de la route. 

nous pouvons alors définir la qualité d'une route comme la somme des qualités des emplacements accessibles à partir de l'emplacement d'arrivée, pondérée par la distance entre l'emplacement d'arrivée.

$$ Q_r(d) = \sum_{i \in A(d) \cap  C(d) } \frac{Q_s(i)}{dist(d, i)}$$

ou $A(d)$ est l'ensemble des emplacements accessibles à partir de l'emplacement d'arrivée de la route, $C(d)$ est l'ensemble des emplacements constructibles, et $dist(d, i)$ est la distance entre l'emplacement d'arrivée de la route et l'emplacement $i$.


> nous verons par la suite que cette mesure peut être améliorée en prenant en compte les actions des autres joueurs, et en utilisant des mesures plus complexes de la qualité des emplacements.




## II - choix du placement du voleur

Le placement du voleur est la désision la plus simple à prendre pour un joueur,
tout en étant importante pour la stratégie du joueur. 

Le voleur bloque la production d'une tuile, et permet de voler une ressource à un autre joueur.
La ressource volée est choisie aléatoirement parmi les ressources possédées par le joueur ciblé.

ainsi il s'agit de choisir un emplacement qui bloque le plus de production possible pour les autres joueurs, tout en maximisant la probabilité de voler une ressource utile pour le joueur actif.
Mais comme la connaissance des ressources possédées par les autres joueurs est cachée, 
il n'est pas rentable de prendre en compte les ressources volées, et il est préférable de se concentrer sur la production bloquée.

On assigne donc un poids à chaque tuile, dépendant des colonies et villes des autres joueurs qui sont adjacentes à cette tuile, ainsi que du numéro associé à la tuile.

notons $T(t)$ le poids de la tuile, $c$ le nombre de colonies et villes des autres joueurs adjacentes à la tuile (colonie=1, ville=2), $n$ le numéro associé à la tuile, et $j$ le nombre de colonies et villes du joueurs, adjacentes à la tuile.

alors :

$$ T(t) = (c - j * N) * P(D=n) $$

> ou $N$ est le nombre de joueurs.


une tuile ne pourra jamais avoir plus de 3 colonies ou villes adjacentes,
dans le pire des cas, une tuile avec 2 villes adverses et 1 colonie du joueur actif, avec un numéro 6 ou 8, aura un poids de $T(t) = (4 - 1 * 4) * 5/36 = 0$.


ce model pourra être amélioré en pondérant les colonies et villes des autres joueurs par leur points de victoire, ainsi il sera plus rentable de bloquer un joueur qui est en tête.


cette nouvelle mesure donnera donc :

en notant $c_j$ le nombre de colonies et villes du joueur $j$ adjacentes à la tuile, et $p_j$ le nombre de points de victoire du joueur $j$, alors si on note $k$ le joueur actif, le poids de la tuile sera donné par :

$$ T_k(t) = P(D=n)(\sum_{j \in J} c_j p_j - \alpha c_k )$$

ou $J$ est l'ensemble des joueurs, et $\alpha$ est un paramètre à déterminer, qui permet de pondérer l'importance de bloquer les autres joueurs par rapport à la production du joueur actif.


## III - Trade et marché central

Cette version simplifiée du jeu Catan introduit un marché central, où les joueurs peuvent acheter et vendre des ressources à un prix variable. Le prix des ressources évolue en fonction de l'offre et de la demande.

Celà rends le comerce plus simple d'un point de vue programmation, notamment pour les agents d'apprentissage par renforcement, qui n'ont pas à négocier avec les autres joueurs.

Mais celà rends les stratégies de commerce plus complexes, car les joueurs doivent prendre en compte l'évolution des prix des ressources au marché central, ainsi que les besoins en ressources des autres joueurs.


Beaucoup de théories économiques peuvent être appliquées pour analyser le marché central,
Nous alons donc dans cette partie, explorer les différentes stratégies envisageables par les joueurs.


### 1. Les Bases

le but du marché central est de permettre aux joueurs d'acheter les ressources dont ils ont besoin pour construire des routes, colonies et villes, chaques ressources ayant un coût variable au marché central,
nous pouvons donc définir le coût d'une action de construction comme la somme des coûts des ressources nécessaires pour cette action, au moment où l'action est effectuée.

une colonie a donc un Prix en or, tout comme une route, une ville, ou une carte développement.

de plus chaques colonie ou ville construite permet de produire des ressources, et donc de générer de l'or pour le joueur, en vendant ces ressources au marché central.

on peut donc donner une espérance de gain en or pour chaque joueurs, en fonction de ses colonies et villes, des numéros associés aux tuiles, et du prix des ressources au marché central.

l'espérance de gain en or pour un terrain, dépendant donc du prix des ressources au marché central
permet de remplacer la mesure de qualité simple $Q_s(i)$.

Cepandant, cette mesure n'a aucun avantage à être utilisée pour le placement initial, car le prix des ressources au marché central est initialisé à 10 d'or pour chaque ressource, et ne varie pas avant que les joueurs aient commencé à construire des colonies et des routes.

Or en début de partie, il peut être claire que certaines ressources seront plus demandées que d'autres, et donc que leur prix au marché central augmentera plus rapidement.

Celà ammène donc a vouloir déterminer un prix "cible" pour chaque ressource dépendant de la production de la ressource sur le plateau, et de son utilitée.

pour commencé, considérons la somme des probabilités de production de chaque ressource sur le plateau:

$$P_r = \sum_{t \in T_r} P(D=n_t)$$

$P_r$ est donc relatif à la production moyenne d'une ressource $r$ sur le plateau

$P(D=n_t)$ etant une probabilité, on peut donc multiplier $P_r$ par 36 pour obtenir une valeur entière

