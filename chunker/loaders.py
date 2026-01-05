from langchain.document_loaders.unstructured import UnstructuredFileLoader
from langchain.document_loaders.unstructured import UnstructuredAPIFileLoader
from langchain.document_loaders import UnstructuredURLLoader
from langchain.document_loaders.git import GitLoader
from langchain.document_loaders import GoogleDriveLoader
from langchain.schema import Document
from utils.config import load_config
from googleapiclient.errors import HttpError

import logging
import pathlib
import os
import shutil
from urllib.parse import urlparse, unquote
import tempfile
import time
import requests
import feedparser
from datetime import datetime

UNSTRUCTURED_KEY=os.getenv('UNSTRUCTURED_KEY')

# utility functions
def convert_to_txt(file_path):
    file_dir, file_name = os.path.split(file_path)
    file_base, file_ext = os.path.splitext(file_name)
    txt_file = os.path.join(file_dir, f"{file_base}.txt")
    shutil.copyfile(file_path, txt_file)
    return txt_file


from pydantic import BaseModel, Field
from typing import Optional

class MyGoogleDriveLoader(GoogleDriveLoader):
    url: Optional[str] = Field(None)

    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs, file_ids=['dummy']) # Pass dummy value
        self.url = url

    def _extract_id(self, url):
        parsed_url = urlparse(unquote(url))
        path_parts = parsed_url.path.split('/')
        
        # Iterate over the parts
        for part in path_parts:
            # IDs are typically alphanumeric and at least a few characters long
            # So let's say that to be an ID, a part has to be at least 15 characters long
            if all(char.isalnum() or char in ['_', '-'] for char in part) and len(part) >= 15:
                return part
        
        # Return None if no ID was found
        return None

    def load_from_url(self, url: str):
        id = self._extract_id(url)

        from googleapiclient.discovery import build

        # Identify type of URL
        try:
            service = build("drive", "v3", credentials=self._load_credentials())
            file = service.files().get(fileId=id).execute()
        except HttpError as err:
            logging.error(f"Error loading file {url}: {str(err)}")
            raise

        mime_type = file["mimeType"]

        if "folder" in mime_type:
            # If it's a folder, load documents from the folder
            return self._load_documents_from_folder(id)
        else:
            # If it's not a folder, treat it as a single file
            if mime_type == "application/vnd.google-apps.document":
                return [self._load_document_from_id(id)]
            elif mime_type == "application/vnd.google-apps.spreadsheet":
                return self._load_sheet_from_id(id)
            elif mime_type == "application/pdf":
                return [self._load_file_from_id(id)]
            else:
                return []

def ignore_files(filepath):
    """Returns True if the given path's file extension is found within 
    config.json "code_extensions" array
    Returns False if not
    """
    # Load the configuration
    config = load_config("config.json")

    code_extensions = config.get("code_extensions", [])

    lower_filepath = filepath.lower()
    # TRUE if on the list, FALSE if not
    return any(lower_filepath.endswith(ext) for ext in code_extensions)

def read_git_repo(clone_url, branch="main", metadata=None):
    logging.info(f"Reading git repo from {clone_url} - {branch}")
    GIT_PAT = os.getenv('GIT_PAT', None)
    if GIT_PAT is None:
        logging.warning("No GIT_PAT is specified, won't be able to clone private git repositories")
    else:
        clone_url = clone_url.replace('https://', f'https://{GIT_PAT}@')
        logging.info("Using private GIT_PAT")

    with tempfile.TemporaryDirectory() as tmp_dir:
            try:    
                loader = GitLoader(repo_path=tmp_dir, 
                                   clone_url=clone_url, 
                                   branch=branch,
                                   file_filter=ignore_files)
            except Exception as err:
                logging.error(f"Failed to load repository: {str(err)}")
                return None
            docs = loader.load()

            if not docs:
                return None
            
            if metadata is not None:
                for doc in docs:
                    doc.metadata.update(metadata)
            
    logging.info(f"GitLoader read {len(docs)} doc(s) from {clone_url}")
        
    return docs


def read_gdrive_to_document(url: str, metadata: dict = None):

    logging.info(f"Reading gdrive doc from {url}")

    loader = MyGoogleDriveLoader(url=url)
    docs = loader.load_from_url(url)
    
    if docs is None or len(docs) == 0:
        return None
    
    if metadata is not None:
        for doc in docs:
            doc.metadata.update(metadata)
    
    logging.info(f"GoogleDriveLoader read {len(docs)} doc(s) from {url}")

    return docs

