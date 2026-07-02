"""jouer.py — Politique d'inférence : joue avec un modèle entraîné.

Utilisée par ``JoueurRL`` (type ``rl``). Charge un modèle sauvegardé et choisit,
à chaque décision, une action légale (argmax masqué par défaut).
"""

import numpy as np
import torch
from torch.distributions import Categorical

from rl.codec import CodecActions, EncodeurObservation
from rl.reseau import ActeurCritique

_CACHE_POLITIQUE = {}


def charger_politique(chemin, device=None):
    """Renvoie une ``PolitiqueRL`` (mise en cache par chemin)."""
    cle = (chemin, device)
    if cle not in _CACHE_POLITIQUE:
        _CACHE_POLITIQUE[cle] = PolitiqueRL(chemin, device)
    return _CACHE_POLITIQUE[cle]


class PolitiqueRL:
    def __init__(self, chemin, device=None):
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        data = torch.load(chemin, map_location=self.device, weights_only=False)
        self.n_joueurs = data.get("n_joueurs", 4)
        self.modele = ActeurCritique(data["dim_obs"], data["dim_actions"],
                                     data.get("cachee", 256)).to(self.device)
        self.modele.load_state_dict(data["modele"])
        self.modele.eval()
        self._outils = {}   # id(plateau) -> (codec, encodeur, plateau)

    def _codec_enc(self, plateau):
        cache = self._outils.get(id(plateau))
        if cache is None or cache[2] is not plateau:
            cache = (CodecActions(plateau),
                     EncodeurObservation(plateau, self.n_joueurs), plateau)
            self._outils[id(plateau)] = cache
        return cache[0], cache[1]

    @torch.no_grad()
    def choisir(self, observation, actions_legales, plateau, position,
                echantillonner=False):
        codec, enc = self._codec_enc(plateau)
        masque, mapping = codec.masque(actions_legales)
        vec = enc.encoder(observation, position)
        o = torch.as_tensor(vec, device=self.device).unsqueeze(0)
        m = torch.as_tensor(masque, dtype=torch.bool, device=self.device).unsqueeze(0)
        logits, _ = self.modele.logits_masques(o, m)
        if echantillonner:
            idx = int(Categorical(logits=logits).sample().item())
        else:
            idx = int(logits.argmax(-1).item())
        return mapping.get(idx) or next(iter(mapping.values()))
