# backend/app.py
from __future__ import annotations

import os, uuid, time
from typing import List, Optional, Literal, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Firestore + Firebase
from google.cloud import firestore
import firebase_admin
from firebase_admin import auth as fb_auth

# LLM client
_OPENAI_READY = False
try:
    from openai import OpenAI
    _OPENAI_READY = True
except Exception:
    _OPENAI_READY = False

import httpx

# -----------------------------------------------------------
# App
# -----------------------------------------------------------
app = FastAPI(title="Manthan Creator Suite API", version="0.5.0")

# Health
@app.get("/health")
def health_root():
    return {"status": "ok"}

@app.get("/api/health")
def health_api():
    return {"ok": True, "ts": int(time.time())}

# -----------------------------------------------------------
# CORS (allow your frontend; allow localhost for dev)
# -----------------------------------------------------------
DEFAULT_ALLOWED = [
    "https://manthan-frontend-524579286496.asia-south1.run.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
ALLOWED_ORIGINS = [
    o.strip() for o in (os.getenv("ALLOWED_ORIGINS") or "").split(",") if o.strip()
] or DEFAULT_ALLOWED

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# -----------------------------------------------------------
# Firebase / Firestore
# -----------------------------------------------------------
if not firebase_admin._apps:
    firebase_admin.initialize_app(
        options={"projectId": os.getenv("GOOGLE_CLOUD_PROJECT")}
    )

FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "projects")
db = firestore.Client()

# -----------------------------------------------------------
# Auth toggle (dev-friendly): set ENFORCE_AUTH=true in prod
# -----------------------------------------------------------
ENFORCE_AUTH = (os.getenv("ENFORCE_AUTH", "false").lower() == "true")
DEV_UID = os.getenv("DEV_UID", "dev-user")

_UNPROTECTED_PATHS = {"/", "/health", "/api/health", "/openapi.json", "/docs", "/docs/oauth2-redirect"}

def _require_or_fake_uid(authorization_header: Optional[str]) -> str:
    """
    - If ENFORCE_AUTH=false (default), return a stable fake UID so Firestore works.
    - If true, verify Firebase ID token from Authorization: Bearer <token>.
    """
    if not ENFORCE_AUTH:
        return DEV_UID

    if not authorization_header or not authorization_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization_header.split(" ", 1)[1].strip()
    try:
        decoded = fb_auth.verify_id_token(token)
        return decoded["uid"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_uid(
    request: Request,
    authorization: str = Header(None, convert_underscores=False)
) -> str:
    # Always allow unprotected paths (docs/health)
    if request.url.path in _UNPROTECTED_PATHS:
        return DEV_UID if not ENFORCE_AUTH else "anonymous"
    return _require_or_fake_uid(authorization)

# -----------------------------------------------------------
# OpenAI helpers
# -----------------------------------------------------------
def make_openai_client() -> Optional[OpenAI]:
    """
    Construct an OpenAI client with timeouts/retries.
    Supports OPENAI_BASE_URL for compatible providers.
    """
    if not _OPENAI_READY:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL") or None
    try:
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0,
            max_retries=2,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI client init failed: {type(e).__name__}: {e}")

ENGINE_MAP = {
    "gpt-5-mini":   os.getenv("MANTHAN_GPT5_MINI",  "gpt-4o-mini"),
    "gpt-5":        os.getenv("MANTHAN_GPT5",       "gpt-4.1"),
    "manthan-lora": os.getenv("MANTHAN_LORA_MODEL","gpt-4o-mini"),
}

def _model_for_engine(engine: str) -> str:
    return ENGINE_MAP.get(engine, ENGINE_MAP["gpt-5-mini"])

def _call_llm(engine: str, system: str, user: str, n: int = 3) -> List[str]:
    """
    Generate n candidates using chat completions (looping for provider compatibility).
    """
    client = make_openai_client()
    if not client:
        raise HTTPException(status_code=500, detail="LLM not configured (OPENAI_API_KEY missing or OpenAI SDK unavailable)")

    model = _model_for_engine(engine)
    texts: List[str] = []
    last_err: Optional[str] = None

    for _ in range(n):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.8,
            )
            content = (resp.choices[0].message.content or "").strip()
            texts.append(content if content else "(empty)")
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"

    if not texts or any(t == "(empty)" for t in texts):
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {last_err or 'empty output'}")

    return texts

