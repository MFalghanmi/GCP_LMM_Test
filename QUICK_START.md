# Quick Start Guide

This guide will help you quickly deploy the application with Twitter and news website data sources.

## Prerequisites Checklist

- [ ] GCP account with billing enabled
- [ ] GitHub account
- [ ] Twitter Developer account (for Twitter API)
- [ ] Python 3.9+ installed locally (for testing)

## Step 1: Get Twitter API Credentials

1. Go to https://developer.twitter.com/
2. Sign up/Sign in
3. Create a new project/app
4. Generate Bearer Token
5. Save the token - you'll need it for GCP Secret Manager

## Step 2: Set Up GCP Project

```bash
# Set variables
export PROJECT_ID=your-project-id
export REGION=us-central1
export GCS_BUCKET=your-bucket-name

# Enable APIs
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com

# Create service account
gcloud iam service-accounts create edmonbrain-sa \
  --display-name="Edmonbrain Service Account"

# Grant permissions
SA_EMAIL=edmonbrain-sa@${PROJECT_ID}.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/pubsub.admin"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/aiplatform.user"
```

## Step 3: Create Secrets in GCP

```bash
# Twitter (required)
echo -n "your-twitter-bearer-token" | gcloud secrets create TWITTER_BEARER_TOKEN --data-file=-

# Other required secrets (update with your values)
echo -n "your-unstructured-key" | gcloud secrets create UNSTRCUTURED_KEY --data-file=-
echo -n "your-openai-key" | gcloud secrets create OPENAI_API_KEY --data-file=-
echo -n "your-supabase-url" | gcloud secrets create SUPABASE_URL --data-file=-
echo -n "your-supabase-key" | gcloud secrets create SUPABASE_KEY --data-file=-
echo -n "your-langchain-key" | gcloud secrets create LANGCHAIN_API_KEY --data-file=-
```

## Step 4: Create GCS Bucket and Upload Config

```bash
# Create bucket
gsutil mb -p $PROJECT_ID -l $REGION gs://$GCS_BUCKET

# Create config.json (copy from config.example.json and customize)
# Then upload it
gsutil cp config.json gs://$GCS_BUCKET/config.json
```

## Step 5: Deploy to GitHub

```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit with Twitter and news sources"

# Add remote and push
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

## Step 6: Set Up GitHub Secrets (for CI/CD)

1. Go to GitHub repository > Settings > Secrets and variables > Actions
2. Add these secrets:
   - `GCP_PROJECT_ID`: Your GCP project ID
   - `GCP_REGION`: Your region (e.g., us-central1)
   - `GCS_BUCKET`: Your bucket name
   - `GCP_SERVICE_ACCOUNT`: edmonbrain-sa@your-project.iam.gserviceaccount.com
   - `GCP_SA_KEY`: Service account JSON key (download from GCP Console)

## Step 7: Deploy Services

### Option A: Manual Deployment

```bash
# Deploy prebuild
cd prebuild
gcloud builds submit --config=cloudbuild_prebuild.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_GCS_BUCKET=gs://$GCS_BUCKET

# Deploy chunker
cd ../chunker
gcloud builds submit --config=cloudbuild_cloudrun_chunker.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-chunker,_REGION=$REGION,_GCS_BUCKET=gs://$GCS_BUCKET,_SERVICE_ACCOUNT=$SA_EMAIL

# Deploy embedder
cd ../embedder
gcloud builds submit --config=cloudbuild_cloudrun_embedder.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-embedder,_REGION=$REGION,_GCS_BUCKET=gs://$GCS_BUCKET,_SERVICE_ACCOUNT=$SA_EMAIL

# Deploy QNA
cd ../qna
gcloud builds submit --config=cloudbuild_cloudrun_qa.yaml \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-qna,_REGION=$REGION,_GCS_BUCKET=gs://$GCS_BUCKET,_SERVICE_ACCOUNT=$SA_EMAIL
```

### Option B: Automated (GitHub Actions)

Just push to main branch - GitHub Actions will deploy automatically!

## Step 8: Test Data Ingestion

### Test Twitter Source

```python
from google.cloud import pubsub_v1

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, "app_to_pubsub_edmonbrain")

# Load tweets from a user
message = "twitter://user:BBCNews"
publisher.publish(topic_path, message.encode())
```

### Test News Website

```python
# RSS Feed
message = "http://feeds.bbci.co.uk/news/rss.xml"
publisher.publish(topic_path, message.encode())

# Or direct URL (will try RSS first)
message = "https://www.bbc.com/news"
publisher.publish(topic_path, message.encode())
```

## Step 9: Verify Deployment

```bash
# Check Cloud Run services
gcloud run services list --region=$REGION

# Check logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=edmonbrain-chunker" --limit 10
```

## Configuration

Edit `config.json` in your GCS bucket to customize:

1. **News Sources**: Add/remove news websites
2. **Twitter Sources**: Add Twitter users/hashtags to monitor
3. **LLM Settings**: Configure models and prompts

## Next Steps

1. Set up Cloud Scheduler to periodically fetch data:
   ```bash
   gcloud scheduler jobs create pubsub fetch-twitter \
     --schedule="0 */6 * * *" \
     --topic=app_to_pubsub_edmonbrain \
     --message-body="twitter://user:BBCNews" \
     --location=$REGION
   ```

2. Monitor costs in GCP Console
3. Set up alerts for errors
4. Customize prompts in config.json

## Troubleshooting

- **Twitter API errors**: Check rate limits and Bearer Token
- **Config not found**: Verify config.json is in bucket root
- **Permission errors**: Check service account roles
- **Deployment fails**: Check Cloud Build logs

For detailed information, see:
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Full deployment guide
- [REQUIREMENTS.md](REQUIREMENTS.md) - Complete requirements list

