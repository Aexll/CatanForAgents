"""train.py — Entraînement d'un agent RL (PPO masqué).

Exemples :
    python -m rl.train --steps 2000000
    python -m rl.train --steps 500000 --adversaires glouton,random,random --out rl/modele.pt

Le modèle est sauvegardé (par défaut ``rl/modele.pt``) ; le joueur ``rl`` l'utilise
ensuite automatiquement :  ``python play.py --j1 rl --j2 random --j3 random --j4 random``.
"""

import argparse

from rl.env import EnvCatan
from rl.ppo import PPO


def main(argv=None):
    p = argparse.ArgumentParser(description="Entraîne un agent Catan par PPO masqué.")
    p.add_argument("--steps", type=int, default=1_000_000, help="Nombre de pas d'environnement.")
    p.add_argument("--adversaires", type=str, default="random,random,random",
                   help="Types d'adversaires séparés par des virgules.")
    p.add_argument("--position", type=int, default=0, help="Place du joueur RL (0..n-1).")
    p.add_argument("--out", type=str, default="rl/modele.pt", help="Chemin du modèle.")
    p.add_argument("--hidden", type=int, default=256, help="Taille des couches cachées.")
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--steps-per-update", type=int, default=2048)
    p.add_argument("--coef-pv", type=float, default=1.0,
                   help="Récompense par point de victoire public gagné (shaping).")
    p.add_argument("--bonus", type=float, default=5.0, help="Bonus de victoire (± en fin de partie).")
    p.add_argument("--device", type=str, default=None, help="'cuda' ou 'cpu' (auto par défaut).")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    adversaires = [a for a in args.adversaires.split(",") if a]
    env = EnvCatan(adversaires=adversaires, position=args.position,
                   coef_pv=args.coef_pv, bonus_victoire=args.bonus, seed=args.seed)
    ppo = PPO(env, cachee=args.hidden, lr=args.lr,
              pas_par_maj=args.steps_per_update, device=args.device)
    print(f"Entraînement : {args.steps} pas | adversaires={adversaires} | "
          f"obs={env.taille_obs} actions={env.taille_actions} | device={ppo.device}")
    ppo.entrainer(total_pas=args.steps, chemin=args.out)
    env.close()
    print("Modèle sauvegardé :", args.out)


if __name__ == "__main__":
    main()
