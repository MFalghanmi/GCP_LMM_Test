# Changes Summary: Twitter and News Website Integration

## What Was Changed

### 1. Added Twitter Data Source Support
- **File**: `chunker/loaders.py`
- **New Function**: `read_twitter_to_document()`
- **Features**:
  - Load tweets from user timelines
  - Search tweets by hashtag
  - Search tweets by query
  - Uses Twitter API v2 via Tweepy library

### 2. Added News Website Data Source Support
- **File**: `chunker/loaders.py`
- **New Functions**:
  - `read_rss_feed_to_document()` - Loads RSS feeds
  - `read_news_website_to_document()` - Smart loader that tries RSS first, then web scraping
- **Features**:
  - Automatic RSS feed detection from config.json
  - Fallback to web scraping if RSS not available
  - Supports multiple news sources

### 3. Updated Data Processing Pipeline
- **File**: `chunker/publish_to_pubsub_embed.py`
- **Changes**:
  - Added Twitter source detection (`twitter://`)
  - Added RSS feed detection
  - Enhanced news website handling with RSS preference

### 4. Updated Dependencies
- **File**: `chunker/requirements.txt`
- **Added**:
  - `tweepy>=4.14.0` - Twitter API client
  - `feedparser>=6.0.10` - RSS feed parser
  - `beautifulsoup4>=4.12.0` - Web scraping support

### 5. Updated Cloud Build Configuration
- **File**: `chunker/cloudbuild_cloudrun_chunker.yaml`
- **Added**: Twitter API secrets to Cloud Run deployment
  - `TWITTER_BEARER_TOKEN`
  - `TWITTER_API_KEY`
  - `TWITTER_API_SECRET`

### 6. Created Deployment Documentation
- **DEPLOYMENT_GUIDE.md** - Comprehensive deployment guide
- **REQUIREMENTS.md** - Complete requirements and setup
- **QUICK_START.md** - Quick start guide for deployment
- **config.example.json** - Example configuration file

### 7. Created CI/CD Pipeline
- **File**: `.github/workflows/deploy.yml`
- **Features**: Automated deployment to GCP on push to main/master

## What You Need to Do

### 1. Get Twitter API Credentials
1. Sign up at https://developer.twitter.com/
2. Create a new project/app
3. Generate Bearer Token
4. Store in GCP Secret Manager as `TWITTER_BEARER_TOKEN`

### 2. Update Configuration
1. Copy `config.example.json` to `config.json`
2. Customize news sources (add/remove websites)
3. Customize Twitter sources (add users/hashtags to monitor)
4. Upload to GCS bucket root

### 3. Create GCP Secrets
Run these commands (update with your values):
```bash
echo -n "your-twitter-bearer-token" | gcloud secrets create TWITTER_BEARER_TOKEN --data-file=-
echo -n "your-twitter-api-key" | gcloud secrets create TWITTER_API_KEY --data-file=-
echo -n "your-twitter-api-secret" | gcloud secrets create TWITTER_API_SECRET --data-file=-
```

### 4. Deploy to GitHub
```bash
git add .
git commit -m "Add Twitter and news website data sources"
git push origin main
```

### 5. Deploy to GCP
Follow the steps in `QUICK_START.md` or `DEPLOYMENT_GUIDE.md`

## How to Use

### Loading Twitter Data

Send messages to Pub/Sub topic `app_to_pubsub_<vector_name>`:

```python
# Load user timeline
"twitter://user:BBCNews"

# Load hashtag tweets
"twitter://hashtag:breakingnews"

# Search tweets
"twitter://search:AI news"
```

### Loading News Website Data

```python
# RSS Feed (preferred)
"http://feeds.bbci.co.uk/news/rss.xml"

# Direct URL (will try RSS from config.json first)
"https://www.bbc.com/news"
```

## Supported News Sources (Example)

The example config includes:
1. **BBC News** - http://feeds.bbci.co.uk/news/rss.xml
2. **Reuters** - https://www.reuters.com/rssFeed/worldNews
3. **CNN** - http://rss.cnn.com/rss/edition.rss
4. **The Guardian** - https://www.theguardian.com/world/rss

You can add more by editing `config.json` in your GCS bucket.

## Important Notes

1. **Twitter API Limits**: 
   - Free tier has rate limits
   - Implement retry logic for production
   - Consider caching results

2. **News Website Scraping**:
   - Some sites may block scrapers
   - Always prefer RSS feeds when available
   - Respect robots.txt and rate limits

3. **Costs**:
   - Twitter API: Free tier available
   - GCP services: Pay per use
   - Monitor costs in GCP Console

4. **Security**:
   - Never commit API keys to git
   - Use GCP Secret Manager
   - Rotate keys regularly

## Next Steps

1. Review `QUICK_START.md` for deployment
2. Customize `config.json` with your sources
3. Set up Cloud Scheduler for periodic data ingestion
4. Monitor logs and costs
5. Adjust configuration as needed

## Files Modified

- `chunker/loaders.py` - Added Twitter and RSS loaders
- `chunker/publish_to_pubsub_embed.py` - Added source detection
- `chunker/requirements.txt` - Added dependencies
- `chunker/cloudbuild_cloudrun_chunker.yaml` - Added Twitter secrets

## Files Created

- `DEPLOYMENT_GUIDE.md` - Full deployment guide
- `REQUIREMENTS.md` - Requirements documentation
- `QUICK_START.md` - Quick start guide
- `config.example.json` - Example configuration
- `.github/workflows/deploy.yml` - CI/CD pipeline
- `CHANGES_SUMMARY.md` - This file

## Testing

Test locally before deploying:

```python
# Test Twitter loader
from chunker.loaders import read_twitter_to_document
docs = read_twitter_to_document("twitter://user:BBCNews", {"test": True})
print(f"Loaded {len(docs)} tweets")

# Test RSS loader
from chunker.loaders import read_rss_feed_to_document
docs = read_rss_feed_to_document("http://feeds.bbci.co.uk/news/rss.xml", {"test": True})
print(f"Loaded {len(docs)} articles")
```

## Support

For issues or questions:
1. Check logs: `gcloud logging read ...`
2. Review deployment guide
3. Check GCP service status
4. Verify secrets are correctly set

