"""Application Streamlit pour afficher les informations WaniKani en francais.
"""

import datetime as dt
import json
from typing import Dict, List

import pandas as pd
import requests
from googletrans import Translator
import streamlit as st

API_BASE = "https://api.wanikani.com/v2/"


def _get(url: str, token: str) -> Dict:
    """Effectue une requete GET a l'API WaniKani."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def fetch_assignments(token: str, subject_type: str) -> List[Dict]:
    """Recupere toutes les assignments pour un type de sujet."""
    url = f"{API_BASE}assignments?subject_types={subject_type}"
    data = []
    while url:
        result = _get(url, token)
        data.extend(result["data"])
        url = result["pages"].get("next_url")
    return data


def fetch_subjects(token: str, ids: List[int]) -> Dict[int, Dict]:
    """Recupere les details des sujets a partir de leurs IDs."""
    if not ids:
        return {}
    url = f"{API_BASE}subjects?ids={','.join(str(i) for i in ids)}"
    result = _get(url, token)
    return {item["id"]: item for item in result["data"]}


def fetch_summary(token: str) -> Dict:
    """Recupere le resume des reviews a venir."""
    url = f"{API_BASE}summary"
    return _get(url, token)


def fetch_available_lessons(token: str) -> List[Dict]:
    """Recupere les assignments disponibles pour les lecons immediates."""
    url = f"{API_BASE}assignments?immediately_available_for_lessons=true"
    data = []
    while url:
        result = _get(url, token)
        data.extend(result["data"])
        url = result["pages"].get("next_url")
    return data


def build_srs_dataframe(assignments: List[Dict]) -> pd.DataFrame:
    """Construit un DataFrame representant la distribution SRS."""
    stages = {
        0: "Leçon",
        1: "Apprenti 1",
        2: "Apprenti 2",
        3: "Apprenti 3",
        4: "Apprenti 4",
        5: "Guru 1",
        6: "Guru 2",
        7: "Maître",
        8: "Éclairé",
        9: "Brûlé",
    }
    counts = {name: 0 for name in stages.values()}
    for a in assignments:
        name = stages.get(a.get("data", {}).get("srs_stage", 0), "Autre")
        counts[name] = counts.get(name, 0) + 1
    df = pd.DataFrame({"SRS": list(counts.keys()), "Nombre": list(counts.values())})
    return df


def translate_meaning(text: str, translator: Translator) -> str:
    """Traduit un texte anglais en francais."""
    try:
        return translator.translate(text, dest="fr").text
    except Exception:
        # En cas d'echec, on renvoie le texte original
        return text


def build_review_schedule(summary: Dict) -> pd.DataFrame:
    """Prepare un DataFrame avec les reviews des prochaines 24h."""
    upcoming = summary.get("data", {}).get("reviews", {}).get("upcoming", [])
    now = dt.datetime.utcnow()
    tomorrow = now + dt.timedelta(hours=24)
    hours = {}
    for item in upcoming:
        available_at = dt.datetime.fromisoformat(item["available_at"].replace("Z", "+00:00"))
        if now <= available_at <= tomorrow:
            hour = available_at.replace(minute=0, second=0, microsecond=0)
            hours[hour] = hours.get(hour, 0) + item["subject_ids"].__len__()
    if not hours:
        return pd.DataFrame(columns=["Heure", "Nombre"])
    data = {"Heure": list(hours.keys()), "Nombre": list(hours.values())}
    df = pd.DataFrame(data)
    df.sort_values("Heure", inplace=True)
    return df


# Interface Streamlit
st.set_page_config(page_title="Tableau de bord WaniKani", page_icon="🎴", layout="wide")
st.title("Tableau de bord WaniKani")

# Style simple rappelant WaniKani
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700&display=swap');
        .stApp {background-color:#f5f5f5;}
        .block-container {background-color:#ffffff; padding:2rem 2rem; border-radius:10px;}
        h1, h2, h3 {color:#a25ef8; font-family:'Noto Sans', sans-serif;}
        body, text, button {font-family:'Noto Sans', sans-serif;}
        .stButton>button {background-color:#a25ef8; color:white; border:none; border-radius:4px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Saisie du token utilisateur
if "token" not in st.session_state:
    st.session_state["token"] = ""

if st.session_state["token"] == "":
    st.write("## Connexion")
    st.session_state["token"] = st.text_input(
        "Entrez votre token API WaniKani", type="password"
    )
    st.stop()

token = st.session_state["token"]
translator = Translator()

# Chargement des donnees
with st.spinner("Récupération des données..."):
    kanji_assignments = fetch_assignments(token, "kanji")
    vocab_assignments = fetch_assignments(token, "vocabulary")
    lesson_assignments = fetch_available_lessons(token)

    kanji_ids = [a["data"]["subject_id"] for a in kanji_assignments]
    vocab_ids = [a["data"]["subject_id"] for a in vocab_assignments]
    lesson_ids = [a["data"]["subject_id"] for a in lesson_assignments]

    subjects = fetch_subjects(token, kanji_ids + vocab_ids + lesson_ids)
    summary = fetch_summary(token)
    srs_df = build_srs_dataframe(kanji_assignments + vocab_assignments)

# Statistiques generales
nb_kanji = len(kanji_assignments)
nb_vocab = len(vocab_assignments)
nb_lessons = len(lesson_assignments)
st.subheader("Statistiques")
col1, col2, col3 = st.columns(3)
col1.metric("Kanji appris", nb_kanji)
col2.metric("Vocabulaire appris", nb_vocab)
col3.metric("Leçons disponibles", nb_lessons)

# Planning des reviews
df_reviews = build_review_schedule(summary)

st.subheader("Reviews à venir (24h)")
if df_reviews.empty:
    st.info("Aucune review prévue dans les prochaines 24h")
else:
    st.bar_chart(df_reviews.set_index("Heure"))

st.subheader("Répartition SRS")
st.bar_chart(srs_df.set_index("SRS"))

# Liste des leçons, kanji et vocabulaire
st.subheader("Éléments d'étude")

tabs = st.tabs(["Leçons", "Kanji", "Vocabulaire"])

# Affichage des leçons disponibles
with tabs[0]:
    if not lesson_ids:
        st.write("Aucune leçon disponible.")
    else:
        lesson_data = []
        for aid in lesson_ids:
            subject = subjects.get(aid, {})
            character = subject.get("data", {}).get("characters", "?")
            meaning = subject.get("data", {}).get("meanings", [])
            if meaning:
                meaning = meaning[0]["meaning"]
                meaning = translate_meaning(meaning, translator)
            else:
                meaning = "?"
            url = f"https://www.wanikani.com/subject/{aid}"
            lesson_data.append({"Élément": character, "Signification": meaning, "Lien": f"[Ouvrir]({url})"})
        df = pd.DataFrame(lesson_data)
        st.write(df.to_html(escape=False), unsafe_allow_html=True)

# Affichage des kanji
with tabs[1]:
    if not kanji_ids:
        st.write("Aucun kanji appris.")
    else:
        kanji_data = []
        for aid in kanji_ids:
            subject = subjects.get(aid, {})
            character = subject.get("data", {}).get("characters", "?")
            meaning = subject.get("data", {}).get("meanings", [])
            if meaning:
                meaning = meaning[0]["meaning"]
                meaning = translate_meaning(meaning, translator)
            else:
                meaning = "?"
            kanji_data.append({"Kanji": character, "Signification": meaning})
        st.table(pd.DataFrame(kanji_data))

# Affichage du vocabulaire
with tabs[2]:
    if not vocab_ids:
        st.write("Aucun vocabulaire appris.")
    else:
        vocab_data = []
        for aid in vocab_ids:
            subject = subjects.get(aid, {})
            character = subject.get("data", {}).get("characters", "?")
            meaning = subject.get("data", {}).get("meanings", [])
            if meaning:
                meaning = meaning[0]["meaning"]
                meaning = translate_meaning(meaning, translator)
            else:
                meaning = "?"
            vocab_data.append({"Vocabulaire": character, "Signification": meaning})
        st.table(pd.DataFrame(vocab_data))

# Bouton de deconnexion
if st.button("Se déconnecter"):
    st.session_state["token"] = ""
    st.experimental_rerun()
