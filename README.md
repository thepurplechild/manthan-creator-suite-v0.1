# Project Manthan OS — Creator Suite v0 (GCP-ready)

A minimal, premium-feel starter focused on the **Creator Suite**:
- Create Project (title, logline, genre, tone)
- AI Pitch Pack stub (logline → synopsis, beats, deck outline — generated from a template on the backend)
- Projects list (saved in **Firestore** for frictionless Cloud Run deploy without networking to Cloud SQL)
- Clean, modern Next.js UI (Tailwind), ready to skin with your brand
- Point-and-click deployment via **Cloud Build** → **Cloud Run** (no terminal)

## What you get
- **frontend/**: Next.js 14 (App Router) + Tailwind. Pages: Dashboard, Projects, New Project wizard. Calls backend.
- **backend/**: FastAPI with endpoints:
  - `POST /api/pitch/generate` — returns a pitch-pack from a stubbed template
  - `GET /api/projects` — list projects
  - `POST /api/projects` — create project
  Uses **Firestore** (native on GCP; easiest to deploy).
- **infra/**: Cloud Build YAMLs that build & deploy two Cloud Run services:
  - `manthan-backend`
  - `manthan-frontend`

> We can migrate storage to Postgres later when we add marketplace & analytics; Firestore keeps setup dead-simple for v0.

---

## Deploy (no terminal)

**Prereqs** (one-time per GCP project):
1. In the GCP Console, create/select a project. Set region: **asia-south1 (Mumbai)** (or asia-south2 Delhi).
2. Enable APIs: Cloud Run, Cloud Build, Artifact Registry, Firestore, Secret Manager, Service Usage.
3. Firestore: Go to Firestore → **Create database** → **Native mode** → Location: same region group as Cloud Run.

**Connect your GitHub repo (clicks only):**
1. Create an **empty GitHub repo** in your account (private is fine).
2. Upload this ZIP’s contents to that repo via the GitHub web UI (“Upload files”). Keep top-level folder structure.
3. In GCP: Cloud Build → **Triggers** → **Connect repository** → select your GitHub and authorize.

**Create Cloud Run services via Cloud Build (GUI):**
1. Cloud Build → **Triggers** → **Create trigger**:
   - Name: `deploy-backend`
   - Event: Push to branch `main`
   - Configuration: “Cloud Build configuration file (yaml)”
   - Location: **/infra/cloudbuild-backend.yaml**
   - Save.
2. Create another trigger:
   - Name: `deploy-frontend`
   - Event: Push to branch `main`
   - Config file: **/infra/cloudbuild-frontend.yaml**
   - Save.

**First deployment (click-run):**
- After triggers are created, in each trigger page click **Run** → choose branch `main` → **Run**.
- Cloud Build will:
  - Build images in Artifact Registry
  - Deploy to Cloud Run services: `manthan-backend`, `manthan-frontend`
- When done, Cloud Run shows service URLs.
- In **frontend**, set the backend URL via env (see below) and re-run the frontend trigger once.

### Environment variables
Set these in each Cloud Run service under **Variables & Secrets** → **Variables**:

**Backend (`manthan-backend`)**
- `GOOGLE_CLOUD_PROJECT` = your GCP project ID (Cloud Run sets it automatically; only add if needed)
- `FIRESTORE_COLLECTION` = `projects` (default)

**Frontend (`manthan-frontend`)**
- `NEXT_PUBLIC_BACKEND_URL` = Cloud Run URL for `manthan-backend`, e.g. `https://manthan-backend-xxxx-uc.a.run.app`

> After setting env vars, redeploy by re-running the corresponding Cloud Build trigger (GUI button).

---

## Local development (optional)
If you ever want to test locally later, you’ll need Node 18+ and Python 3.11+ and a Google service account JSON, but for now we’re avoiding terminals per your preference.

---

## Next steps
- Brand the UI (name, colors, logo).
- Add Google Sign-In (Identity Platform) → gate routes.
- Add asset upload (Cloud Storage) for scripts and lookbooks.
- Extend the AI generator to your preferred model when you’re ready to add keys.

---

**Support**
If anything fails in Cloud Build/Run, copy the error and I’ll fix the config for you.
