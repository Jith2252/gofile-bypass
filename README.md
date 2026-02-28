# Telegram VPLink Bot

A Telegram bot that monitors Channel A for vplink short URLs, retrieves destination URLs using VPLink API 1, reshortens them with VPLink API 2, and posts to Channel B.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure the Bot

Edit `telegram_vplink_bot.py` and update:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from [@BotFather](https://t.me/BotFather)
- `SOURCE_CHANNEL_ID`: Channel A ID (where messages come from)
- `TARGET_CHANNEL_ID`: Channel B ID (where to post processed messages)
- `VPLINK_API1_KEY`: Your first VPLink API key (for retrieving destination URLs)
- `VPLINK_API2_KEY`: Your second VPLink API key (for creating new short URLs)

### 3. Get Channel IDs

To get channel IDs, you can:
1. Forward a message from the channel to [@userinfobot](https://t.me/userinfobot)
2. Or add your bot to the channel and check the logs

### 4. Add Bot to Channels

1. Add your bot as an administrator to both Channel A and Channel B
2. Make sure the bot has these permissions:
   - Channel A: Read messages
   - Channel B: Post messages

### 5. VPLink API Setup

You need to configure the correct API endpoints based on VPLink documentation:
- Check VPLink API documentation for the correct endpoints
- Update `VPLINK_EXPAND_API` and `VPLINK_SHORTEN_API` URLs
- Verify the request/response format matches their API

## Running the Bot

```bash
python telegram_vplink_bot.py
```

The bot will:
1. Monitor Channel A for new messages
2. Detect vplink.in URLs in messages
3. Use API 1 to get the destination URL
4. Use API 2 to create a new short URL
5. Post the message with the new URL to Channel B

## Troubleshooting

- **Bot doesn't receive messages**: Make sure the bot is an admin in the source channel
- **Can't post to target channel**: Verify bot is admin in target channel with post permissions
- **API errors**: Check your VPLink API keys and endpoints
- **URL extraction fails**: Check the regex pattern matches your vplink URLs

## Notes

- The bot preserves the original message text and only replaces the URLs
- Multiple vplink URLs in one message are all processed
- Failed URL processing is logged but doesn't stop the bot
