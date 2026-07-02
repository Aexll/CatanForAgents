"""reseau.py — Réseau acteur-critique (MLP) avec masquage des actions."""

import torch
import torch.nn as nn


class ActeurCritique(nn.Module):
    """Tronc commun + tête politique (logits par action) + tête valeur."""

    def __init__(self, dim_obs, dim_actions, cachee=256):
        super().__init__()
        self.tronc = nn.Sequential(
            nn.Linear(dim_obs, cachee), nn.Tanh(),
            nn.Linear(cachee, cachee), nn.Tanh(),
        )
        self.politique = nn.Linear(cachee, dim_actions)
        self.valeur = nn.Linear(cachee, 1)
        self.dim_obs = dim_obs
        self.dim_actions = dim_actions

    def forward(self, x):
        h = self.tronc(x)
        return self.politique(h), self.valeur(h).squeeze(-1)

    def logits_masques(self, x, masque):
        """Logits avec les actions illégales mises à -inf (via le masque booléen)."""
        logits, valeur = self.forward(x)
        logits = logits.masked_fill(~masque, float("-inf"))
        return logits, valeur
