# Setup Checklist - SalesTrainer Pro

## Development Setup Prerequisites

Before starting development or deployment, verify these requirements:

### System Requirements
- [ ] Python 3.13+ installed (backend requirement)
- [ ] Node.js 18+ installed (frontend requirement)
- [ ] `uv` package manager installed (`pip install uv`)
- [ ] `gcloud` CLI installed and authenticated

### Backend Environment
- [ ] Google Cloud project `salescoach-494901` created
- [ ] Gemini API enabled and API key obtained (or alternative: OpenAI API key or AWS credentials for Nova)
- [ ] Firestore database created
- [ ] Service account with appropriate permissions created
- [ ] Environment variables configured in `.env` (see `/backend/.env.example`)

### Voice Provider Selection
Choose one or more voice providers:
- [ ] **Gemini** (default): `VOICE_PROVIDER=gemini` + `GEMINI_API_KEY`
- [ ] **OpenAI Realtime**: `VOICE_PROVIDER=openai` + `OPENAI_API_KEY` + `OPENAI_ORG_ID` (optional)
- [ ] **Amazon Nova**: `VOICE_PROVIDER=nova` + AWS credentials (IAM role or access keys)
- [ ] Set `VOICE_PROVIDER_FALLBACK` for automatic fallback chain (e.g., `"gemini,openai,nova"`)

### Frontend Setup
- [ ] Node.js dependencies installed (`npm install`)
- [ ] Backend API URL configured in `.env.local` or proxy settings

---

## Custom Domain Setup Checklist

Use this checklist when manually setting up a custom domain (example: `your-domain.example.com`). SalesTrainer Pro does not currently use a custom domain in production — see `documentation/CICD_GUIDE.md` for the default Cloud Run URLs.

Refer to `CUSTOM_DOMAIN_SETUP.md` for detailed command instructions.

---

## Pre-Setup

- [ ] GCP project `salescoach-494901` exists and billing is enabled
- [ ] You have admin access to Cloud DNS or your domain registrar
- [ ] Backend and frontend Cloud Run services are deployed
- [ ] `gcloud` CLI is installed and authenticated

---

## Step 1: Enable APIs

- [ ] Enable Compute Engine API
  ```bash
  gcloud services enable compute.googleapis.com --project=salescoach-494901
  ```

---

## Step 2: Create Network Endpoint Groups (NEGs)

- [ ] Create backend NEG (connects load balancer to backend Cloud Run)
- [ ] Create frontend NEG (connects load balancer to frontend Cloud Run)
- [ ] Verify NEGs created:
  ```bash
  gcloud compute network-endpoint-groups list --project=salescoach-494901
  ```

---

## Step 3: Create Backend Services

- [ ] Create backend service (for API) with 5-minute timeout
- [ ] Add backend NEG to backend service
- [ ] Create frontend service (for static assets) with CDN enabled
- [ ] Add frontend NEG to frontend service
- [ ] Verify backend services created:
  ```bash
  gcloud compute backend-services list --project=salescoach-494901
  ```

---

## Step 4: Reserve External IP

- [ ] Reserve global IP address named `salescoach-ip`
- [ ] **Save this IP address** (needed for DNS):
  ```bash
  gcloud compute addresses describe salescoach-ip \
    --global \
    --project=salescoach-494901 \
    --format="get(address)"
  ```
  IP: ___________________________

---

## Step 5: Create SSL Certificate

- [ ] Create managed SSL certificate for `your-domain.example.com`
- [ ] Note: Will provision after DNS is configured (15-60 min)

---

## Step 6: Create URL Map (Routing)

- [ ] Create URL map with default route to frontend
- [ ] Add path matcher for `your-domain.example.com`
- [ ] Add routing rules:
  - [ ] `/api/*` → backend
  - [ ] `/ws/*` → backend
  - [ ] `/auth/*` → backend
  - [ ] `/health` → backend
  - [ ] `/docs`, `/redoc`, `/openapi.json` → backend

---

## Step 7: Create HTTPS Proxy

- [ ] Create HTTPS target proxy
- [ ] Attach URL map
- [ ] Attach SSL certificate

