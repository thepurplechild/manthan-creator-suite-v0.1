from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os, time

# Optional: OpenAI for model-powered generation
USE_MODEL = os.getenv("USE_MODEL", "0") in ("1","true","True","yes","YES")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5")  # swap if needed

# Optional: Firestore autosave
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
AUTOSAVE = os.getenv("AUTOSAVE", "1") in ("1","true","True","yes","YES")

app = FastAPI(title="Manthan Creator Suite Backend")

# CORS policy
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")
origins = ["*"] if not FRONTEND_ORIGIN else [FRONTEND_ORIGIN]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Models ----------
class IdeaInput(BaseModel):
    title: str
    logline: str
    genre: Optional[str] = None
    tone: Optional[str] = None

class PitchPack(BaseModel):
    outline: List[str]
    one_pager: str
    deck_outline: List[str]
    quality: Dict[str, Any]
    doc_id: Optional[str] = None

# ---------- Helpers ----------
def local_outline(logline: str) -> List[str]:
    return [
        f"Act 1 — Inciting incident tied to: {logline}",
        "Act 2 — Reversals & midpoint dilemma",
        "Act 3 — Climax & resolution with emotional payoff",
    ]

def local_one_pager(title: str, logline: str) -> str:
    return (
        f"Title: {title}\n\nLogline: {logline}\n\n"
        "Summary: In a world that mirrors contemporary India, our protagonist faces a choice "
        "between duty and desire, escalating through culturally grounded stakes."
    )

def local_deck() -> List[str]:
    return ["Cover", "Logline", "Synopsis", "Characters", "World", "Season Arc", "Why now?"]

def quality_gate(idea: IdeaInput, outline: List[str], one_pager: str) -> Dict[str, Any]:
    score = 0
    reasons = []
    if idea.title and len(idea.title) >= 3:
        score += 20
    else:
        reasons.append("Title too short")
    if idea.logline and len(idea.logline.split()) >= 10:
        score += 25
    else:
        reasons.append("Logline needs more detail (>=10 words)")
    if idea.genre:
        score += 15
    else:
        reasons.append("No genre provided")
    if idea.tone:
        score += 10
    else:
        reasons.append("No tone provided")
    if len(outline) >= 3:
        score += 15
    else:
        reasons.append("Outline should have at least 3 beats")
    if len(one_pager.split()) >= 60:
        score += 15
    else:
        reasons.append("One-pager is very short")

    label = "Strong" if score >= 80 else ("Decent" if score >= 60 else "Needs work")
    return {"score": score, "label": label, "reasons": reasons}

def try_model_generate(idea: IdeaInput):
    # Fallback to local generation if no key or disabled
    if not (USE_MODEL and OPENAI_API_KEY):
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        sys_prompt = (
            "You are an assistant that turns an idea into:
"
            "1) a 3-beat outline (array of 3-6 short bullets),
"
            "2) a concise one-pager (120-200 words),
"
            "3) a deck outline (array of 6-10 section titles).
"
            "Reply strictly as JSON with keys: outline, one_pager, deck_outline."
        )
        user_payload = {
            "title": idea.title,
            "logline": idea.logline,
            "genre": idea.genre,
            "tone": idea.tone
        }

        chat = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": str(user_payload)},
            ],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        content = chat.choices[0].message.content
        import json as _json
        data = _json.loads(content)
        # sanity
        outline = data.get("outline") or []
        one_pager = data.get("one_pager") or ""
        deck = data.get("deck_outline") or []
        # normalize types
        outline = [str(x) for x in outline][:8]
        deck = [str(x) for x in deck][:12]
        return outline, one_pager, deck
    except Exception as e:
        # Silent fallback
        return None

def autosave_pitchpack(project_id: Optional[str], payload: Dict[str, Any]) -> Optional[str]:
    if not AUTOSAVE:
        return None
    try:
        from google.cloud import firestore
        db = firestore.Client(project=PROJECT_ID or None)
        col = db.collection("pitch_packs")
        doc_ref = col.document() if not project_id else col.document(project_id)
        payload["updated_at"] = int(time.time())
        if not project_id:
            payload["created_at"] = payload["updated_at"]
        doc_ref.set(payload, merge=True)
        return doc_ref.id
    except Exception as e:
        # Don't block on autosave errors
        return None

# ---------- Routes ----------
@app.post("/api/pitch/generate", response_model=PitchPack)
def generate_pitch(inp: IdeaInput):
    gen = try_model_generate(inp)
    if gen is None:
        outline = local_outline(inp.logline)
        one_pager = local_one_pager(inp.title, inp.logline)
        deck = local_deck()
    else:
        outline, one_pager, deck = gen

    q = quality_gate(inp, outline, one_pager)

    # Autosave
    doc_id = autosave_pitchpack(
        None,
        {
            "idea": inp.model_dump(),
            "outline": outline,
            "one_pager": one_pager,
            "deck_outline": deck,
            "quality": q,
        },
    )

    return PitchPack(outline=outline, one_pager=one_pager, deck_outline=deck, quality=q, doc_id=doc_id)

@app.get("/health/config")
def config_health():
    return {
        "ok": True,
        "frontend_origin": FRONTEND_ORIGIN or "*",
        "use_model": USE_MODEL,
        "autosave": AUTOSAVE,
    }
