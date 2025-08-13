# backend/app.py

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os, json, re, logging, base64

from google.cloud import firestore
import firebase_admin
from firebase_admin import auth as fb_auth

# --- OpenAI (optional) ---
try:
    from openai import OpenAI
    _openai_available = True
except Exception:
    _openai_available = False

# ---------- Env / Config ----------
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
OPENAI_TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))
DEBUG_MODE = os.environ.get("DEBUG", "0") == "1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manthan-backend")

app = FastAPI(title="Manthan Creator Suite API", version="0.4.1")

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---------- Firebase Admin (stable init) ----------
if not firebase_admin._apps:
    try:
        if PROJECT_ID:
            firebase_admin.initialize_app(options={"projectId": PROJECT_ID})
        else:
            firebase_admin.initialize_app()
        logger.info("Firebase Admin initialized (project=%s)", PROJECT_ID)
    except Exception:
        logger.exception("Firebase Admin init failed")

# ---------- Firestore (lazy) ----------
_db = None
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "projects")

def get_db():
    global _db
    if _db is None:
        logger.info("Creating Firestore client (project=%s)", PROJECT_ID)
        _db = firestore.Client(project=PROJECT_ID) if PROJECT_ID else firestore.Client()
    return _db

# ---------- Models ----------
class ProjectIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    logline: str = Field(..., min_length=5, max_length=400)
    genre: Optional[str] = None
    tone: Optional[str] = None
    creator_name: Optional[str] = None

class Project(ProjectIn):
    id: str
    owner_uid: Optional[str] = None

class PitchRequest(BaseModel):
    title: str
    logline: str
    genre: Optional[str] = None
    tone: Optional[str] = None

class PitchPack(BaseModel):
    title: str
    logline: str
    synopsis: str
    beat_sheet: List[str]
    deck_outline: List[str]

# ---------- Helpers ----------
def _doc_to_project(doc) -> Project:
    data = doc.to_dict()
    return Project(id=doc.id, **data)

def _peek_claims(token: str):
    """Decode JWT payload (no verification) to log aud/iss on failures."""
    try:
        payload_b64 = token.split(".")[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        return data.get("aud"), data.get("iss"), data
    except Exception:
        return None, None, None

def get_uid(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        decoded = fb_auth.verify_id_token(token)  # verifies signature, exp, aud, iss for PROJECT_ID
        return decoded["uid"]
    except Exception as e:
        aud, iss, payload = _peek_claims(token)
        logger.error(
            "verify_id_token failed: %s | PROJECT_ID=%s | aud=%s | iss=%s",
            e, PROJECT_ID, aud, iss
        )
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def _parse_json_loose(text: str):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    s = m.group(0) if m else text
    try:
        return json.loads(s)
    except Exception:
        return None

def _clamp_list(xs, n):
    if xs is None:
        return []
    return [str(x).strip() for x in xs][:n]

def _generate_with_gpt5(title: str, logline: str, genre: str, tone: str):
    if not _openai_available or not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        client = OpenAI()
        system = (
            "You are the Packaging Agent for Project Manthan. "
            "Write culturally authentic Indian film/series material (Hindi/Tamil/Telugu). "
            "Everything must be tightly grounded in the given TITLE and LOGLINE; avoid boilerplate."
        )
        instructions = (
            "Return ONLY valid JSON with keys: "
            "title, logline, synopsis (200-300 words), beat_sheet (10 items), deck_outline (8 items). "
            "Each beat must logically pay off the premise in the logline; prefer Indian settings & tone."
        )
        payload = {"title": title, "logline": logline, "genre": genre or "Drama", "tone": tone or "Grounded"}
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"{instructions}\n\nINPUT:\n{json.dumps(payload, ensure_ascii=False)}"},
            ],
        )
        txt = resp.choices[0].message.content
        data = _parse_json_loose(txt)
        if not data:
            return None
        data["title"] = data.get("title") or title
        data["logline"] = data.get("logline") or logline
        data["synopsis"] = str(data.get("synopsis") or "")
        data["beat_sheet"] = _clamp_list(data.get("beat_sheet"), 10)
        data["deck_outline"] = _clamp_list(data.get("deck_outline"), 8)
        if not data["synopsis"] or not data["beat_sheet"] or not data["deck_outline"]:
            return None
        return data
    except Exception:
        logger.exception("GPT-5 generation failed")
        return None

