# Manthan Creator Suite — v0.2.1 (Agents Upgrade)

This drop upgrades v0.2 with:
- **Model-powered generation** (optional): set `USE_MODEL=1` and `OPENAI_API_KEY` to switch from scaffold to GPT.
- **Autosave agent (Firestore)**: saves each generated pack under `pitch_packs/{docId}` with idea, outputs, and quality.
- **Quality Gate**: lightweight scoring with label **Strong/Decent/Needs work** + suggestions.

## Deploy vars (Cloud Run → manthan-backend → Variables)
- `FRONTEND_ORIGIN = https://<your-frontend>.a.run.app` (recommended)
- `USE_MODEL = 1` (to enable GPT) and `MODEL_NAME = gpt-5` (or another)
- `OPENAI_API_KEY = <secret-value>` (store in Secret Manager and **Reference as env var**)
- `AUTOSAVE = 1` (default on)
- `GOOGLE_CLOUD_PROJECT = <your-project-id>` (often injected automatically by GCP)

## Firestore
Enable **Firestore in Native mode** in the same region as Cloud Run. The backend uses application default creds.
Collection: `pitch_packs` (auto ID). Fields: idea, outline, one_pager, deck_outline, quality, created_at, updated_at.

## Frontend
- Agent Button now shows **quality label & score**, **Firestore doc ID**, and **suggestions**.
- Health Card shows **Model powered** and **Autosave** flags.

## Safety
If the model call fails or is disabled, the backend silently falls back to local scaffolds.