def read_url_to_document(url: str, metadata: dict = None):
    
    loader = UnstructuredURLLoader(urls=[url])
    docs = loader.load()
    if metadata is not None:
        for doc in docs:
            doc.metadata.update(metadata)
    
    logging.info(f"UnstructuredURLLoader docs: {docs}")
    
    return docs

def read_file_to_document(gs_file: pathlib.Path, split=False, metadata: dict = None):
    
    docs = []
    done = False
    pdf_path = pathlib.Path(gs_file)
    if pdf_path.suffix == ".pdf":
        from chunker.pdfs import read_pdf_file
        local_doc = read_pdf_file(pdf_path, metadata=metadata)
        if local_doc is not None:
            docs.append(local_doc)
            done = True
    
    if not done:
        try:
            logging.info(f"Sending {gs_file} to UnstructuredAPIFileLoader")
            UNSTRUCTURED_URL = os.getenv("UNSTRUCTURED_URL", None)
            if UNSTRUCTURED_URL is not None:
                logging.debug(f"Found UNSTRUCTURED_URL: {UNSTRUCTURED_URL}")
                the_endpoint = f"{UNSTRUCTURED_URL}/general/v0/general"
                loader = UnstructuredAPIFileLoader(gs_file, url=the_endpoint)
            else:
                loader = UnstructuredAPIFileLoader(gs_file, api_key=UNSTRUCTURED_KEY)
            
            if split:
                # only supported for some file types
                docs = loader.load_and_split()
            else:
                start = time.time()
                docs = loader.load() # this takes a long time 30m+ for big PDF files
                end = time.time()
                elapsed_time = round((end - start) / 60, 2)
                logging.info(f"Loaded docs for {gs_file} from UnstructuredAPIFileLoader took {elapsed_time} mins")
        except ValueError as e:
            logging.info(f"Error for {gs_file} from UnstructuredAPIFileLoader: {str(e)}")
            if "file type is not supported in partition" in str(e):
                logging.info("trying locally via .txt conversion")
                txt_file = None
                try:
                    # Convert the file to .txt and try again
                    txt_file = convert_to_txt(gs_file)
                    loader = UnstructuredFileLoader(txt_file, mode="elements")
                    if split:
                        docs = loader.load_and_split()
                    else:
                        docs = loader.load()

                except Exception as inner_e:
                    raise Exception("An error occurred during txt conversion or loading.") from inner_e

                finally:
                    # Ensure cleanup happens if txt_file was created
                    if txt_file is not None and os.path.exists(txt_file):
                        os.remove(txt_file)

    for doc in docs:
        #doc.metadata["file_sha1"] = file_sha1
        logging.info(f"doc_content: {doc.page_content[:30]} - length: {len(doc.page_content)}")
        if metadata is not None:
            doc.metadata.update(metadata)
    
    logging.info(f"gs_file:{gs_file} read into {len(docs)} docs")

    return docs

