# Deployment Guide (Render)

Follow these steps to deploy this bot on Render for free.

## Prerequisites
1. **GitHub Account**: Your code should be in a GitHub repository.
2. **MongoDB Atlas**: Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) and create a free cluster. Get your `MONGO_URI`.
3. **Telegram API Details**: Get your `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org).
4. **Bot Token**: Get your `BOT_TOKEN` from [@BotFather](https://t.me/BotFather) on Telegram.
5. **Admin ID**: Get your numeric Telegram User ID from [@userinfobot](https://t.me/userinfobot).

## Deploying on Render
1. Create an account on [Render.com](https://render.com).
2. Click on **New** -> **Web Service**.
3. Connect your GitHub account and select this repository (`FORWARDING-BOT`).
4. Set the following details:
   - **Name**: Give your bot a name.
   - **Environment**: Docker
   - **Instance Type**: Free
5. Scroll down to **Environment Variables** and add the following:
   - `API_ID`: Your API ID
   - `API_HASH`: Your API HASH
   - `BOT_TOKEN`: Your Bot Token
   - `MONGO_URI`: Your MongoDB connection string
   - `ADMIN_ID`: Your Telegram User ID
6. Click **Create Web Service**.

## Keeping it Alive 24/7
Render's free tier sleeps after 15 minutes. This bot includes a built-in web server to prevent this.
1. Once deployed, copy the Render URL (e.g., `https://your-bot-name.onrender.com`).
2. Go to [cron-job.org](https://cron-job.org) and create a free account.
3. Create a new cron job.
4. Paste your Render URL.
5. Set the execution schedule to **every 10 minutes**.
6. Save it. Your bot will now run 24/7 without sleeping!
