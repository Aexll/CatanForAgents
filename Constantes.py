"""Constantes.py — Constantes du jeu Catan (version simplifiée).

Regroupe les symboles de ressources, les coûts de construction, la composition
du plateau standard, le paquet de cartes développement et les paramètres du
marché central, conformément à l'étude (etude.md).
"""

# ----------------------------------------------------------------------
# Ressources
# ----------------------------------------------------------------------
BOIS    = "B"   # bois (wood)
BLE     = "W"   # blé  (wheat)
MOUTON  = "S"   # mouton (sheep)
MINERAI = "O"   # minerai (ore)
ARGILE  = "C"   # argile (clay)
DESERT  = "X"   # rien (désert ou mer)

# Les cinq ressources échangeables/productibles.
RESSOURCES = [BOIS, BLE, MOUTON, MINERAI, ARGILE]

# ----------------------------------------------------------------------
# Coûts de construction (en ressources)
# ----------------------------------------------------------------------
COUT_ROUTE   = {BOIS: 1, ARGILE: 1}
COUT_COLONIE = {BOIS: 1, ARGILE: 1, BLE: 1, MOUTON: 1}
COUT_VILLE   = {MINERAI: 3, BLE: 2}
COUT_DEV     = {MINERAI: 1, BLE: 1, MOUTON: 1}

# ----------------------------------------------------------------------
# Cartes développement (les cartes Progrès sont retirées dans cette version)
# ----------------------------------------------------------------------
DEV_CHEVALIER = "CHEVALIER"
DEV_POINT     = "POINT_VICTOIRE"

NB_CHEVALIERS     = 14
NB_POINTS_VICTOIRE = 5

# ----------------------------------------------------------------------
# Marché central
# ----------------------------------------------------------------------
OR_INITIAL        = 10   # or de départ par joueur
PRIX_INITIAL      = 10   # prix de départ de chaque ressource
PRIX_MIN          = 1    # le prix ne peut pas descendre en dessous de 1

# ----------------------------------------------------------------------
# Plateau standard (19 tuiles, coordonnées axiales de rayon 2)
# ----------------------------------------------------------------------
# Composition en ressources : 4 bois, 3 argile, 4 mouton, 4 blé, 3 minerai, 1 désert.
COMPOSITION_TUILES = (
    [BOIS] * 4 + [ARGILE] * 3 + [MOUTON] * 4 + [BLE] * 4 + [MINERAI] * 3 + [DESERT] * 1
)

# Jetons numéros pour les 18 tuiles productives (le désert n'en reçoit pas).
JETONS_NUMEROS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

RAYON_PLATEAU = 2  # un plateau hexagonal de rayon 2 contient 19 tuiles

# ----------------------------------------------------------------------
# Ports : 4 ports génériques 3:1 (type X) et 1 port 2:1 par ressource.
# ----------------------------------------------------------------------
PORTS = [DESERT, DESERT, DESERT, DESERT, BOIS, BLE, MOUTON, MINERAI, ARGILE]
TAUX_PORT_GENERIQUE = 3   # port 3:1
TAUX_PORT_RESSOURCE = 2   # port 2:1
TAUX_BANQUE         = 4   # échange 4:1 avec la banque

# ----------------------------------------------------------------------
# Conditions de partie
# ----------------------------------------------------------------------
VICTOIRE_POINTS   = 10    # nombre de points de victoire pour gagner
ARMEE_MIN         = 3     # nombre de chevaliers pour prétendre à la plus grande armée
BONUS_ARMEE       = 2     # points de victoire accordés par la plus grande armée
ROUTE_MIN         = 5     # longueur minimale pour prétendre à la route la plus longue
BONUS_ROUTE       = 2     # points de victoire accordés par la route la plus longue
SEUIL_DEFAUSSE    = 7     # au-delà de 7 cartes, défausse de la moitié sur un 7
MAX_TOURS         = 2000  # garde-fou contre les parties qui ne se terminent pas

# ----------------------------------------------------------------------
# États de la machine d'état
# ----------------------------------------------------------------------
ETAT_PREP   = "PREP"
ETAT_DES    = "DES"
ETAT_JOUEUR = "JOUEUR"
ETAT_VOL    = "VOL"
