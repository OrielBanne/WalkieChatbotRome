# Streamlit Cloud Deployment Guide

This guide will help you deploy the Rome Places Chatbot to Streamlit Cloud, making it accessible as a web app on any device including iPhone.

## Prerequisites

- GitHub account (you already have this ✅)
- Streamlit Cloud account (free)
- OpenAI API key

## Step 1: Sign Up for Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "Sign up" or "Continue with GitHub"
3. Authorize Streamlit to access your GitHub repositories

## Step 2: Deploy Your App

1. Click "New app" in Streamlit Cloud dashboard
2. Select your repository: `OrielBanne/WalkieChatbotRome`
3. Set the branch: `main`
4. Set the main file path: `src/app.py`
5. Click "Advanced settings" (optional)

## Step 3: Configure Secrets

This is CRITICAL - your OpenAI API key must be added as a secret:

1. In the deployment settings, find "Secrets"
2. Add your secrets in TOML format:

```toml
OPENAI_API_KEY = "sk-your-actual-api-key-here"
```

3. You can also add optional configuration:

```toml
OPENAI_API_KEY = "sk-your-actual-api-key-here"
LLM_MODEL = "gpt-3.5-turbo"
EMBEDDING_MODEL = "text-embedding-3-small"
```

## Step 4: Deploy

1. Click "Deploy!"
2. Wait 2-5 minutes for the app to build and deploy
3. You'll get a URL like: `https://walkiechatbotrome.streamlit.app`

## Step 5: Initial Setup

After deployment, you need to populate the knowledge base:

1. Open your deployed app
2. Go to the sidebar → "📚 Knowledge Base"
3. Add YouTube videos about Rome
4. Click "🔄 Rebuild Knowledge Base"
5. Wait for the rebuild to complete

## Step 6: Use on iPhone

### Option A: Browser Access
1. Open Safari on your iPhone
2. Navigate to your app URL
3. Use it directly in the browser

### Option B: Add to Home Screen (Recommended)
1. Open your app URL in Safari
2. Tap the Share button (square with arrow)
3. Scroll down and tap "Add to Home Screen"
4. Name it "Rome Places" or whatever you prefer
5. Tap "Add"
6. Now you have an app icon on your home screen!

## Troubleshooting

### App Won't Start
- Check that secrets are properly configured
- Verify OpenAI API key is valid
- Check the logs in Streamlit Cloud dashboard

### spaCy Model Error
- The app should auto-download the model
- If it fails, check the logs
- May need to wait a few minutes on first deployment

### Knowledge Base Empty
- You need to manually add videos and rebuild after deployment
- The vector store is not included in the repository (too large)
- Add at least 2-3 YouTube videos about Rome to get started

### Slow Performance
- Free tier has resource limits
- Consider upgrading to Streamlit Cloud Pro for better performance
- Reduce number of videos if needed

## Managing Your Deployment

### Update the App
1. Push changes to your GitHub repository
2. Streamlit Cloud will automatically redeploy
3. Changes appear in 1-2 minutes

### View Logs
1. Go to Streamlit Cloud dashboard
2. Click on your app
3. Click "Manage app" → "Logs"

### Reboot the App
1. Go to Streamlit Cloud dashboard
2. Click on your app
3. Click "Reboot app" if needed

## Cost Considerations

### Streamlit Cloud
- Free tier: 1 app, limited resources
- Pro tier: $20/month for more apps and resources

### OpenAI API
- Costs based on usage
- Embeddings: ~$0.0001 per 1K tokens
- GPT-3.5-turbo: ~$0.002 per 1K tokens
- Monitor usage in OpenAI dashboard

## Security Notes

- Never commit your `.env` file or API keys to GitHub
- Always use Streamlit Cloud secrets for sensitive data
- Rotate your API keys periodically
- Monitor API usage for unexpected spikes

## Support

- Streamlit Cloud docs: [docs.streamlit.io/streamlit-community-cloud](https://docs.streamlit.io/streamlit-community-cloud)
- Streamlit forum: [discuss.streamlit.io](https://discuss.streamlit.io)
- OpenAI docs: [platform.openai.com/docs](https://platform.openai.com/docs)

## Next Steps

After successful deployment:

1. Share your app URL with friends
2. Add more content sources (videos, websites, PDFs)
3. Customize the theme in `.streamlit/config.toml`
4. Monitor usage and costs
5. Consider adding authentication for private use

Enjoy your Rome Places Chatbot on the go! 🏛️📱
