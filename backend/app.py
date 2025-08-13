from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os, json, re, logging

from google.cloud import firestore
import firebase_admin
from firebase_admin import auth as fb_auth

# --- OpenAI (GPT-5 / GPT-5mini) optional wiring ---
try:
    from openai import OpenAI
    _openai_available = True
except Exception:
    _openai_available = False

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Manthan Creator Suite API", version="0.3.1")

# -------- CORS ----------
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# -------- Firebase Admin (verify ID tokens) ----------
if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app(options={"projectId": PROJECT_ID})
        logging.info("Firebase Admin initialized (project=%s)", PROJECT_ID)
    except Exception as e:
        logging.exception("Firebase Admin init failed")

# -------- Firestore (lazy) ----------
_db = None
def get_db():
    global _db
    if _db is None:
        logging.info("Creating Firestore client (project=%s)", PROJECT_ID)
        _db = firestore.Client(project=PROJECT_ID) if PROJECT_ID else firestore.Client()
    return _db

FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "projects")

# -------- Models ----------
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

# -------- Helpers ----------
def _doc_to_project(doc) -> Project:
    data = doc.to_dict()
    return Project(id=doc.id, **data)

def get_uid(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        decoded = fb_auth.verify_id_token(token)
        return decoded["uid"]
    except Exception:
        logging.exception("verify_id_token failed")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def _parse_json_loose(text: str) -> Optional[dict]:
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

def _generate_with_gpt5(title: str, logline: str, genre: str, tone: str) -> Optional[dict]:
    if not _openai_available or not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        client = OpenAI()
        system = (
            "You are the Packaging Agent for Project Manthan. "
            "Write culturally authentic Indian film/series material. "
            "Everything must be grounded in the given TITLE and LOGLINE; avoid boilerplate."
        )
        instructions = (
            "Return ONLY valid JSON with keys: "
            "title, logline, synopsis (200-300 words), beat_sheet (10 items), deck_outline (8 items). "
            "Each beat must logically pay off the logline; prefer Indian settings & tone."
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
        logging.exception("GPT-5 generation failed")
        return None

# -------- Events ----------
@app.on_event("startup")
def on_startup():
    logging.info("App starting (project=%s, origin=%s)", PROJECT_ID, ALLOWED_ORIGIN)

# -------- Routes ----------
@app.get("/api/health")
def health():
    return {"ok": True}

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
            "Act I establishes the world and immediate stakes from this premise; "
            "Act II escalates with choices that logically follow; "
            "Act III resolves the tension in a way that pays off the premise."
        )
        beat_sheet = [
            "Opening Image — show the world implied by the logline.",
            "Theme Stated — a line tied to the inner conflict.",
            "Catalyst — inciting event that activates the premise.",
            "Debate — cost of engaging the premise.",
            "Break into Two — decisive step that embodies the premise.",
            "Midpoint — reversal/reveal that reframes stakes.",
            "Bad Guys Close In — pressure tied to the premise.",
            "All Is Lost — the premise appears unwinnable.",
            "Break into Three — insight earned from contradictions.",
            "Finale — specific payoff rooted in the logline.",
        ]
        deck_outline = [
            "Cover: Title & logline (premise centered).",
            "Overview: Why now (market/audience in India).",
            "World & Characters: 3–5 leads with premise-tied arcs.",
            "Story: 1-page synopsis referencing the logline.",
            "Beat Board: The 10 beats above.",
            "Lookbook: Visual references (India-specific).",
            "Market & Comps: Relevant Indian films/OTT.",
            "Team & Next Steps: Attachments, timeline, budget.",
        ]
        data = {"title": title, "logline": logline, "synopsis": synopsis,
                "beat_sheet": beat_sheet, "deck_outline": deck_outline}
    return PitchPack(**data)

