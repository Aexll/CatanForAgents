"""play.py — Lancement et sauvegarde des parties.

Initialise les joueurs, joue une ou plusieurs parties via le moteur, et
sauvegarde chacune au format JSONL.

Exemple (issu de l'étude) :
    python play.py --games 500 --j1 rl --j2 random --j3 random --j4 random --cycle

Lance 500 parties à 4 joueurs (3 aléatoires, 1 RL). Avec --cycle, la disposition
des joueurs tourne d'une partie à l'autre (pour neutraliser l'avantage de place).

Pour générer beaucoup de parties rapidement :
    python play.py --games 2000 --workers 8        # parallélise sur 8 processus
    python play.py --games 2000 --no-save          # sans sauvegarde JSONL (~3x plus rapide)
"""

import argparse
import os
import time

from moteur import Moteur
from joueur import creer_joueur


def construire_arguments():
    p = argparse.ArgumentParser(
        description="Lance et sauvegarde des parties de Catan (version simplifiée)."
    )
    p.add_argument("--games", type=int, default=1,
                   help="Nombre de parties à jouer (défaut : 1).")
    p.add_argument("--j1", type=str, default=None, help="Type du joueur 1.")
    p.add_argument("--j2", type=str, default=None, help="Type du joueur 2.")
    p.add_argument("--j3", type=str, default=None, help="Type du joueur 3.")
    p.add_argument("--j4", type=str, default=None, help="Type du joueur 4.")
    p.add_argument("--cycle", action="store_true",
                   help="Fait tourner la disposition des joueurs entre les parties.")
    p.add_argument("--seed", type=int, default=None,
                   help="Graine aléatoire de base (reproductibilité).")
    p.add_argument("--out", type=str, default="sauvegardes",
                   help="Dossier de sauvegarde des parties (défaut : sauvegardes/).")
    p.add_argument("--workers", type=int, default=1,
                   help="Nombre de processus parallèles (défaut : 1 ; "
                        "essayez le nombre de cœurs CPU pour aller plus vite).")
    p.add_argument("--no-save", action="store_true",
                   help="Ne pas écrire les fichiers JSONL (génération la plus rapide).")
    p.add_argument("--quiet", action="store_true",
                   help="Réduit l'affichage console.")
    return p


def types_joueurs(args):
    """Récupère la liste ordonnée des types de joueurs depuis les arguments."""
    bruts = [args.j1, args.j2, args.j3, args.j4]
    types = [t for t in bruts if t is not None]
    if len(types) < 2:
        types = ["random", "random", "random", "random"]  # défaut : 4 aléatoires
    return types


def _jouer_une_partie(params):
    """Joue une partie (fonction de niveau module, picklable pour multiprocessing).

    ``params`` = (partie, types, seed_base, cycle, out). Renvoie un résumé.
    """
    partie, types, seed_base, cycle, out = params
    n = len(types)
    decalage = (partie % n) if cycle else 0
    types_partie = types[decalage:] + types[:decalage]
    seed_partie = None if seed_base is None else seed_base + partie

    joueurs = [
        creer_joueur(t, nom=f"{t}#{i}",
                     seed=(None if seed_partie is None else seed_partie * 100 + i))
        for i, t in enumerate(types_partie)
    ]
    chemin = None
    if out is not None:
        chemin = os.path.join(out, f"partie_{partie:05d}.jsonl")
    moteur = Moteur(joueurs, seed=seed_partie,
                    chemin_sauvegarde=chemin, partie_id=partie)
    gagnant = moteur.jouer_partie()
    return {
        "partie": partie,
        "position_origine": (gagnant + decalage) % n,
        "type_gagnant": types_partie[gagnant],
        "nom_gagnant": joueurs[gagnant].nom,
        "points": moteur._points(gagnant, inclure_prive=True),
        "chemin": chemin,
    }


def main(argv=None):
    args = construire_arguments().parse_args(argv)
    types = types_joueurs(args)
    n = len(types)
    out = None if args.no_save else args.out
    if out is not None:
        os.makedirs(out, exist_ok=True)

    taches = [(partie, types, args.seed, args.cycle, out)
              for partie in range(args.games)]
    victoires = [0] * n
    victoires_type = {}

    def traiter(res):
        victoires[res["position_origine"]] += 1
        vt = res["type_gagnant"]
        victoires_type[vt] = victoires_type.get(vt, 0) + 1
        if not args.quiet:
            cible = res["chemin"] or "(non sauvegardée)"
            print(f"Partie {res['partie']:>5} | gagnant : {res['nom_gagnant']} "
                  f"({res['points']} pts) | {cible}")

    debut = time.perf_counter()
    if args.workers and args.workers > 1:
        import multiprocessing as mp
        with mp.Pool(args.workers) as pool:
            for res in pool.imap_unordered(_jouer_une_partie, taches):
                traiter(res)
    else:
        for tache in taches:
            traiter(_jouer_une_partie(tache))
    duree = time.perf_counter() - debut

    print("\n=== Bilan ===")
    print(f"{args.games} partie(s), {n} joueur(s), {args.workers} processus.")
    print(f"Durée : {duree:.2f} s  ({args.games/duree:.1f} parties/s, "
          f"{duree/max(1, args.games)*1000:.0f} ms/partie).")
    print("Victoires par type de joueur :")
    for t in sorted(victoires_type):
        print(f"  {t:<8} : {victoires_type[t]}")
    if out is not None:
        print(f"Sauvegardes écrites dans : {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
