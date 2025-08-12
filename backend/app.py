from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from google.cloud import firestore

app = FastAPI(title="Manthan Creator Suite API", version="0.1.0")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firestore config
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "projects")
db = firestore.Client()

class ProjectIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    logline: str = Field(..., min_length=5, max_length=400)
    genre: Optional[str] = None
    tone: Optional[str] = None
    creator_name: Optional[str] = None

class Project(ProjectIn):
    id: str

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

# ---- Helpers ----
def _doc_to_project(doc) -> Project:
    data = doc.to_dict()
    return Project(id=doc.id, **data)

# ---- Routes ----
@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/projects", response_model=List[Project])
def list_projects():
    docs = db.collection(FIRESTORE_COLLECTION).order_by("title").stream()
    return [_doc_to_project(d) for d in docs]

@app.post("/api/projects", response_model=Project, status_code=201)
def create_project(payload: ProjectIn):
    ref = db.collection(FIRESTORE_COLLECTION).document()
    data = payload.dict()
    ref.set(data)
    return Project(id=ref.id, **data)

@app.post("/api/pitch/generate", response_model=PitchPack)
def generate_pitch(payload: PitchRequest):
    # Stubbed generator — deterministic, no external API keys needed yet.
    title = payload.title.strip()
    logline = payload.logline.strip()
    genre = (payload.genre or "Drama").strip()
    tone = (payload.tone or "Grounded, character-driven").strip()

    synopsis = (
        f"**{title}** is a {genre.lower()} told with a {tone.lower()} tone. "
        f"It centers on the premise: {logline} "
        "In Act I, we meet the protagonist at a point of quiet crisis; in Act II, "
        "a bold decision reroutes their life; Act III delivers a surprising yet inevitable resolution."
    )

    beat_sheet = [
        "Opening Image — a snapshot of the protagonist’s everyday contradiction",
        "Theme Stated — a line that foreshadows the inner journey",
        "Catalyst — an event that upends the status quo",
        "Debate — resist or leap?",
        "Break into Two — commitment to a new path",
        "Midpoint — stakes and truth sharpen",
        "Bad Guys Close In — pressure mounts",
        "All Is Lost — confrontation with the core fear",
        "Break into Three — integrating lesson + new plan",
        "Finale — decisive action and transformation",
        "Final Image — mirror of the opening, now evolved"
    ]

    deck_outline = [
        "Cover: Title, logline, key art placeholder",
        "Overview: Why now? Audience? Tone & genre anchors",
        "World & Characters: 3-5 leads with concise arcs",
        "Story: 1-page synopsis + 10-beat board",
        "Lookbook: Visual references (mood, palette, comps)",
        "Market: Comps, potential buyers, format & runtime",
        "Team: Creator bio, past credits, attachments (if any)",
        "Next Steps: What we need (budget, partners, timeline)"
    ]

    return PitchPack(title=title, logline=logline, synopsis=synopsis, beat_sheet=beat_sheet, deck_outline=deck_outline)
