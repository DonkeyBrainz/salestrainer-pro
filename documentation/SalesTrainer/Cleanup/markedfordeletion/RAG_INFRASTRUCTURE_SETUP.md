# RAG Infrastructure Setup Guide

## Overview
This guide explains the infrastructure needed for Phase 1 RAG implementation using Firestore Vector Search. You have two options: automated via Terraform or manual via GCP Console.

---

## What Infrastructure is Needed

### 1. GCS Bucket for PDFs
**Purpose:** Store the 10 product knowledge PDFs (5 training guides + 5 selling sheets)

**Terraform resource:** `google_storage_bucket.knowledge_bucket` in `terraform/storage.tf`

**What it creates:**
- Bucket name: `<PROJECT_ID>-sales-coach-knowledge`
- Location: `us-central1` (same region as other resources)
- Versioning: Enabled (keeps last 3 versions of each PDF)
- Access: Backend service account has read-only access

### 2. Firestore Vector Search Indexes
**Purpose:** Enable fast similarity search on product knowledge embeddings

**Terraform resources:** `terraform/firestore.tf`
- `google_firestore_index.knowledge_chunks_vector` - Main vector search index
- `google_firestore_index.knowledge_chunks_filtered` - Composite index for metadata filtering

**What it creates:**
- Index on `knowledge_chunks` collection
- Vector field: `embedding` (768 dimensions)
- Distance measure: COSINE similarity
- Additional indexing on `metadata.category` and `metadata.product_type`

---

## Option 1: Terraform (Automated)

### What Terraform Does

If you run terraform apply, it will:

1. **Create GCS bucket**
   - Creates bucket with proper naming convention
   - Enables versioning and lifecycle rules
   - Grants IAM permission to backend service account
   - Takes ~10 seconds

2. **Create Firestore indexes**
   - Registers vector search index configuration
   - Triggers index build process in Firestore
   - Takes 30-60 minutes for index to become active
   - You can monitor progress in GCP Console

### Commands to Execute Terraform

```bash
cd /Users/mpuerto/Documents/wt-rag-phase-1/terraform

# Initialize terraform (if not already done)
terraform init

# Preview what will be created
terraform plan

# Create the resources
terraform apply
```

### What to Expect

**Terminal output:**
```
Terraform will perform the following actions:

  # google_storage_bucket.knowledge_bucket will be created
  + resource "google_storage_bucket" "knowledge_bucket" {
      + name     = "ashley-ai-coach-dev-sales-coach-knowledge"
      + location = "us-central1"
      ...
    }

  # google_storage_bucket_iam_member.backend_storage_reader will be created
  ...

  # google_firestore_index.knowledge_chunks_vector will be created
  ...

Plan: 4 to add, 0 to change, 0 to destroy.
```

**After applying:**
- GCS bucket ready immediately
- Firestore indexes start building (30-60 min wait)
- Check status: GCP Console → Firestore → Indexes

---

## Option 2: Manual Setup (Recommended for You)

Since you want to understand the process and do it manually, here are the exact steps.

### Step 1: Create GCS Bucket

**Via GCP Console:**
1. Go to: https://console.cloud.google.com/storage
2. Click "Create Bucket"
3. Bucket name: `<YOUR_PROJECT_ID>-sales-coach-knowledge`
   - Example: `ashley-ai-coach-dev-sales-coach-knowledge`
4. Location type: Region
5. Region: `us-central1` (match your other resources)
6. Storage class: Standard
7. Access control: Uniform
8. Versioning: Enable object versioning
9. Click "Create"

**Via gcloud CLI:**
```bash
# Set your project ID
PROJECT_ID="ashley-ai-coach-dev"  # Replace with actual project ID

# Create bucket
gcloud storage buckets create gs://${PROJECT_ID}-sales-coach-knowledge \
  --location=us-central1 \
  --uniform-bucket-level-access \
  --versioning

# Grant backend service account read access
gcloud storage buckets add-iam-policy-binding \
  gs://${PROJECT_ID}-sales-coach-knowledge \
  --member="serviceAccount:salescoach-backend-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

**Verify:**
```bash
# List buckets to confirm creation
gcloud storage buckets list | grep knowledge

