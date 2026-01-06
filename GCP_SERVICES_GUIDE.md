# GCP Services Required for Deployment

This guide explains all the Google Cloud Platform (GCP) services you need to deploy and run the Edmonbrain LLM application with Twitter and news website data sources.

## Core Services (Required)

### 1. **Cloud Run** 🚀
**What it does:** Serverless container platform that runs your application services

**Why you need it:**
- Hosts your microservices (chunker, embedder, qna, webapp)
- Automatically scales up/down based on traffic
- Scales to zero when not in use (saves money)
- Handles HTTPS, load balancing, and auto-scaling

**Services deployed:**
- `edmonbrain-chunker` - Processes documents and chunks them
- `edmonbrain-embedder` - Creates embeddings from chunks
- `edmonbrain-qna` - Handles Q&A queries
- `edmonbrain-webapp` - Web interface (optional)
- `edmonbrain-unstructured` - Document processing service (if self-hosting)

**Configuration:**
- Memory: 4GB (chunker), 2-4GB (others)
- CPU: 2 vCPUs (chunker), 1-2 vCPUs (others)
- Min instances: 0 (scales to zero)
- Max instances: 8 (adjust based on traffic)

**Cost:** 
- Pay per request: $0.40 per million requests
- CPU/Memory: ~$0.00002400 per vCPU-second, ~$0.00000250 per GiB-second
- Free tier: 2 million requests/month

**Enable API:**
```bash
gcloud services enable run.googleapis.com
```

---

### 2. **Cloud Storage (GCS)** 📦
**What it does:** Object storage for files and documents

**Why you need it:**
- Stores your `config.json` file
- Stores uploaded documents (PDFs, text files, etc.)
- Stores processed chunks temporarily
- Acts as a data lake for your documents

**What you'll store:**
- Configuration files (`config.json`)
- Uploaded documents from users
- Processed document chunks
- Temporary files during processing

**Cost:**
- Storage: $0.020 per GB/month (Standard class)
- Operations: $0.05 per 10,000 Class A operations (writes)
- Free tier: 5 GB storage, 5,000 Class A operations/month

**Enable API:**
```bash
gcloud services enable storage.googleapis.com
```

**Create bucket:**
```bash
gsutil mb -p $PROJECT_ID -l $REGION gs://$GCS_BUCKET
```

---

### 3. **Cloud Pub/Sub** 📨
**What it does:** Asynchronous messaging service for microservices communication

**Why you need it:**
- Queues messages between services
- Decouples services (chunker → embedder → qna)
- Handles retries and dead-letter queues
- Enables event-driven architecture

**Topics created:**
- `app_to_pubsub_<vector_name>` - Receives new documents/data
- `embed_chunk_<vector_name>` - Sends chunks for embedding
- `pubsub_state_messages` - Status/logging messages

**How it works:**
1. User uploads document → Pub/Sub topic
2. Chunker processes → Publishes chunks to embedder
3. Embedder creates embeddings → Stores in vector DB
4. QNA service queries vector DB for answers

**Cost:**
- First 10 GB/month: Free
- Additional: $0.40 per million messages
- Free tier: 10 GB/month

**Enable API:**
```bash
gcloud services enable pubsub.googleapis.com
```

---

### 4. **Secret Manager** 🔐
**What it does:** Securely stores API keys, passwords, and sensitive data

**Why you need it:**
- Stores Twitter API credentials
- Stores OpenAI API keys
- Stores database connection strings
- Stores other sensitive configuration

**Secrets you'll store:**
- `TWITTER_BEARER_TOKEN` - Twitter API token
- `TWITTER_API_KEY` - Twitter API key (optional)
- `TWITTER_API_SECRET` - Twitter API secret (optional)
- `UNSTRUCTURED_KEY` - Unstructured.io API key
- `OPENAI_API_KEY` - OpenAI API key
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase API key
- `LANGCHAIN_API_KEY` - LangChain API key
- `GIT_PAT` - GitHub Personal Access Token
- `DB_CONNECTION_STRING` - Database connection

**Cost:**
- First 6 secrets: Free
- Additional secrets: $0.06 per secret per month
- Secret versions: $0.03 per version per month
- Access operations: $0.03 per 10,000 operations

**Enable API:**
```bash
gcloud services enable secretmanager.googleapis.com
```

**Create secret:**
```bash
echo -n "your-secret-value" | gcloud secrets create SECRET_NAME --data-file=-
```

---

## Optional but Recommended Services

### 5. **Cloud Build** 🔨
**What it does:** Builds and deploys your container images

**Why you need it:**
- Builds Docker images from your code
- Pushes images to Container Registry
- Deploys to Cloud Run automatically
- Enables CI/CD pipeline

**What it does:**
1. Reads your `cloudbuild_*.yaml` files
2. Builds Docker images
3. Pushes to Google Container Registry (GCR)
4. Deploys to Cloud Run

**Cost:**
- First 120 build-minutes/day: Free
- Additional: $0.003 per build-minute
- Free tier: 120 build-minutes/day

**Enable API:**
```bash
gcloud services enable cloudbuild.googleapis.com
```

---