# -----------------------------------------------------------
# Models
# -----------------------------------------------------------
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

StageName = Literal["outline", "onepager", "screenplay", "script", "dialogue"]

class StageGenerateRequest(BaseModel):
    project_id: str
    stage: StageName
    tweak: Optional[str] = ""
    engine: Optional[str] = "gpt-5-mini"
    language: Optional[str] = "en"

class Candidate(BaseModel):
    id: str
    text: str
    meta: Optional[Dict[str, Any]] = None

class StageGenerateResponse(BaseModel):
    candidates: List[Candidate]

class StageChooseRequest(BaseModel):
    project_id: str
    stage: StageName
    chosen_id: str
    edits: Optional[str] = ""

# -----------------------------------------------------------
# Helper functions
# -----------------------------------------------------------
def _doc_to_project(doc) -> Project:
    data = doc.to_dict()
    return Project(id=doc.id, **data)

def _get_project_for_owner(project_id: str, uid: str) -> Project:
    doc = db.collection(FIRESTORE_COLLECTION).document(project_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")
    p = _doc_to_project(doc)
    if p.owner_uid and p.owner_uid != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    return p

def _stage_ref(project_id: str, stage: str):
    return (
        db.collection(FIRESTORE_COLLECTION)
        .document(project_id)
        .collection("stages")
        .document(stage)
    )

def _system_prompt(stage: StageName, language: str) -> str:
    base = (
        "You are Manthan, a professional film/series development assistant. "
        "Be concrete, cinematic, market-aware. Avoid placeholders. "
        "Reflect the premise throughout."
    )
    if language and language != "en":
        base += f" Respond in language code: {language}."
    stage_note = {
        "outline":   "Produce a tight outline with acts and clear turning points.",
        "onepager":  "Write a compelling one-page synopsis for pitching.",
        "screenplay":"Write crisp scene beats (bulleted, visual).",
        "script":    "Write properly formatted script pages for a selected segment.",
        "dialogue":  "Write dialogue passes with distinct voice and cultural texture.",
    }[stage]
    return base + " " + stage_note

def _user_prompt(stage: StageName, p: Project, tweak: str) -> str:
    lines = [
        f"TITLE: {p.title}",
        f"LOGLINE: {p.logline}",
        f"GENRE: {p.genre or 'Drama'}",
        f"TONE: {p.tone or 'Grounded, character-driven'}",
        "INSTRUCTIONS:",
        "- Use culturally specific details; avoid generic phrasing.",
        "- Keep it production-ready.",
    ]
    if tweak:
        lines.append(f"STEERING_NOTE: {tweak}")
    extras = {
        "outline":   "- 10–12 labeled beats across acts; 1–2 lines each.",
        "onepager":  "- 4–6 paragraphs; strong arc and hook; no headings.",
        "screenplay":"- 10–14 beats; each is a visual moment, not prose.",
        "script":    "- 1–2 pages of formatted script (INT/EXT, action, dialogue).",
        "dialogue":  "- 2–3 pages equivalent; crisp, characterful exchanges.",
    }
    lines.append(extras[stage])
    return "\n".join(lines)

# -----------------------------------------------------------
# Routes
# -----------------------------------------------------------
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
    title = payload.title.strip()
    logline = payload.logline.strip()
    genre = (payload.genre or "Drama").strip()
    tone  = (payload.tone  or "Grounded, character-driven").strip()

    synopsis = (
        f"**{title}** is a {genre.lower()} told with a {tone.lower()} tone. "
        f"It centers on the premise: {logline} "
        "Act I introduces a quiet crisis; Act II forces a bold decision; "
        "Act III lands a surprising yet inevitable resolution."
    )
    beat_sheet = [
        "Opening Image — everyday contradiction of the protagonist",
        "Theme Stated — a line that foreshadows the inner journey",
        "Catalyst — the event that upends the status quo",
        "Debate — resist or leap?",
        "Break into Two — commitment to a new path",
        "Midpoint — stakes and truth sharpen",
        "Bad Guys Close In — pressure mounts",
        "All Is Lost — face the core fear",
        "Break into Three — integrate lesson + new plan",
        "Finale — decisive action and transformation",
        "Final Image — mirror of the opening, now evolved",
    ]
    deck_outline = [
        "Cover: Title, logline, key art placeholder",
        "Overview: Why now? Audience? Tone & genre anchors",
        "World & Characters: 3–5 leads with concise arcs",
        "Story: 1-page synopsis + 10-beat board",
        "Lookbook: Visual references (mood, palette, comps)",
        "Market: Comps, potential buyers, format & runtime",
        "Team: Creator bio, key attachments",
        "Next Steps: Budget, partners, timeline",
    ]
    return PitchPack(
        title=title, logline=logline,
        synopsis=synopsis, beat_sheet=beat_sheet, deck_outline=deck_outline
    )

@app.post("/api/stage/generate", response_model=StageGenerateResponse)
def stage_generate(body: StageGenerateRequest, uid: str = Depends(get_uid)):
    p = _get_project_for_owner(body.project_id, uid)

    sys_prompt = _system_prompt(body.stage, body.language or "en")
    usr_prompt = _user_prompt(body.stage, p, body.tweak or "")

    if body.engine == "manthan-lora":
        usr_prompt += (
            "\nFEW-SHOT STYLE SIGNALS:\n"
            "- Lean into Indian subcontinent texture and vernacular.\n"
            "- Keep choices under pressure; avoid generic phrasing.\n"
        )

    outs = _call_llm(body.engine, sys_prompt, usr_prompt, n=3)
    cands = [Candidate(id=str(uuid.uuid4()), text=t, meta={"engine": body.engine}) for t in outs]

    _stage_ref(body.project_id, body.stage).set(
        {
            "last_generated": [c.dict() for c in cands],
            "engine": body.engine,
            "language": body.language or "en",
            "tweak": body.tweak or "",
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return StageGenerateResponse(candidates=cands)

@app.post("/api/stage/choose")
def stage_choose(body: StageChooseRequest, uid: str = Depends(get_uid)):
    _ = _get_project_for_owner(body.project_id, uid)
    snap = _stage_ref(body.project_id, body.stage).get()
    if not snap.exists:
        raise HTTPException(status_code=400, detail="Nothing generated for this stage yet")

    data = snap.to_dict() or {}
    cands = data.get("last_generated", [])
    chosen = next((c for c in cands if c.get("id") == body.chosen_id), None)
    if not chosen:
        raise HTTPException(status_code=404, detail="Chosen candidate not found")

    chosen_text = body.edits.strip() if body.edits else (chosen.get("text") or "")

    _stage_ref(body.project_id, body.stage).set(
        {
            "chosen": {
                "id": body.chosen_id,
                "text": chosen_text,
                "meta": chosen.get("meta", {}),
            },
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
        merge=True,
    )
    return {"ok": True, "stage": body.stage, "chosen_id": body.chosen_id}

# -----------------------------------------------------------
# Debug
# -----------------------------------------------------------
@app.get("/api/debug/whoami")
def debug_whoami(uid: str = Depends(get_uid)):
    return {
        "uid": uid,
        "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "allowed_origins": ALLOWED_ORIGINS,
        "engine_map": ENGINE_MAP,
        "has_key": bool(os.getenv("OPENAI_API_KEY")),
        "base_url": os.getenv("OPENAI_BASE_URL") or None,
        "enforce_auth": ENFORCE_AUTH,
    }

@app.get("/api/debug/openai-ping")
def debug_openai_ping(uid: str = Depends(get_uid)):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="No OPENAI_API_KEY env")
    try:
        r = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=20.0,
        )
        return {"status": r.status_code, "ok": r.is_success, "body_snippet": r.text[:200]}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Outbound probe failed: {type(e).__name__}: {e}")


