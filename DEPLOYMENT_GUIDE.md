# Deployment Guide: GitHub and GCP

This guide will help you deploy the Edmonbrain LLM application to GitHub and Google Cloud Platform (GCP).

## Prerequisites

### 1. GitHub Account Setup
- Create a GitHub repository (or use existing)
- Generate a Personal Access Token (PAT) with `repo` scope if you need to clone private repos
- Store PAT in GCP Secret Manager as `gitpython_PAT`

### 2. GCP Account Setup

#### Required GCP Services:
- **Cloud Run** - For running containerized services
- **Cloud Storage** - For storing documents and config files
- **Pub/Sub** - For message queuing between services
- **Secret Manager** - For storing API keys and credentials
- **Cloud Build** - For CI/CD (optional but recommended)
- **BigQuery** - For structured data storage (if using)
- **Vertex AI** - For LLM models (if using Vertex AI)

#### GCP Project Setup:
```bash
# Set your project ID
export PROJECT_ID=your-project-id
export REGION=us-central1  # or your preferred region
export GCS_BUCKET=your-bucket-name

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com
```

### 3. Required API Keys and Secrets

Store these in GCP Secret Manager:

#### Twitter API (New Requirement)
- **TWITTER_BEARER_TOKEN** - Twitter API v2 Bearer Token
- **TWITTER_API_KEY** - Twitter API Key (optional, for advanced features)
- **TWITTER_API_SECRET** - Twitter API Secret (optional)

To get Twitter API credentials:
1. Go to https://developer.twitter.com/
2. Create a developer account
3. Create a new app/project
4. Generate Bearer Token

