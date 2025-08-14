# backend/app_stages.py
from typing import List, Optional, Literal, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import get_uid, get_db  # absolute import

router = APIRouter(prefix="/api/stage", tags=["stages"])

Stage = Literal["outline", "onepager", "screenplay", "script", "dialogue"]

class Candidate(BaseModel):
    id: str
    text: str
    meta: Dict[str, Any] = {}

class StageGenIn(BaseModel):
    project_id: str
    stage: Stage
    tweak: Optional[str] = None
    engine: Optional[str] = None  # "gpt-5" | "gpt-5-mini" | "manthan-lora"

class StageGenOut(BaseModel):
    candidates: List[Candidate]

@router.post("/generate", response_model=StageGenOut)
def generate_stage(payload: StageGenIn, uid: str = Depends(get_uid)):
    db = get_db()
    doc = db.collection("projects").document(payload.project_id).get()
    if not doc.exists or doc.to_dict().get("owner_uid") != uid:
        raise HTTPException(404, "Project not found")

    # ---- STUB OUTPUT (3 options). Replace with ai_orchestrator later.
    base = f"[{payload.stage.upper()}] engine={payload.engine or 'gpt-5-mini'}"
    steer = f" | tweak: {payload.tweak}" if payload.tweak else ""
    cands = [
        Candidate(id="c1", text=f"{base} — Option A{steer}"),
        Candidate(id="c2", text=f"{base} — Option B{steer}"),
        Candidate(id="c3", text=f"{base} — Option C{steer}"),
    ]
    return {"candidates": cands}

class ChooseIn(BaseModel):
    project_id: str
    stage: Stage
    chosen_id: str
    edits: Optional[str] = None

@router.post("/choose")
def choose_stage(payload: ChooseIn, uid: str = Depends(get_uid)):
    db = get_db()
    doc_ref = db.collection("projects").document(payload.project_id)
    snap = doc_ref.get()
    if not snap.exists or snap.to_dict().get("owner_uid") != uid:
        raise HTTPException(404, "Project not found")

    # Advance stage (simple linear flow)
    next_stage_map = {
        "outline": "onepager",
        "onepager": "screenplay",
        "screenplay": "script",
        "script": "dialogue",
        "dialogue": "final",
    }
    if payload.stage in next_stage_map:
        doc_ref.update({"stage": next_stage_map[payload.stage]})
    # You can store revision documents here as well

    return {"ok": True, "next": next_stage_map.get(payload.stage, "final")}

