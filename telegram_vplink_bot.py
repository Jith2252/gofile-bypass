import re
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import logging
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import urllib.parse

# Load environment variables from config.env
load_dotenv('config.env')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SOURCE_CHANNEL_ID = int(os.getenv('SOURCE_CHANNEL_ID'))  # Channel A
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID'))  # Channel B

# VPLink API credentials
VPLINK_API1_KEY = os.getenv('VPLINK_API1_KEY')  # For retrieving destination URL
VPLINK_API2_KEY = os.getenv('VPLINK_API2_KEY')  # For creating new short URL

# VPLink API endpoints
VPLINK_EXPAND_API = os.getenv('VPLINK_EXPAND_API', 'https://vplink.in/api')
VPLINK_SHORTEN_API = os.getenv('VPLINK_SHORTEN_API', 'https://vplink.in/api')


def extract_vplink_urls(text):
    """Extract all vplink.in URLs from text"""
    if not text:
        return []
    # Match vplink.in URLs
    pattern = r'https?://(?:www\.)?vplink\.in/[A-Za-z0-9]+'
    return re.findall(pattern, text)


def get_destination_url(short_url, api_key):
    """
    Retrieve the destination URL from vplink short URL using VPLink API 1
    If API fails, fallback to HTML parsing
    """
    try:
        logger.info(f"Attempting to get destination URL for: {short_url} using API")
        
        # Extract the short code from URL (e.g., A8ne5 from https://vplink.in/A8ne5)
        short_code = short_url.split('/')[-1]
        
        # Try multiple API endpoints to expand the URL
        api_endpoints = [
            f"https://vplink.in/api?api={api_key}&url={short_url}",
            f"https://vplink.in/api?api={api_key}&url=vplink.in/{short_code}",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        for endpoint in api_endpoints:
            try:
                logger.info(f"Trying API endpoint: {endpoint}")
                response = requests.get(endpoint, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        logger.info(f"API Response: {data}")
                        
                        # Check if we got a destination URL
                        if data.get('status') == 'success':
                            # API might return the shortened URL, try to extract or use shortenedUrl field
                            dest = data.get('destination') or data.get('destinationUrl') or data.get('longUrl')
                            if dest:
                                logger.info(f"Got destination from API: {dest}")
                                return dest
                    except:
                        # Response might be plain text
                        if response.text and 'https://' in response.text:
                            dest = response.text.strip()
                            logger.info(f"Got destination from API (text): {dest}")
                            return dest
            except Exception as e:
                logger.warning(f"API endpoint failed: {e}")
                continue
        
        # Fallback: Parse HTML page to find destination
        logger.info(f"API failed, falling back to HTML parsing for: {short_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        # Known shortener domains to keep following
        shortener_domains = ['vplink.in', 'ohcar2022.co.in', 'ohcar', 'bit.ly', 'tinyurl.com', 'shorturl.at', 'clk.sh']
        
        def extract_url(url, depth=0, max_depth=10):
            """Recursively extract destination URL from shortener pages"""
            if depth >= max_depth:
                logger.warning(f"Max depth {max_depth} reached")
                return url
            
            logger.info(f"[Depth {depth}] Fetching: {url}")
            
            # Check if this is already a final destination (not a shortener)
            is_shortener = any(domain in url for domain in shortener_domains)
            if not is_shortener:
                logger.info(f"[Depth {depth}] Final destination reached: {url}")
                return url
            
            try:
                response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
                
                # If we got redirected to a non-shortener, return it
                if response.url != url and not any(domain in response.url for domain in shortener_domains):
                    logger.info(f"[Depth {depth}] Redirected to final: {response.url}")
                    return response.url
                
                # Parse the HTML to find the destination URL
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Method 1: Look for skip button or direct link
                skip_link = soup.find('a', {'id': 'skip_button'}) or soup.find('a', {'class': 'skip'}) or soup.find('a', string=re.compile('skip|continue|get link', re.IGNORECASE))
                if skip_link and skip_link.get('href'):
                    destination = skip_link.get('href')
                    if not destination.startswith('http'):
                        parsed = urllib.parse.urlparse(url)
                        destination = f"{parsed.scheme}://{parsed.netloc}{destination}"
                    logger.info(f"[Depth {depth}] Found in skip button: {destination}")
                    return extract_url(destination, depth + 1, max_depth)
                
                # Method 2: Look for meta refresh
                meta_refresh = soup.find('meta', {'http-equiv': 'refresh'})
                if meta_refresh:
                    content = meta_refresh.get('content', '')
                    match = re.search(r'url=(.+)', content, re.IGNORECASE)
                    if match:
                        destination = match.group(1).strip('\'"')
                        logger.info(f"[Depth {depth}] Found in meta refresh: {destination}")
                        return extract_url(destination, depth + 1, max_depth)
                
                # Method 3: Look for any direct file hosting links (gofile, mediafire, etc.)
                destination_domains = ['gofile.io', 'mediafire.com', 'drive.google.com', 'mega.nz', 'dropbox.com']
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    if any(domain in href for domain in destination_domains):
                        logger.info(f"[Depth {depth}] Found destination link in anchor: {href}")
                        return href
                
                # Method 4: Look for iframes with destination URLs
                for iframe in soup.find_all('iframe'):
                    src = iframe.get('src')
                    if src:
                        for domain in destination_domains:
                            if domain in src:
                                logger.info(f"[Depth {depth}] Found in iframe: {src}")
                                return src
                
                # Method 5: Look for JavaScript redirects (various patterns)
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        # Search for any gofile.io URLs in JavaScript
                        gofile_match = re.search(r'(["\']https://gofile\.io/d/[A-Za-z0-9]+["\'])', script.string)
                        if gofile_match:
                            destination = gofile_match.group(1).strip('\'"')
                            logger.info(f"[Depth {depth}] Found gofile URL in JavaScript: {destination}")
                            return destination
                        
                        # Look for window.location patterns
                        patterns = [
                            r'(?:window\.location|location\.href)\s*=\s*["\']([^"\']+)["\']',
                            r'window\.open\(["\']([^"\']+)["\']',
                            r'redirect\(["\']([^"\']+)["\']',
                            r'fetch\(["\']([^"\']+)["\']',
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, script.string)
                            if match:
                                destination = match.group(1)
                                
                                # Skip self-references
                                if destination in ['#', 'javascript:void(0)', '']:
                                    continue
                                
                                # Make absolute URL if relative
                                if destination.startswith('/'):
                                    parsed = urllib.parse.urlparse(url)
                                    destination = f"{parsed.scheme}://{parsed.netloc}{destination}"
                                
                                logger.info(f"[Depth {depth}] Found in JavaScript pattern: {destination}")
                                return extract_url(destination, depth + 1, max_depth)
                
                # Method 6: Look in all text for gofile URLs (last resort)
                page_text = response.text
                gofile_urls = re.findall(r'https://gofile\.io/d/[A-Za-z0-9]+', page_text)
                if gofile_urls:
                    destination = gofile_urls[0]
                    logger.info(f"[Depth {depth}] Found gofile URL in page content: {destination}")
                    return destination
                
                # Method 7: Look for encoded/escaped URLs
                escaped_urls = re.findall(r'(https?:\\\/\\\/[^\s\\"]+)', page_text)
                for escaped_url in escaped_urls:
                    unescaped = escaped_url.replace('\\/', '/')
                    if any(domain in unescaped for domain in destination_domains):
                        logger.info(f"[Depth {depth}] Found escaped URL: {unescaped}")
                        return extract_url(unescaped, depth + 1, max_depth)
                
                logger.warning(f"[Depth {depth}] No destination found in: {url}")
                return url
                
            except Exception as e:
                logger.error(f"[Depth {depth}] Error: {e}")
                return url
        
        # Start the recursive extraction
        final_url = extract_url(short_url)
        logger.info(f"Final destination URL: {final_url}")
        return final_url
        
    except Exception as e:
        logger.error(f"Error getting destination URL for {short_url}: {e}")
        return None


def create_short_url(destination_url, api_key):
    """
    Create a new vplink short URL using API 2
    VPLink API format: https://vplink.in/api?api=YOUR_API_KEY&url=DESTINATION_URL
    """
    try:
        # VPLink API endpoint
        api_url = f"https://vplink.in/api?api={api_key}&url={destination_url}"
        
        response = requests.get(api_url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            # VPLink returns: {"status":"success","shortenedUrl":"https://vplink.in/xxxxx"}
            if data.get('status') == 'success':
                short_url = data.get('shortenedUrl')
                logger.info(f"Created short URL: {short_url}")
                return short_url
            else:
                logger.error(f"API returned error: {data}")
                return None
        else:
            logger.error(f"Failed to create short URL: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating short URL for {destination_url}: {e}")
        return None


async def handle_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle messages from source channel
    """
    message = update.channel_post or update.message
    
    # Check if message is from source channel
    if message.chat_id != SOURCE_CHANNEL_ID:
        return
    
    # Extract text from message
    text = message.text or message.caption or ""
    
    # Find vplink URLs in the message
    vplink_urls = extract_vplink_urls(text)
    
    if not vplink_urls:
        logger.info("No vplink URLs found in message")
        return
    
    logger.info(f"Found {len(vplink_urls)} vplink URL(s): {vplink_urls}")
    
    # Process each URL
    new_text = text
    for short_url in vplink_urls:
        # Step 1: Get destination URL using API 1
        destination_url = get_destination_url(short_url, VPLINK_API1_KEY)
        
        if not destination_url:
            logger.error(f"Failed to get destination URL for {short_url}")
            continue
        
        logger.info(f"Destination URL: {destination_url}")
        
        # Step 2: Create new short URL using API 2
        new_short_url = create_short_url(destination_url, VPLINK_API2_KEY)
        
        if not new_short_url:
            logger.error(f"Failed to create new short URL for {destination_url}")
            continue
        
        logger.info(f"New short URL: {new_short_url}")
        
        # Format the new URL to show without https:// prefix
        formatted_url = new_short_url.replace('https://', '').replace('http://', '')
        
        # Replace old URL with new formatted URL in text
        new_text = new_text.replace(short_url, formatted_url)
    
    # Post to target channel
    try:
        await context.bot.send_message(
            chat_id=TARGET_CHANNEL_ID,
            text=new_text,
            disable_web_page_preview=False
        )
        logger.info(f"Successfully posted to target channel")
    except Exception as e:
        logger.error(f"Error posting to target channel: {e}")


def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handler for channel posts
    application.add_handler(
        MessageHandler(
            filters.TEXT & (filters.ChatType.CHANNEL | filters.ChatType.SUPERGROUP),
            handle_channel_message
        )
    )
    
    # Start the bot
    logger.info("Bot started. Monitoring for vplink URLs...")
    application.run_polling(allowed_updates=["channel_post", "message"])


if __name__ == "__main__":
    main()
