from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import os, uuid, time

# Firebase + Firestore
from google.cloud import firestore
import firebase_admin
from firebase_admin import auth as fb_auth

# OpenAI (or compatible) for LLM generation
_OPENAI_READY = False
try:
    from openai import OpenAI
    _OPENAI_READY = True
except Exception:
    _OPENAI_READY = False


app = FastAPI(title="Manthan Creator Suite API", version="0.3.0")

# ---------------- CORS ----------------
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ---------------- Firestore ----------------
FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "projects")
db = firestore.Client()

# ---------------- Firebase Admin ----------------
if not firebase_admin._apps:
    firebase_admin.initialize_app(
        options={"projectId": os.environ.get("GOOGLE_CLOUD_PROJECT")}
    )

# ---------------- OpenAI Client ----------------
def make_openai_client() -> Optional[OpenAI]:
    """
    Creates an OpenAI client. Supports custom base URLs for compatible providers.
    """
    if not _OPENAI_READY:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL")  # optional (e.g. Azure/Fireworks compatible)
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)

# Engines your UI sends; map to actual deployable models if needed
ENGINE_MAP = {
    "gpt-5-mini": os.getenv("MANTHAN_GPT5_MINI", "gpt-4o-mini"),  # fallback that exists
    "gpt-5":      os.getenv("MANTHAN_GPT5", "gpt-4.1"),
    # "LoRA" lane: if you have a hosted finetuned / lora model, put its id in env
    "manthan-lora": os.getenv("MANTHAN_LORA_MODEL", "gpt-4o-mini"),  # fallback
}

# ---------------- Models ----------------
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

# Stage flow
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

# ---------------- Helpers ----------------
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
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def _get_project_for_owner(project_id: str, uid: str) -> Project:
    doc = db.collection(FIRESTORE_COLLECTION).document(project_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")
    p = _doc_to_project(doc)
    if p.owner_uid and p.owner_uid != uid:
        raise HTTPException(status_code=403, detail="Forbidden")
    return p

def _stage_ref(project_id: str, stage: str):
    return db.collection(FIRESTORE_COLLECTION).document(project_id).collection("stages").document(stage)

# -------- Prompt templates (short, stage-specific) --------
def _system_prompt(stage: StageName, language: str) -> str:
    base = (
        "You are Manthan, a professional film/series development assistant. "
        "Write in the requested language. Be specific, cinematic, and market-aware. "
        "Avoid placeholders. Use concrete details and character-driven logic."
    )
    if language != "en":
        base += f" Respond in language code: {language}."
    stage_note = {
        "outline":   "Produce a tight outline with acts and clear turning points.",
        "onepager":  "Produce a compelling 1-page synopsis suitable for a pitch.",
        "screenplay":"Produce scene beats (bulleted). Each beat is a crisp, visual moment.",
        "script":    "Produce formatted script pages (concise) for a selected segment.",
        "dialogue":  "Produce dialogue passes with distinct voice and cultural texture.",
    }[stage]
    return base + " " + stage_note

def _user_prompt(stage: StageName, p: Project, tweak: str) -> str:
    # EVERYTHING real flows from title/logline/genre/tone; no placeholders allowed
    lines = [
        f"TITLE: {p.title}",
        f"LOGLINE: {p.logline}",
        f"GENRE: {p.genre or 'Drama'}",
        f"TONE: {p.tone or 'Grounded, character-driven'}",
        "INSTRUCTIONS:",
        "- Reflect the logline in every beat/paragraph.",
        "- Use culturally specific detail (names, settings, objects) appropriate to the premise.",
        "- Keep it production-ready, no vagueness.",
    ]
    if tweak:
        lines.append(f"STEERING_NOTE: {tweak}")
    # Stage-specific extra constraints
    extras = {
        "outline":  "- 10-12 bullets, clearly labeled act/beat, each 1-2 lines.",
        "onepager": "- 4-6 paragraphs max. No subheads. Strong arc + hook.",
        "screenplay": "- 10-14 beats for a pilot/feature section. Pure beats, not prose.",
        "script":   "- 1-2 pages of properly formatted script text (INT./EXT., action, dialogue).",
        "dialogue": "- 2-3 pages equivalent of dialogue-centered exchanges; crisp, characterful.",
    }
    lines.append(extras[stage])
    return "\n".join(lines)

def _model_for_engine(engine: str) -> str:
    # Map UI engine to deployable model
    return ENGINE_MAP.get(engine, ENGINE_MAP["gpt-5-mini"])

def _call_llm(engine: str, system: str, user: str, n: int = 3) -> List[str]:
    """
    Calls the model and returns n candidate texts. Falls back if a model string is invalid.
    """
    client = make_openai_client()
    if not client:
        # If no key/client, fail loudly so you don't see placeholders
        raise HTTPException(status_code=500, detail="LLM not configured (OPENAI_API_KEY missing or OpenAI SDK unavailable)")

    model = _model_for_engine(engine)

    # Try to generate n candidates in separate calls (simple & robust)
    texts: List[str] = []
    last_err: Optional[str] = None
    for _ in range(n):
        try:
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            # Standardize: first text output chunk
            out = ""
            for item in resp.output:
                if item.type == "message":
                    for cc in item.message.content:
                        if cc.type == "output_text":
                            out += cc.text
            texts.append(out.strip() or "(empty)")
        except Exception as e:
            last_err = str(e)

    if not texts or any(t == "(empty)" for t in texts):
        # If responses failed or were empty, surface the sdk error if any
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {last_err or 'empty output'}")

    return texts

# ---------------- Routes ----------------
@app.get("/api/health")
def health():
    return {"ok": True, "ts": int(time.time())}

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

# ---- Existing simple pitch endpoint (kept) ----
@app.post("/api/pitch/generate", response_model=PitchPack)
def generate_pitch(payload: PitchRequest, uid: str = Depends(get_uid)):
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
        "Final Image — mirror of the opening, now evolved",
    ]

    deck_outline = [
        "Cover: Title, logline, key art placeholder",
        "Overview: Why now? Audience? Tone & genre anchors",
        "World & Characters: 3-5 leads with concise arcs",
        "Story: 1-page synopsis + 10-beat board",
        "Lookbook: Visual references (mood, palette, comps)",
        "Market: Comps, potential buyers, format & runtime",
        "Team: Creator bio, past credits, attachments (if any)",
        "Next Steps: What we need (budget, partners, timeline)",
    ]

    return PitchPack(
        title=title,
        logline=logline,
        synopsis=synopsis,
        beat_sheet=beat_sheet,
        deck_outline=deck_outline,
    )

