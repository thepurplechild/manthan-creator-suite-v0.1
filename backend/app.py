# backend/app.py
from __future__ import annotations

import os, uuid, time, json
from typing import List, Optional, Literal, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Firestore + Firebase
from google.cloud import firestore
import firebase_admin
from firebase_admin import auth as fb_auth

# HTTP for simple outbound checks
import httpx

# ---------------------- LLM client (OpenAI-compatible) ----------------------
_OPENAI_READY = False
try:
    from openai import OpenAI
    _OPENAI_READY = True
except Exception:
    _OPENAI_READY = False

def make_openai_client() -> Optional[OpenAI]:
    """
    Build an OpenAI client. Supports OPENAI_BASE_URL for compatible providers.
    Returns None if not configured so we can gracefully fall back.
    """
    if not _OPENAI_READY:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL") or None
    return OpenAI(api_key=api_key, base_url=base_url, timeout=60.0, max_retries=2)

ENGINE_MAP = {
    "gpt-5-mini":  os.getenv("MANTHAN_GPT5_MINI",  "gpt-4o-mini"),
    "gpt-5":       os.getenv("MANTHAN_GPT5",       "gpt-4.1"),
    "manthan-lora":os.getenv("MANTHAN_LORA_MODEL","gpt-4o-mini"),
}
def _model_for_engine(engine: str) -> str:
    return ENGINE_MAP.get(engine, ENGINE_MAP["gpt-5-mini"])

# ---------------------------- FastAPI app -----------------------------------
app = FastAPI(title="Manthan Creator Suite API", version="0.5.0")

# CORS — allow your frontend and local docs
ALLOWED_ORIGINS = [
    "https://manthan-frontend-524579286496.asia-south1.run.app",
    os.getenv("ALLOWED_ORIGIN") or "",
    # Swagger UI is served from the same backend origin, so leave that alone.
]
ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ---------------------- Firebase/Firestore ----------------------------------
if not firebase_admin._apps:
    firebase_admin.initialize_app(
        options={"projectId": os.getenv("GOOGLE_CLOUD_PROJECT")}
    )

FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "projects")
db = firestore.Client()

# ------------------------------ Models --------------------------------------
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
    # Optional overrides
    engine: Optional[str] = "gpt-5-mini"
    language: Optional[str] = "en"

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

# -------------------------- Auth / helpers ----------------------------------
def _doc_to_project(doc) -> Project:
    data = doc.to_dict()
    return Project(id=doc.id, **data)

def get_uid(authorization: str = Header(None)) -> str:
    # Expect "Authorization: Bearer <FirebaseIDToken>"
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
    return (
        db.collection(FIRESTORE_COLLECTION)
        .document(project_id)
        .collection("stages")
        .document(stage)
    )

# ------------------------- Health / debug -----------------------------------
@app.get("/health")
def plain_health():
    return {"status": "ok"}

@app.get("/api/health")
def api_health():
    return {"ok": True, "ts": int(time.time())}

