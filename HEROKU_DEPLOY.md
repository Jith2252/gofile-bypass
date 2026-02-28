# Deploy to Heroku

## Prerequisites
1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Create a [Heroku account](https://signup.heroku.com/)

## Deployment Steps

### 1. Login to Heroku
```bash
heroku login
```

### 2. Create a new Heroku app
```bash
heroku create your-vplink-bot
```

### 3. Initialize Git repository (if not already done)
```bash
git init
git add .
git commit -m "Initial commit"
```

### 4. Deploy to Heroku
```bash
git push heroku master
```
Or if you're on main branch:
```bash
git push heroku main
```

### 5. Scale the worker dyno
```bash
heroku ps:scale worker=1
```

### 6. Check logs
```bash
heroku logs --tail
```

## Important Notes

- The bot is configured as a **worker** dyno (not web), so it won't use Heroku's web dyno hours
- Free Heroku tier gives you 550-1000 dyno hours per month
- All credentials are already in the code, but for better security, consider using Heroku Config Vars
- Make sure your bot is added as admin to both channels before deploying

## Using Config Vars (Optional - More Secure)

Instead of hardcoding credentials, you can use Heroku Config Vars:

```bash
heroku config:set TELEGRAM_BOT_TOKEN="7813395754:AAHXlegCoaNZyyZselLKTniZTcwXaMuyTZM"
heroku config:set SOURCE_CHANNEL_ID="-1002780245823"
heroku config:set TARGET_CHANNEL_ID="-1003744021205"
heroku config:set VPLINK_API1_KEY="556884f698b2fc4270c55310dfebc5483c081200"
heroku config:set VPLINK_API2_KEY="50cf08b699d0fd0988e27d5c76732c4ff46ab3f6"
```

Then update the bot code to read from environment variables.

## Troubleshooting

- **Bot not starting**: Check logs with `heroku logs --tail`
- **No dyno running**: Run `heroku ps:scale worker=1`
- **Check dyno status**: Run `heroku ps`
- **Restart app**: Run `heroku restart`