def read_twitter_to_document(twitter_source: str, metadata: dict = None):
    """
    Load tweets from Twitter API.
    Supports:
    - twitter://user:username - Load user timeline
    - twitter://hashtag:hashtag - Load tweets with hashtag
    - twitter://search:query - Search tweets
    
    Args:
        twitter_source: Twitter source string in format twitter://type:value
        metadata: Optional metadata to add to documents
    """
    import tweepy
    
    logging.info(f"Reading Twitter source: {twitter_source}")
    
    # Parse Twitter source
    if not twitter_source.startswith("twitter://"):
        logging.error(f"Invalid Twitter source format: {twitter_source}")
        return None
    
    source_type, source_value = twitter_source.replace("twitter://", "").split(":", 1)
    
    # Get Twitter credentials
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
    if not TWITTER_BEARER_TOKEN:
        logging.error("TWITTER_BEARER_TOKEN not found in environment variables")
        return None
    
    try:
        # Initialize Twitter API v2 client
        client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
        
        docs = []
        tweets = []
        
        if source_type == "user":
            # Get user timeline
            try:
                user = client.get_user(username=source_value)
                if user.data:
                    tweets_response = client.get_users_tweets(
                        id=user.data.id,
                        max_results=100,  # Twitter API v2 limit
                        tweet_fields=['created_at', 'public_metrics', 'text']
                    )
                    if tweets_response.data:
                        tweets = tweets_response.data
            except Exception as e:
                logging.error(f"Error fetching user timeline for {source_value}: {str(e)}")
                return None
                
        elif source_type == "hashtag":
            # Search tweets by hashtag (remove # if present)
            hashtag = source_value.lstrip('#')
            try:
                tweets_response = client.search_recent_tweets(
                    query=f"#{hashtag} -is:retweet",
                    max_results=100,
                    tweet_fields=['created_at', 'public_metrics', 'text', 'author_id']
                )
                if tweets_response.data:
                    tweets = tweets_response.data
            except Exception as e:
                logging.error(f"Error searching hashtag {hashtag}: {str(e)}")
                return None
                
        elif source_type == "search":
            # Search tweets by query
            try:
                tweets_response = client.search_recent_tweets(
                    query=source_value,
                    max_results=100,
                    tweet_fields=['created_at', 'public_metrics', 'text', 'author_id']
                )
                if tweets_response.data:
                    tweets = tweets_response.data
            except Exception as e:
                logging.error(f"Error searching query {source_value}: {str(e)}")
                return None
        else:
            logging.error(f"Unknown Twitter source type: {source_type}")
            return None
        
        # Convert tweets to documents
        for tweet in tweets:
            tweet_metadata = {
                "source": twitter_source,
                "type": "twitter",
                "twitter_id": str(tweet.id),
                "created_at": tweet.created_at.isoformat() if hasattr(tweet, 'created_at') and tweet.created_at else None,
            }
            
            if hasattr(tweet, 'public_metrics'):
                tweet_metadata["retweet_count"] = tweet.public_metrics.get('retweet_count', 0)
                tweet_metadata["like_count"] = tweet.public_metrics.get('like_count', 0)
                tweet_metadata["reply_count"] = tweet.public_metrics.get('reply_count', 0)
            
            if metadata:
                tweet_metadata.update(metadata)
            
            # Create document from tweet text
            doc = Document(
                page_content=tweet.text,
                metadata=tweet_metadata
            )
            docs.append(doc)
        
        logging.info(f"TwitterLoader read {len(docs)} tweet(s) from {twitter_source}")
        return docs
        
    except Exception as e:
        logging.error(f"Error loading Twitter data: {str(e)}")
        return None

def read_rss_feed_to_document(rss_url: str, metadata: dict = None):
    """
    Load content from RSS feed.
    
    Args:
        rss_url: URL of the RSS feed
        metadata: Optional metadata to add to documents
    """
    logging.info(f"Reading RSS feed from {rss_url}")
    
    try:
        # Parse RSS feed
        feed = feedparser.parse(rss_url)
        
        if not feed.entries:
            logging.warning(f"No entries found in RSS feed: {rss_url}")
            return None
        
        docs = []
        for entry in feed.entries:
            # Combine title and summary/content
            content_parts = []
            if hasattr(entry, 'title'):
                content_parts.append(f"Title: {entry.title}")
            if hasattr(entry, 'summary'):
                content_parts.append(entry.summary)
            elif hasattr(entry, 'content'):
                # Some feeds use content instead of summary
                if isinstance(entry.content, list) and len(entry.content) > 0:
                    content_parts.append(entry.content[0].value)
                else:
                    content_parts.append(str(entry.content))
            
            page_content = "\n\n".join(content_parts)
            
            entry_metadata = {
                "source": rss_url,
                "type": "rss_feed",
                "feed_title": feed.feed.get('title', 'Unknown'),
            }
            
            if hasattr(entry, 'link'):
                entry_metadata["url"] = entry.link
            if hasattr(entry, 'published'):
                entry_metadata["published"] = entry.published
            if hasattr(entry, 'author'):
                entry_metadata["author"] = entry.author
            
            if metadata:
                entry_metadata.update(metadata)
            
            doc = Document(
                page_content=page_content,
                metadata=entry_metadata
            )
            docs.append(doc)
        
        logging.info(f"RSSLoader read {len(docs)} article(s) from {rss_url}")
        return docs
        
    except Exception as e:
        logging.error(f"Error loading RSS feed {rss_url}: {str(e)}")
        return None

def read_news_website_to_document(url: str, metadata: dict = None):
    """
    Load content from a news website.
    First tries RSS feed if available, then falls back to web scraping.
    
    Args:
        url: URL of the news website
        metadata: Optional metadata to add to documents
    """
    logging.info(f"Reading news website from {url}")
    
    # Try to detect RSS feed
    config = load_config("config.json")
    news_sources = config.get("news_sources", [])
    
    # Check if URL matches a configured news source with RSS
    for source in news_sources:
        if source.get("url") == url or url.startswith(source.get("url", "")):
            rss_url = source.get("rss")
            if rss_url:
                logging.info(f"Found RSS feed for {url}: {rss_url}")
                return read_rss_feed_to_document(rss_url, metadata)
    
    # Fall back to regular URL loader
    logging.info(f"Falling back to UnstructuredURLLoader for {url}")
    return read_url_to_document(url, metadata)