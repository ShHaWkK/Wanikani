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

API_BASE = "https://api.wanikani.com/v2/"


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
st.set_page_config(page_title="WaniKani Dashboard", page_icon="🎴", layout="wide", initial_sidebar_state="auto")
WANIKANI_PINK = "#f06"

# --- STYLE Pro ---

st.set_page_config(page_title="Tableau de bord WaniKani", page_icon="🎴", layout="wide")

# Thème semi-sombre japonisant
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');

:root {
    --sakura-pink: #f06292;
    --japan-dark: #1e1e2f;
    --japan-panel: #2a2a3d;
    --text-color: #f5f5f5;
}

html, body, .stApp {
    background-color: var(--japan-dark);
    color: var(--text-color);
    font-family: 'Noto Sans JP', sans-serif;
}

.block-container {
    background-color: var(--japan-panel);
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

h1, h2, h3, h4 {
    color: var(--sakura-pink);
    font-weight: bold;
}

.stButton>button {
    background-color: var(--sakura-pink);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.5rem 1rem;
}

.element-container svg text {
    fill: var(--text-color) !important;
}

table {
    color: white;
    background-color: #333333;
    border-radius: 6px;
}

a {
    color: #ffb3c6;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}
</style>
""", unsafe_allow_html=True)

# --- Titre ---
st.markdown("<div class='wanikani-header'>🎴 Tableau de bord WaniKani</div>", unsafe_allow_html=True)

# --- Authentification ---
if "token" not in st.session_state:
    st.session_state["token"] = ""

if not st.session_state["token"]:
    st.subheader("🔐 Connexion à l'API WaniKani")
    st.session_state["token"] = st.text_input("Entrez votre API Token WaniKani", type="password", placeholder="ex : wk...123")
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

# --- Statistiques ---
st.subheader("📊 Statistiques générales")
col1, col2, col3 = st.columns(3)
col1.metric("Kanji", len(kanji_assignments))
col2.metric("Vocabulaire", len(vocab_assignments))
col3.metric("Leçons disponibles", len(lesson_assignments))

# --- Graphiques ---
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

# --- Éléments d’étude ---
st.subheader("📚 Détails des éléments")
tabs = st.tabs(["📝 Leçons", "🈚 Kanji", "📖 Vocabulaire"])

with tabs[0]:
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

with tabs[1]:
    data = []
    for a in kanji_assignments:
        sid = a["data"]["subject_id"]
        s = subjects.get(sid, {})
        char = s.get("data", {}).get("characters", "?")
        meaning = s.get("data", {}).get("meanings", [{}])[0].get("meaning", "?")
        data.append({"Kanji": char, "Signification": meaning})
    st.dataframe(pd.DataFrame(data), use_container_width=True)

with tabs[2]:
    data = []
    for a in vocab_assignments:
        sid = a["data"]["subject_id"]
        s = subjects.get(sid, {})
        char = s.get("data", {}).get("characters", "?")
        meaning = s.get("data", {}).get("meanings", [{}])[0].get("meaning", "?")
        data.append({"Vocabulaire": char, "Signification": meaning})
    st.dataframe(pd.DataFrame(data), use_container_width=True)

# --- Déconnexion ---
st.divider()
if st.button("🔒 Se déconnecter"):
    st.session_state["token"] = ""
    st.experimental_rerun()