#### Existing Secrets (from original setup)
- **UNSTRUCTURED_KEY** - Unstructured.io API key (https://www.unstructured.io/api-key/)
- **LANGCHAIN_API_KEY** - LangChain API key (https://smith.langchain.com/settings) or dummy value
- **GIT_PAT** - GitHub Personal Access Token (if using private repos)
- **SUPABASE_URL** - Supabase project URL (if using Supabase vector store)
- **SUPABASE_KEY** - Supabase API key
- **OPENAI_API_KEY** - OpenAI API key (if using OpenAI models)
- **DB_CONNECTION_STRING** - Database connection string

#### Create Secrets in GCP:
```bash
# Twitter secrets
echo -n "your-twitter-bearer-token" | gcloud secrets create TWITTER_BEARER_TOKEN --data-file=-
echo -n "your-twitter-api-key" | gcloud secrets create TWITTER_API_KEY --data-file=-
echo -n "your-twitter-api-secret" | gcloud secrets create TWITTER_API_SECRET --data-file=-

# Existing secrets (update with your values)
echo -n "your-unstructured-key" | gcloud secrets create UNSTRCUTURED_KEY --data-file=-
echo -n "your-langchain-key" | gcloud secrets create LANGCHAIN_API_KEY --data-file=-
# ... repeat for other secrets
```

### 4. Service Account Setup

Create a service account with necessary permissions:
```bash
# Create service account
gcloud iam service-accounts create edmonbrain-sa \
  --display-name="Edmonbrain Service Account"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/pubsub.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

### 5. GCS Bucket Setup

```bash
# Create bucket
gsutil mb -p $PROJECT_ID -l $REGION gs://$GCS_BUCKET

# Upload config.json to bucket root
gsutil cp config.json gs://$GCS_BUCKET/config.json
```

## Configuration File

Create `config.json` in your GCS bucket root with the following structure:

```json
{
  "code_extensions": [".py", ".js", ".java", ".c", ".cpp", ".cs", ".rb", ".php", ".txt", ".md", ".json", ".yaml", ".sql", ".r"],
  "news_sources": [
    {
      "name": "BBC News",
      "url": "https://www.bbc.com/news",
      "rss": "http://feeds.bbci.co.uk/news/rss.xml",
      "type": "rss"
    },
    {
      "name": "Reuters",
      "url": "https://www.reuters.com",
      "rss": "https://www.reuters.com/rssFeed/worldNews",
      "type": "rss"
    },
    {
      "name": "CNN",
      "url": "https://www.cnn.com",
      "rss": "http://rss.cnn.com/rss/edition.rss",
      "type": "rss"
    },
    {
      "name": "The Guardian",
      "url": "https://www.theguardian.com",
      "rss": "https://www.theguardian.com/world/rss",
      "type": "rss"
    }
  ],
  "twitter_sources": [
    {
      "username": "BBCNews",
      "type": "user_timeline"
    },
    {
      "username": "Reuters",
      "type": "user_timeline"
    },
    {
      "hashtag": "breakingnews",
      "type": "hashtag"
    }
  ],
  "edmonbrain": {
    "llm": "openai",
    "vectorstore": "supabase",
    "prompt": "You are a happy, optimistic British AI who always works step by step logically through why you are answering any particular question.\n"
  }
}
```

## Deployment Steps

### Step 1: Deploy Prebuild Image

The prebuild step creates a base image with common dependencies:

```bash
cd prebuild
gcloud builds submit --config=cloudbuild_prebuild.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_GCS_BUCKET=$GCS_BUCKET
```

### Step 2: Deploy Unstructured Service (if using self-hosted)

```bash
cd unstructured
gcloud builds submit --config=cloudbuild_unstructured.yaml \
  --substitutions=_REGION=$REGION,_SERVICE_ACCOUNT=edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### Step 3: Deploy Chunker Service

```bash
cd chunker
gcloud builds submit --config=cloudbuild_cloudrun_chunker.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-chunker,_REGION=$REGION,_GCS_BUCKET=gs://$GCS_BUCKET,_SERVICE_ACCOUNT=edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### Step 4: Deploy Embedder Service

```bash
cd embedder
gcloud builds submit --config=cloudbuild_cloudrun_embedder.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-embedder,_REGION=$REGION,_GCS_BUCKET=gs://$GCS_BUCKET,_SERVICE_ACCOUNT=edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### Step 5: Deploy QNA Service

```bash
cd qna
gcloud builds submit --config=cloudbuild_cloudrun_qa.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-qna,_REGION=$REGION,_GCS_BUCKET=gs://$GCS_BUCKET,_SERVICE_ACCOUNT=edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com
```

### Step 6: Deploy Webapp (Optional)

```bash
cd webapp
gcloud builds submit --config=cloudbuild_cloudrun.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-webapp,_REGION=$REGION,_GCS_BUCKET=gs://$GCS_BUCKET,_SERVICE_ACCOUNT=edmonbrain-sa@$PROJECT_ID.iam.gserviceaccount.com
```

## GitHub Deployment

### Option 1: Manual Deployment

1. Push code to GitHub:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

2. Deploy manually using Cloud Build as shown above.

### Option 2: Automated CI/CD with GitHub Actions

See `.github/workflows/deploy.yml` for automated deployment.

## Data Source Configuration

### Twitter Sources

To add Twitter as a data source, send a message to the Pub/Sub topic:

```python
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "app_to_pubsub_edmonbrain")

# Load tweets from a user
message = "twitter://user:username"
publisher.publish(topic_path, message.encode())

# Load tweets with a hashtag
message = "twitter://hashtag:breakingnews"
publisher.publish(topic_path, message.encode())
```

### News Website Sources

To add news websites, send URLs to Pub/Sub:

```python
# RSS Feed
message = "https://www.bbc.com/news/rss.xml"
publisher.publish(topic_path, message.encode())

# Direct URL
message = "https://www.reuters.com/world/"
publisher.publish(topic_path, message.encode())
```

Or use the webapp interface to submit URLs.

## Monitoring and Logs

View logs:
```bash
# Chunker logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=edmonbrain-chunker" --limit 50

# QNA logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=edmonbrain-qna" --limit 50
```

## Troubleshooting

### Common Issues:

1. **Secret not found**: Ensure all secrets are created in Secret Manager
2. **Permission denied**: Check service account has necessary IAM roles
3. **Config file not found**: Ensure config.json is uploaded to GCS bucket root
4. **Twitter API rate limits**: Twitter API has rate limits - implement retry logic
5. **News website blocking**: Some sites may block scrapers - use RSS feeds when possible

## Cost Optimization

- Set `--min-instances 0` to scale to zero when not in use
- Use appropriate instance sizes (start with smaller instances)
- Monitor Pub/Sub message volume
- Consider using Cloud Scheduler for periodic data ingestion instead of continuous polling

## Next Steps

1. Set up Cloud Scheduler jobs to periodically fetch from Twitter and news sources
2. Configure monitoring and alerting
3. Set up backup and disaster recovery
4. Implement rate limiting for external APIs

