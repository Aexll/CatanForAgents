# Apprentissage par renforcement (RL)

Un agent Catan entraîné par **PPO masqué**, en PyTorch pur (aucune dépendance
externe : ni gymnasium, ni stable-baselines3).

## Prérequis

PyTorch (déjà installé). Le GPU est utilisé automatiquement s'il est disponible.

## Entraîner

```bash
python -m rl.train --steps 2000000
```

Options :

- `--adversaires random,random,random` : types d'adversaires (agents du dossier `agents/`)
- `--position 0` : place du joueur RL
- `--out rl/modele.pt` : chemin du modèle
- `--coef-pv 1.0` : récompense par point de victoire public gagné (*reward shaping*)
- `--bonus 5.0` : bonus (±) accordé à la fin selon victoire / défaite
- `--hidden 256`, `--lr 3e-4`, `--steps-per-update 2048`, `--device cuda|cpu`

Le suivi affiche, par mise à jour : retour moyen, **taux de victoire** récent et
entropie de la politique.

## Jouer / évaluer

Le joueur `rl` charge automatiquement `rl/modele.pt` (ou le chemin
`CATAN_RL_MODELE`) ; sans modèle, il joue aléatoirement.

```bash
python play.py --games 200 --j1 rl --j2 random --j3 random --j4 random --cycle
python view.py        # pour observer une partie de l'agent
```

## Comment ça marche

| Fichier | Rôle |
|---|---|
| `codec.py` | observation → **vecteur fixe** ; actions → **espace discret fixe + masque** des actions légales |
| `env.py` | environnement `reset`/`step` ; inverse le moteur synchrone via un **thread** (joueur « pont ») |
| `reseau.py` | réseau **acteur-critique** (MLP) avec masquage |
| `ppo.py` | **PPO** clippé : GAE, masque des actions, perte valeur, entropie |
| `train.py` | script d'entraînement (CLI) |
| `jouer.py` | politique d'inférence utilisée par `JoueurRL` |

**Récompense** : à chaque point de victoire public gagné `+coef-pv`, et à la fin
`±bonus` selon victoire/défaite (signal dense + objectif final).

**Espace d'actions** : ~232 actions canoniques (passer, routes/colonies/villes par
emplacement, dev, chevalier, voleur par tuile, achat/vente/échange par ressource).
Un masque restreint le choix aux actions légales du pas courant.

## Notes

- L'entraînement utilise un seul environnement (le moteur est rapide) ; on peut
  augmenter `--steps-per-update` pour des mises à jour plus stables.
- Un modèle non entraîné joue au niveau du hasard ; il faut typiquement **plusieurs
  millions de pas** pour dépasser nettement les adversaires aléatoires.