# ---- New: Stage generation (3 candidates) ----
@app.post("/api/stage/generate", response_model=StageGenerateResponse)
def stage_generate(body: StageGenerateRequest, uid: str = Depends(get_uid)):
    p = _get_project_for_owner(body.project_id, uid)

    sys_prompt = _system_prompt(body.stage, body.language or "en")
    usr_prompt = _user_prompt(body.stage, p, body.tweak or "")

    # For "manthan-lora" you can inject style primers / fewshots here
    if body.engine == "manthan-lora":
        usr_prompt += (
            "\nFEW-SHOT STYLE SIGNALS:\n"
            "- Lean into Indian subcontinent texture, modern vernacular.\n"
            "- Show character choice under pressure; avoid generic phrasing.\n"
        )

    outs = _call_llm(body.engine, sys_prompt, usr_prompt, n=3)

    cands = [
        Candidate(id=str(uuid.uuid4()), text=t, meta={"engine": body.engine})
        for t in outs
    ]

    # Persist last generation for the stage
    _stage_ref(body.project_id, body.stage).set({
        "last_generated": [c.dict() for c in cands],
        "engine": body.engine,
        "language": body.language or "en",
        "updated_at": firestore.SERVER_TIMESTAMP,
        "tweak": body.tweak or "",
    }, merge=True)

    return StageGenerateResponse(candidates=cands)

# ---- New: Stage choose (store selected, optional edits) ----
@app.post("/api/stage/choose")
def stage_choose(body: StageChooseRequest, uid: str = Depends(get_uid)):
    _ = _get_project_for_owner(body.project_id, uid)
    sref = _stage_ref(body.project_id, body.stage).get()
    if not sref.exists:
        raise HTTPException(status_code=400, detail="Nothing generated for this stage yet")

    data = sref.to_dict() or {}
    cands = data.get("last_generated", [])
    chosen = next((c for c in cands if c.get("id") == body.chosen_id), None)
    if not chosen:
        raise HTTPException(status_code=404, detail="Chosen candidate not found")

    chosen_text = chosen.get("text", "")
    if body.edits:
        chosen_text = body.edits.strip()

    _stage_ref(body.project_id, body.stage).set({
        "chosen": {
            "id": body.chosen_id,
            "text": chosen_text,
            "meta": chosen.get("meta", {}),
        },
        "updated_at": firestore.SERVER_TIMESTAMP,
    }, merge=True)

    return {"ok": True, "stage": body.stage, "chosen_id": body.chosen_id}
