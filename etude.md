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
