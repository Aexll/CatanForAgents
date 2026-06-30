"""joueur.py — Classes de joueurs et fabrique.

Deux niveaux d'interface coexistent :

1. La classe de base ``Joueur`` (bas niveau, ici) : le moteur appelle
   ``decider(observation, actions_legales)`` et attend en retour l'une des actions
   de ``actions_legales``. C'est l'interface générique du moteur.

2. La classe ``AgentCatan`` (haut niveau, dans ``agent.py``) : à sous-classer pour
   implémenter facilement son propre algorithme. Les agents concrets vivent dans le
   dossier ``agents/`` et sont **détectés automatiquement** : ajouter un fichier qui
   hérite de ``AgentCatan`` suffit pour qu'il apparaisse dans ``TYPES_JOUEURS`` et
   soit utilisable (``python play.py --j1 mon_nom ...``).

Voir ``agents/COMMENT_CREER_UN_AGENT.md`` pour le guide.
"""

import random


class Joueur:
    """Classe de base abstraite représentant un joueur."""

    def __init__(self, nom=None):
        self.nom = nom or self.__class__.__name__
        self.indice = None    # affecté par le moteur au début de la partie
        self.plateau = None   # plateau statique (perception fixe), idem

    def nouvelle_partie(self, indice, plateau=None):
        """Appelé par le moteur au début de chaque partie.

        ``indice`` est la position du joueur, et ``plateau`` le graphe statique
        (perception fixe : tuiles, numéros, ports). Voir ``AgentCatan`` pour son
        format détaillé.
        """
        self.indice = indice
        self.plateau = plateau

    def decider(self, observation, actions_legales):
        """Renvoie l'action choisie parmi ``actions_legales``.

        ``observation`` est le vecteur d'observation décrit dans l'étude.
        Doit être surchargée par les classes dérivées.
        """
        raise NotImplementedError

    def __repr__(self):
        return f"{self.__class__.__name__}({self.nom!r})"


class JoueurRandom(Joueur):
    """Joueur de référence : choisit une action légale au hasard."""

    def __init__(self, nom=None, seed=None):
        super().__init__(nom)
        self.rng = random.Random(seed)

    def decider(self, observation, actions_legales):
        return self.rng.choice(actions_legales)


class JoueurRL(Joueur):
    """Joueur piloté par apprentissage par renforcement.

    Pour l'instant, la politique n'est pas encore entraînée : on utilise une
    politique aléatoire de remplacement afin que la chaîne complète (moteur,
    sauvegarde) puisse être exécutée de bout en bout. Le modèle RL viendra se
    brancher ici, en consommant ``observation`` (le vecteur d'observation) et en
    renvoyant une action de ``actions_legales``.
    """

    def __init__(self, nom=None, seed=None, politique=None):
        super().__init__(nom)
        self.rng = random.Random(seed)
        self.politique = politique  # callable(observation, actions) -> action

    def decider(self, observation, actions_legales):
        if self.politique is not None:
            return self.politique(observation, actions_legales)
        # TODO : remplacer par l'inférence du modèle entraîné.
        return self.rng.choice(actions_legales)


class JoueurHumain(Joueur):
    """Joueur humain.

    L'interaction se fera via l'interface visuelle (dearpygui), développée plus
    tard. En exécution headless (batch), on se rabat sur une politique aléatoire
    pour ne pas bloquer la partie.
    """

    def __init__(self, nom=None, seed=None):
        super().__init__(nom)
        self.rng = random.Random(seed)

    def decider(self, observation, actions_legales):
        # TODO : brancher l'entrée utilisateur de l'interface visuelle.
        return self.rng.choice(actions_legales)


# ======================================================================
#  Fabrique : types de joueurs « intégrés » + agents découverts
# ======================================================================
# Joueurs intégrés (toujours disponibles).
TYPES_JOUEURS = {
    "random": JoueurRandom,
    "rl": JoueurRL,
    "human": JoueurHumain,
}

# Réexport pratique de l'interface de haut niveau (``from joueur import AgentCatan``).
# Importé ici (après ``Joueur``) pour éviter tout import circulaire.
from agent import AgentCatan, ActionsTour  # noqa: E402


def _charger_agents():
    """Découvre les agents du dossier ``agents/`` et les ajoute à TYPES_JOUEURS."""
    try:
        from agents import charger_agents
    except Exception as e:  # le dossier d'agents est optionnel
        print(f"[joueur] découverte des agents impossible : {e}")
        return
    for nom, cls in charger_agents().items():
        TYPES_JOUEURS[nom] = cls


_charger_agents()  # remplit TYPES_JOUEURS automatiquement à l'import


def creer_joueur(type_joueur, nom=None, seed=None):
    """Instancie un joueur à partir de son type (ex. ``"random"``, ``"glouton"``)."""
    type_joueur = type_joueur.lower()
    if type_joueur not in TYPES_JOUEURS:
        raise ValueError(
            f"Type de joueur inconnu : {type_joueur!r}. "
            f"Choix possibles : {sorted(TYPES_JOUEURS)}"
        )
    return TYPES_JOUEURS[type_joueur](nom=nom, seed=seed)
