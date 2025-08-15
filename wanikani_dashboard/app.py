import datetime as dt
import os
from typing import Dict, List

import pandas as pd
import requests
import streamlit as st

# --- Sécurité de lancement ---
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx() is None:
        print("Ce script doit être exécuté avec 'streamlit run'.")
        raise SystemExit
except Exception:
    pass

API_BASE = os.getenv("WANIKANI_API_BASE", "https://api.wanikani.com/v2/")


# --- Appels API ---
def _get(url: str, token: str) -> Dict:
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def fetch_assignments(token: str, subject_type: str) -> List[Dict]:
    url = f"{API_BASE}assignments?subject_types={subject_type}"
    data = []
    while url:
        result = _get(url, token)
        data.extend(result["data"])
        url = result["pages"].get("next_url")
    return data


def fetch_subjects(token: str, ids: List[int]) -> Dict[int, Dict]:
    if not ids:
        return {}
    url = f"{API_BASE}subjects?ids={','.join(str(i) for i in ids)}"
    result = _get(url, token)
    return {item["id"]: item for item in result["data"]}


def fetch_summary(token: str) -> Dict:
    return _get(f"{API_BASE}summary", token)


def fetch_available_lessons(token: str) -> List[Dict]:
    url = f"{API_BASE}assignments?immediately_available_for_lessons=true"
    data = []
    while url:
        result = _get(url, token)
        data.extend(result["data"])
        url = result["pages"].get("next_url")
    return data


def fetch_revision_session(token: str) -> Dict:
    """Récupère un sujet aléatoire pour un exercice rapide."""
    return _get(f"{API_BASE}revision-session", token)


# --- Traitements des données ---
def build_srs_dataframe(assignments: List[Dict]) -> pd.DataFrame:
    stages = {
        0: "Leçon", 1: "Apprenti 1", 2: "Apprenti 2", 3: "Apprenti 3", 4: "Apprenti 4",
        5: "Guru 1", 6: "Guru 2", 7: "Maître", 8: "Éclairé", 9: "Brûlé"
    }
    counts = {name: 0 for name in stages.values()}
    for a in assignments:
        name = stages.get(a.get("data", {}).get("srs_stage", 0), "Autre")
        counts[name] = counts.get(name, 0) + 1
    return pd.DataFrame({"SRS": list(counts.keys()), "Nombre": list(counts.values())})


def build_review_schedule(summary: Dict) -> pd.DataFrame:
    reviews = summary.get("data", {}).get("reviews", [])

    now = dt.datetime.now(dt.timezone.utc)
    tomorrow = now + dt.timedelta(hours=24)
    hours = {}

    for review_block in reviews:
        available_at_str = review_block.get("available_at")
        subject_ids = review_block.get("subject_ids", [])

        if not available_at_str:
            continue

        try:
            available_at = dt.datetime.fromisoformat(available_at_str.replace("Z", "+00:00"))
        except Exception:
            continue

        if now <= available_at <= tomorrow:
            hour = available_at.replace(minute=0, second=0, microsecond=0)
            hours[hour] = hours.get(hour, 0) + len(subject_ids)

    if not hours:
        return pd.DataFrame(columns=["Heure", "Nombre"])

    df = pd.DataFrame({"Heure": list(hours.keys()), "Nombre": list(hours.values())})
    df.sort_values("Heure", inplace=True)
    return df


def build_level_dataframe(assignments: List[Dict], subjects: Dict[int, Dict]) -> pd.DataFrame:
    levels = {}
    for a in assignments:
        sid = a["data"].get("subject_id")
        level = subjects.get(sid, {}).get("data", {}).get("level")
        if level is not None:
            levels[level] = levels.get(level, 0) + 1
    if not levels:
        return pd.DataFrame(columns=["Niveau", "Nombre"])
    df = pd.DataFrame({"Niveau": list(levels.keys()), "Nombre": list(levels.values())})
    df.sort_values("Niveau", inplace=True)
    return df


# --- Interface Streamlit ---
st.set_page_config(page_title="Tableau de bord WaniKani", page_icon="🎴", layout="wide", initial_sidebar_state="auto")

# Thème clair moderne
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');

:root {
    --primary-color: #3B82F6;
    --secondary-color: #1E3A8A;
    --bg-color: #f9fafb;
    --panel-color: #ffffff;
    --text-color: #111827;
}

html, body, .stApp {
    background-color: var(--bg-color);
    color: var(--text-color);
    font-family: 'Inter', sans-serif;
}

.wanikani-header {
    font-size: 2.5rem;
    text-align: center;
    margin-bottom: 2rem;
    padding: 1rem;
    background: var(--primary-color);
    border-radius: 8px;
    color: white;
}

