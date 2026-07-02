"""ppo.py — PPO masqué (auto-suffisant, PyTorch).

Entraîne un ``ActeurCritique`` sur ``EnvCatan`` : collecte de trajectoires, avantages
GAE, objectif PPO clippé (avec masque des actions), perte de valeur et bonus
d'entropie. Un seul environnement (le moteur est déjà rapide).
"""

import time

import numpy as np
import torch
import torch.nn as nn
from torch.distributions import Categorical

from rl.reseau import ActeurCritique


class PPO:
    def __init__(self, env, cachee=256, lr=3e-4, gamma=0.999, lam=0.95,
                 clip=0.2, coef_valeur=0.5, coef_entropie=0.01,
                 pas_par_maj=2048, epochs=4, taille_lot=256, device=None):
        self.env = env
        self.gamma, self.lam, self.clip = gamma, lam, clip
        self.coef_valeur, self.coef_entropie = coef_valeur, coef_entropie
        self.pas_par_maj, self.epochs, self.taille_lot = pas_par_maj, epochs, taille_lot
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

        env.reset()  # initialise les tailles
        self.modele = ActeurCritique(env.taille_obs, env.taille_actions, cachee).to(self.device)
        self.opt = torch.optim.Adam(self.modele.parameters(), lr=lr)

        self.obs, self.mask = env.reset()
        self.retours_episodes = []   # retours des épisodes terminés (pour le suivi)
        self.victoires = []

    # ------------------------------------------------------------------
    def _tenseur(self, x, dtype=torch.float32):
        return torch.as_tensor(np.asarray(x), dtype=dtype, device=self.device)

    @torch.no_grad()
    def _valeur(self, obs, mask):
        o = self._tenseur(obs).unsqueeze(0)
        m = self._tenseur(mask, torch.bool).unsqueeze(0)
        _, v = self.modele.logits_masques(o, m)
        return float(v.item())

    # ------------------------------------------------------------------
    def collecter(self):
        """Collecte ``pas_par_maj`` transitions et renvoie les tenseurs du lot."""
        N = self.pas_par_maj
        obs_b = np.zeros((N, self.env.taille_obs), np.float32)
        mask_b = np.zeros((N, self.env.taille_actions), bool)
        act_b = np.zeros(N, np.int64)
        logp_b = np.zeros(N, np.float32)
        val_b = np.zeros(N, np.float32)
        rew_b = np.zeros(N, np.float32)
        fin_b = np.zeros(N, np.float32)
        retour_courant = 0.0

        for t in range(N):
            obs_b[t] = self.obs
            mask_b[t] = self.mask
            with torch.no_grad():
                o = self._tenseur(self.obs).unsqueeze(0)
                m = self._tenseur(self.mask, torch.bool).unsqueeze(0)
                logits, v = self.modele.logits_masques(o, m)
                dist = Categorical(logits=logits)
                a = dist.sample()
            act_b[t] = int(a.item())
            logp_b[t] = float(dist.log_prob(a).item())
            val_b[t] = float(v.item())

            self.obs, self.mask, r, fini, info = self.env.step(act_b[t])
            rew_b[t] = r
            fin_b[t] = 1.0 if fini else 0.0
            retour_courant += r
            if fini:
                self.retours_episodes.append(retour_courant)
                self.victoires.append(1.0 if info.get("gagnant") == self.env.position else 0.0)
                retour_courant = 0.0
                self.obs, self.mask = self.env.reset()

        # Avantages GAE.
        derniere_val = self._valeur(self.obs, self.mask)
        adv = np.zeros(N, np.float32)
        dernier = 0.0
        for t in reversed(range(N)):
            non_terminal = 1.0 - fin_b[t]
            val_suiv = val_b[t + 1] if t + 1 < N else derniere_val
            delta = rew_b[t] + self.gamma * val_suiv * non_terminal - val_b[t]
            dernier = delta + self.gamma * self.lam * non_terminal * dernier
            adv[t] = dernier
        ret = adv + val_b

        return {
            "obs": self._tenseur(obs_b),
            "mask": self._tenseur(mask_b, torch.bool),
            "act": self._tenseur(act_b, torch.int64),
            "logp": self._tenseur(logp_b),
            "adv": self._tenseur(adv),
            "ret": self._tenseur(ret),
        }

    # ------------------------------------------------------------------
    def maj(self, lot):
        adv = lot["adv"]
        adv = (adv - adv.mean()) / (adv.std() + 1e-8)
        N = lot["obs"].shape[0]
        idx = np.arange(N)
        infos = {"perte_pol": 0.0, "perte_val": 0.0, "entropie": 0.0, "n": 0}
        for _ in range(self.epochs):
            np.random.shuffle(idx)
            for debut in range(0, N, self.taille_lot):
                b = idx[debut:debut + self.taille_lot]
                logits, v = self.modele.logits_masques(lot["obs"][b], lot["mask"][b])
                dist = Categorical(logits=logits)
                logp = dist.log_prob(lot["act"][b])
                ratio = torch.exp(logp - lot["logp"][b])
                a = adv[b]
                perte_pol = -torch.min(ratio * a,
                                       torch.clamp(ratio, 1 - self.clip, 1 + self.clip) * a).mean()
                perte_val = ((v - lot["ret"][b]) ** 2).mean()
                entropie = dist.entropy().mean()
                perte = perte_pol + self.coef_valeur * perte_val - self.coef_entropie * entropie

                self.opt.zero_grad()
                perte.backward()
                nn.utils.clip_grad_norm_(self.modele.parameters(), 0.5)
                self.opt.step()

                infos["perte_pol"] += float(perte_pol.item())
                infos["perte_val"] += float(perte_val.item())
                infos["entropie"] += float(entropie.item())
                infos["n"] += 1
        for k in ("perte_pol", "perte_val", "entropie"):
            infos[k] /= max(1, infos["n"])
        return infos

    # ------------------------------------------------------------------
    def entrainer(self, total_pas, chemin=None, journal=True):
        t0 = time.time()
        pas = 0
        while pas < total_pas:
            lot = self.collecter()
            infos = self.maj(lot)
            pas += self.pas_par_maj
            if journal:
                nb = len(self.retours_episodes)
                ret_moy = np.mean(self.retours_episodes[-30:]) if nb else float("nan")
                tx_vict = np.mean(self.victoires[-30:]) if self.victoires else float("nan")
                print(f"pas {pas:>8} | épisodes {nb:>4} | retour~{ret_moy:6.2f} "
                      f"| victoire~{tx_vict:4.2f} | H={infos['entropie']:.2f} "
                      f"| {pas/(time.time()-t0):.0f} pas/s")
            if chemin:
                self.sauvegarder(chemin)
        return self.modele

    # ------------------------------------------------------------------
    def sauvegarder(self, chemin):
        torch.save({"modele": self.modele.state_dict(),
                    "dim_obs": self.env.taille_obs,
                    "dim_actions": self.env.taille_actions,
                    "n_joueurs": self.env.n_joueurs,
                    "cachee": self.modele.tronc[0].out_features}, chemin)
