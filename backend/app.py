from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import json
import re

from google.cloud import firestore
import firebase_admin
from firebase_admin import auth as fb_auth

# --- OpenAI (GPT-5 / GPT-5mini) optional wiring ---
try:
    from openai import OpenAI
    _openai_available = True
except Exception:
    _openai_available = False

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")  # set to "gpt-5" when you want
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

app = FastAPI(title="Manthan Creator Suite API", version="0.3.0")

# -------- CORS ----------
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,  # we use Authorization header (no cookies)
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# -------- Firestore ----------
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "projects")
db = firestore.Client()

# -------- Firebase Admin (verify ID tokens) ----------
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={"projectId": os.environ.get("GOOGLE_CLOUD_PROJECT")})

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
        decoded = fb_auth.verify_id_token(token)  # verifies signature & expiry
        return decoded["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def _parse_json_loose(text: str) -> Optional[dict]:
    """Accept JSON with or without code fences; try to recover first {...} block."""
    if not text:
        return None
    # strip fences if present
    fenced = re.search(r"\{.*\}", text, re.DOTALL)
    s = fenced.group(0) if fenced else text
    try:
        return json.loads(s)
    except Exception:
        return None

def _clamp_list(xs, n):
    if xs is None:
        return []
    return [str(x).strip() for x in xs][:n]

def _generate_with_gpt5(title: str, logline: str, genre: str, tone: str) -> Optional[dict]:
    """
    Calls GPT-5/5mini (if OPENAI_API_KEY present). Returns dict or None on any error.
    Enforces tight conditioning on the provided logline/title and strict JSON output.
    """
    if not _openai_available or not os.getenv("OPENAI_API_KEY"):
        return None

    client = OpenAI()
    system = (
        "You are the Packaging Agent for Project Manthan. "
        "Write culturally authentic Indian film/series material across Hindi/Tamil/Telugu contexts. "
        "Bias toward specificity, visuality, and market-ready language. "
        "Everything must be tightly grounded in the given TITLE and LOGLINE."
    )
    instructions = (
        "Return ONLY valid JSON with keys: "
        "title, logline, synopsis (200-300 words), beat_sheet (10 items), deck_outline (8 items). "
        "Each beat must logically pay off the exact premise in the logline; avoid generic boilerplate. "
        "Prefer Indian settings, references, and tone appropriate to the genre."
    )
    user_payload = {
        "title": title,
        "logline": logline,
        "genre": genre or "Drama",
        "tone":  tone  or "Grounded, character-driven"
    }

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=OPENAI_TEMPERATURE,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": f"{instructions}\n\nINPUT:\n{json.dumps(user_payload, ensure_ascii=False)}"
                },
            ],
        )
        txt = resp.choices[0].message.content
        data = _parse_json_loose(txt)
        if not data:
            return None
        # minimal schema guard + clamping
        data["title"] = data.get("title") or title
        data["logline"] = data.get("logline") or logline
        data["synopsis"] = str(data.get("synopsis") or "")
        data["beat_sheet"] = _clamp_list(data.get("beat_sheet"), 10)
        data["deck_outline"] = _clamp_list(data.get("deck_outline"), 8)
        # ensure nothing came back empty
        if not data["synopsis"] or not data["beat_sheet"] or not data["deck_outline"]:
            return None
        return data
    except Exception:
        return None

# -------- Routes ----------
@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/projects", response_model=List[Project])
def list_projects(uid: str = Depends(get_uid)):
    docs = (
        db.collection(FIRESTORE_COLLECTION)
        .where("owner_uid", "==", uid)
        .order_by("title")
        .stream()
    )
    return [_doc_to_project(d) for d in docs]

@app.post("/api/projects", response_model=Project, status_code=201)
def create_project(payload: ProjectIn, uid: str = Depends(get_uid)):
    ref = db.collection(FIRESTORE_COLLECTION).document()
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

    # 1) Try GPT-5/5mini
    data = _generate_with_gpt5(title, logline, genre, tone)

    # 2) Fallback (template) if no key or model hiccup
    if not data:
        synopsis = (
            f"**{title}** is a {genre.lower()} told with a {tone.lower()} tone. "
            f"The core premise is: {logline} "
            "Act I establishes the world and the protagonist’s immediate stakes born from this premise; "
            "Act II escalates with choices that logically follow the logline’s conflict; "
            "Act III resolves the tension in a way that pays off the premise."
        )
        beat_sheet = [
            "Opening Image — show the world implied by the logline (place, class, rhythm).",
            "Theme Stated — a line tied to the logline’s inner conflict.",
            "Catalyst — the inciting event that activates the premise.",
            "Debate — protagonist weighs the cost of engaging the premise.",
            "Break into Two — decisive step that embodies the premise.",
            "Midpoint — a reversal or reveal that reframes the premise’s stakes.",
            "Bad Guys Close In — pressure tied directly to the premise.",
            "All Is Lost — premise appears unwinnable.",
            "Break into Three — insight earned from the premise’s contradictions.",
            "Finale — visual, specific payoff rooted in the logline."
        ]
        deck_outline = [
            "Cover: Title & logline (centered on the premise).",
            "Overview: Why now (market/audience fit in India).",
            "World & Characters: 3–5 leads with premise-tied arcs.",
            "Story: 1-page synopsis referencing the logline.",
            "Beat Board: The 10 beats above.",
            "Lookbook: 6–8 Indian visual references (mood/locations).",
            "Market & Comps: Indian OTT/films relevant to the premise.",
            "Team & Next Steps: Attachments, timeline, budget range."
        ]
        data = {
            "title": title, "logline": logline, "synopsis": synopsis,
            "beat_sheet": beat_sheet, "deck_outline": deck_outline
        }

    return PitchPack(**data)