.block-container {
    background-color: var(--panel-color);
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

h1, h2, h3, h4 {
    color: var(--secondary-color);
    font-weight: bold;
}

.stButton>button {
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.5rem 1rem;
}

.element-container svg text {
    fill: var(--text-color) !important;
}

table {
    color: var(--text-color);
    background-color: var(--panel-color);
    border-radius: 6px;
}

a {
    color: var(--primary-color);
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

.footer {
    text-align: center;
    margin-top: 2rem;
    color: var(--text-color);
    font-size: 0.8rem;
}
</style>
""", unsafe_allow_html=True)

# --- Titre ---
st.markdown("<div class='wanikani-header'>🎴 Tableau de bord WaniKani</div>", unsafe_allow_html=True)
st.sidebar.header("Menu")
page = st.sidebar.radio("Navigation", ["Dashboard", "Leçons", "Exercices"])

# --- Authentification ---
if "token" not in st.session_state:
    st.session_state["token"] = ""

if not st.session_state["token"]:
    st.subheader("🔐 Connexion à l'API WaniKani")
    token_input = st.text_input(
        "Entrez votre API Token WaniKani",
        type="password",
        placeholder="ex : wk...123",
    )
    if st.button("Connexion") and token_input:
        st.session_state["token"] = token_input.strip()
        st.experimental_rerun()
    st.stop()

token = st.session_state["token"]

# --- Chargement données ---
with st.spinner("🔄 Chargement des données..."):
    try:
        kanji_assignments = fetch_assignments(token, "kanji")
        vocab_assignments = fetch_assignments(token, "vocabulary")
        lesson_assignments = fetch_available_lessons(token)

        all_ids = [a["data"]["subject_id"] for a in kanji_assignments + vocab_assignments + lesson_assignments]
        subjects = fetch_subjects(token, all_ids)
        summary = fetch_summary(token)

        srs_df = build_srs_dataframe(kanji_assignments + vocab_assignments)
        level_df = build_level_dataframe(kanji_assignments + vocab_assignments, subjects)
    except requests.HTTPError:
        st.error("❌ Token invalide ou connexion API échouée.")
        st.stop()
    except Exception as exc:
        st.error(f"💥 Erreur : {exc}")
        st.stop()

if page == "Dashboard":
    st.subheader("📊 Statistiques générales")
    col1, col2, col3 = st.columns(3)
    col1.metric("Kanji", len(kanji_assignments))
    col2.metric("Vocabulaire", len(vocab_assignments))
    col3.metric("Leçons disponibles", len(lesson_assignments))

    st.subheader("⏰ Reviews dans les 24h")
    df_reviews = build_review_schedule(summary)
    if df_reviews.empty:
        st.info("Aucune review à venir dans les prochaines 24h.")
    else:
        st.bar_chart(df_reviews.set_index("Heure"))

    st.subheader("🔁 Répartition SRS")
    st.bar_chart(srs_df.set_index("SRS"))

    st.subheader("📈 Progression par niveau")
    if not level_df.empty:
        st.bar_chart(level_df.set_index("Niveau"))
    else:
        st.info("Aucune donnée de niveau disponible.")

elif page == "Leçons":
    st.subheader("📝 Leçons disponibles")
    if not lesson_assignments:
        st.write("Aucune leçon disponible.")
    else:
        data = []
        for a in lesson_assignments:
            sid = a["data"]["subject_id"]
            s = subjects.get(sid, {})
            char = s.get("data", {}).get("characters", "?")
            meaning = s.get("data", {}).get("meanings", [{}])[0].get("meaning", "?")
            url = f"https://www.wanikani.com/subject/{sid}"
            data.append({"Élément": char, "Signification": meaning, "Lien": f"[Ouvrir]({url})"})
        st.write(pd.DataFrame(data).to_html(escape=False), unsafe_allow_html=True)

    st.subheader("🈚 Kanji")
    data = []
    for a in kanji_assignments:
        sid = a["data"]["subject_id"]
        s = subjects.get(sid, {})
        char = s.get("data", {}).get("characters", "?")
        meaning = s.get("data", {}).get("meanings", [{}])[0].get("meaning", "?")
        data.append({"Kanji": char, "Signification": meaning})
    st.dataframe(pd.DataFrame(data), use_container_width=True)

    st.subheader("📖 Vocabulaire")
    data = []
    for a in vocab_assignments:
        sid = a["data"]["subject_id"]
        s = subjects.get(sid, {})
        char = s.get("data", {}).get("characters", "?")
        meaning = s.get("data", {}).get("meanings", [{}])[0].get("meaning", "?")
        data.append({"Vocabulaire": char, "Signification": meaning})
    st.dataframe(pd.DataFrame(data), use_container_width=True)

elif page == "Exercices":
    st.subheader("🎯 Exercice rapide")
    try:
        session = fetch_revision_session(token)
        subj = session.get("subject", {}).get("data", {})
        char = subj.get("characters", "?")
        meaning = subj.get("meaning") or subj.get("meanings", [{}])[0].get("meaning", "?")
        st.markdown(f"## {char}")
        if st.button("Révéler la réponse"):
            st.write(f"Signification : {meaning}")
    except Exception:
        st.error("Impossible de charger un exercice.")

# --- Déconnexion ---
st.divider()
if st.button("🔒 Se déconnecter"):
    st.session_state["token"] = ""
    st.experimental_rerun()

st.markdown(
    "<div class='footer'>Inspiré par <a href='https://www.wanikani.com' target='_blank'>WaniKani</a></div>",
    unsafe_allow_html=True,
)
