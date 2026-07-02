"""env.py — Environnement RL (reset/step) autour du moteur synchrone.

Le moteur appelle ``joueur.decider(...)`` (contrôle « tiré » par le moteur), alors
qu'un environnement RL est « poussé » par l'agent (``env.step(action)``). On inverse
le flot en lançant la partie dans un **thread** : le joueur RL est un *pont* qui, à
chaque décision, transmet l'observation à l'environnement via une file et attend en
retour l'action choisie.

L'espace d'actions étant variable, ``step`` prend un **indice discret** (cf. codec)
et ``masque_actions()`` donne les actions légales du pas courant.
"""

import queue
import random
import threading

import numpy as np

from joueur import Joueur, creer_joueur
from moteur import Moteur
from rl.codec import CodecActions, EncodeurObservation

_ABORT = object()          # sentinelle pour interrompre une partie en cours


class _AbortGame(Exception):
    pass


class _PontJoueur(Joueur):
    """Joueur « pont » : relaie observation/action entre le moteur et l'environnement."""

    def __init__(self, vers_env, depuis_env):
        super().__init__("RL")
        self.vers_env = vers_env
        self.depuis_env = depuis_env

    def nouvelle_partie(self, indice, plateau=None):
        super().nouvelle_partie(indice, plateau)
        self.vers_env.put(("plateau", plateau))

    def decider(self, observation, actions_legales):
        self.vers_env.put(("decision", observation, actions_legales))
        action = self.depuis_env.get()
        if action is _ABORT:
            raise _AbortGame()
        return action


class EnvCatan:
    """Environnement d'une partie de Catan du point de vue d'un joueur RL.

    ``reset()`` -> ``(observation_vecteur, masque)``
    ``step(indice)`` -> ``(observation, masque, recompense, termine, info)``
    """

    def __init__(self, adversaires=("random", "random", "random"), position=0,
                 coef_pv=1.0, bonus_victoire=5.0, seed=None):
        self.adversaires = list(adversaires)
        self.n_joueurs = len(self.adversaires) + 1
        self.position = position
        self.coef_pv = coef_pv
        self.bonus_victoire = bonus_victoire
        self.rng = random.Random(seed)

        self.vers_env = queue.Queue()
        self.depuis_env = queue.Queue()
        self.thread = None
        self.codec = None
        self.enc = None
        self.taille_obs = None
        self.taille_actions = None
        self.mask = None
        self.mapping = {}
        self.pv_prev = 0
        self.termine = True

    # ------------------------------------------------------------------
    def masque_actions(self):
        return self.mask

    # ------------------------------------------------------------------
    def reset(self, seed=None):
        self._interrompre()
        if seed is not None:
            self.rng.seed(seed)
        graine = self.rng.randrange(2 ** 31)

        pont = _PontJoueur(self.vers_env, self.depuis_env)
        autres = [creer_joueur(t, nom=f"{t}#{i}", seed=graine * 10 + i)
                  for i, t in enumerate(self.adversaires)]
        joueurs, k = [], 0
        for p in range(self.n_joueurs):
            if p == self.position:
                joueurs.append(pont)
            else:
                joueurs.append(autres[k]); k += 1

        self.thread = threading.Thread(target=self._boucle_partie,
                                       args=(graine, joueurs), daemon=True)
        self.thread.start()

        msg = self.vers_env.get()
        if msg[0] != "plateau":
            raise RuntimeError(f"Message inattendu au démarrage : {msg[0]}")
        plateau = msg[1]
        if self.codec is None:
            self.codec = CodecActions(plateau)
        self.enc = EncodeurObservation(plateau, self.n_joueurs)
        if self.taille_obs is None:
            self.taille_obs = self.enc.taille
            self.taille_actions = self.codec.taille

        vec, mask, _r, _fini, _info = self._recevoir(premier=True)
        return vec, mask

    # ------------------------------------------------------------------
    def step(self, indice):
        action = self.mapping.get(int(indice))
        if action is None:                      # sécurité : repli sur une action légale
            action = next(iter(self.mapping.values()))
        self.depuis_env.put(action)
        return self._recevoir(premier=False)

    # ------------------------------------------------------------------
    def _recevoir(self, premier):
        msg = self.vers_env.get()
        typ = msg[0]
        if typ == "decision":
            _, obs, actions = msg
            self.mask, self.mapping = self.codec.masque(actions)
            vec = self.enc.encoder(obs, self.position)
            pv = obs.get("pv_publics", [0] * self.n_joueurs)[self.position]
            recompense = 0.0 if premier else self.coef_pv * (pv - self.pv_prev)
            self.pv_prev = pv
            self.termine = False
            return vec, self.mask, recompense, False, {}
        if typ == "fin":
            _, gagnant, points = msg
            self.termine = True
            recompense = self.bonus_victoire * (1.0 if gagnant == self.position else -1.0)
            vec = np.zeros(self.taille_obs, dtype=np.float32)
            self.mask = np.zeros(self.taille_actions, dtype=bool)
            self.mask[self.codec.O_PASSER] = True
            return vec, self.mask, recompense, True, {"gagnant": gagnant, "points": points}
        raise RuntimeError(f"Erreur du moteur : {msg[1] if len(msg) > 1 else msg}")

    # ------------------------------------------------------------------
    def _boucle_partie(self, graine, joueurs):
        moteur = Moteur(joueurs, seed=graine, chemin_sauvegarde=None)
        try:
            gagnant = moteur.jouer_partie()
            points = [moteur._points(p) for p in range(len(joueurs))]
            self.vers_env.put(("fin", gagnant, points))
        except _AbortGame:
            return
        except Exception as e:               # remonte l'erreur à l'environnement
            self.vers_env.put(("erreur", repr(e)))

    # ------------------------------------------------------------------
    def _interrompre(self):
        if self.thread is not None and self.thread.is_alive():
            self.depuis_env.put(_ABORT)
            self.thread.join(timeout=2.0)
        self.thread = None
        for q in (self.vers_env, self.depuis_env):
            try:
                while True:
                    q.get_nowait()
            except queue.Empty:
                pass

    def close(self):
        self._interrompre()
