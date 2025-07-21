# Wanikani
Cette application Streamlit permet d'afficher vos kanji, vocabulaire et statistiques WaniKani avec une interface en français.

## Installation
1. Installez les dépendances Python :
   ```bash
   pip install -r requirements.txt
   ```
2. Lancez l'application :
   ```bash
   streamlit run wanikani_dashboard/app.py
   ```
3. Récupérez votre token API WaniKani :
   - Si vous ne possédez pas de compte, créez-en un sur [wanikani.com](https://www.wanikani.com/).
   - Dans vos paramètres WaniKani, section *API Tokens*, générez un token **Read Only** et copiez‑le. Ce token vous sera demandé au lancement de l'application.
4. (Optionnel) Démarrez l'API de démonstration :
   ```bash
   uvicorn mock_wanikani_api:app --reload
   ```
   Cette API simplifiée permet désormais la création de compte (`/signup`), la connexion (`/login`) et fournit une route de session de révision (`/v2/revision-session`).
   Les comptes et tokens sont stockés en mémoire uniquement pour vos tests locaux.
   Pour créer un compte de test :
   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d '{"username": "demo", "password": "demo"}' \
        http://127.0.0.1:8000/signup
   ```
   Puis connectez-vous pour récupérer un token :
   ```bash
   curl -X POST -H "Content-Type: application/json" \
        -d '{"username": "demo", "password": "demo"}' \
        http://127.0.0.1:8000/login
   ```
   Utilisez la valeur `access_token` renvoyée pour faire des requêtes protégées.

5. Si vous utilisez l'API de démonstration, vous pouvez changer l'URL de base en
   définissant la variable d'environnement `WANIKANI_API_BASE`. Par défaut, l'app
   pointe vers `https://api.wanikani.com/v2/`.

## Fonctionnalités

- Authentification par token API WaniKani.
- Affichage du nombre de kanji et de vocabulaire appris.
- Tableau des reviews à venir sur les prochaines 24h.
- Liste détaillée des kanji et du vocabulaire avec leur signification traduite en français.
- Possibilité de se déconnecter ou de rafraîchir les données.

## Notes

La traduction des significations est réalisée à l'aide de la librairie `googletrans`. Une connexion internet est donc nécessaire pour obtenir les traductions.