# Check IAM permissions
gcloud storage buckets get-iam-policy gs://${PROJECT_ID}-sales-coach-knowledge
```

### Step 2: Upload PDFs to GCS

**Organize your local PDFs:**
```
local_pdfs/
├── training_guide_1.pdf
├── training_guide_2.pdf
├── training_guide_3.pdf
├── training_guide_4.pdf
├── training_guide_5.pdf
├── selling_sheet_1.pdf
├── selling_sheet_2.pdf
├── selling_sheet_3.pdf
├── selling_sheet_4.pdf
└── selling_sheet_5.pdf
```

**Upload via gcloud:**
```bash
# Navigate to your PDF directory
cd /path/to/your/pdfs

# Upload all PDFs to products/ subfolder
gcloud storage cp *.pdf gs://${PROJECT_ID}-sales-coach-knowledge/products/

# Verify upload
gcloud storage ls gs://${PROJECT_ID}-sales-coach-knowledge/products/
```

**Upload via GCP Console:**
1. Go to: https://console.cloud.google.com/storage
2. Click on your `<PROJECT_ID>-sales-coach-knowledge` bucket
3. Click "Create Folder" → Name it "products"
4. Click into the "products" folder
5. Click "Upload Files"
6. Select all 10 PDFs
7. Wait for upload to complete

### Step 3: Create Firestore Vector Search Indexes

**IMPORTANT:** Firestore Vector Search is in preview. The exact UI/API may vary.

**Via GCP Console:**
1. Go to: https://console.cloud.google.com/firestore
2. Select your database (usually "(default)")
3. Click "Indexes" tab
4. Click "Create Index"

**Index 1: Vector Search Index**
- Collection ID: `knowledge_chunks`
- Fields to index:
  - Field 1: `embedding` → Vector (768 dimensions, COSINE distance)
  - Field 2: `metadata.category` → Ascending
- Query scope: Collection
- Click "Create"

**Index 2: Composite Index for Filtering**
- Collection ID: `knowledge_chunks`
- Fields to index:
  - Field 1: `metadata.category` → Ascending
  - Field 2: `metadata.product_type` → Ascending
- Query scope: Collection
- Click "Create"

**Via gcloud CLI:**
```bash
# Note: Vector search index creation via CLI may require beta/alpha features
# Check current gcloud documentation for exact syntax

# Basic approach (syntax may need adjustment):
gcloud firestore indexes composite create \
  --collection-group=knowledge_chunks \
  --field-config=field-path=embedding,vector-config='{dimension:768,flat:{}}' \
  --field-config=field-path=metadata.category,order=ascending \
  --database='(default)'
```

**Monitor Index Build:**
- Go to: https://console.cloud.google.com/firestore → Indexes
- Status will show "Building..." (30-60 minutes)
- When complete, status shows "Enabled"

### Step 4: Verify Setup

**Check GCS bucket:**
```bash
# List bucket contents
gcloud storage ls -r gs://${PROJECT_ID}-sales-coach-knowledge/

# Should see:
# gs://<PROJECT_ID>-sales-coach-knowledge/products/
# gs://<PROJECT_ID>-sales-coach-knowledge/products/training_guide_1.pdf
# ... (all 10 PDFs)
```

**Check Firestore indexes:**
```bash
# List all indexes
gcloud firestore indexes composite list --database='(default)'

# Should see two indexes for knowledge_chunks collection
```

**Check IAM permissions:**
```bash
# Verify backend SA can read from bucket
gcloud storage buckets get-iam-policy gs://${PROJECT_ID}-sales-coach-knowledge \
  | grep salescoach-backend-sa