# ---------- Lifecycle ----------
@app.on_event("startup")
def on_startup():
    logger.info(
        "App starting | PROJECT_ID=%s | ALLOWED_ORIGIN=%s | OPENAI_MODEL=%s | DEBUG=%s",
        PROJECT_ID, ALLOWED_ORIGIN, OPENAI_MODEL, DEBUG_MODE
    )

# ---------- Routes ----------
@app.get("/api/health")
def health():
    return {"ok": True}

# TEMPORARY: debug token claims (enable with DEBUG=1)
if DEBUG_MODE:
    @app.get("/api/debug/token")
    def debug_token(authorization: str = Header(None)):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")
        token = authorization.split(" ", 1)[1].strip()
        aud, iss, payload = _peek_claims(token)
        return {
            "backend_PROJECT_ID": PROJECT_ID,
            "aud": aud,
            "iss": iss,
            "sub": payload.get("sub") if payload else None,
            "auth_time": payload.get("auth_time") if payload else None,
            "exp": payload.get("exp") if payload else None,
        }

@app.get("/api/projects", response_model=List[Project])
def list_projects(uid: str = Depends(get_uid)):
    docs = (
        get_db().collection(FIRESTORE_COLLECTION)
        .where("owner_uid", "==", uid)
        .order_by("title")
        .stream()
    )
    return [_doc_to_project(d) for d in docs]

@app.post("/api/projects", response_model=Project, status_code=201)
def create_project(payload: ProjectIn, uid: str = Depends(get_uid)):
    ref = get_db().collection(FIRESTORE_COLLECTION).document()
    data = payload.dict()
    data["owner_uid"] = uid
    ref.set(data)
    return Project(id=ref.id, **data)

@app.post("/api/pitch/generate", response_model=PitchPack)
def generate_pitch(payload: PitchRequest, uid: str = Depends(get_uid)):
    title = (payload.title or "").strip()
    logline = (payload.logline or "").strip()
    genre = (payload.genre or "Drama").strip()
    tone  = (payload.tone  or "Grounded, character-driven").strip()

    data = _generate_with_gpt5(title, logline, genre, tone)
    if not data:
        synopsis = (
            f"**{title}** is a {genre.lower()} told with a {tone.lower()} tone. "
            f"The core premise is: {logline} "
            "Act I establishes world and immediate stakes; Act II escalates logically; "
            "Act III resolves in a way that pays off the premise."
        )
        beat_sheet = [
            "Opening Image — world implied by the logline.",
            "Theme Stated — line tied to inner conflict.",
            "Catalyst — event that activates the premise.",
            "Debate — cost of engaging the premise.",
            "Break into Two — decisive step embodying the premise.",
            "Midpoint — reversal/reveal reframing stakes.",
            "Bad Guys Close In — pressure tied to premise.",
            "All Is Lost — premise appears unwinnable.",
            "Break into Three — insight from contradictions.",
            "Finale — specific payoff rooted in the logline.",
        ]
        deck_outline = [
            "Cover: Title & logline.",
            "Overview: Why now (India market/audience).",
            "World & Characters: 3–5 leads tied to premise.",
            "Story: 1-page synopsis referencing the logline.",
            "Beat Board: The 10 beats above.",
            "Lookbook: India-specific references.",
            "Market & Comps: Relevant Indian films/OTT.",
            "Team & Next Steps: Attachments, timeline, budget.",
        ]
        data = {"title": title, "logline": logline, "synopsis": synopsis,
                "beat_sheet": beat_sheet, "deck_outline": deck_outline}
    return PitchPack(**data)


