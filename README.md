# Wanikani
Cette application Streamlit permet d'afficher vos kanji, vocabulaire et statistiques WaniKani avec une interface en français.

## Installation
1. Installez les dépendances Python :
   ```bash
   pip install -r requirements.txt
   ```
2. Lancez l'application avec Streamlit ou directement via Python :
   ```bash
   # méthode conseillée
   streamlit run wanikani_dashboard/app.py
   
   # ou en mode script simple
   python wanikani_dashboard/app.py
   ```

## Fonctionnalités

- Authentification par token API WaniKani.
- Affichage du nombre de kanji et de vocabulaire appris.
- Tableau des reviews à venir sur les prochaines 24h.
- Liste détaillée des kanji et du vocabulaire avec leur signification traduite en français.
- Graphique de progression par niveau pour visualiser vos avancées.
- Possibilité de se déconnecter ou de rafraîchir les données.

## Notes

La traduction des significations est réalisée à l'aide de la librairie `googletrans`. Une connexion internet est donc nécessaire pour obtenir les traductions.
