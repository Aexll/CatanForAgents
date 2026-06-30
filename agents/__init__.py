"""agents — découverte automatique des agents.

Tout fichier ``.py`` placé dans ce dossier (sauf ceux commençant par « _ ») est
importé, et chaque classe qui hérite de ``AgentCatan`` y est enregistrée
automatiquement. Le nom utilisé en ligne de commande est l'attribut de classe
``NOM`` (ou, à défaut, le nom de la classe en minuscules).

Voir ``COMMENT_CREER_UN_AGENT.md`` pour le guide complet.
"""

import importlib
import inspect
import os
import pkgutil

from agent import AgentCatan


def charger_agents():
    """Renvoie un dict ``{nom: classe}`` de tous les agents du dossier."""
    registre = {}
    dossier = os.path.dirname(__file__)
    for info in pkgutil.iter_modules([dossier]):
        if info.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{info.name}")
        except Exception as e:  # un agent défectueux ne doit pas tout bloquer
            print(f"[agents] fichier '{info.name}.py' ignoré (erreur d'import) : {e}")
            continue
        for nom_cls, cls in inspect.getmembers(module, inspect.isclass):
            if (issubclass(cls, AgentCatan) and cls is not AgentCatan
                    and cls.__module__ == module.__name__):
                nom = (getattr(cls, "NOM", None) or nom_cls).lower()
                if nom in registre and registre[nom] is not cls:
                    print(f"[agents] nom '{nom}' en double : "
                          f"{cls.__name__} remplace {registre[nom].__name__}")
                registre[nom] = cls
    return registre
