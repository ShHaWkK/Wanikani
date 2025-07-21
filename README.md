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

## Fonctionnalités

- Authentification par token API WaniKani.
- Affichage du nombre de kanji et de vocabulaire appris.
- Tableau des reviews à venir sur les prochaines 24h.
- Liste détaillée des kanji et du vocabulaire avec leur signification traduite en français.
- Possibilité de se déconnecter ou de rafraîchir les données.

## Notes

La traduction des significations est réalisée à l'aide de la librairie `googletrans`. Une connexion internet est donc nécessaire pour obtenir les traductions.
