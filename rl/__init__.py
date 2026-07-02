"""rl — apprentissage par renforcement pour le Catan simplifié (PyTorch, sans dépendance externe).

Modules :
  * ``codec``  : encodage de l'observation (vecteur fixe) et des actions (espace
    discret fixe + masque des actions légales) ;
  * ``env``    : environnement pilotable (reset/step) qui inverse le moteur synchrone ;
  * ``reseau`` : réseau acteur-critique ;
  * ``ppo``    : entraînement PPO masqué ;
  * ``jouer``  : politique d'inférence (chargée par ``JoueurRL``).
"""