# Should see: member: serviceAccount:salescoach-backend-sa@...
```

---

## What Happens Next (After Infrastructure is Ready)

### Phase 1 Implementation Flow

Once infrastructure is set up, the code implementation will:

1. **Indexing script runs** (`scripts/build_knowledge_index.py`)
   - Loads PDFs from GCS bucket
   - Extracts text using pypdf
   - Chunks text (800 chars, 200 overlap)
   - Generates embeddings via Gemini API (768 dimensions)
   - Stores in Firestore `knowledge_chunks` collection
   - Expected output: ~1000-1200 documents (10 PDFs × 100-120 chunks each)

2. **RAG service runs** (`app/services/rag_service.py`)
   - Receives query from coach agent
   - Embeds query via Gemini API
   - Queries Firestore vector search (top 3 results)
   - Returns formatted context string

3. **Coach agent uses RAG** (`app/agents/coach/analyzer.py`)
   - Before calling LLM, fetches product context via RAG
   - Injects context into coach prompt
   - LLM generates hint with product-specific details

---

## Cost Analysis

### Terraform vs Manual: Same Cost

The infrastructure costs the same whether created via Terraform or manually.

**GCS Bucket:**
- Storage: ~50MB (10 PDFs × ~5MB each)
- Cost: $0.00/month (within 5GB free tier)
- Data transfer: Minimal (one-time PDF load)

**Firestore Vector Search:**
- Storage: ~2.5MB (1000 documents × 2.5KB each)
- Cost: $0.00/month (within 1GB free tier)
- Reads: ~2,000/day (100 sessions × 20 hints each)
- Cost: $0.00/month (within 20K reads/day free tier)

**Gemini Embeddings:**
- One-time: 1000 chunks to embed
- Ongoing: 2,000 query embeddings/day
- Cost: $0.00/month (within free tier)

**Total Cost: $0/month** (all within GCP free tiers)

---

## Terraform vs Manual: Pros and Cons

### Terraform Advantages
- **Reproducible:** Can recreate infrastructure with one command
- **Version controlled:** Infrastructure as code tracked in git
- **Automated:** No manual clicking in console
- **Declarative:** State is tracked automatically
- **Safer:** Preview changes before applying

### Manual Advantages
- **Learning:** Understand each step and what it does
- **Control:** See exactly what's being created
- **No dependencies:** Don't need terraform installed/configured
- **Immediate:** No need to learn terraform syntax
- **Flexible:** Can adjust as you go

### Recommendation for This Project

**Use Terraform for:**
- Production deployments
- When you have multiple environments (dev, staging, prod)
- When infrastructure changes frequently
- When collaborating with team

**Use Manual for:**
- Learning and exploration (what you're doing now)
- One-off setups
- Quick prototyping
- When terraform syntax is unclear (preview features like vector search)

---

## Troubleshooting

### Bucket Already Exists
**Error:** "Bucket already exists"

**Solution:**
- Bucket names are globally unique
- Add a suffix: `${PROJECT_ID}-sales-coach-knowledge-v2`
- Or delete existing bucket if it's from previous attempt

### Index Build Takes Too Long
**Expected:** 30-60 minutes for vector index to build

**If stuck >2 hours:**
- Check Firestore quotas in GCP Console
- Verify Firestore API is enabled
- Check for error messages in index status
- Try deleting and recreating index

### IAM Permission Errors
**Error:** "Permission denied" when indexing script runs

**Check:**
```bash
# Verify backend SA has Firestore access
gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:salescoach-backend-sa@*" \
  --format="table(bindings.role)"

# Should see: roles/datastore.user
```

### PDF Upload Fails
**Error:** Size limit or network timeout

**Solutions:**
- Upload PDFs one at a time instead of all at once
- Use gsutil instead of gcloud: `gsutil -m cp *.pdf gs://bucket/products/`
- Check internet connection
- Verify PDFs aren't corrupted (try opening locally)

---

## Next Steps After Infrastructure Setup

### 1. Update Dependencies
```bash
cd /Users/mpuerto/Documents/wt-rag-phase-1/backend
# Add to pyproject.toml:
# google-cloud-storage>=2.14.0
# pypdf>=3.17.0
uv sync
```

### 2. Implement RAG Service
Create `backend/app/services/rag_service.py` (250 lines)
- Document chunking
- Embedding generation
- Firestore vector search
- Context formatting

### 3. Build Knowledge Index
Create and run `backend/scripts/build_knowledge_index.py`
- Loads PDFs from GCS
- Populates Firestore knowledge_chunks collection
- One-time execution (unless PDFs change)

### 4. Integrate with Coach Agent
Modify `backend/app/agents/coach/analyzer.py` (+15 lines)
Modify `backend/app/agents/coach/prompts.py` (+30 lines)

### 5. Test End-to-End
- Unit tests for RAG service
- Integration tests with sample PDF
- Manual testing in training session

---

## Summary

**You've created (or will create manually):**
- [x] `terraform/storage.tf` - GCS bucket definition
- [x] `terraform/firestore.tf` - Vector search index definitions
- [ ] GCS bucket: `<PROJECT_ID>-sales-coach-knowledge`
- [ ] 10 PDFs uploaded to `gs://bucket/products/`
- [ ] Firestore vector search indexes (building...)

**Terraform would automate:**
- Bucket creation (10 seconds)
- IAM binding (5 seconds)
- Index creation request (5 seconds)
- But index build still takes 30-60 min regardless

**Manual gives you:**
- Understanding of each component
- Control over the process
- No terraform learning curve
- Flexibility to adjust

**Both approaches result in identical infrastructure with $0/month cost.**