@app.get("/api/debug/whoami")
def debug_whoami(uid: str = Depends(get_uid)):
    return {
        "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "allowed_origins": ALLOWED_ORIGINS,
        "engine_map": ENGINE_MAP,
        "has_key": bool(os.getenv("OPENAI_API_KEY")),
        "base_url": os.getenv("OPENAI_BASE_URL") or None,
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

# ---------------------------- LLM prompts -----------------------------------
def _pitch_system(language: str) -> str:
    base = (
        "You are Manthan, a professional Indian film/series development exec. "
        "Write culturally specific, cinematic, and market-aware material. "
        "Avoid placeholders and generic beats. Respect the given genre and tone. "
        "Prefer Indian settings, names, and vernacular when unspecified."
    )
    if language and language != "en":
        base += f" Respond using language code: {language}."
    return base

_PITCH_JSON_INSTRUCTIONS = (
    "Return STRICT JSON with keys: title, logline, synopsis, beat_sheet (array of 10-12 items), "
    "deck_outline (array of 7-9 items). Do not include markdown or extra text."
)

def _pitch_user_prompt(title: str, logline: str, genre: str, tone: str) -> str:
    return (
        f"TITLE: {title}\n"
        f"LOGLINE: {logline}\n"
        f"GENRE: {genre}\n"
        f"TONE: {tone}\n"
        "TASK: Create a pitch pack that would excite Indian OTT buyers. "
        "Keep the synopsis 180–260 words, with a clear arc and hook. "
        "Beat sheet should be specific, visual, and motivated by character choices. "
        "Deck outline should be practical for a sales deck in India (audience, comps, lookbook, etc.).\n"
        f"{_PITCH_JSON_INSTRUCTIONS}"
    )

def _call_llm_json(engine: str, system: str, user: str) -> Dict[str, Any]:
    """
    Calls chat.completions and parses STRICT JSON. If parsing fails, raises HTTPException.
    """
    client = make_openai_client()
    if not client:
        raise HTTPException(status_code=500, detail="LLM not configured (OPENAI_API_KEY missing or SDK unavailable)")

    model = _model_for_engine(engine)

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
        # Attempt to extract JSON
        # Some models may wrap in code fences; strip them
        if content.startswith("```"):
            content = content.strip("`")
            # remove leading 'json' if present
            if content.startswith("json"):
                content = content[4:].strip()
        data = json.loads(content)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {type(e).__name__}: {e}")

# ------------------------------ Routes --------------------------------------
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

# ----------- PITCH: now uses LLM with India-aware prompt & JSON output -------
@app.post("/api/pitch/generate", response_model=PitchPack)
def generate_pitch(payload: PitchRequest, uid: str = Depends(get_uid)):
    title = payload.title.strip()
    logline = payload.logline.strip()
    genre = (payload.genre or "Drama").strip()
    tone  = (payload.tone  or "Grounded, character-driven").strip()
    engine = payload.engine or "gpt-5-mini"
    language = payload.language or "en"

    client = make_openai_client()

    if client:
        # LLM path
        system = _pitch_system(language)
        user = _pitch_user_prompt(title, logline, genre, tone)

        # Add a bit of extra style guidance for your custom lane
        if engine == "manthan-lora":
            user += (
                "\nSTYLE NOTES: Lean into Indic texture (names, food, festivals, class dynamics). "
                "Use concrete Mumbai/Chennai/Hyderabad locales if unspecified. Avoid clichés."
            )

        data = _call_llm_json(engine, system, user)

        # Validate minimally so FastAPI returns a clean 422 if malformed
        try:
            return PitchPack(**{
                "title": data.get("title", title),
                "logline": data.get("logline", logline),
                "synopsis": data["synopsis"],
                "beat_sheet": data["beat_sheet"],
                "deck_outline": data["deck_outline"],
            })
        except Exception as e:
            # If the model returned junk, fall back to a deterministic template
            pass

    # Fallback (no key or invalid JSON from model) — still specific to inputs
    synopsis = (
        f"**{title}** is a {genre.lower()} set against an Indian backdrop, told with a {tone.lower()} tone. "
        f"It centers on: {logline}. We enter through a vivid everyday image, pivot into a catalytic choice, "
        "and end with a payoff that feels surprising yet earned for the audience you’d find on today’s OTTs."
    )
    beat_sheet = [
        "Opening Image — a concrete slice of life that hints at the core contradiction",
        "Theme Stated — a line or beat that foreshadows the inner journey",
        "Catalyst — an external jolt that forces a decision",
        "Debate — resist or leap; cost becomes clear",
        "Break into Two — choice made; world tilts",
        "First Sequence Wins/Losses — initial plan meets reality",
        "Midpoint — truth revealed; stakes escalate",
        "Bad Guys Close In — pressure from all sides",
        "All Is Lost — protagonist faces core fear",
        "Break into Three — synthesis and new plan",
        "Finale — decisive action with character change visible",
        "Final Image — mirrors the opening, now transformed",
    ]
    deck_outline = [
        "Cover: Title, logline, key art",
        "Why Now / Audience: who it’s for, platform fit",
        "World & Characters: 3–5 leads with arcs",
        "Story: 1‑page synopsis + 10–12 beats",
        "Lookbook: tone, palette, visual comps (India‑specific)",
        "Market & Comps: recent Indian shows/films it sits beside",
        "Team & Attachments",
        "Production Notes: format, runtime, language(s)",
        "Next Steps: outreach plan, budget roughs",
    ]
    return PitchPack(
        title=title, logline=logline,
        synopsis=synopsis, beat_sheet=beat_sheet, deck_outline=deck_outline
    )

# -------- Stage generate (kept; unchanged except minor polish) ---------------
def _stage_system_prompt(stage: StageName, language: str) -> str:
    base = (
        "You are Manthan, a professional film/series development assistant. "
        "Be concrete, cinematic, and market-aware. Avoid placeholders."
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

def _stage_user_prompt(stage: StageName, p: Project, tweak: str) -> str:
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

@app.post("/api/stage/generate", response_model=StageGenerateResponse)
def stage_generate(body: StageGenerateRequest, uid: str = Depends(get_uid)):
    p = _get_project_for_owner(body.project_id, uid)

    sys_prompt = _stage_system_prompt(body.stage, body.language or "en")
    usr_prompt = _stage_user_prompt(body.stage, p, body.tweak or "")

    if body.engine == "manthan-lora":
        usr_prompt += (
            "\nFEW-SHOT STYLE SIGNALS:\n"
            "- Lean into Indian subcontinent texture and vernacular.\n"
            "- Keep choices under pressure; avoid generic phrasing.\n"
        )

    client = make_openai_client()
    texts: List[str] = []
    last_err = None

    if client:
        model = _model_for_engine(body.engine or "gpt-5-mini")
        for _ in range(3):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": usr_prompt},
                    ],
                    temperature=0.85,
                )
                content = (resp.choices[0].message.content or "").strip()
                texts.append(content if content else "(empty)")
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"

    if not texts:
        # Deterministic backup if LLM not configured
        texts = [f"[DEMO] {body.stage} draft for '{p.title}' — refine once LLM key is set."]

    cands = [Candidate(id=str(uuid.uuid4()), text=t, meta={"engine": body.engine}) for t in texts]

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

    # If all were empty or errors
    if any(c.text == "(empty)" for c in cands):
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {last_err or 'empty output'}")

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