### 6. **BigQuery** 📊
**What it does:** Serverless data warehouse for structured data

**Why you need it:**
- Stores Q&A history
- Stores structured metadata
- Enables analytics and reporting
- Used for querying conversation history

**When you need it:**
- If using structured data storage
- If storing Q&A conversation history
- If you need analytics on queries

**Cost:**
- Storage: $0.020 per GB/month
- Queries: $5 per TB processed (first 1 TB/month free)
- Free tier: 10 GB storage, 1 TB queries/month

**Enable API:**
```bash
gcloud services enable bigquery.googleapis.com
```

---

### 7. **Vertex AI** 🤖
**What it does:** Google's AI/ML platform for LLM models

**Why you need it:**
- If using Google's LLM models (instead of OpenAI)
- Access to PaLM, Gemini, and other Vertex AI models
- Alternative to OpenAI API

**When you need it:**
- If using `llm: "vertex"` in config.json
- If using `llm: "codey"` in config.json
- Want to use Google's models instead of OpenAI

**Cost:**
- Varies by model and usage
- Check current pricing: https://cloud.google.com/vertex-ai/pricing
- Some models have free tiers

**Enable API:**
```bash
gcloud services enable aiplatform.googleapis.com
```

---

## Additional Services (Depending on Configuration)

### 8. **Cloud Scheduler** ⏰
**What it does:** Cron job service for scheduled tasks

**Why you might need it:**
- Periodically fetch Twitter data
- Periodically fetch news website updates
- Scheduled data ingestion

**Example use case:**
```bash
# Fetch Twitter data every 6 hours
gcloud scheduler jobs create pubsub fetch-twitter \
  --schedule="0 */6 * * *" \
  --topic=app_to_pubsub_edmonbrain \
  --message-body="twitter://user:BBCNews"
```

**Cost:**
- First 3 jobs: Free
- Additional: $0.10 per job per month
- Free tier: 3 jobs

**Enable API:**
```bash
gcloud services enable cloudscheduler.googleapis.com
```

---

### 9. **Cloud Logging** 📝
**What it does:** Centralized logging for all services

**Why you need it:**
- View logs from all Cloud Run services
- Debug issues
- Monitor application health
- Track errors and performance

**Cost:**
- First 50 GB/month: Free
- Additional: $0.50 per GB
- Free tier: 50 GB/month

**Automatically enabled** - No setup needed

---

### 10. **Cloud Monitoring** 📈
**What it does:** Monitoring and alerting for your services

**Why you might need it:**
- Set up alerts for errors
- Monitor service health
- Track performance metrics
- Create dashboards

**Cost:**
- Free tier: 150 MB metrics ingestion/month
- Additional: $0.258 per MB

**Enable API:**
```bash
gcloud services enable monitoring.googleapis.com
```

---

## Service Architecture Flow

```
User/API Request
    ↓
Cloud Storage (config.json, documents)
    ↓
Pub/Sub (message queue)
    ↓
Cloud Run - Chunker Service
    ↓
Pub/Sub (chunks queue)
    ↓
Cloud Run - Embedder Service
    ↓
Vector Database (Supabase or other)
    ↓
Cloud Run - QNA Service
    ↓
Response to User
```

## Enable All Required APIs

Run this command to enable all required APIs at once:

```bash
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  cloudscheduler.googleapis.com \
  monitoring.googleapis.com
```

## Estimated Monthly Costs

**Small deployment (low traffic):**
- Cloud Run: $5-20/month
- Cloud Storage: $1-5/month
- Pub/Sub: Free (under 10 GB)
- Secret Manager: Free (under 6 secrets)
- Cloud Build: Free (under 120 min/day)
- **Total: ~$10-30/month**

**Medium deployment (moderate traffic):**
- Cloud Run: $20-50/month
- Cloud Storage: $5-15/month
- Pub/Sub: $5-10/month
- Secret Manager: Free
- Cloud Build: $5-10/month
- **Total: ~$35-85/month**

**Large deployment (high traffic):**
- Cloud Run: $50-200/month
- Cloud Storage: $15-50/month
- Pub/Sub: $10-30/month
- Secret Manager: $1-5/month
- Cloud Build: $10-30/month
- **Total: ~$90-315/month**

*Note: Costs vary significantly based on usage. Use GCP Pricing Calculator for accurate estimates.*

## Free Tier Benefits

GCP offers free tiers for many services:
- **Cloud Run**: 2 million requests/month
- **Cloud Storage**: 5 GB storage
- **Pub/Sub**: 10 GB/month
- **Secret Manager**: 6 secrets
- **Cloud Build**: 120 build-minutes/day
- **BigQuery**: 10 GB storage, 1 TB queries/month
- **Cloud Logging**: 50 GB/month

You can run a small deployment for **free or very low cost** within free tier limits!

## Next Steps

1. **Enable all required APIs** (use command above)
2. **Create a GCS bucket** for storage
3. **Create secrets** in Secret Manager
4. **Set up service account** with proper permissions
5. **Deploy services** using Cloud Build or manually

For detailed setup instructions, see:
- [QUICK_START.md](QUICK_START.md)
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

