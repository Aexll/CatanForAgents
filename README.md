# Catan — moteur, agents et analyse

Une version **simplifiée** du jeu *Catan* (avec un marché central et une ressource
d'or), pensée pour l'**apprentissage par renforcement** : un moteur de jeu, des
agents programmables, un visualiseur et un notebook d'analyse.

## Contenu

| Fichier / dossier | Rôle |
|---|---|
| `moteur.py` | Moteur du jeu (règles, machine d'état, sauvegarde JSONL) |
| `Constantes.py` | Constantes (ressources, coûts, plateau…) |
| `joueur.py` | Joueurs de base + fabrique (`random`, `rl`, `human`) |
| `agent.py` | Interface `AgentCatan` pour écrire son propre algorithme |
| `agents/` | Les agents (détectés automatiquement) + guide de création |
| `play.py` | Lancer et sauvegarder des parties |
| `view.py` | Visualiseur graphique d'une partie (dearpygui) |
| `Catan_Analyse.ipynb` | Statistiques sur de nombreuses parties (Plotly) |
| `etude.md`, `Latex/` | Étude mathématique du jeu |

## Installation

```bash
pip install dearpygui plotly pandas numpy nbformat
pip install orjson        # optionnel : chargement du notebook plus rapide
```

## Démarrer

**Jouer et sauvegarder des parties :**
```bash
python play.py --games 100 --j1 glouton --j2 random --j3 random --j4 random --cycle
```
Options utiles : 

- `--workers 8` : parallélise
- `--no-save` : sans écriture de sauvegarde
- `--seed N`: change la seed
- `--cycle` : cycle le placement initial des joueurs sur chaques parties.

**Visualiser une partie :**
```bash
python view.py
```
Puis « Charger une sauvegarde » pour rejouer une partie pas à pas (plateau, marché,
historique des prix…).

**Analyser un ensemble de parties :**
Ouvrir `Catan_Analyse.ipynb` et l'exécuter (il pointe sur le dossier `sauvegardes/`).

## Écrire son propre agent

Ajoutez un fichier dans `agents/` qui hérite de `AgentCatan` 

Exemple:

```python
from agent import AgentCatan

class MonAgent(AgentCatan):
    NOM = "mon_agent"

    def jouer_tour(self, observation, actions):
        if actions.construire_villes:
            return actions.construire_villes[0]
        return actions.passer
```

Guide complet : [`agents/COMMENT_CREER_UN_AGENT.md`](agents/COMMENT_CREER_UN_AGENT.md).
