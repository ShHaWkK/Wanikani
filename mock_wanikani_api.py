from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
import datetime as dt
import secrets
import random

app = FastAPI(title="Simple WaniKani-like API")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
auth_scheme = HTTPBearer()

users = {}
tokens = {}

SAMPLE_SUBJECTS = {
    1: {"id": 1, "object": "kanji", "data": {"characters": "日", "meaning": "sun", "level": 1}},
    2: {"id": 2, "object": "vocabulary", "data": {"characters": "本", "meaning": "book", "level": 1}},
}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
) -> str:
    token = credentials.credentials
    user = tokens.get(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return user


@app.post("/signup")
def signup(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    if username in users:
        raise HTTPException(status_code=400, detail="user already exists")
    users[username] = pwd_context.hash(password)
    return {"message": "account created"}


@app.post("/login")
def login(payload: dict):
    username = payload.get("username")
    password = payload.get("password")
    hashed = users.get(username)
    if not hashed or not pwd_context.verify(password, hashed):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = secrets.token_hex(16)
    tokens[token] = username
    return {"access_token": token}

@app.get("/v2/assignments")
def get_assignments():
    return {"data": [
        {"id": 1, "data": {"subject_id": 1}},
        {"id": 2, "data": {"subject_id": 2}},
    ]}

@app.get("/v2/subjects")
def get_subjects(ids: str):
    ids_int = [int(i) for i in ids.split(",")]
    return {"data": [SAMPLE_SUBJECTS[i] for i in ids_int if i in SAMPLE_SUBJECTS]}

@app.get("/v2/summary")
def get_summary():
    now = dt.datetime.utcnow().isoformat() + "Z"
    return {"data": {"reviews": {"upcoming": [{"available_at": now, "subject_ids": [1, 2]}]}}}


@app.get("/v2/revision-session")
def revision_session(user: str = Depends(get_current_user)):
    subject = random.choice(list(SAMPLE_SUBJECTS.values()))
    return {"user": user, "subject": subject}
