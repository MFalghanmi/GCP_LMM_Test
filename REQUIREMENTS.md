# Requirements and Setup Guide

## Overview

This document outlines all requirements needed to deploy the Edmonbrain LLM application with Twitter and news website data sources.

## System Requirements

### Python Version
- Python 3.9 or higher

### GCP Services Required
1. **Cloud Run** - Container hosting
2. **Cloud Storage** - File storage
3. **Pub/Sub** - Message queuing
4. **Secret Manager** - API key storage
5. **Cloud Build** - CI/CD (optional)
6. **BigQuery** - Database (if using structured data)
7. **Vertex AI** - LLM models (if using Vertex AI)

## API Keys and Credentials Required

### Twitter API (Required for Twitter data source)
1. **Twitter Developer Account**
   - Sign up at: https://developer.twitter.com/
   - Create a new project/app
   - Generate Bearer Token (required)
   - Optional: API Key and Secret for advanced features

2. **Twitter API Limits**
   - Free tier: 1,500 tweets/month for user timeline
   - Free tier: 10,000 tweets/month for search
   - Rate limits apply - implement retry logic

### News Websites
- No API keys required for RSS feeds
- Some websites may require user-agent headers
- Consider rate limiting to avoid being blocked

### Existing API Keys
- **Unstructured.io API Key**: https://www.unstructured.io/api-key/
- **LangChain API Key**: https://smith.langchain.com/settings (or dummy value)
- **OpenAI API Key**: If using OpenAI models
- **Supabase Credentials**: If using Supabase vector store
- **GitHub PAT**: If loading private repositories

## Environment Variables

### Required Environment Variables

Set these in GCP Secret Manager:

```
TWITTER_BEARER_TOKEN          # Twitter API Bearer Token (required for Twitter)
UNSTRUCTURED_KEY              # Unstructured.io API key
LANGCHAIN_API_KEY              # LangChain API key (or dummy value)
GCS_BUCKET                     # Google Cloud Storage bucket name
SUPABASE_URL                   # Supabase project URL (if using)
SUPABASE_KEY                   # Supabase API key (if using)
OPENAI_API_KEY                 # OpenAI API key (if using OpenAI)
DB_CONNECTION_STRING           # Database connection string
GIT_PAT                        # GitHub Personal Access Token (if using private repos)
```

### Optional Environment Variables

```
TWITTER_API_KEY                # Twitter API Key (optional)
TWITTER_API_SECRET             # Twitter API Secret (optional)
UNSTRUCTURED_URL               # Self-hosted Unstructured service URL
EMBED_URL                      # Embedder service URL
QNA_URL                        # QNA service URL
```

## GCP Project Setup

### 1. Enable Required APIs

```bash
gcloud services enable \
  run.googleapis.com \
  storage.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com
```

### 2. Create Service Account

```bash
gcloud iam service-accounts create edmonbrain-sa \
  --display-name="Edmonbrain Service Account"
```

### 3. Grant Permissions

```bash
PROJECT_ID=your-project-id
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

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.dataEditor"
```

### 4. Create Secrets

```bash
# Twitter secrets
echo -n "your-twitter-bearer-token" | gcloud secrets create TWITTER_BEARER_TOKEN --data-file=-
echo -n "your-twitter-api-key" | gcloud secrets create TWITTER_API_KEY --data-file=-
echo -n "your-twitter-api-secret" | gcloud secrets create TWITTER_API_SECRET --data-file=-

# Other secrets
echo -n "your-unstructured-key" | gcloud secrets create UNSTRCUTURED_KEY --data-file=-
echo -n "your-langchain-key" | gcloud secrets create LANGCHAIN_API_KEY --data-file=-
# ... add other secrets
```

### 5. Create GCS Bucket

```bash
gsutil mb -p $PROJECT_ID -l $REGION gs://$GCS_BUCKET
gsutil cp config.json gs://$GCS_BUCKET/config.json
```

## Configuration File

Create `config.json` in your GCS bucket with:

1. **News Sources**: List of news websites with RSS feeds
2. **Twitter Sources**: List of Twitter users/hashtags to monitor
3. **LLM Configuration**: Model settings for each vector store

See `config.example.json` for a complete example.

## Data Source Configuration

### Twitter Sources

Supported formats:
- `twitter://user:username` - Load user timeline
- `twitter://hashtag:hashtag` - Load tweets with hashtag (without #)
- `twitter://search:query` - Search tweets

Example:
```python
# Load tweets from a user
message = "twitter://user:BBCNews"

# Load tweets with a hashtag
message = "twitter://hashtag:breakingnews"

# Search tweets
message = "twitter://search:AI news"
```

### News Website Sources

Supported formats:
- RSS Feed URL: `https://feeds.bbci.co.uk/news/rss.xml`
- News Website URL: `https://www.bbc.com/news` (will try RSS first)

The system will:
1. Check config.json for RSS feed URL
2. If found, use RSS feed
3. Otherwise, scrape the website

## GitHub Setup

### GitHub Secrets (for CI/CD)

If using GitHub Actions, add these secrets:

1. **GCP_PROJECT_ID** - Your GCP project ID
2. **GCP_REGION** - Your GCP region (e.g., us-central1)
3. **GCS_BUCKET** - Your GCS bucket name
4. **GCP_SERVICE_ACCOUNT** - Service account email
5. **GCP_SA_KEY** - Service account JSON key (for authentication)

### GitHub Actions Setup

1. Go to your repository Settings > Secrets and variables > Actions
2. Add all required secrets
3. Push to main/master branch to trigger deployment

## Cost Considerations

### GCP Costs
- **Cloud Run**: Pay per request, scales to zero
- **Cloud Storage**: Storage and egress costs
- **Pub/Sub**: Message volume costs
- **Secret Manager**: Free for first 6 secrets, then $0.06/secret/month

### API Costs
- **Twitter API**: Free tier available, paid tiers for higher limits
- **OpenAI API**: Pay per token
- **Unstructured.io**: Free tier available, paid for higher usage

### Optimization Tips
- Set Cloud Run to scale to zero (`--min-instances 0`)
- Use appropriate instance sizes
- Implement caching where possible
- Monitor API rate limits

## Testing

### Local Testing

1. Install dependencies:
```bash
pip install -r chunker/requirements.txt
```

2. Set environment variables:
```bash
export TWITTER_BEARER_TOKEN=your-token
export GCS_BUCKET=your-bucket
# ... other env vars
```

3. Test Twitter loader:
```python
from chunker.loaders import read_twitter_to_document
docs = read_twitter_to_document("twitter://user:BBCNews")
print(docs)
```

4. Test RSS loader:
```python
from chunker.loaders import read_rss_feed_to_document
docs = read_rss_feed_to_document("http://feeds.bbci.co.uk/news/rss.xml")
print(docs)
```

## Troubleshooting

### Common Issues

1. **Twitter API Rate Limits**
   - Implement exponential backoff
   - Cache results
   - Use Twitter API v2 efficiently

2. **News Website Blocking**
   - Use RSS feeds when available
   - Set proper user-agent headers
   - Implement rate limiting

3. **Secret Not Found**
   - Verify secret name matches exactly
   - Check service account has Secret Manager access
   - Ensure secret exists in correct project

4. **Config File Not Found**
   - Verify config.json is in GCS bucket root
   - Check bucket name is correct
   - Verify service account has Storage access

## Next Steps

1. Set up Cloud Scheduler for periodic data ingestion
2. Configure monitoring and alerting
3. Set up backup and disaster recovery
4. Implement rate limiting and caching
5. Monitor costs and optimize