---

## Step 8: Create Forwarding Rules

- [ ] Create HTTPS forwarding rule (port 443)
- [ ] Create HTTP to HTTPS redirect URL map
- [ ] Create HTTP target proxy
- [ ] Create HTTP forwarding rule (port 80)
- [ ] Verify forwarding rules:
  ```bash
  gcloud compute forwarding-rules list --project=salescoach-494901
  ```

---

## Step 9: Configure DNS

- [ ] Get load balancer IP from Step 4
- [ ] Create DNS A record:
  - Host: `your-domain.example.com`
  - Type: `A`
  - Value: ___________________________
  - TTL: `300`
- [ ] Verify DNS propagation (may take 5-10 minutes):
  ```bash
  dig your-domain.example.com +short
  ```

---

## Step 10: Update Cloud Run Ingress

- [ ] Update backend ingress to `internal-and-cloud-load-balancing`
- [ ] Update frontend ingress to `internal-and-cloud-load-balancing`
- [ ] Verify ingress settings:
  ```bash
  gcloud run services describe salescoach-backend \
    --region=us-central1 \
    --project=salescoach-494901 \
    --format="get(spec.ingress)"
  ```

---

## Step 11: Remove Public Access

- [ ] Remove `allUsers` IAM binding from backend
- [ ] Remove `allUsers` IAM binding from frontend
- [ ] Verify direct Cloud Run URLs return 403 (forbidden)

---

## Step 12: Update OAuth Apps

### Google OAuth
- [ ] Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
- [ ] Click OAuth 2.0 Client ID
- [ ] Add redirect URI: `https://your-domain.example.com/auth/callback`
- [ ] Save

### Microsoft OAuth (if configured)
- [ ] Go to [Azure Portal → App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
- [ ] Click app → Authentication
- [ ] Add redirect URI: `https://your-domain.example.com/auth/callback`
- [ ] Save

---

## Step 13: Wait for SSL Certificate

- [ ] Wait 15-60 minutes after DNS configuration
- [ ] Check SSL certificate status:
  ```bash
  gcloud compute ssl-certificates describe salescoach-ssl-cert \
    --global \
    --project=salescoach-494901 \
    --format="get(managed.status)"
  ```
- [ ] Status should be `ACTIVE`

---

## Testing

### Load Balancer
- [ ] DNS resolves: `dig your-domain.example.com +short`
- [ ] HTTPS works: `curl https://your-domain.example.com/`
- [ ] HTTP redirects: `curl -I http://your-domain.example.com/`

### Backend
- [ ] Health check: `curl https://your-domain.example.com/health`
- [ ] API docs: `curl https://your-domain.example.com/docs`

### Frontend
- [ ] Homepage loads in browser: `https://your-domain.example.com`
- [ ] Static assets load (check DevTools)

### OAuth & Cookies
- [ ] Open `https://your-domain.example.com` in **incognito mode**
- [ ] Click login
- [ ] Complete OAuth flow
- [ ] Verify logged in
- [ ] Check cookies in DevTools → Application → Cookies:
  - [ ] `oauth_state` cookie exists
  - [ ] `SameSite=Lax`
  - [ ] `Secure=true`
  - [ ] `HttpOnly=true`
- [ ] No CORS errors in browser console

### WebSockets (if applicable)
- [ ] Start a session
- [ ] Verify WebSocket connection in DevTools → Network → WS
- [ ] Verify messages sent/received

---

## Cleanup (if needed)

To revert to original setup (public Cloud Run):

- [ ] Re-enable public access (see `CUSTOM_DOMAIN_SETUP.md` Rollback section)
- [ ] Update OAuth redirect URIs back to Cloud Run URLs
- [ ] Delete load balancer resources (optional, stops billing)

---

## Notes

**Completion time**: 1-2 hours (including SSL provisioning wait)

**Cost**: ~$36-50/month for load balancer

**Support**: See `CUSTOM_DOMAIN_SETUP.md` Troubleshooting section

**Status**:
- Started: ___________________________
- Completed: ___________________________
- Tested by: ___________________________
