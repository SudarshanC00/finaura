# Deployment Guide

This guide covers deploying the Financial RAG application using **Vercel** (frontend) + **Render** (backend), with **GitHub Actions** CI/CD.

---

## Architecture Overview

```
GitHub (push to main)
    │
    ├──► GitHub Actions CI/CD
    │     ├── Lint frontend (ESLint)
    │     ├── Build frontend (Next.js)
    │     ├── Lint backend (Ruff)
    │     ├── Build Docker image → GHCR
    │     └── Trigger deploy → Render
    │
    ├──► Vercel (auto-deploy frontend)
    │     └── https://your-app.vercel.app
    │
    └──► Render (Docker backend)
          └── https://your-api.onrender.com
```

---

## Step 1: Deploy the Backend (Render)

### Option A: One-Click Deploy (Recommended)

1. Go to [render.com/deploy](https://render.com/deploy)
2. Connect your GitHub repo: `SudarshanC00/Financial-RAG`
3. Render will detect the `render.yaml` blueprint and auto-configure
4. Set the `OPENAI_API_KEY` environment variable in the dashboard
5. Click **Deploy**

### Option B: Manual Setup

1. Log in to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Name**: `financial-rag-api`
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Plan**: Starter ($7/month) or higher
4. Add environment variable:
   - `OPENAI_API_KEY` = your key
5. Add a **Disk** (persistent storage for Qdrant):
   - Mount Path: `/app/storage`
   - Size: 1 GB
6. Deploy

Your backend URL will be something like: `https://financial-rag-api.onrender.com`

---

## Step 2: Deploy the Frontend (Vercel)

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repo: `SudarshanC00/Financial-RAG`
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
4. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://financial-rag-api.onrender.com` (your Render URL from Step 1)
5. Click **Deploy**

Your frontend URL will be something like: `https://financial-rag.vercel.app`

---

## Step 3: Update Backend CORS

After both are deployed, update `api.py` to allow your Vercel domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://financial-rag.vercel.app",   # ← Add your Vercel URL
    ],
    ...
)
```

Commit and push — the CI/CD pipeline will redeploy automatically.

---

## Step 4: CI/CD Pipeline (GitHub Actions)

The pipeline at `.github/workflows/ci-cd.yml` runs automatically on every push/PR:

### On Pull Requests:
| Job | What it does |
|---|---|
| **Frontend Checks** | `npm ci` → `npm run lint` → `npm run build` |
| **Backend Checks** | `pip install` → `ruff check` → validate imports |

### On Push to `main` (after checks pass):
| Job | What it does |
|---|---|
| **Docker Build** | Builds image → pushes to `ghcr.io/sudarshanc00/financial-rag:latest` |
| **Deploy Backend** | Triggers Render redeploy via webhook |

### Enable Auto-Deploy Webhook

1. In Render dashboard → your service → **Settings** → **Deploy Hook**
2. Copy the hook URL
3. In GitHub → **Settings** → **Secrets and variables** → **Actions**
4. Add secret: `RENDER_DEPLOY_HOOK_URL` = the URL from Render
5. In `.github/workflows/ci-cd.yml`, uncomment the curl line in the `deploy-backend` job

---

## Environment Variables Summary

### Backend (Render)
| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | OpenAI or OpenRouter API key |

### Frontend (Vercel)
| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | Full URL of the deployed backend (e.g., `https://financial-rag-api.onrender.com`) |

### GitHub Actions Secrets
| Secret | Required | Description |
|---|---|---|
| `RENDER_DEPLOY_HOOK_URL` | Optional | Render deploy hook for auto-redeploy |
| `GITHUB_TOKEN` | Auto | Provided by GitHub for GHCR push |

---

## Alternative Platforms

### Railway (Backend)
1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select the repo, Railway auto-detects the Dockerfile
3. Add `OPENAI_API_KEY` env var
4. Add a **Volume** for persistent storage at `/app/storage`

### Fly.io (Backend)
```bash
fly launch --dockerfile Dockerfile
fly secrets set OPENAI_API_KEY="your-key"
fly volumes create rag_storage --size 1
fly deploy
```

### Netlify (Frontend)
1. Similar to Vercel — connect repo, set root to `frontend`
2. Build command: `npm run build`
3. Publish directory: `.next`
4. Set `NEXT_PUBLIC_API_URL` env var

---

## Monitoring

- **Render**: Built-in logs and metrics at dashboard
- **Vercel**: Analytics and function logs
- **Health Check**: `GET https://your-api.onrender.com/api/health`
