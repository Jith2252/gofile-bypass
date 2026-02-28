import re
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import logging
import os
from dotenv import load_dotenv

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
    Retrieve the destination URL from vplink short URL using API 1
    """
    try:
        # Method 1: Using API (adjust based on vplink documentation)
        params = {
            'api': api_key,
            'url': short_url
        }
        response = requests.get(VPLINK_EXPAND_API, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Adjust based on actual API response structure
            return data.get('destination_url') or data.get('url')
        
        # Method 2: Follow redirects if API doesn't work
        logger.warning(f"API method failed, trying redirect method for {short_url}")
        response = requests.get(short_url, allow_redirects=True, timeout=10)
        return response.url
        
    except Exception as e:
        logger.error(f"Error getting destination URL for {short_url}: {e}")
        return None


def create_short_url(destination_url, api_key):
    """
    Create a new vplink short URL using API 2
    """
    try:
        # Adjust based on vplink API documentation
        params = {
            'api': api_key,
            'url': destination_url
        }
        response = requests.get(VPLINK_SHORTEN_API, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Adjust based on actual API response structure
            short_url = data.get('shortenedUrl') or data.get('short_url') or data.get('url')
            return short_url
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
        
        # Replace old URL with new URL in text
        new_text = new_text.replace(short_url, new_short_url)
    
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
