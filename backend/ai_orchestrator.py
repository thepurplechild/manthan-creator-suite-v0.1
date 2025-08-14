# backend/ai_orchestrator.py
import os, uuid
from typing import List, Dict, Any
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_BASE = """You are Manthan's writer-room engine for Indian cinema.
Write culturally specific, buyer-ready material in the user's language.
Always return concise, distinct options (3), each with a short label.
"""

PROMPTS = {
    "outline": """Title: {title}
Logline: {logline}
Genre: {genre}, Language: {language}
{tweak}
Task: Produce three different high-level story outlines (Act I-III with 6–10 beats total).
Each option must feel culturally authentic for {language}. Avoid generic phrasing.""",
    "onepager": """Using this approved outline:
{approved_text}
Task: Write three distinct one-page treatments (≤ 400 words). Keep tone {genre}. {tweak}""",
    "screenplay": """From this one-pager:
{approved_text}
Task: Generate three alternative scene-beat breakdowns for a pilot or feature (12–18 beats). {tweak}""",
    "script": """From these beats:
{approved_text}
Task: Produce three script pages for the opening, in industry format (INT./EXT., character cues). {tweak}""",
    "dialogue": """From this script segment:
{approved_text}
Task: Offer three dialogue passes: (A) grounded, (B) heightened/comic, (C) regional colloquialisms. Keep language {language}. {tweak}"""
}

def _parse_three(text: str) -> List[Dict[str, Any]]:
    # naive splitter; can be improved with JSON mode if available
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    out = []
    for i, p in enumerate(parts[:3], 1):
        out.append({"id": f"opt{i}-{uuid.uuid4().hex[:6]}", "text": p, "meta": {}})
    return out

def generate_candidates(stage: str, project: dict, tweak: str|None, engine: str) -> List[Dict[str,Any]]:
    prompt = PROMPTS[stage].format(
        title=project["title"],
        logline=project["logline"],
        genre=project.get("genre",""),
        language=project.get("language","en"),
        approved_text=project.get(f"{stage}_approved",""),
        tweak=(f"User tweak: {tweak}" if tweak else "")
    )

    # Route to GPT-5 / GPT-5-mini for now (LoRA section below will add adapters)
    model = "gpt-5" if engine == "gpt-5" else "gpt-5-mini"

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":SYSTEM_BASE},
                  {"role":"user","content":prompt}],
        temperature=0.9, n=1
    )
    return _parse_three(resp.choices[0].message.content or "")
